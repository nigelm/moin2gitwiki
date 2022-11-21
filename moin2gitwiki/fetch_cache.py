import json
import uuid
from pathlib import Path

import attr
import requests


@attr.s(kw_only=True, slots=True)
class FetchCache:
    """
    Implements a local cache for URLs which can be persistant between runs

    Basic cache directory which contains an `index.json` file with a table of
    URLs and the cache file they map to.  Has zero intelligence - assumes
    everything can be cached for ever - which is reasonable considering the
    things we request via the cache.

    Attributes:
        cache_directory:    Path of the cache directory
        index_path:         Path of the cache index file - normally `index.json` within `cache_directory`
        cache_map:          The dict mapping URLs to filenames within the cache
        ctx:                Context object (used for logging etc)

    """

    cache_directory: Path = attr.ib()
    index_path: Path = attr.ib()
    cache_map: dict = attr.ib(default={})
    ctx = attr.ib(repr=False)
    session: requests.sessions.Session = attr.ib()

    @classmethod
    def initialise_cache(cls, cache_directory: Path, ctx):
        """
        Build and preload the cache object

        Creates if needed the passed `cache_directory`, and either loads the
        existing `index.json` or writes an empty one.
        """
        # ensure directory exists
        cache_directory.mkdir(mode=0o777, parents=True, exist_ok=True)
        # ensure we have it as an absolute path
        cache_directory = cache_directory.resolve(strict=True)
        #
        # load the index should it exist
        index_path = cache_directory.joinpath("index.json")
        cache_map = {}
        try:
            cache_map = json.loads(index_path.read_text())
        except (OSError, ValueError):
            # if anything goes wrong then we just ignore it and
            # write out a blank cache file
            cache_map = {}
            cls.write_index(index_path=index_path, cache_map=cache_map)
        #
        # build the requests session
        session = requests.Session()
        if len(ctx.proxies) > 0:
            session.proxies.update(ctx.proxies)
        #
        # build and return the object
        ctx.logger.debug(f"Building cache in directory {cache_directory}")
        return cls(
            cache_directory=cache_directory,
            index_path=index_path,
            cache_map=cache_map,
            ctx=ctx,
            session=requests.Session(),
        )

    @classmethod
    def write_index(cls, index_path: Path, cache_map: dict):
        """Write the cache index out to disk"""
        index_path.write_text(json.dumps(cache_map, indent=2))

    def fetch(self, url: str) -> str:
        """Fetch a URL, from the cache if there, otherwise put a copy into cache"""
        #
        # is this in the cache already
        if url in self.cache_map:
            item_name = self.cache_map[url]
            item_path = self.cache_directory.joinpath(item_name)
            try:
                content = item_path.read_text()
                self.ctx.logger.debug(f"Retrieved {url} from cache")
                return content
            except OSError:
                pass  # just move on to refetch
        #
        # if you get here then the url is either not in the cache or we
        # failed to retrieve it off disk - in either case we just fetch it
        item_name = uuid.uuid4().hex
        item_path = item_path = self.cache_directory.joinpath(item_name)
        self.ctx.logger.debug(f"Fetching {url}")
        try:
            response = requests.get(url, proxies=self.ctx.proxies)
            content = response.text
        except OSError:
            self.ctx.logger.warning(f"No response to {url}")
            content = ""
        #
        # write to cache
        item_path.write_text(content)
        self.ctx.logger.debug(f"Wrote {url} to {item_name}")
        #
        # update cache index
        self.cache_map[url] = item_name
        self.write_index(index_path=self.index_path, cache_map=self.cache_map)
        #
        # return response content
        return content


# end
