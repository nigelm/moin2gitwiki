import os
import subprocess
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
@click.version_option(__version__)
@click.pass_context
def moin2gitwiki(ctx, syslog, verbose, debug, moin_data, user_map):
    """MoinMoin To Git Wiki Tools Command Line Utility

    The other global options are related to the logging setup.

    #### Environment Variables

    The common options can also be set by use of environment variables:

    - `--debug` - `MOIN2GIT_DEBUG` - Output debugging logging
    - `--verbose` - `MOIN2GIT_VERBOSE` - Output verbose logging
    - `--syslog` - `MOIN2GIT_SYSLOG` - Send logging to syslog
    - `--moin-data` - `MOIN2GIT_DATA` - Data directory for moin
    - `--user-map` - `MOIN2GIT_USERS` - User map for moin
    - `--cache` - `MOIN2GIT_CACHE` - Directory for moin component fetches

    #### Help

    Running the ``moin2gitwiki`` command on its own will show some help
    information.

    """
    ctx.obj = Moin2GitContext.create_context(
        syslog=syslog,
        debug=debug,
        verbose=verbose,
        moin_data=moin_data,
        user_map=user_map,
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
    """Write the user map out to a file"""
    ctx.users.save_users_to_file(filename)


# -----------------------------------------------------------------------
@moin2gitwiki.command()
@click.pass_obj
def list_revisions(ctx):
    """List all the revisions in the wiki"""
    revisions = MoinEditEntries.create_edit_entries(ctx=ctx)
    print(revisions)


# -----------------------------------------------------------------------
@moin2gitwiki.command()
@click.option(
    "--cache-directory",
    default="_cache",
    envvar="MOIN2GIT_CACHE",
)
@click.argument(
    "destination",
    type=click.Path(exists=False, file_okay=False, dir_okay=True),
)
@click.pass_obj
def fast_export(ctx, cache_directory, destination):
    """Git fast-export all the revisions in the wiki"""
    # build the translator
    translator = Moin2Markdown.create_translator(
        ctx=ctx,
        cache_directory=Path(cache_directory),
    )
    # cwd = Path.cwd()
    destination = Path(destination)
    if destination.exists():
        raise SystemExit(f"Destination path {destination} already exists.")
    # build your initial revision set from the wiki data
    revisions = MoinEditEntries.create_edit_entries(ctx=ctx)
    click.echo(click.style(f"Read {revisions.count()} wiki revisions", fg="green"))
    #
    # build the output git instance
    destination.mkdir(mode=0o755)
    os.chdir(destination)
    subprocess.run(["git", "init"])
    with subprocess.Popen(["git", "fast-import"], stdin=subprocess.PIPE) as gitstream:
        export = GitExportStream(output=gitstream.stdin, ctx=ctx)
        for revision in revisions.entries:
            page_name = revision.page_name + ".md"  # Markdown extension for page names
            content = translator.retrieve_and_translate(revision=revision)
            export.add_wiki_revision(
                revision=revision,
                content=content,
                name=page_name,
            )
        export.end_stream()
    subprocess.run(["git", "gc", "--aggressive"])  # pack it
    subprocess.run(["git", "checkout", "master"])  # check out the data


# -----------------------------------------------------------------------
# end
