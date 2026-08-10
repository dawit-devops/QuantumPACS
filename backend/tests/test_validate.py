"""R2-M6: capped request bodies (1MB → 413), cached reads, and the 413
exception plumbing through the shared validation handler."""
import pytest

from pydantic import BaseModel, Field
from starlette.applications import Starlette
from starlette.endpoints import HTTPEndpoint
from starlette.routing import Route
from starlette.testclient import TestClient

from api.validate import (
    MAX_BODY_BYTES, read_body, parse_body, _BodyTooLargeException,
    validation_exception_handler, _ValidationException,
)


class _DemoModel(BaseModel):
    name: str = Field(min_length=1, max_length=32)


class _DemoEndpoint(HTTPEndpoint):
    async def post(self, request):
        from starlette.responses import JSONResponse

        data = await parse_body(_DemoModel, request)
        return JSONResponse({'ok': data.name})


def _make_app():
    return Starlette(
        routes=[Route('/demo', endpoint=_DemoEndpoint, methods=['POST'])],
        exception_handlers={_ValidationException: validation_exception_handler},
    )


class TestReadBodyCap:
    @pytest.mark.asyncio
    async def test_oversized_body_raises_413(self):
        class _Req:
            async def stream(self):
                yield b'x' * MAX_BODY_BYTES
                yield b'y'

        with pytest.raises(_BodyTooLargeException) as ei:
            await read_body(_Req())
        assert ei.value.status == 413

    @pytest.mark.asyncio
    async def test_body_under_cap_passes_and_caches(self):
        class _Req:
            async def stream(self):
                yield b'{"name": "ok"}'

        req = _Req()
        body = await read_body(req)
        assert body == b'{"name": "ok"}'
        # Cached: subsequent reads must not re-consume the stream.
        assert req._body == body
        assert await read_body(req) == body


class TestParseBodyEndpoint:
    def test_oversized_body_returns_413(self):
        client = TestClient(_make_app())
        resp = client.post('/demo', content=b'x' * (MAX_BODY_BYTES + 1))
        assert resp.status_code == 413
        assert resp.json()['error']['details'][0]['type'] == 'body_too_large'

    def test_malformed_json_returns_422(self):
        # Malformed JSON is treated as an empty body → pydantic validation
        # error (422), never a 500.
        client = TestClient(_make_app())
        resp = client.post('/demo', content=b'{not json', headers={
            'Content-Type': 'application/json',
        })
        assert resp.status_code == 422

    def test_json_array_body_returns_422(self):
        client = TestClient(_make_app())
        resp = client.post('/demo', content=b'[1,2,3]', headers={
            'Content-Type': 'application/json',
        })
        assert resp.status_code == 422

    def test_valid_body_parses(self):
        client = TestClient(_make_app())
        resp = client.post('/demo', json={'name': 'hello'})
        assert resp.status_code == 200
        assert resp.json() == {'ok': 'hello'}


class TestRefreshTokenSchemaBound:
    def test_refresh_token_length_is_bounded(self):
        # R2-M6: an unbounded refresh_token field would buffer arbitrary
        # payloads through the pydantic layer.
        from pydantic import ValidationError

        from api.schemas.auth_refresh import RefreshTokenRequest

        with pytest.raises(ValidationError):
            RefreshTokenRequest(refresh_token='x' * 5000)
        ok = RefreshTokenRequest(refresh_token='x' * 4096)
        assert len(ok.refresh_token) == 4096


class TestOAuthProvidersSchema:
    def test_default_role_is_patient(self):
        # R2-H3: least-privilege JIT default — never a billing/clinical role.
        from api.schemas.oauth_providers import CreateOAuthProviderRequest

        req = CreateOAuthProviderRequest(issuer='https://idp.example.com', client_id='c')
        assert req.default_role == 'patient'

    def test_groups_map_field_roundtrip(self):
        from api.schemas.oauth_providers import CreateOAuthProviderRequest

        req = CreateOAuthProviderRequest(
            issuer='https://idp.example.com', client_id='c',
            groups_map={'radiologists': 'radiologist'},
        )
        assert req.groups_map == {'radiologists': 'radiologist'}
