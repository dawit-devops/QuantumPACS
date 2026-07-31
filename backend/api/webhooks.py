import json
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

        payload = {
            'event': 'test.ping',
            'timestamp': '2026-07-29T00:00:00Z',
            'message': 'This is a test webhook from QuantumPACS',
        }
        secret = body.get('secret', '')

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                headers = {'Content-Type': 'application/json'}
                if secret:
                    import hmac, hashlib
                    sig = hmac.new(secret.encode(), json.dumps(payload).encode(), hashlib.sha256).hexdigest()
                    headers['X-Webhook-Signature'] = sig
                resp = await client.post(url, json=payload, headers=headers)
            return ok({
                'success': resp.status_code < 400,
                'status_code': resp.status_code,
                'body': resp.text[:500],
            })
        except Exception as e:
            return ok({
                'success': False,
                'status_code': 0,
                'error': str(e),
            })
