from pathlib import Path
from typing import Optional

import attr
from bs4 import BeautifulSoup
from furl import furl

from .fetch_cache import FetchCache
from .wikiindex import MoinEditEntry


@attr.s(kw_only=True, frozen=True, slots=True)
class Moin2Markdown:
    #
    # -- attributes
    fetch_cache: FetchCache = attr.ib()
    url_prefix: furl = attr.ib()
    link_table: dict = attr.ib()
    ctx = attr.ib(repr=False)

    @classmethod
    def create_translator(
        cls,
        ctx,
        cache_directory: Path,
        url_prefix: str,
        link_table: dict,
    ):
        #
        # Build a fetch cache
        fetch_cache = FetchCache.initialise_cache(
            cache_directory=cache_directory,
            ctx=ctx,
        )
        return cls(
            fetch_cache=fetch_cache,
            link_table=link_table,
            url_prefix=furl(url_prefix),
            ctx=ctx,
        )

    def retrieve_and_translate(self, revision: MoinEditEntry) -> Optional[str]:
        # check if this revision has any content...
        lines = revision.wiki_content()
        if lines is None:
            return None
        else:
            target = self.url_prefix.copy()
            target /= revision.page_path_unescaped()
            target.args["action"] = "recall"
            target.args["rev"] = revision.page_revision
            content = self.fetch_cache.fetch(target.url)
            main_content = self.extract_content_section(content)
            return main_content

    def extract_content_section(self, html: str) -> str:
        soup = BeautifulSoup(html, "html.parser")
        content = soup.find(id="content").contents
        return content


# end
