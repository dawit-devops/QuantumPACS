import io
import json
import logging

from log import request_id_var, tenant_var, user_id_var, JSONFormatter


def _make_handler():
    handler = logging.StreamHandler(io.StringIO())
    fmt = JSONFormatter(datefmt='%Y-%m-%dT%H:%M:%S')
    handler.setFormatter(fmt)
    handler.setLevel(logging.DEBUG)
    return handler


class TestJSONFormatter:
    def test_basic_fields(self):
        logger = logging.getLogger('test_basic')
        logger.propagate = False
        logger.setLevel(logging.DEBUG)
        handler = _make_handler()
        logger.addHandler(handler)

        logger.info('hello')

        record = json.loads(handler.stream.getvalue())
        assert record['level'] == 'INFO'
        assert record['logger'] == 'test_basic'
        assert record['message'] == 'hello'
        assert 'timestamp' in record
        logger.handlers.clear()

    def test_request_context(self):
        logger = logging.getLogger('test_context')
        logger.propagate = False
        logger.setLevel(logging.DEBUG)
        handler = _make_handler()
        logger.addHandler(handler)

        request_id_var.set('req-1')
        tenant_var.set('tenant-a')
        user_id_var.set('user-1')

        logger.info('with context')
        val = handler.stream.getvalue()

        record = json.loads(val)
        assert record['request_id'] == 'req-1'
        assert record['tenant'] == 'tenant-a'
        assert record['user_id'] == 'user-1'

        request_id_var.set('')
        tenant_var.set('')
        user_id_var.set('')
        logger.handlers.clear()

    def test_error_stack(self):
        logger = logging.getLogger('test_error')
        logger.propagate = False
        handler = _make_handler()
        logger.addHandler(handler)

        try:
            raise ValueError('fail')
        except ValueError:
            logger.exception('an error')

        record = json.loads(handler.stream.getvalue())
        assert 'error' in record
        assert 'stack' in record['error']
        assert 'ValueError' in record['error']['stack']
        assert 'fail' in record['error']['stack']
        logger.handlers.clear()

    def test_no_context_when_empty(self):
        logger = logging.getLogger('test_empty')
        logger.propagate = False
        logger.setLevel(logging.DEBUG)
        handler = _make_handler()
        logger.addHandler(handler)

        request_id_var.set('')
        tenant_var.set('')
        user_id_var.set('')

        logger.info('no context')

        record = json.loads(handler.stream.getvalue())
        assert 'request_id' not in record
        assert 'tenant' not in record
        assert 'user_id' not in record
        logger.handlers.clear()
