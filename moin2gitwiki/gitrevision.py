import typing

import attr

from .wikiindex import MoinEditEntry


@attr.s(kw_only=True, slots=True)
class GitExportStream:
    output: typing.BinaryIO = attr.ib()
    mark_number: int = attr.ib(default=1)
    last_commit_mark: int = attr.ib(default=None)
    branch: str = attr.ib(default="refs/heads/master")
    ctx = attr.ib(repr=False)

    def add_wiki_revision(
        self,
        revision: MoinEditEntry,
        content: bytes,
        name: str = None,
    ):
        if name is None:
            name = revision.page_name
        if content is not None:
            blob_ref = self.output_blob(content)
        if self.last_commit_mark is None:
            self.write_string(f"reset {self.branch}\n")
        self.write_string(f"commit {self.branch}\n")
        commit_ref = self.write_next_mark()
        self.write_changer("author", revision)
        self.write_changer("committer", revision)
        if revision.comment != "":
            self.output_data_string(f"{revision.comment}\n")
        else:
            if content is not None:
                self.output_data_string(f"Add/Update {name}\n")
            else:
                self.output_data_string(f"Delete {name}\n")
        if self.last_commit_mark is not None:
            self.write_string(f"from :{self.last_commit_mark}\n")
        if content is None:
            self.write_string(f"D {name}\n\n")
        else:
            self.write_string(f"M 100644 :{blob_ref} {name}\n\n")
        self.last_commit_mark = commit_ref
        self.ctx.logger.debug(f"Written commit {commit_ref}")

    def write_changer(self, what: str, revision: MoinEditEntry):
        self.write_string(
            f"{what} {revision.user.moin_name} <{revision.user.email}> {int(revision.edit_date.timestamp())} +0000\n",
        )

    def get_next_mark(self):
        mark = self.mark_number
        self.mark_number += 1
        return mark

    def write_next_mark(self):
        mark = self.get_next_mark()
        self.write_string(f"mark :{mark}\n")
        return mark

    def output_blob(self, content: bytes):
        self.output.write(b"blob\n")
        blob_ref = self.write_next_mark()
        self.output_data(content)
        return blob_ref

    def output_data(self, content: bytes):
        self.write_string(f"data {len(content)}\n")
        self.output.write(content)

    def write_string(self, string: str):
        self.output.write(string.encode("utf-8"))

    def output_data_string(self, string: str):
        self.output_data(string.encode("utf-8"))

    def end_stream(self):
        self.write_string(f"reset {self.branch}\n")
        self.write_string(f"from :{self.last_commit_mark}\n")


# end
