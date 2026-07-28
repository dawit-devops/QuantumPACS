import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from api import tracing


class TestTracingSetup:
    def teardown_method(self):
        from opentelemetry import trace
        existing = trace._TRACER_PROVIDER
        if existing is not None and hasattr(existing, 'shutdown'):
            try:
                existing.shutdown()
            except Exception:
                pass
        trace._TRACER_PROVIDER_SET_ONCE._done = False
        trace._TRACER_PROVIDER = None

    def test_setup_tracing_uses_batch_processor(self):
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.sdk.trace import TracerProvider
        with patch('api.tracing.TracerProvider') as mock_provider_cls, \
             patch('api.tracing.ConsoleSpanExporter'):
            mock_provider = MagicMock()
            mock_provider_cls.return_value = mock_provider
            tracing.setup_tracing()
            mock_provider.add_span_processor.assert_called_once()
            args = mock_provider.add_span_processor.call_args.args
            assert any(isinstance(a, BatchSpanProcessor) for a in args)

    def test_setup_tracing_attaches_resource(self):
        with patch('api.tracing.TracerProvider') as mock_provider_cls, \
             patch('api.tracing.Resource') as mock_resource:
            mock_provider = MagicMock()
            mock_provider_cls.return_value = mock_provider
            tracing.setup_tracing()
            mock_resource.create.assert_called_once()
            attrs = mock_resource.create.call_args.args[0]
            assert 'service.name' in attrs

    def test_setup_tracing_uses_otlp_when_endpoint_set(self, monkeypatch):
        mock_provider = MagicMock()
        with patch('api.tracing.TracerProvider', return_value=mock_provider), \
             patch('api.tracing._build_exporter') as mock_build, \
             patch('api.tracing.config', {
                 'otel_exporter_otlp_endpoint': 'http://otel.example:4317',
                 'otel_service_name': 'test',
                 'otel_deployment_environment': 'test',
                 'otel_use_batch_processor': 'true',
                 'otel_bsp_schedule_delay': '5000',
                 'otel_bsp_max_queue_size': '2048',
                 'otel_bsp_max_export_batch_size': '512',
             }):
            mock_exporter = MagicMock()
            mock_build.return_value = mock_exporter
            tracing.setup_tracing()
            mock_build.assert_called_once()

    def test_setup_tracing_falls_back_to_console_when_no_endpoint(self):
        with patch.dict('os.environ', {}, clear=False):
            with patch('api.tracing.ConsoleSpanExporter') as mock_console:
                with patch('api.tracing.config', {'otel_exporter_otlp_endpoint': ''}):
                    tracing.setup_tracing()
                    mock_console.assert_called()

    def test_shutdown_calls_provider_shutdown(self):
        from opentelemetry import trace
        mock_provider = MagicMock()
        mock_provider.shutdown = MagicMock()
        trace._TRACER_PROVIDER = mock_provider

        tracing.shutdown_tracing()
        mock_provider.shutdown.assert_called_once()
