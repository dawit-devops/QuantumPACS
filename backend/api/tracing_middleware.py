from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

from api.tracing import get_tracer


class TracingMiddleware:
    def __init__(self, app):
        self.app = app
        self._tracer = get_tracer('quantumpacs.http')

    async def __call__(self, scope, receive, send):
        if scope.get('type') != 'http':
            await self.app(scope, receive, send)
            return

        method = scope.get('method', 'GET')
        path = scope.get('path', '/')
        span_name = f'HTTP {method} {path}'

        with self._tracer.start_as_current_span(span_name) as span:
            span.set_attribute('http.method', method)
            span.set_attribute('http.target', path)
            span.set_attribute('http.scheme', scope.get('scheme', 'http'))

            async def wrapped_send(message):
                if message.get('type') == 'http.response.start':
                    status_code = message.get('status', 0)
                    span.set_attribute('http.status_code', status_code)
                    if status_code >= 500:
                        span.set_status(Status(StatusCode.ERROR))
                await send(message)

            try:
                await self.app(scope, receive, wrapped_send)
            except Exception as exc:
                span.record_exception(exc)
                span.set_status(Status(StatusCode.ERROR))
                raise
