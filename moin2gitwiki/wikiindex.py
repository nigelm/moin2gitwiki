import os
import re
from datetime import datetime
from datetime import timedelta

import attr

from .users import Moin2GitUser


@attr.s(kw_only=True, frozen=True, slots=True)
class MoinEditEntry:
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

    edit_date: datetime = attr.ib()
    page_revision: str = attr.ib()
    edit_type: str = attr.ib()
    page_name: str = attr.ib()
    page_path: str = attr.ib()
    attachment: str = attr.ib(default="")
    comment: str = attr.ib(default="")
    user: Moin2GitUser = attr.ib()
    ctx = attr.ib(repr=False)

    def wiki_content_path(self):
        return os.path.join(
            self.ctx.moin_data,
            "pages",
            self.page_path,
            "revisions",
            self.page_revision,
        )

    def wiki_content_bytes(self):
        lines = self.wiki_content()
        if lines is None:
            return lines
        else:
            return "".join(lines).encode("utf-8")

    def wiki_content(self):
        lines = []
        try:
            with open(self.wiki_content_path()) as f:
                lines = f.readlines()
        except OSError:
            lines = None
        return lines

    def unescape(self, thing):
        return thing.replace("(2f)", "/")

    def page_name_unescaped(self):
        return self.unescape(self.page_name)


@attr.s(kw_only=True, frozen=True, slots=True)
class MoinEditEntries:
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


# end
