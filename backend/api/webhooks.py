import asyncio
import ipaddress
import json
import socket
from urllib.parse import urlparse

import httpx

from starlette.endpoints import HTTPEndpoint

from api.rbac import requires_permission
from api.permissions import Permission
from api.response import ok, created, api_error
from api.schemas.webhooks import WebhookCreate, WebhookUpdate
from api.validate import parse_body
from db.conn import get_conn
from db.webhook import Webhook
from log import get_logger

log = get_logger(__name__)

AVAILABLE_EVENTS = [
    'study.arrived',
    'study.updated',
    'patient.created',
    'patient.updated',
    'hl7.message.received',
    'hl7.message.failed',
    'user.created',
    'user.deleted',
]

# Addresses the test ping may never be sent to. Besides RFC1918 and loopback
# this covers link-local (incl. the 169.254.169.254 cloud-metadata address),
# CGNAT, documentation ranges, multicast, and broadcast — anything that is
# not a publicly routable endpoint.
_PRIVATE_NETWORKS = [
    ipaddress.ip_network('0.0.0.0/8'),
    ipaddress.ip_network('10.0.0.0/8'),
    ipaddress.ip_network('100.64.0.0/10'),
    ipaddress.ip_network('127.0.0.0/8'),
    ipaddress.ip_network('169.254.0.0/16'),
    ipaddress.ip_network('172.16.0.0/12'),
    ipaddress.ip_network('192.0.0.0/24'),
    ipaddress.ip_network('192.0.2.0/24'),
    ipaddress.ip_network('192.168.0.0/16'),
    ipaddress.ip_network('198.18.0.0/15'),
    ipaddress.ip_network('198.51.100.0/24'),
    ipaddress.ip_network('203.0.113.0/24'),
    ipaddress.ip_network('224.0.0.0/4'),
    ipaddress.ip_network('240.0.0.0/4'),
    ipaddress.ip_network('255.255.255.255/32'),
    ipaddress.ip_network('::/128'),
    ipaddress.ip_network('::1/128'),
    ipaddress.ip_network('fc00::/7'),
    ipaddress.ip_network('fe80::/10'),
    ipaddress.ip_network('ff00::/8'),
]

_LOCAL_HOSTNAMES = frozenset({'localhost', 'localhost.localdomain'})


class _IPPinnedTransport(httpx.AsyncHTTPTransport):
    """Connect only to a pre-validated IP instead of letting httpx re-resolve
    the hostname at connect time (NEW #6 — the SSRF check above and the
    delivery used to race: DNS rebinding could repoint the hostname between
    them). The original host survives as the Host header and as the TLS SNI
    (httpcore's `sni_hostname` extension) so virtual-host routing and
    certificate verification still target the caller's hostname."""

    def __init__(self, ip, **kwargs):
        self._pin_ip = ip
        super().__init__(**kwargs)

    def handle_async_request(self, request):
        host = request.url.host
        default_port = 443 if request.url.scheme == 'https' else 80
        port = request.url.port or default_port
        pinned_url = request.url.copy_with(host=self._pin_ip, port=port)
        # httpx.AsyncHTTPTransport rebuilds an httpcore request from
        # `request.headers.raw` (bytes pairs), so the Host header must be
        # manipulated on the raw list. `Request(stream=...)` adds no
        # auto-populated headers — the single Host below is the only one
        # emitted on the wire.
        headers = [(k, v) for k, v in request.headers.raw if k.lower() != b'host']
        host_header = host if port == default_port else f'{host}:{port}'
        headers.append((b'Host', host_header.encode()))
        extensions = dict(request.extensions)
        extensions['sni_hostname'] = host
        pinned = httpx.Request(
            request.method, str(pinned_url),
            headers=headers, stream=request.stream,
            extensions=extensions,
        )
        return super().handle_async_request(pinned)


def _is_blocked_address(host):
    """True when `host` is a literal IP in a private/reserved range.

    IPv4-mapped IPv6 literals (::ffff:127.0.0.1) are unwrapped so they get
    the same treatment as their v4 form. Anything unparseable is refused —
    fail closed, the URL is not worth a delivery attempt.
    """
    try:
        addr = ipaddress.ip_address(host)
    except ValueError:
        return True
    if isinstance(addr, ipaddress.IPv6Address):
        mapped = addr.ipv4_mapped
        if mapped is not None:
            addr = mapped
    return any(addr in net for net in _PRIVATE_NETWORKS)


async def _resolve_host(host):
    """Resolve a hostname, returning all candidate IP strings.

    Resolution runs in a worker thread (getaddrinfo blocks) under a timeout
    so a wedged resolver cannot hang the test-ping endpoint.
    """
    infos = await asyncio.wait_for(
        asyncio.to_thread(socket.getaddrinfo, host, None), timeout=5,
    )
    return [info[4][0] for info in infos]


class WebhooksHandler(HTTPEndpoint):
    @requires_permission(Permission.SYSTEM_ADMIN)
    async def get(self, request):
        async with get_conn() as conn:
            hooks = await Webhook(conn).get_all()
        return ok({'webhooks': hooks, 'available_events': AVAILABLE_EVENTS})

    @requires_permission(Permission.SYSTEM_ADMIN)
    async def post(self, request):
        data = await parse_body(WebhookCreate, request)
        async with get_conn() as conn:
            wh = Webhook(conn)
            wh_id = await wh.create(data.model_dump())
            hook = await wh.get_by_id(wh_id)
        return created(hook)


class WebhookHandler(HTTPEndpoint):
    @requires_permission(Permission.SYSTEM_ADMIN)
    async def get(self, request):
        wh_id = request.path_params['id']
        async with get_conn() as conn:
            hook = await Webhook(conn).get_by_id(wh_id)
        if not hook:
            return api_error('NOT_FOUND', 'Webhook not found', status=404)
        return ok(hook)

    @requires_permission(Permission.SYSTEM_ADMIN)
    async def put(self, request):
        wh_id = request.path_params['id']
        data = await parse_body(WebhookUpdate, request)
        updates = data.model_dump(exclude_none=True)
        if not updates:
            return api_error('NO_CHANGES', 'No changes provided', status=400)
        async with get_conn() as conn:
            wh = Webhook(conn)
            existing = await wh.get_by_id(wh_id)
            if not existing:
                return api_error('NOT_FOUND', 'Webhook not found', status=404)
            await wh.update_webhook(wh_id, updates)
            hook = await wh.get_by_id(wh_id)
        return ok(hook)

    @requires_permission(Permission.SYSTEM_ADMIN)
    async def delete(self, request):
        wh_id = request.path_params['id']
        async with get_conn() as conn:
            wh = Webhook(conn)
            existing = await wh.get_by_id(wh_id)
            if not existing:
                return api_error('NOT_FOUND', 'Webhook not found', status=404)
            await wh.delete(wh_id)
        return ok({'deleted': True})


class WebhookTestHandler(HTTPEndpoint):
    @requires_permission(Permission.SYSTEM_ADMIN)
    async def post(self, request):
        body = await request.json()
        url = body.get('url', '')
        if not url:
            return api_error('VALIDATION', 'url is required', status=400)

        parsed = urlparse(url)
        host = parsed.hostname or ''
        if parsed.scheme not in ('http', 'https'):
            return api_error('SSRF_BLOCKED', 'Only http/https URLs are allowed', status=400)
        if not host:
            return api_error('SSRF_BLOCKED', 'URL has no valid host', status=400)
        # _is_blocked_address fails closed for anything it cannot parse, so
        # it must only be applied to literal IPs here; hostnames are vetted
        # after resolution below (they may point at internal addresses via
        # DNS rebinding or integer-form IPs).
        try:
            ipaddress.ip_address(host)
        except ValueError:
            pass
        else:
            if _is_blocked_address(host):
                return api_error('SSRF_BLOCKED', 'Requests to private/reserved IP ranges are blocked', status=400)
        if host.lower() in _LOCAL_HOSTNAMES or host.lower().endswith(('.local', '.localhost')):
            return api_error('SSRF_BLOCKED', 'Requests to local hostnames are blocked', status=400)

        # A public-looking hostname can still resolve to an internal address
        # (metadata endpoints, DNS rebinding, integer-form IPs like
        # 2130706433). Resolve first and refuse the delivery when any
        # candidate address is blocked.
        try:
            addresses = await _resolve_host(host)
        except Exception:
            return ok({
                'success': False,
                'status_code': 0,
                'error': 'Could not resolve host',
            })
        if any(_is_blocked_address(a) for a in addresses):
            return api_error('SSRF_BLOCKED', 'Requests to private/reserved IP ranges are blocked', status=400)
        # Defense in depth: pick the first validated (non-blocked) address —
        # the connection below is pinned to exactly this IP, never resolved
        # again from the hostname.
        target_ip = next((a for a in addresses if not _is_blocked_address(a)), None)
        if target_ip is None:
            return api_error('SSRF_BLOCKED', 'Requests to private/reserved IP ranges are blocked', status=400)

        payload = {
            'event': 'test.ping',
            'timestamp': '2026-07-29T00:00:00Z',
            'message': 'This is a test webhook from QuantumPACS',
        }
        secret = body.get('secret', '')

        try:
            transport = _IPPinnedTransport(target_ip)
            async with httpx.AsyncClient(timeout=10, transport=transport) as client:
                headers = {'Content-Type': 'application/json'}
                if secret:
                    import hmac
                    import hashlib
                    sig = hmac.new(secret.encode(), json.dumps(payload).encode(), hashlib.sha256).hexdigest()
                    headers['X-Webhook-Signature'] = sig
                resp = await client.post(url, json=payload, headers=headers)
            return ok({
                'success': resp.status_code < 400,
                'status_code': resp.status_code,
                'body': resp.text[:500],
            })
        except Exception as e:
            # httpx errors embed URLs/connection internals — bound the text so
            # diagnostic payloads never carry unbounded exception content.
            detail = str(e) or type(e).__name__
            return ok({
                'success': False,
                'status_code': 0,
                'error': detail[:200],
            })
