from unittest.mock import AsyncMock, MagicMock, patch

import httpx

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.routing import Route
from starlette.testclient import TestClient

from api.auth import User
from api.webhooks import WebhookTestHandler, _IPPinnedTransport


class TestIPPinnedTransport:
    """NEW #6: delivery is pinned to the pre-validated IP so DNS rebinding
    between the SSRF check and the connect can never redirect the request to
    an internal address. The caller's hostname survives as the Host header
    and as the TLS SNI so virtual-host routing and certificate verification
    still target the original host."""

    def _capture(self, transport, original):
        captured = {}
        with patch.object(
            httpx.AsyncHTTPTransport, 'handle_async_request',
            new=lambda self, request: captured.setdefault('request', request),
        ):
            transport.handle_async_request(original)
        return captured['request']

    def test_rewrites_url_host_to_pinned_ip(self):
        transport = _IPPinnedTransport('93.184.216.34')
        original = httpx.Request('POST', 'https://hooks.example.com:8443/path?q=1', json={'a': 1})
        req = self._capture(transport, original)
        assert req.url.host == '93.184.216.34'
        assert req.url.port == 8443
        assert req.url.path == '/path'
        assert 'q=1' in str(req.url)

    def test_preserves_host_header_with_non_default_port(self):
        transport = _IPPinnedTransport('93.184.216.34')
        original = httpx.Request('POST', 'https://hooks.example.com:8443/path', json={})
        req = self._capture(transport, original)
        assert req.headers['Host'] == 'hooks.example.com:8443'
        hosts = [k for k, v in req.headers.raw if k.lower() == b'host']
        assert len(hosts) == 1

    def test_default_port_omitted_from_host_header(self):
        transport = _IPPinnedTransport('93.184.216.34')
        original = httpx.Request('GET', 'https://hooks.example.com/path')
        req = self._capture(transport, original)
        assert req.headers['Host'] == 'hooks.example.com'

    def test_sets_sni_hostname_extension(self):
        transport = _IPPinnedTransport('93.184.216.34')
        original = httpx.Request('POST', 'https://hooks.example.com/path', json={})
        req = self._capture(transport, original)
        assert req.extensions['sni_hostname'] == 'hooks.example.com'

    def test_keeps_request_body(self):
        transport = _IPPinnedTransport('93.184.216.34')
        original = httpx.Request('POST', 'https://hooks.example.com/path', json={'a': 1})
        req = self._capture(transport, original)
        # stream= requests are not read until sent — read() mirrors what the
        # transport does before serializing.
        req.read()
        assert b'"a":1' in req.content


class _FakeAuth(BaseHTTPMiddleware):
    def __init__(self, app, user=None):
        super().__init__(app)
        self._user = user or User({'id': 1, 'permissions': ['SYSTEM_ADMIN']})

    async def dispatch(self, request, call_next):
        request.scope['user'] = self._user
        request.scope['auth'] = None
        return await call_next(request)


class TestWebhookDeliveryPinned:
    def _make_app(self):
        return Starlette(
            routes=[Route('/api/webhooks/test', endpoint=WebhookTestHandler, methods=['POST'])],
            middleware=[Middleware(_FakeAuth)],
        )

    def test_delivery_uses_transport_pinned_to_validated_ip(self):
        client = TestClient(self._make_app())
        fake_post = AsyncMock(return_value=MagicMock(status_code=204, text=''))
        with (
            patch('api.webhooks._resolve_host', new=AsyncMock(return_value=['93.184.216.34'])),
            patch('api.webhooks.httpx.AsyncClient') as mock_client,
        ):
            mock_client.return_value.__aenter__.return_value.post = fake_post
            resp = client.post(
                '/api/webhooks/test',
                json={'url': 'https://hooks.example.com:8443/hook', 'secret': 's3cret'},
            )
        assert resp.status_code == 200
        assert resp.json()['success'] is True
        transport = mock_client.call_args.kwargs['transport']
        assert isinstance(transport, _IPPinnedTransport)
        assert transport._pin_ip == '93.184.216.34'
        # Pinning is transparent to the app layer: the original URL is posted.
        assert fake_post.await_args.args[0] == 'https://hooks.example.com:8443/hook'

    def test_failed_delivery_returns_bounded_error(self):
        client = TestClient(self._make_app())
        fake_post = AsyncMock(side_effect=RuntimeError('x' * 500))
        with (
            patch('api.webhooks._resolve_host', new=AsyncMock(return_value=['93.184.216.34'])),
            patch('api.webhooks.httpx.AsyncClient') as mock_client,
        ):
            mock_client.return_value.__aenter__.return_value.post = fake_post
            resp = client.post(
                '/api/webhooks/test',
                json={'url': 'https://hooks.example.com/hook'},
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body['success'] is False
        assert len(body['error']) <= 200
