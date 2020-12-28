import click

from . import __version__
from .context import Moin2GitContext


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
# end
