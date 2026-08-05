import asyncio
from collections import defaultdict

from starlette.endpoints import HTTPEndpoint, WebSocketEndpoint
from starlette.websockets import WebSocket, WebSocketDisconnect

from api.response import ok
from api.tokens import create_token as gen_token

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


def _channel(file_id):
    return f'channel:file:{file_id}'


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
            file_id = channel.split(':', 2)[-1]
            data = message['data']
            if isinstance(data, bytes):
                data = data.decode()
            import json
            try:
                payload = json.loads(data)
            except Exception:
                continue
            async with state.sub_lock:
                conns = list(state.local_clients.get(file_id, {}).values())
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

        type_ = data.get('type')

        match type_:
            case 'open':
                f = data['file']
                async with state.sub_lock:
                    state.local_clients[f][str(id(websocket))] = websocket
                ps = await _get_pubsub(state)
                if ps is not None:
                    try:
                        await ps.subscribe(_channel(f))
                        _ensure_listener(state)
                    except Exception:
                        pass
                await websocket.send_json(
                    {
                        'type': 'send_state',
                        'file': f,
                        'state': data.get('state', {}),
                    },
                )
                websocket.file = f

            case 'send_state':
                f = data['file']
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
                    await r.publish(_channel(f), json.dumps(payload))
                except Exception:
                    async with state.sub_lock:
                        conns = list(state.local_clients.get(f, {}).values())
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
        f = getattr(websocket, 'file', None)
        if f:
            async with state.sub_lock:
                state.local_clients[f].pop(str(id(websocket)), None)
                if not state.local_clients[f]:
                    del state.local_clients[f]
                    ps = await _get_pubsub(state)
                    if ps is not None:
                        try:
                            await ps.unsubscribe(_channel(f))
                        except Exception:
                            pass
