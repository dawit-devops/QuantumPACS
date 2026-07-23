import json
from datetime import datetime, timezone

import pytest

from api.response import (
    ok, created, no_content, not_found,
    validation_error, server_error, unauthorized, forbidden,
)


class TestResponseHelpers:
    def test_ok_returns_200(self):
        resp = ok({'key': 'value'})
        assert resp.status_code == 200
        body = json.loads(resp.body)
        assert body == {'key': 'value'}

    def test_ok_default_empty_dict(self):
        resp = ok()
        assert resp.status_code == 200
        body = json.loads(resp.body)
        assert body == {}

    def test_created_returns_201(self):
        resp = created({'id': 1})
        assert resp.status_code == 201
        body = json.loads(resp.body)
        assert body == {'id': 1}

    def test_created_default_empty_dict(self):
        resp = created()
        assert resp.status_code == 201
        assert json.loads(resp.body) == {}

    def test_no_content_returns_204(self):
        resp = no_content()
        assert resp.status_code == 204
        assert json.loads(resp.body) == {}

    def test_not_found_returns_404(self):
        resp = not_found('User not found')
        assert resp.status_code == 404
        body = json.loads(resp.body)
        assert body == {'error': 'User not found'}

    def test_not_found_default_message(self):
        resp = not_found()
        assert resp.status_code == 404
        assert json.loads(resp.body) == {'error': 'Not found'}

    def test_validation_error_returns_400(self):
        resp = validation_error('Invalid input')
        assert resp.status_code == 400
        assert json.loads(resp.body) == {'error': 'Invalid input'}

    def test_validation_error_default_message(self):
        resp = validation_error()
        assert resp.status_code == 400
        assert json.loads(resp.body) == {'error': 'Validation error'}

    def test_server_error_returns_500(self):
        resp = server_error('Something broke')
        assert resp.status_code == 500
        assert json.loads(resp.body) == {'error': 'Something broke'}

    def test_server_error_default_message(self):
        resp = server_error()
        assert resp.status_code == 500
        assert json.loads(resp.body) == {'error': 'Internal server error'}

    def test_server_error_custom_status(self):
        resp = server_error('Custom error', status_code=502)
        assert resp.status_code == 502
        assert json.loads(resp.body) == {'error': 'Custom error'}

    def test_unauthorized_returns_401(self):
        resp = unauthorized('Bad token')
        assert resp.status_code == 401
        assert json.loads(resp.body) == {'error': 'Bad token'}

    def test_unauthorized_default_message(self):
        resp = unauthorized()
        assert resp.status_code == 401
        assert json.loads(resp.body) == {'error': 'Unauthorized'}

    def test_forbidden_returns_403(self):
        resp = forbidden('No access')
        assert resp.status_code == 403
        assert json.loads(resp.body) == {'error': 'No access'}

    def test_forbidden_default_message(self):
        resp = forbidden()
        assert resp.status_code == 403
        assert json.loads(resp.body) == {'error': 'Forbidden'}

    def test_content_type_is_application_json(self):
        resp = ok({'a': 1})
        assert resp.headers['content-type'] == 'application/json'

    def test_ok_serializes_datetime(self):
        now = datetime.now(timezone.utc)
        resp = ok({'timestamp': now})
        body = json.loads(resp.body)
        assert body['timestamp'] == now.isoformat()

    def test_ok_serializes_date(self):
        from datetime import date
        d = date(2026, 7, 4)
        resp = ok({'date': d})
        body = json.loads(resp.body)
        assert body['date'] == d.isoformat()

    def test_ok_ensure_ascii_false(self):
        resp = ok({'msg': 'héllo'})
        body = resp.body.decode('utf-8')
        assert 'héllo' in body

    def test_ok_rejects_nan(self):
        with pytest.raises(ValueError):
            ok({'value': float('nan')})

    def test_ok_compact_separators(self):
        resp = ok({'a': 1, 'b': 2})
        body = resp.body.decode('utf-8')
        assert ',:' not in body
        assert ':' in body
