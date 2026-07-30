import asyncio
from collections import defaultdict

from starlette.endpoints import HTTPEndpoint, WebSocketEndpoint
from starlette.websockets import WebSocket, WebSocketDisconnect

from api.response import ok
from api.tokens import create_token as gen_token

local_clients = defaultdict(dict)
_sub_lock = asyncio.Lock()
_pubsub = None


async def _get_pubsub():
    global _pubsub
    if _pubsub is not None:
        return _pubsub
    try:
        import redis.asyncio as aioredis
        from config import config
        host = config.get('redis_host', 'localhost')
        port = int(config.get('redis_port', '6379'))
        password = config.get('redis_password') or None
        r = aioredis.Redis(
            host=host, port=port, password=password, db=4,
            socket_connect_timeout=1,
            socket_timeout=2,
        )
        await r.ping()
        _pubsub = r.pubsub()
        return _pubsub
    except Exception:
        return None


def _channel(file_id):
    return f'channel:file:{file_id}'


async def _pubsub_listener():
    ps = await _get_pubsub()
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
            async with _sub_lock:
                conns = list(local_clients.get(file_id, {}).values())
            for c in conns:
                if isinstance(c, WebSocket):
                    try:
                        await c.send_json(payload)
                    except WebSocketDisconnect:
                        pass
    except Exception:
        pass


_listener_task = None
_cleanup_task = None


def _ensure_listener():
    global _listener_task, _cleanup_task
    if _listener_task is None or _listener_task.done():
        _listener_task = asyncio.create_task(_pubsub_listener())
    if _cleanup_task is None or _cleanup_task.done():
        _cleanup_task = asyncio.create_task(_stale_cleanup())


async def _stale_cleanup():
    while True:
        await asyncio.sleep(30)
        async with _sub_lock:
            for file_id in list(local_clients):
                file_clients = local_clients[file_id]
                stale = [k for k, v in file_clients.items() if isinstance(v, WebSocket) and v.client_state == 3]
                for k in stale:
                    del file_clients[k]
                if not file_clients:
                    del local_clients[file_id]


class WSToken(HTTPEndpoint):
    async def get(self, request):
        token = gen_token(request.user.to_dict(), {'minutes': 1})
        return ok({'token': token})


class WebsocketHandler(WebSocketEndpoint):
    encoding = 'json'

    async def on_connect(self, websocket):
        await websocket.accept()

    async def on_receive(self, websocket, data):
        type_ = data.get('type')

        match type_:
            case 'open':
                f = data['file']
                async with _sub_lock:
                    local_clients[f][str(id(websocket))] = websocket
                ps = await _get_pubsub()
                if ps is not None:
                    try:
                        await ps.subscribe(_channel(f))
                        _ensure_listener()
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
                    import redis.asyncio as aioredis
                    from config import config
                    host = config.get('redis_host', 'localhost')
                    port = int(config.get('redis_port', '6379'))
                    password = config.get('redis_password') or None
                    r = aioredis.Redis(
                        host=host, port=port, password=password, db=4,
                        socket_connect_timeout=1,
                        socket_timeout=1,
                    )
                    await r.publish(_channel(f), json.dumps(payload))
                    await r.aclose()
                except Exception:
                    async with _sub_lock:
                        conns = list(local_clients.get(f, {}).values())
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
        f = getattr(websocket, 'file', None)
        if f:
            async with _sub_lock:
                local_clients[f].pop(str(id(websocket)), None)
                if not local_clients[f]:
                    del local_clients[f]
                    ps = await _get_pubsub()
                    if ps is not None:
                        try:
                            await ps.unsubscribe(_channel(f))
                        except Exception:
                            pass
