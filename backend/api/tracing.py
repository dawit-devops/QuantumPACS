from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor

from config import config


def setup_tracing():
    endpoint = config.get('otel_exporter_otlp_endpoint', '')
    service_name = config.get('otel_service_name', 'quantumpacs-backend')
    provider = TracerProvider()
    if endpoint:
        try:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
            processor = SimpleSpanProcessor(OTLPSpanExporter(endpoint=endpoint))
        except Exception:
            processor = SimpleSpanProcessor(ConsoleSpanExporter())
    else:
        processor = SimpleSpanProcessor(ConsoleSpanExporter())
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)


def get_tracer(name: str = 'quantumpacs'):
    return trace.get_tracer(name)


def traced_connection(pool):
    tracer = get_tracer('quantumpacs.db')
    original_acquire = pool.acquire

    def traced_acquire(*args, **kwargs):
        ctx = original_acquire(*args, **kwargs)
        return _TracedAcquireContext(ctx, tracer)

    pool.acquire = traced_acquire
    return pool


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

    async def fetchval(self, query, *args, **kwargs):
        with self._tracer.start_as_current_span('db.query') as span:
            span.set_attribute('db.statement', query)
            span.set_attribute('db.system', 'postgresql')
            return await self._conn.fetchval(query, *args, **kwargs)

    async def fetch(self, query, *args, **kwargs):
        with self._tracer.start_as_current_span('db.query') as span:
            span.set_attribute('db.statement', query)
            span.set_attribute('db.system', 'postgresql')
            return await self._conn.fetch(query, *args, **kwargs)

    async def fetchrow(self, query, *args, **kwargs):
        with self._tracer.start_as_current_span('db.query') as span:
            span.set_attribute('db.statement', query)
            span.set_attribute('db.system', 'postgresql')
            return await self._conn.fetchrow(query, *args, **kwargs)

    async def execute(self, query, *args, **kwargs):
        with self._tracer.start_as_current_span('db.query') as span:
            span.set_attribute('db.statement', query)
            span.set_attribute('db.system', 'postgresql')
            return await self._conn.execute(query, *args, **kwargs)