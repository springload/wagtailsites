import sys
from os.path import join

from .django import SITE_NAME
from .paths import DJANGO_ROOT

__all__ = ["LOGGING"]  # don't import DEV_LOGGING by default

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] %(message)s",
            "datefmt": "%d/%b/%Y %H:%M:%S",
        },
        "simple": {"format": "%(levelname)s %(message)s"},
    },
    "handlers": {
        "stdout": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["stdout"],
            "propagate": True,
            "level": "ERROR",
        },
        "core": {
            "handlers": ["stdout"],
            "propagate": True,
            "level": "ERROR",
        },
    },
}

DEV_LOGGING = {
    "version": 1,
    "disable_existing_loggers": True,
    "formatters": {},
    "handlers": {
        "dev_console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "stream": sys.stderr,
        },
    },
    "root": {  # using root logger to catch and log all interesting messages
        "level": "WARNING",
        "handlers": ["dev_console"],
    },
    "loggers": {
        "django": {
            "handlers": ["dev_console"],
            "propagate": False,
            "level": "INFO",
        },
        "core": {
            "handlers": ["dev_console"],
            "propagate": False,
            "level": "DEBUG",
        },
    },
}
