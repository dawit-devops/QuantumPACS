from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
    SimpleSpanProcessor,
)

from config import config


def _build_resource() -> Resource:
    service_name = config.get('otel_service_name', 'quantumpacs-backend')
    deployment_env = config.get('otel_deployment_environment', 'development')
    return Resource.create({
        'service.name': service_name,
        'deployment.environment': deployment_env,
    })


def _build_exporter():
    endpoint = config.get('otel_exporter_otlp_endpoint', '')
    if endpoint:
        try:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
                OTLPSpanExporter,
            )
            return OTLPSpanExporter(endpoint=endpoint)
        except Exception:
            return ConsoleSpanExporter()
    return ConsoleSpanExporter()


def _build_processor(exporter):
    use_batch = config.get('otel_use_batch_processor', 'true').lower() != 'false'
    if not use_batch:
        return SimpleSpanProcessor(exporter)
    return BatchSpanProcessor(
        exporter,
        schedule_delay_millis=int(config.get('otel_bsp_schedule_delay', '5000')),
        max_queue_size=int(config.get('otel_bsp_max_queue_size', '2048')),
        max_export_batch_size=int(config.get('otel_bsp_max_export_batch_size', '512')),
    )


def setup_tracing():
    resource = _build_resource()
    provider = TracerProvider(resource=resource)
    exporter = _build_exporter()
    processor = _build_processor(exporter)
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)


def shutdown_tracing():
    provider = trace.get_tracer_provider()
    if hasattr(provider, 'shutdown'):
        try:
            provider.shutdown()
        except Exception:
            pass


def get_tracer(name: str = 'quantumpacs'):
    return trace.get_tracer(name)


def traced_connection(pool):
    tracer = get_tracer('quantumpacs.db')
    return _TracedPool(pool, tracer)


class _TracedPool:
    def __init__(self, pool, tracer):
        object.__setattr__(self, '_pool', pool)
        object.__setattr__(self, '_tracer', tracer)

    def __getattr__(self, name):
        if name == 'acquire':
            return self._traced_acquire
        return getattr(self._pool, name)

    def _traced_acquire(self, *args, **kwargs):
        ctx = self._pool.acquire(*args, **kwargs)
        return _TracedAcquireContext(ctx, self._tracer)


class _TracedAcquireContext:
    def __init__(self, ctx, tracer):
        self._ctx = ctx
        self._tracer = tracer

    async def __aenter__(self):
        conn = await self._ctx.__aenter__()
        return _TracedConnection(conn, self._tracer)

    async def __aexit__(self, *args):
        return await self._ctx.__aexit__(*args)


class _TracedConnection:
    def __init__(self, conn, tracer):
        object.__setattr__(self, '_conn', conn)
        object.__setattr__(self, '_tracer', tracer)

    def __getattr__(self, name):
        return getattr(self._conn, name)

    def __setattr__(self, name, value):
        setattr(self._conn, name, value)

    async def _trace_query(self, query, method, *args, **kwargs):
        import time
        from api.telemetry import db_query_duration_seconds
        start = time.monotonic()
        with self._tracer.start_as_current_span('db.query') as span:
            span.set_attribute('db.statement', query)
            span.set_attribute('db.system', 'postgresql')
            try:
                result = await getattr(self._conn, method)(query, *args, **kwargs)
            except Exception as exc:
                span.record_exception(exc)
                span.set_status(trace.Status(trace.StatusCode.ERROR))
                raise
        elapsed = time.monotonic() - start
        db_query_duration_seconds.labels(operation=method.upper()).observe(elapsed)
        return result

    async def fetchval(self, query, *args, **kwargs):
        return await self._trace_query(query, 'fetchval', *args, **kwargs)

    async def fetch(self, query, *args, **kwargs):
        return await self._trace_query(query, 'fetch', *args, **kwargs)

    async def fetchrow(self, query, *args, **kwargs):
        return await self._trace_query(query, 'fetchrow', *args, **kwargs)

    async def execute(self, query, *args, **kwargs):
        return await self._trace_query(query, 'execute', *args, **kwargs)
