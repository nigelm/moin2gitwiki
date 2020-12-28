import logging.handlers
import sys

import attr


CONSOLE_FORMATTER = logging.Formatter(
    "%(asctime)s — %(name)s — %(levelname)s — %(funcName)s:%(lineno)d — %(message)s",
)
SYSLOG_FORMATTER = logging.Formatter("%(name)s: [%(levelname)s] %(message)s")


@attr.s
class Moin2GitContext:
    logger: logging.Logger = attr.ib()
    syslog: bool = attr.ib(default=False)
    debug: bool = attr.ib(default=False)
    verbose: bool = attr.ib(default=False)

    @classmethod
    def create_context(cls, **kwargs):
        if "logger" not in kwargs:
            logger = logging.getLogger("moin2gitwiki")
            kwargs["logger"] = logger
        return cls(**kwargs)

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
