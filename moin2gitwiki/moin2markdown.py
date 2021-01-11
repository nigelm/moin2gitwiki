import re
import subprocess
from pathlib import Path
from typing import Optional

import attr
from bs4 import BeautifulSoup
from furl import furl

from .fetch_cache import FetchCache
from .wikiindex import MoinEditEntry


def is_a_linemark_para(tag):
    return (
        tag.name == "p"
        and tag.has_attr("class")
        and re.match(r"line\\d+", tag["class"][0])
    )


@attr.s(kw_only=True, frozen=True, slots=True)
class Moin2Markdown:
    """
    Conversion object to convert MoinMoin wiki markup to Markdown

    Attributes:
        fetch_cache:    A FetchCache object used to retrieve URLs
        url_prefix:     The URL prefix of the Moin wiki web presence
        link_table:     A mapping of Moin unescaped names to page names
        ctx:            Context object - logger and user mapping etc
    """

    #
    # -- attributes
    fetch_cache: FetchCache = attr.ib()
    url_prefix: furl = attr.ib()
    link_table: dict = attr.ib()
    ctx = attr.ib(repr=False)
    #
    # smiley mapping
    smiley_map = {
        "X-(": ":rage:",
        ":(": ":confused:",
        ";)": ":wink:",
        ":-?": ":stuck_out_tongue:",
        ":-(": ":frowning_face:",
        ";-)": ":wink:",
        "{X}": ":x:",
        "{3}": ":three:",
        ":D": ":grin:",
        ":)": ":slightly_smiling_face:",
        "/!\\": ":warning:",
        ":\\": ":confounded:",
        ":-)": ":smiley:",
        "|-)": ":pensive:",
        "{i}": ":information_source:",
        "{*}": ":star:",
        "<:(": ":mask:",
        "B)": ":sunglasses:",
        "<!>": ":warning:",
        ">:>": ":imp:",
        "B-)": ":nerd_face:",
        "(./)": ":white_check_mark:",
        "{1}": ":one:",
        "{o}": ":star:",
        ":o": ":anguished:",
        ":))": ":rofl:",
        "(!)": ":bulb:",
        "|)": ":monocle_face:",
        ":-))": ":rofl:",
        "{OK}": ":ok:",
        "{2}": ":two:",
    }

    @classmethod
    def create_translator(
        cls,
        ctx,
        cache_directory: Path,
        url_prefix: str,
        link_table: dict,
    ):
        """
        Build a translator object

        Parameters:
            ctx:            Context object (logger etc)
            cache_directory:    Path object for the cache directory
            url_prefix:     The base URL for the MoinMoin wiki
            link_table:     A translation table for wiki links

        """
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
        """
        Retrieve a wiki revision, and translate it to markdown

        Parameters:
            revision:    The wiki revision object for the revision we want

        If the revision maps to an empty object - ie it deleted the page, or
        similar, then a None object is returned.

        """
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
            translated = self.translate(main_content)
            return translated

    def extract_content_section(self, html: str) -> str:
        """
        Extract the content part of the HTML, and simplify

        Parameters:
            html:    The html data

        Pulls out the content div and simplifies the  HTML.
        Simplification consists of:-

        - stripping out redundant anchor spans
        - remove the additional line marking paragraphs
        - rewrite a/hrefs
        - strip internal a/hrefs that have no existng target
        - strip class attributes from links
        - remap any emoji img to the emoji sequence

        """
        soup = BeautifulSoup(html, "html.parser")
        content = soup.find(id="content")
        #
        # now strip out excess rubbish - anchor spans
        for tag in content.find_all(class_="anchor"):
            tag.decompose()
        #
        # Remove dead <p class="line???"> with no closer
        for tag in content.find_all(is_a_linemark_para):
            tag.unwrap()
        #
        # now find all the links, and if within the wiki, rewrite
        for tag in content.find_all("a"):
            target = tag["href"]
            if target:
                url = self.url_prefix.copy().join(target)
                if url.url.startswith(self.url_prefix.url):
                    new_url = url.url[len(self.url_prefix.url) :]
                    if new_url in self.link_table:
                        tag["href"] = self.link_table[new_url]
                    else:
                        tag.unwrap()
            #
            # strip any class attributes on links - tend to upset the translator
            if tag.has_attr("class"):
                del tag["class"]
        #
        # This might not always work but removing all <div>s makes output cleaner
        for tag in content.find_all("div"):
            tag.unwrap()
        #
        # now find all the images and see if they map to emojis
        # MoinMoin puts the emoji code in the title, so will purely match on that
        for tag in content.find_all("img"):
            if tag.has_attr("title") and tag["title"] in self.smiley_map:
                tag.replace_with(" " + self.smiley_map[tag["title"]] + " ")

        return "".join([str(x) for x in content.contents])

    def translate(self, input: str) -> str:
        """Translate HTML to Github Flavoured Markdown using pandoc"""
        process = subprocess.Popen(
            ["pandoc", "-f", "html", "-t", "gfm"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
        )
        (output, _) = process.communicate(input.encode("utf-8"))
        return output.decode("utf-8")


# end
