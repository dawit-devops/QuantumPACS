import asyncio
from collections import defaultdict

from starlette.endpoints import HTTPEndpoint, WebSocketEndpoint
from starlette.websockets import WebSocket, WebSocketDisconnect

from api.rbac import has_permission
from api.permissions import Permission
from api.response import ok
from api.tokens import create_token as gen_token
from db.conn import get_conn
from db.files import Files

_app = None


def set_app(app):
    global _app
    _app = app


def _get_state():
    if _app is None:
        return None
    if not hasattr(_app.state, 'ws_state'):
        raise RuntimeError('WS state not initialized on app')
    return _app.state.ws_state


class WSState:
    def __init__(self):
        self.local_clients = defaultdict(dict)
        # Per-user registry for server-initiated pushes (e.g. notification
        # events) that are not bound to a specific file channel.
        self.user_clients = defaultdict(dict)
        self.sub_lock = asyncio.Lock()
        self.pubsub = None
        self.listener_task = None
        self.cleanup_task = None


async def _get_pubsub(state):
    if state.pubsub is not None:
        return state.pubsub
    try:
        from api.redis_client import get_client
        r = await get_client(db=4)
        await r.ping()
        state.pubsub = r.pubsub()
        return state.pubsub
    except Exception:
        return None


def _channel(tenant_slug, file_id):
    # N3: channels are tenant-qualified. File ids are per-tenant SERIALs, so
    # a bare `channel:file:{id}` collides across tenants — the slug bakes the
    # data scope into the channel namespace itself.
    return f'channel:file:{tenant_slug}:{file_id}'


def _user_tenant(user):
    # WebSockets never pass through TenantMiddleware (BaseHTTPMiddleware
    # skips non-HTTP scopes), so the JWT tenant claim is the only scope a
    # socket can have — no X-Tenant-ID override exists on this transport.
    return getattr(user, 'tenant', None) or ''


async def _send_error(websocket, message):
    try:
        await websocket.send_json({'type': 'error', 'message': message})
    except WebSocketDisconnect:
        pass


async def broadcast_to_user(user_id, payload):
    """Push a server-initiated event to every socket a user has open.

    Used e.g. after a notification is created so the bell badge can refresh
    immediately instead of waiting for the next poll. Shares the sub_lock with
    the file-channel registry so concurrent connect/disconnect cannot race.
    """
    state = _get_state()
    if state is None:
        return
    async with state.sub_lock:
        conns = list(state.user_clients.get(user_id, {}).values())
    for c in conns:
        if isinstance(c, WebSocket):
            try:
                await c.send_json(payload)
            except WebSocketDisconnect:
                pass


async def _pubsub_listener(state):
    ps = await _get_pubsub(state)
    if ps is None:
        return
    try:
        async for message in ps.listen():
            if message['type'] != 'message':
                continue
            channel = message['channel']
            if isinstance(channel, bytes):
                channel = channel.decode()
            data = message['data']
            if isinstance(data, bytes):
                data = data.decode()
            import json
            try:
                payload = json.loads(data)
            except Exception:
                continue
            async with state.sub_lock:
                conns = list(state.local_clients.get(channel, {}).values())
            for c in conns:
                if isinstance(c, WebSocket):
                    try:
                        await c.send_json(payload)
                    except WebSocketDisconnect:
                        pass
    except Exception:
        pass


def _ensure_listener(state):
    if state.listener_task is None or state.listener_task.done():
        state.listener_task = asyncio.create_task(_pubsub_listener(state))
    if state.cleanup_task is None or state.cleanup_task.done():
        state.cleanup_task = asyncio.create_task(_stale_cleanup(state))


async def _stale_cleanup(state):
    while True:
        await asyncio.sleep(30)
        async with state.sub_lock:
            for file_id in list(state.local_clients):
                file_clients = state.local_clients[file_id]
                stale = [k for k, v in file_clients.items() if isinstance(v, WebSocket) and v.client_state == 3]
                for k in stale:
                    del file_clients[k]
                if not file_clients:
                    del state.local_clients[file_id]


class WSToken(HTTPEndpoint):
    async def get(self, request):
        token = gen_token(request.user.to_dict(), {'minutes': 1})
        return ok({'token': token})


class WebsocketHandler(WebSocketEndpoint):
    encoding = 'json'

    async def on_connect(self, websocket):
        await websocket.accept()
        # AuthenticationMiddleware puts the User on the scope for both HTTP
        # and WS requests; read it via scope so sockets opened in test
        # clients without the middleware are simply not registered.
        user = websocket.scope.get('user')
        if user is None:
            return
        state = _get_state()
        if state is None:
            return
        async with state.sub_lock:
            state.user_clients[user.id][str(id(websocket))] = websocket
        websocket.user_id = user.id

    async def on_receive(self, websocket, data):
        state = _get_state()
        if state is None:
            return
        if not isinstance(data, dict):
            return

        type_ = data.get('type')
        user = websocket.scope.get('user')

        match type_:
            case 'open':
                raw_f = data.get('file')
                f = raw_f
                # CornerstoneElement opens the channel with the wadouri image
                # URL (`wadouri:{API_URL}/files/{id}/data`); normalize both
                # forms to the file id so the bigint lookup never sees the URL
                # string (asyncpg would reject it with a type error). The raw
                # value is still echoed back so legacy string-id callers keep
                # the exact contract.
                if isinstance(f, str):
                    try:
                        if '/files/' in f:
                            f = int(f.rsplit('/files/', 1)[1].split('/')[0])
                        else:
                            f = int(f)
                    except (ValueError, IndexError):
                        f = None
                # Channel authz: subscribing registers this socket in the
                # file's broadcast list, so the user must hold FILE_READ.
                # Permissions ride on the JWT (share-key sockets never pass
                # the WS auth path), making this a pure permission gate.
                if f is None or not user or not getattr(user, 'is_authenticated', False) \
                        or not has_permission(user, Permission.FILE_READ):
                    await _send_error(websocket, 'Forbidden: FILE_READ required')
                    return
                # M-5: WebSockets skip TenantMiddleware, so verify the target
                # file actually belongs to the user's tenant (DB-per-tenant
                # isolation) before subscribing. Without this, a caller who
                # knows a file id could open a channel for another tenant's
                # study and receive / collide with its viewer-state broadcast.
                async with get_conn() as conn:
                    file = await Files(conn).get_extra(f)
                if not file or file.get('deleted') \
                        or (file.get('tenant') and not getattr(user, 'admin', False)
                            and file.get('tenant') != getattr(user, 'tenant', None)):
                    await _send_error(websocket, 'Forbidden: file not accessible')
                    return
                chan = _channel(_user_tenant(user), f)
                async with state.sub_lock:
                    state.local_clients[chan][str(id(websocket))] = websocket
                ps = await _get_pubsub(state)
                if ps is not None:
                    try:
                        await ps.subscribe(chan)
                        _ensure_listener(state)
                    except Exception:
                        pass
                await websocket.send_json(
                    {
                        'type': 'send_state',
                        'file': raw_f,
                        'state': data.get('state', {}),
                    },
                )
                websocket.file = raw_f
                websocket.channel = chan

            case 'send_state':
                # Publishing to a file channel is the write side of the same
                # broadcast membership the 'open' gate protects — a socket
                # without FILE_READ must be rejected here too, and the scope
                # must be the sender's own tenant (the channel namespace is
                # derived from the user, never from the payload).
                if not user or not getattr(user, 'is_authenticated', False) \
                        or not has_permission(user, Permission.FILE_READ):
                    await _send_error(websocket, 'Forbidden: FILE_READ required')
                    return
                f = data.get('file')
                if f is None or data.get('state') is None:
                    await _send_error(websocket, 'Invalid payload: file and state are required')
                    return
                # M-5: only publish to the channel this socket was authorized
                # to open. A socket that never passed the 'open' ownership gate
                # (or passes a different file) must not inject viewer state into
                # another tenant's channel.
                if not getattr(websocket, 'channel', None) or f != getattr(websocket, 'file', None):
                    await _send_error(websocket, 'Forbidden: open the file channel first')
                    return
                chan = websocket.channel
                payload = {
                    'type': 'send_state',
                    'file': f,
                    'state': data['state'],
                }
                import json
                r = None
                try:
                    from api.redis_client import get_client
                    r = await get_client(db=4)
                    await r.publish(chan, json.dumps(payload))
                except Exception:
                    async with state.sub_lock:
                        conns = list(state.local_clients.get(chan, {}).values())
                    for c in conns:
                        if c == websocket:
                            continue
                        if isinstance(c, WebSocket):
                            try:
                                await c.send_json(payload)
                            except WebSocketDisconnect:
                                pass
                finally:
                    if r is not None:
                        try:
                            await r.aclose()
                        except Exception:
                            pass

    async def on_disconnect(self, websocket, close_code):
        state = _get_state()
        if state is None:
            return
        async with state.sub_lock:
            uid = getattr(websocket, 'user_id', None)
            if uid:
                state.user_clients.get(uid, {}).pop(str(id(websocket)), None)
                if not state.user_clients.get(uid):
                    state.user_clients.pop(uid, None)
        f = getattr(websocket, 'channel', None)
        if f:
            async with state.sub_lock:
                state.local_clients.get(f, {}).pop(str(id(websocket)), None)
                if not state.local_clients.get(f):
                    state.local_clients.pop(f, None)
                    ps = await _get_pubsub(state)
                    if ps is not None:
                        try:
                            await ps.unsubscribe(f)
                        except Exception:
                            pass
