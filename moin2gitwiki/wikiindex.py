import os
import re
from datetime import datetime
from datetime import timedelta
from typing import Tuple

import attr

from .users import Moin2GitUser


@attr.s(kw_only=True, frozen=True, slots=True)
class MoinEditEntry:
    """
    Represents a Moin page revision

    There are multiple revisions per page.

    Attributes:
        edit_date: The date of the edit
        page_revision: The revision id of this revision - a string of a zero padded number
        edit_type: Moin edit type
        page_name: The name of the page from the index file
        previous_page_name: The name the page previously had if renamed
        page_path: The name on the filesystem of the page
        attachment: attachment field - not used
        comment: comment filed - only used for git comments
        user: the mapped moin user
        ctx: Context - there for moin_path and logging

    """

    edit_date: datetime = attr.ib()
    page_revision: str = attr.ib()
    edit_type: str = attr.ib()
    page_name: str = attr.ib()
    previous_page_name: str = attr.ib(default=None)
    page_path: str = attr.ib()
    attachment: str = attr.ib(default="")
    comment: str = attr.ib(default="")
    user: Moin2GitUser = attr.ib()
    ctx = attr.ib(repr=False)

    def wiki_content_path(self):
        """The file pathname of the revision file"""
        return self.ctx.moin_data.joinpath(
            "pages",
            self.page_path,
            "revisions",
            self.page_revision,
        )

    def wiki_content_bytes(self):
        """The content of the wiki revision retrieved as a byte string"""
        lines = self.wiki_content()
        if lines is None:
            return lines
        else:
            lines.append("")
            return "\n".join(lines).encode("utf-8")

    def wiki_content(self):
        """The content of the wiki revision as an array of strings"""
        lines = []
        try:
            lines = self.wiki_content_path().read_text().splitlines(keepends=False)
        except OSError:
            lines = None
        return lines

    def unescape(self, thing: str) -> str:
        """Uescape a wiki name - translate (2f) to /"""
        return thing.replace("(2f)", "/")

    def page_name_unescaped(self) -> str:
        """Unescape the page name"""
        return self.unescape(self.page_name)

    def page_path_unescaped(self) -> str:
        """Unescape the page path"""
        return self.unescape(self.page_path)

    def markdown_transform(self, thing: str) -> str:
        """Translates the (2f) to _ for use in Markdown page names"""
        return thing.replace("(2f)", "_")

    def markdown_page_path(self):
        """Page path translated"""
        return self.markdown_transform(self.page_name) + ".md"

    def markdown_page_name(self):
        """Page name translated"""
        return self.markdown_transform(self.page_name)


@attr.s(kw_only=True, frozen=True, slots=True)
class MoinEditEntries:
    """
    A sorted collection of Moin revision entry objects
    """

    entries: list = attr.ib()
    ctx = attr.ib(repr=False)

    @classmethod
    def create_edit_entries(cls, ctx):
        pages_dir = os.path.join(ctx.moin_data, "pages")
        pages = os.listdir(pages_dir)
        epoch = datetime(1970, 1, 1)
        entries = []
        for page in pages:
            ctx.logger.debug(f"Reading page {page}")
            edit_log_file = os.path.join(pages_dir, page, "edit-log")
            # read the edit-log file
            try:
                with open(edit_log_file) as f:
                    edit_log_data = f.readlines()
            except OSError:
                ctx.logger.warning(f"No edit-log for page {page}")
                continue
            # read the lines in the edit-log file
            previous_page_name = None
            for edit_line in edit_log_data:
                if not re.match(r"\d{15}", edit_line):  # check its an edit entry
                    continue
                # extract the fields out the edit entry
                edit_fields = edit_line.rstrip("\n").split("\t")
                edit_date = epoch + timedelta(microseconds=int(edit_fields[0]))
                edit_type = edit_fields[2]
                if edit_type in ("SAVENEW", "SAVE"):
                    entry = MoinEditEntry(
                        edit_date=edit_date,
                        page_revision=edit_fields[1],
                        edit_type=edit_type,
                        page_name=edit_fields[3],
                        previous_page_name=previous_page_name,
                        attachment=edit_fields[7],
                        comment=edit_fields[8],
                        page_path=page,
                        user=ctx.users.get_user_by_id_or_anonymous(edit_fields[6]),
                        ctx=ctx,
                    )
                    entries.append(entry)
        ctx.logger.debug("Sorting edit entries")
        entries.sort(key=lambda x: x.edit_date)
        ctx.logger.debug("Building edit entries object")
        return cls(
            entries=entries,
            ctx=ctx,
        )

    def count(self) -> int:
        return len(self.entries)

    def create_home_page(self) -> Tuple[MoinEditEntry, str]:
        """Builds a synthetic home page to link all the wiki entries together"""
        revision = MoinEditEntry(
            edit_date=datetime.now(),
            page_revision="1",
            edit_type="SAVENEW",
            page_name="Home",
            attachment="",
            comment="Synthetic Home Page",
            page_path="Home",
            user=self.ctx.users.get_user_by_id_or_anonymous("0"),
            ctx=self.ctx,
        )
        pages = set()
        for entry in self.entries:
            if entry.page_name.find("(2f)") < 0:
                pages.add(entry.markdown_page_name())
        content = "# Home Page\n\n"
        for item in sorted(pages):
            content += f"- [{item}]({item})\n"
        content += "\n----\n"

        return (revision, content)


# end
