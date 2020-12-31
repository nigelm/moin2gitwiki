import re
from pathlib import Path
from typing import Optional

import attr

from .fetch_cache import FetchCache
from .wikiindex import MoinEditEntry


@attr.s(kw_only=True, frozen=True, slots=True)
class Moin2Markdown:
    #
    # -- attributes
    fetch_cache: FetchCache = attr.ib()
    ctx = attr.ib(repr=False)
    #
    # -- regular expressions used
    moin_macro_pattern = re.compile(
        r"""
                (?:\<\<|\[\[)                           # opening part
                (?P<macroname>  [A-Za-z0-9]+        )   # macro name
                \(                                      # opening parens
                (?P<params>     [^\]]*              )   # parameters
                \)                                      # closing parens
                (?:\>\>|\]\])                           # closing part
                """,
        re.VERBOSE,
    )

    @classmethod
    def create_translator(cls, ctx, cache_directory=Path):
        #
        # Build a fetch cache
        fetch_cache = FetchCache.initialise_cache(
            cache_directory=cache_directory,
            ctx=ctx,
        )
        return cls(fetch_cache=fetch_cache, ctx=ctx)

    def retrieve_and_translate(self, revision: MoinEditEntry) -> Optional[bytes]:
        lines = revision.wiki_content()
        if lines is None:
            return None
        else:
            lines = self.translate(revision, lines)
            return "".join(lines).encode("utf-8")

    def translate(self, revision: MoinEditEntry, lines: list) -> list:
        lines = self.pre_process_lines(revision=revision, lines=lines)
        return lines

    def pre_process_lines(self, revision: MoinEditEntry, lines: list) -> list:
        new_lines = []
        for line in lines:
            # handle macro inserts
            match = re.search(self.moin_macro_pattern, line)
            if match is not None:
                new_lines.extend(
                    self.process_macro(
                        revision=revision,
                        line=line,
                        macro_name=match.group("macroname"),
                        params=match.group("params"),
                    ),
                )
            else:
                new_lines.append(line)
        return new_lines

    def process_macro(
        self,
        revision: MoinEditEntry,
        line: str,
        macro_name: str,
        params: str,
    ):
        if macro_name == "IncludeUrlContentWiki":
            return self.process_include_url_content_wiki(revision, params=params)
        else:
            self.ctx.logger.warning(f"Unknown macro {macro_name}")
            return [line]

    def process_include_url_content_wiki(self, revision: MoinEditEntry, params: str):
        url = params.strip().replace("%s", revision.unescape(revision.page_name))
        return self.fetch_cache.fetch(url)
