import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestTracingMiddleware:
    async def test_middleware_calls_next_with_scope(self):
        from api.tracing_middleware import TracingMiddleware
        next_app = AsyncMock()
        mw = TracingMiddleware(next_app)
        scope = {'type': 'http', 'method': 'GET', 'path': '/api/test'}
        receive = AsyncMock()
        send = AsyncMock()
        await mw(scope, receive, send)
        next_app.assert_called_once()

    async def test_middleware_creates_span_around_request(self):
        from api.tracing_middleware import TracingMiddleware
        mock_span_cm = MagicMock()
        mock_span = MagicMock()
        mock_span_cm.__enter__.return_value = mock_span
        mock_tracer = MagicMock()
        mock_tracer.start_as_current_span.return_value = mock_span_cm

        with patch('api.tracing_middleware.get_tracer', return_value=mock_tracer):
            mw = TracingMiddleware(AsyncMock())
            scope = {'type': 'http', 'method': 'POST', 'path': '/api/ingest'}
            await mw(scope, AsyncMock(), AsyncMock())
            mock_tracer.start_as_current_span.assert_called_once()
            span_name = mock_tracer.start_as_current_span.call_args.args[0]
            assert 'POST' in span_name

    async def test_middleware_skips_non_http_requests(self):
        from api.tracing_middleware import TracingMiddleware
        next_app = AsyncMock()
        mw = TracingMiddleware(next_app)
        scope = {'type': 'websocket'}
        await mw(scope, AsyncMock(), AsyncMock())
        next_app.assert_called_once()

    async def test_middleware_records_exception(self):
        from api.tracing_middleware import TracingMiddleware
        mock_span = MagicMock()
        mock_span_cm = MagicMock()
        mock_span_cm.__enter__.return_value = mock_span

        mock_tracer = MagicMock()
        mock_tracer.start_as_current_span.return_value = mock_span_cm

        error_app = AsyncMock(side_effect=RuntimeError('boom'))

        with patch('api.tracing_middleware.get_tracer', return_value=mock_tracer):
            mw = TracingMiddleware(error_app)
            scope = {'type': 'http', 'method': 'GET', 'path': '/x'}
            with pytest.raises(RuntimeError):
                await mw(scope, AsyncMock(), AsyncMock())
            mock_span.record_exception.assert_called_once()
            mock_span.set_status.assert_called_once()
