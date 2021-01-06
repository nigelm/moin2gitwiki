import typing

import attr

from .wikiindex import MoinEditEntry


@attr.s(kw_only=True, slots=True)
class GitExportStream:
    """
    Output a git fast-export formatted stream for each revision

    This object handles the state information to output the git commits for
    the Moin wiki revisions.

    Attributes:
        output:     The output file stream of git fast-export commands
        mark_number: The current git mark number
        last_commit_mark: The git mark number of the last commit
        ctx:        The context object - used for `logger` and `user` mapping

    """

    output: typing.BinaryIO = attr.ib()
    mark_number: int = attr.ib(default=1)
    last_commit_mark: int = attr.ib(default=None)
    branch: str = attr.ib(default="refs/heads/master")
    ctx = attr.ib(repr=False)

    def add_wiki_revision(
        self,
        revision: MoinEditEntry,
        content: bytes,
    ):
        """
        Add a wiki revision as a git commit

        Parameters:
            revision:   A wiki revision object
            content:    The content of the wiki object, after translation, as bytes

        """
        name = revision.markdown_page_path()
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
            if (
                revision.previous_page_name is not None
                and revision.previous_page_name != revision.page_name
            ):
                self.write_string(
                    f"D {revision.markdown_transform(revision.previous_page_name)}\n",
                )
            self.write_string(f"M 100644 :{blob_ref} {name}\n\n")
        self.last_commit_mark = commit_ref
        self.ctx.logger.debug(f"Written commit {commit_ref}")

    def write_changer(self, what: str, revision: MoinEditEntry):
        """
        Add an author/committer entry with date

        Parameters:
            what:       Normally either `committer` or `author`
            revision:   A wiki revision object

        """
        self.write_string(
            f"{what} {revision.user.moin_name} <{revision.user.email}> {int(revision.edit_date.timestamp())} +0000\n",
        )

    def get_next_mark(self):
        """
        Increment and return the mark number
        """
        mark = self.mark_number
        self.mark_number += 1
        return mark

    def write_next_mark(self):
        """
        Write out the next mark number
        """
        mark = self.get_next_mark()
        self.write_string(f"mark :{mark}\n")
        return mark

    def output_blob(self, content: bytes):
        """
        Output a blob object

        Parameters:
            content:    The content of the blob, as bytes

        """
        self.output.write(b"blob\n")
        blob_ref = self.write_next_mark()
        self.output_data(content)
        return blob_ref

    def output_data(self, content: bytes):
        """
        Output a set of data bytes

        Parameters:
            content:    The content of data, as bytes

        """
        self.write_string(f"data {len(content)}\n")
        self.output.write(content)

    def write_string(self, string: str):
        """
        Write a string out with utf-8 encoding into bytes
        """
        self.output.write(string.encode("utf-8"))

    def output_data_string(self, string: str):
        """
        Write a string out as a data object with utf-8 encoding into bytes
        """
        self.output_data(string.encode("utf-8"))

    def end_stream(self):
        """
        Write the end of stream information
        """
        self.write_string(f"reset {self.branch}\n")
        self.write_string(f"from :{self.last_commit_mark}\n")


# end
