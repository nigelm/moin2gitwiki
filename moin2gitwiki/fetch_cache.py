import json
import os
import uuid

import attr
import requests


@attr.s(kw_only=True, slots=True)
class FetchCache:
    cache_directory: str = attr.ib()
    index_path: str = attr.ib()
    cache_map: dict = attr.ib(default={})
    ctx = attr.ib(repr=False)

    @classmethod
    def initialise_cache(cls, cache_directory: str, ctx):
        # ensure directory exists
        os.makedirs(cache_directory, mode=0o777, exist_ok=True)
        #
        # load the index should it exist
        index_path = os.path.join(cache_directory, "index.json")
        cache_map = {}
        try:
            with open(index_path) as f:
                cache_map = json.load(f)
        except (OSError, ValueError):
            # if anything goes wrong then we just ignore it and
            # write out a blank cache file
            cls.write_index(index_path=index_path, cache_map=cache_map)
        #
        # build and return the object
        ctx.logger.debug(f"Building cache in directory {cache_directory}")
        return cls(
            cache_directory=cache_directory,
            index_path=index_path,
            cache_map=cache_map,
            ctx=ctx,
        )

    @classmethod
    def write_index(cls, index_path: str, cache_map: dict):
        with open(index_path, "w") as f:
            json.dump(cache_map, f, indent=2)

    def fetch(self, url: str):
        #
        # is this in the cache already
        if url in self.cache_map:
            item_name = self.cache_map[url]
            item_path = os.path.join(self.cache_directory, item_name)
            try:
                with open(item_path) as f:
                    content = f.readlines()
                self.ctx.logger.debug(f"Retrieved {url} from cache")
                return content
            except OSError:
                pass  # just move on to refetch
        #
        # if you get here then the url is either not in the cache or we
        # failed to retrieve it off disk - in either case we just fetch it
        item_name = uuid.uuid4().hex
        item_path = os.path.join(self.cache_directory, item_name)
        self.ctx.logger.debug(f"Fetching {url}")
        try:
            response = requests.get(url)
            content = response.text.splitlines(keepends=True)
        except OSError:
            self.ctx.logger.warning(f"No response to {url}")
            content = ["\n"]
        #
        # write to cache
        with open(item_path, "w") as f:
            f.writelines(content)
        self.ctx.logger.debug(f"Wrote {url} to {item_name}")
        #
        # update cache index
        self.cache_map[url] = item_name
        self.write_index(index_path=self.index_path, cache_map=self.cache_map)
        #
        # return response as a set of lines
        return content


# end
