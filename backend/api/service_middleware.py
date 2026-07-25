from starlette.middleware.base import BaseHTTPMiddleware


class ServiceMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        registry = getattr(request.app.state, 'services', None)
        request.state.services = registry
        return await call_next(request)