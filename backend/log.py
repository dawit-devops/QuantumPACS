"""Structured logging setup with ISO-8601 timestamps and noisy-library suppression."""
import logging
import sys


def setup_logging():
    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers.clear()
    root.addHandler(handler)

    # quiet noisy libs
    logging.getLogger('aiobotocore').setLevel(logging.WARNING)
    logging.getLogger('botocore').setLevel(logging.WARNING)
    logging.getLogger('elasticsearch').setLevel(logging.WARNING)
    logging.getLogger('pynetdicom').setLevel(logging.WARNING)


def get_logger(name):
    return logging.getLogger(name)
