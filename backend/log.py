"""Structured logging setup with ISO-8601 timestamps and noisy-library suppression."""
import json
import logging
import os
import sys
from contextvars import ContextVar

request_id_var: ContextVar[str] = ContextVar('request_id', default='')


class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_entry = {
            'timestamp': self.formatTime(record, self.datefmt),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
        }
        if record.exc_info and record.exc_info[0]:
            log_entry['exception'] = self.formatException(record.exc_info)
        rid = request_id_var.get()
        if rid:
            log_entry['request_id'] = rid
        extra = getattr(record, 'extra', None)
        if extra:
            log_entry.update(extra)
        return json.dumps(log_entry, default=str)


def setup_logging():
    formatter = JSONFormatter(datefmt='%Y-%m-%dT%H:%M:%S')
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(os.getenv('LOG_LEVEL', 'INFO').upper())
    root.handlers.clear()
    root.addHandler(handler)

    logging.getLogger('aiobotocore').setLevel(logging.WARNING)
    logging.getLogger('botocore').setLevel(logging.WARNING)
    logging.getLogger('elasticsearch').setLevel(logging.WARNING)
    logging.getLogger('pynetdicom').setLevel(logging.WARNING)


def get_logger(name):
    return logging.getLogger(name)
