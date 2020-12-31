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
    link_table: dict = attr.ib()
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
    ignored_moin_macros = (
        "AttachInfo",
        "AttachList",
        "DateTime",
        "FormCheckbox",
        "FormFooter",
        "FormHeader",
        "FormRadio",
        "FormSelect",
        "FormSubmit",
        "FormText",
        "FormTextarea",
        "FormUpload",
        "FullSearch",
        "GetText",
        "GrabIt",
        "Icon",
        "IncVar",
        "Include",
        "MailTo",
        "Navigation",
        "PageList",
        "RandomPage",
        "RandomQuote",
        "StatsChart",
        "TableOfContents",
    )

    @classmethod
    def create_translator(cls, ctx, cache_directory: Path, link_table: dict):
        #
        # Build a fetch cache
        fetch_cache = FetchCache.initialise_cache(
            cache_directory=cache_directory,
            ctx=ctx,
        )
        return cls(fetch_cache=fetch_cache, link_table=link_table, ctx=ctx)

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
            match = self.moin_macro_pattern.search(line)
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
        elif macro_name in self.ignored_moin_macros:
            line = self.moin_macro_pattern.sub("", line)
        else:
            self.ctx.logger.warning(f"Unknown macro '{macro_name}'")
        return [line]

    def process_include_url_content_wiki(self, revision: MoinEditEntry, params: str):
        url = params.strip().replace("%s", revision.unescape(revision.page_name))
        return self.fetch_cache.fetch(url)
