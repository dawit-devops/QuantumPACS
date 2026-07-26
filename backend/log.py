"""Structured logging setup with ISO-8601 timestamps and noisy-library suppression."""
import json
import logging
import os
import sys
from contextvars import ContextVar

request_id_var: ContextVar[str] = ContextVar('request_id', default='')
tenant_var: ContextVar[str] = ContextVar('tenant', default='')
user_id_var: ContextVar[str] = ContextVar('user_id', default='')
trace_id_var: ContextVar[str] = ContextVar('trace_id', default='')
span_id_var: ContextVar[str] = ContextVar('span_id', default='')


class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_entry = {
            'timestamp': self.formatTime(record, self.datefmt),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
        }
        if record.exc_info and record.exc_info[0]:
            log_entry['error'] = {'stack': self.formatException(record.exc_info)}
        rid = request_id_var.get()
        if rid:
            log_entry['request_id'] = rid
        tid = trace_id_var.get()
        if tid:
            log_entry['trace_id'] = tid
        sid = span_id_var.get()
        if sid:
            log_entry['span_id'] = sid
        t = tenant_var.get()
        if t:
            log_entry['tenant'] = t
        uid = user_id_var.get()
        if uid:
            log_entry['user_id'] = uid
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
