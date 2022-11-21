"""
moin2gitwiki Command Line Handling

Documentation is in the commands part of the documentation - the general
internals handling does not parse click decorators very well :-(

"""
import os
import subprocess
import sys
from pathlib import Path

import click

from . import __version__
from .context import Moin2GitContext
from .gitrevision import GitExportStream
from .moin2markdown import Moin2Markdown
from .wikiindex import MoinEditEntries


# -----------------------------------------------------------------------
@click.group()
@click.option("--debug/--no-debug", default=False, envvar="MOIN2GIT_DEBUG")
@click.option("--verbose/--no-verbose", default=False, envvar="MOIN2GIT_VERBOSE")
@click.option("--syslog/--no-syslog", default=False, envvar="MOIN2GIT_SYSLOG")
@click.option(
    "--moin-data",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    envvar="MOIN2GIT_DATA",
)
@click.option(
    "--user-map",
    type=click.Path(exists=True, file_okay=True, dir_okay=False),
    envvar="MOIN2GIT_USERS",
)
@click.option("--proxy", multiple=True, default=[], envvar="MOIN2GIT_PROXY")
@click.version_option(__version__)
@click.pass_context
def moin2gitwiki(ctx, syslog, verbose, debug, moin_data, user_map, proxy):
    """
    MoinMoin To Git Wiki Tools Command Line Utility

    Converts a MoinMoin wiki into a git repository populated with Markdown
    formatted pages, set up for use on a git based wiki such as the built in
    wiki for `gitea`, `github` or `gitlab`

    This parses the users and the revision structure from the MoinMoin data
    filesystem.  However converting the wiki markup was found to be best done
    by converting the output HTML using `pandoc`.

    The utility requires `git` and `pandoc` commands to be available in the
    path.

    #### Environment Variables

    The common options can also be set by use of environment variables:

    - `--debug` - `MOIN2GIT_DEBUG` - Output debugging logging

    - `--verbose` - `MOIN2GIT_VERBOSE` - Output verbose logging

    - `--syslog` - `MOIN2GIT_SYSLOG` - Send logging to syslog

    - `--moin-data` - `MOIN2GIT_DATA` - Data directory for moin

    - `--user-map` - `MOIN2GIT_USERS` - User map for moin - see the `save-users` command for info

    - `cache-directory` - `MOIN2GIT_CACHE` - Directory for moin component fetches.
      This defaults to `_cache` in the current directory.

    #### Help

    Running the ``moin2gitwiki`` command on its own will show some help
    information.

    """
    # this is to work around https://bugs.launchpad.net/beautifulsoup/+bug/1471755
    # see https://github.com/nigelm/moin2gitwiki/issues/3
    sys.setrecursionlimit(4000)

    ctx.obj = Moin2GitContext.create_context(
        syslog=syslog,
        debug=debug,
        verbose=verbose,
        moin_data=moin_data,
        user_map=user_map,
        proxies=proxy,
    )


# -----------------------------------------------------------------------
@moin2gitwiki.command()
@click.pass_obj
def check(ctx):
    """A minimal check to see if we run in this environment"""
    # we may improve on this...
    click.echo("System check identified no issues")
    ctx.logger.debug("check complete")


# -----------------------------------------------------------------------
@moin2gitwiki.command()
@click.argument("filename", type=click.Path(file_okay=True, dir_okay=False))
@click.pass_obj
def save_users(ctx, filename):
    """
    Write the user map out to a file

    This writes all the users found in the wiki out to a JSON file. This can
    then be modified, if required, and used as the input to the `--user-map`
    option - typically this would be to fix any email address or name issues.

    These user entries are used to set the author of git commits within the
    output repository.

    The file format is an JSON file consisting of an array of user records,
    which each look like:-

        {
            "email": "user@example.com",
            "moin_id": "1358271613.26.36417",
            "moin_name": "SomeUser"
        },

    """
    ctx.users.save_users_to_file(filename)


# -----------------------------------------------------------------------
@moin2gitwiki.command()
@click.option(
    "--cache-directory",
    default="_cache",
    envvar="MOIN2GIT_CACHE",
)
@click.option(
    "--url-prefix",
    "--prefix",
    default="http://localhost/jrtwiki/",
    envvar="MOIN2GIT_PREFIX",
)
@click.option("--home-page/--no-home-page", default=True)
@click.argument(
    "destination",
    type=click.Path(exists=False, file_okay=False, dir_okay=True),
)
@click.pass_obj
def fast_export(ctx, cache_directory, url_prefix, home_page, destination):
    """
    Git fast-export all the revisions in the wiki into markdown git wiki form

    Named for the `git fast-export` command, although it actually builds a new
    git repository and then translates each revision at a time into a command
    stream for `git-fast-import` on that new repository.  After all pages and
    revisions have been processed the new git wiki repo instance is garbage
    collected  (to compress all the revisions into a more compact set of git
    packs) and finally checked out.

    Page names are slightly modified - the "(2f)" seen in wiki file names
    (which is normally displayed as a `/` character) are changed to
    underscores.  Internal links are remapped - however if a link goes within
    the wiki namespace to something that was not found in the wiki (this may
    include attachments which are not currently bought across), then the link
    is deleted (although the link text is left).

    Although the filesystem data is read to derive the revision and history
    information, the actual page transformation is done by retrieving the
    page html from its webserver, cutting the content div out of that html,
    doing a few simplifications and translations (specifcially images
    corresponding to emojis are converted to emoji forms).  This HTML is then
    pass through pandoc to get a markdown (specifically github flavoured
    markdown).

    """
    # cwd = Path.cwd()
    destination = Path(destination)
    if destination.exists():
        raise SystemExit(f"Destination path {destination} already exists.")
    #
    # build your initial revision set from the wiki data
    revisions = MoinEditEntries.create_edit_entries(ctx=ctx)
    click.echo(click.style(f"Read {revisions.count()} wiki revisions", fg="green"))
    #
    # build the translator
    translator = Moin2Markdown.create_translator(
        ctx=ctx,
        cache_directory=Path(cache_directory),
        url_prefix=url_prefix,
        revisions=revisions,
    )
    #
    # build the output git instance
    destination.mkdir(mode=0o755)
    os.chdir(destination)
    subprocess.run(["git", "init"])
    with subprocess.Popen(["git", "fast-import"], stdin=subprocess.PIPE) as gitstream:
        export = GitExportStream(output=gitstream.stdin, ctx=ctx)
        with click.progressbar(revisions.entries) as entries:
            for revision in entries:
                content = translator.retrieve_and_translate(revision=revision)
                export.add_wiki_revision(
                    revision=revision,
                    content=content,
                )
        if home_page:
            revision, content = revisions.create_home_page()
            export.add_wiki_revision(revision=revision, content=content.encode("utf-8"))
        export.end_stream()
    subprocess.run(["git", "gc", "--aggressive"])  # pack it
    subprocess.run(["git", "checkout", "master"])  # check out the data


# -----------------------------------------------------------------------
@moin2gitwiki.command()
@click.option(
    "--cache-directory",
    default="_cache",
    envvar="MOIN2GIT_CACHE",
)
@click.option(
    "--url-prefix",
    "--prefix",
    default="http://localhost/jrtwiki/",
    envvar="MOIN2GIT_PREFIX",
)
@click.argument("page", required=True, type=str)
@click.argument("version", required=True, type=int)
@click.pass_obj
def translate_page(ctx, cache_directory, url_prefix, page, version):
    """
    Fetch a single page revision and translate to Markdown

    The first argument is a page name, the second an integer revision.

    The translation process is as described for the `fast-export` command.
    """
    #
    # build your initial revision set from the wiki data
    revisions = MoinEditEntries.create_edit_entries(ctx=ctx)
    click.echo(click.style(f"Read {revisions.count()} wiki revisions", fg="green"))
    #
    # build the translator
    translator = Moin2Markdown.create_translator(
        ctx=ctx,
        cache_directory=Path(cache_directory),
        url_prefix=url_prefix,
        revisions=revisions,
    )
    #
    # find the page and translate it
    for revision in revisions.entries:
        if revision.page_name == page and int(revision.page_revision) == version:
            content = translator.retrieve_and_translate(revision=revision)
            print(content.decode("utf-8"))


# -----------------------------------------------------------------------
# end
