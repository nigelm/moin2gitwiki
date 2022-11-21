"""
moin2gitwiki context object - carries state between components

This contains the basic context object, which has various global
state information in it such as the logging objects.
"""
import logging.handlers
import sys
from pathlib import Path
from typing import Dict

import attr

from .users import Moin2GitUserSet


LOG_FILE = "moin2gitwiki.log"
FILE_FORMATTER = logging.Formatter(
    "%(asctime)s — %(name)s — %(levelname)s — %(funcName)s:%(lineno)d — %(message)s",
)
CONSOLE_FORMATTER = logging.Formatter(
    "%(asctime)s — %(name)s — %(levelname)s — %(funcName)s:%(lineno)d — %(message)s",
)
SYSLOG_FORMATTER = logging.Formatter("%(name)s: [%(levelname)s] %(message)s")


@attr.s(kw_only=True, slots=True)
class Moin2GitContext:
    """
    Moin2GitContext Context Object - holds state, logging, etc

    Called from the cli code.  Sets up all the common requirements.

    Attributes:
        debug:      if true we output more debugging chatter
        verbose:    if true we output more progress information
        syslog:     if true we additionally log to syslog at debug level
        logger:     Logging object
        moin_data:  Path of the MoinMoin data directory
        users:      Moin user set object

    """

    logger: logging.Logger = attr.ib()
    _moin_data: Path = attr.ib(default=None)
    users: Moin2GitUserSet = attr.ib(default=None)
    syslog: bool = attr.ib(default=False)
    debug: bool = attr.ib(default=False)
    verbose: bool = attr.ib(default=False)
    proxies: Dict[str, str] = attr.ib(default={})

    @property
    def moin_data(self):
        if self._moin_data is not None:
            return self._moin_data
        else:
            raise RuntimeError("moin_data is not set - look at --moin-data option")

    @classmethod
    def create_context(cls, **kwargs):
        """
        Create the context object

        Builds the requirements for the context object and returns an object
        """
        if "logger" not in kwargs:
            logger = logging.getLogger("moin2gitwiki")
            kwargs["logger"] = logger
        if "moin_data" in kwargs:
            moin_data = kwargs["moin_data"]
            del kwargs["moin_data"]
        else:
            moin_data = None
        if "user_map" in kwargs:
            user_map = kwargs["user_map"]
            del kwargs["user_map"]

        if moin_data:
            #
            # make the paths absolute
            kwargs["_moin_data"] = Path(moin_data).resolve(strict=True)
            #
            # get the proxies
            proxies: Dict[str, str] = {}
            if "proxies" in kwargs:
                for proxy_setting in kwargs["proxies"]:
                    key, value = proxy_setting.split("=", maxsplit=1)
                    proxies[key] = value
            kwargs["proxies"] = proxies
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
        elif moin_data:
            context.users = Moin2GitUserSet.load_users_from_wiki_data(
                wiki_data_path=context.moin_data,
                logger=context.logger,
            )
        #
        return context

    def get_file_handler(self) -> logging.handlers.TimedRotatingFileHandler:
        """
        Sets up and returns the file logging handler

        Returns:
            file_handler: logger file handler
        """
        file_handler = logging.handlers.TimedRotatingFileHandler(
            LOG_FILE,
            when="midnight",
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(FILE_FORMATTER)
        return file_handler

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
        logger.addHandler(self.get_file_handler())


# end
