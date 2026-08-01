import json
import uuid
from datetime import datetime, timezone

from api.response import ok, paginated


def test_ok_serializes_uuid():
    # asyncpg returns uuid columns as pgproto.UUID (uuid.UUID subclass);
    # role_id joins previously 500'd here.
    resp = ok({'id': uuid.uuid4(), 'name': 'x'})
    assert resp.status_code == 200
    assert json.loads(resp.body)['name'] == 'x'


def test_ok_serializes_datetime():
    resp = ok({'at': datetime(2026, 1, 1, tzinfo=timezone.utc)})
    body = json.loads(resp.body)
    assert body['at'] == '2026-01-01T00:00:00+00:00'


def test_paginated_accepts_uuid_rows():
    req = type('Req', (), {'url': type('U', (), {'path': '/api/users'})()})()
    resp = paginated(
        [{'id': 1, 'role_id': uuid.uuid4()}],
        total=1, page=1, per_page=20, request=req,
    )
    assert resp.status_code == 200
    assert json.loads(resp.body)['data'][0]['role_id']
