import logging.handlers
import os
import sys

import attr

from .fetch_cache import FetchCache
from .users import Moin2GitUserSet


CONSOLE_FORMATTER = logging.Formatter(
    "%(asctime)s — %(name)s — %(levelname)s — %(funcName)s:%(lineno)d — %(message)s",
)
SYSLOG_FORMATTER = logging.Formatter("%(name)s: [%(levelname)s] %(message)s")


@attr.s(kw_only=True, slots=True)
class Moin2GitContext:
    logger: logging.Logger = attr.ib()
    moin_data: str = attr.ib()
    cache: str = attr.ib(default=None)
    users: Moin2GitUserSet = attr.ib(default=None)
    syslog: bool = attr.ib(default=False)
    debug: bool = attr.ib(default=False)
    verbose: bool = attr.ib(default=False)

    @classmethod
    def create_context(cls, **kwargs):
        if "logger" not in kwargs:
            logger = logging.getLogger("moin2gitwiki")
            kwargs["logger"] = logger
        if "user_map" in kwargs:
            user_map = kwargs["user_map"]
            del kwargs["user_map"]
        #
        # make the paths absolute
        kwargs["moin_data"] = os.path.abspath(kwargs["moin_data"])
        #
        # build a fetch cache object
        if "cache" in kwargs:
            cache = (
                os.path.abspath(kwargs["cache"])
                if kwargs["cache"] is not None
                else "_cache"
            )
            del kwargs["cache"]
        else:
            cache = "_cache"
        cache_directory = os.path.abspath(cache)
        #
        # build the context object
        context = cls(**kwargs)
        context.configure_logger()
        #
        # get the users
        if user_map is not None:
            context.users = Moin2GitUserSet.load_users_from_file(
                path=user_map,
                logger=context.logger,
            )
        else:
            context.users = Moin2GitUserSet.load_users_from_wiki_data(
                wiki_data_path=context.moin_data,
                logger=context.logger,
            )
        #
        # Build a fetch cache
        context.cache = FetchCache.initialise_cache(
            cache_directory=cache_directory,
            ctx=context,
        )
        #
        return context

    def configure_logger(self):
        logger = self.logger
        logger.setLevel(logging.DEBUG)
        #
        # set up the console logging
        console_handler = logging.StreamHandler(sys.stdout)
        if self.debug:
            console_handler.setLevel(logging.DEBUG)
        elif self.verbose:
            console_handler.setLevel(logging.INFO)
        else:
            console_handler.setLevel(logging.WARNING)
        console_handler.setFormatter(CONSOLE_FORMATTER)
        logger.addHandler(console_handler)
        #
        # set up syslog
        if self.syslog:
            syslog_handler = logging.handlers.SysLogHandler(
                address="/dev/log",
                facility=logging.handlers.SysLogHandler.LOG_LOCAL0,
            )
            syslog_handler.setLevel(logging.DEBUG)
            syslog_handler.setFormatter(SYSLOG_FORMATTER)
            logger.addHandler(syslog_handler)


# end
