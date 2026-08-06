import asyncio
import sys
import threading
from dataclasses import dataclass
from typing import Any, Optional

from es import es
import db.conn
from db.roles import Roles
from db.table import Table
from db.tenants import TenantConnectionPool
from db.users import Users
from config import config, is_docker
from log import get_logger
from api.redis_client import get_client as get_redis
from api.redis_client import is_available as redis_available
from api.telemetry import set_stream_monitor
from services.interfaces import (
    MetadataService as _MetadataServiceProtocol,
    SearchService as _SearchServiceProtocol,
    StorageService as _StorageServiceProtocol,
)
from services.pg_notify_bridge import PgNotifyBridge
from services.stream_monitor import StreamMonitor

log = get_logger(__name__)

_RETRYABLE = (ConnectionError, OSError, asyncio.TimeoutError)

_app: Any = None


def set_app(app):
    global _app
    _app = app


def get_app_state() -> Optional['LifecycleState']:
    if _app is None:
        return None
    if not hasattr(_app.state, 'lifecycle'):
        _app.state.lifecycle = LifecycleState()
    return _app.state.lifecycle


@dataclass
class LifecycleState:
    bridge: Optional[PgNotifyBridge] = None
    monitor: Optional[StreamMonitor] = None
    dicom_thread: Optional[threading.Thread] = None
    ingestion_worker: Any = None
    ingestion_task: Optional[asyncio.Task] = None
    dicom_scp: Any = None
    mllp_task: Optional[asyncio.Task] = None


def _run_dicom():
    state = get_app_state()
    try:
        from pynetdicom import AE, StoragePresentationContexts
        from pynetdicom.presentation import build_context
        from pynetdicom.sop_class import (
            ModalityWorklistInformationFind,
            PatientRootQueryRetrieveInformationModelFind,
            StudyRootQueryRetrieveInformationModelFind,
        )
        import dcm.server as _dcm_server
        try:
            _dcm_server._loop = asyncio.get_running_loop()
        except RuntimeError:
            _dcm_server._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(_dcm_server._loop)
        ae = AE()
        ae.ae_title = config.get('dicom_ae_title', 'QUANTUMPACS')
        _dcm_server.apply_association_policy(ae)
        ae.supported_contexts = (
            StoragePresentationContexts
            + [build_context(ModalityWorklistInformationFind)]
            + [
                # Q/R C-FIND only. C-MOVE/C-GET are NOT advertised: the old
                # handlers answered 0x0000 (Success) without transferring any
                # data, which silently breaks SCUs — refusing the association
                # is the honest behaviour until retrieval is implemented.
                build_context(PatientRootQueryRetrieveInformationModelFind),
                build_context(StudyRootQueryRetrieveInformationModelFind),
            ]
        )
        port = int(config.get('dicom_cstore_port', '11112'))
        server = ae.start_server(('', port), evt_handlers=_dcm_server.handlers)
        if state:
            state.dicom_scp = server
        log.info('DICOM C-STORE server started on port %s', port)
        server.serve_forever()
    except Exception:
        log.warning('Failed to start DICOM server', exc_info=True)


def _start_dicom():
    state = get_app_state()
    thread = threading.Thread(target=_run_dicom, daemon=True)
    if state:
        state.dicom_thread = thread
    thread.start()


def _stop_dicom():
    state = get_app_state()
    if state and state.dicom_scp is not None:
        try:
            state.dicom_scp.shutdown()
            log.info('DICOM server stopped')
        except Exception:
            log.warning('DICOM server shutdown error', exc_info=True)
        state.dicom_scp = None
    if state:
        state.dicom_thread = None


async def _start_mllp():
    state = get_app_state()
    try:
        import ssl
        from services.ingestion.hl7_server import MllpServer
        port = int(config.get('hl7_mllp_port', '12579'))
        ssl_context = None
        cert_file = config.get('hl7_mllp_tls_cert', '')
        key_file = config.get('hl7_mllp_tls_key', '')
        if cert_file and key_file:
            ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            ssl_context.load_cert_chain(cert_file, key_file)
        allowed_ips_str = config.get('hl7_mllp_allowed_ips', '')
        allowed_ips = [ip.strip() for ip in allowed_ips_str.split(',') if ip.strip()] if allowed_ips_str else []
        server = MllpServer(host='', port=port, ssl_context=ssl_context, allowed_ips=allowed_ips)

        async def _run():
            await server.start()
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                pass
            await server.stop()

        task = asyncio.create_task(_run())
        if state:
            state.mllp_task = task
        log.info('MLLP server started on port %s', port)
    except Exception:
        log.warning('Failed to start MLLP server', exc_info=True)
        if state:
            state.mllp_task = None


def _stop_mllp():
    state = get_app_state()
    if state and state.mllp_task is not None:
        state.mllp_task.cancel()
        state.mllp_task = None
        log.info('MLLP server stopped')


async def setup(db_pool_size=None, sync_db=False, services=None):
    from api.tracing import setup_tracing
    setup_tracing()

    if not is_docker() and not config.get('redis_password'):
        log.critical('SECURITY: redis_password must be set in production (non-Docker mode). Set REDIS_PASSWORD env var or config.local.yaml.')
        sys.exit(1)

    success = False
    last_exc = None
    for i in range(30):
        try:
            await db.conn.setup(pool_size=db_pool_size)
            await es.setup()
            success = True
            break
        except _RETRYABLE as e:
            log.warning('Startup attempt %d/30 failed: %s', i + 1, e)
            last_exc = e
            try:
                await teardown()
            except Exception:
                pass
        except Exception as e:
            log.critical('Non-retryable startup error: %s', e)
            await teardown()
            raise
        await asyncio.sleep(0.5 * 2 ** i)

    if not success:
        log.critical("Can't connect to database or elasticsearch: %s", last_exc)
        await teardown()
        raise RuntimeError(f'Startup failed after 30 retries: {last_exc}')

    log.info('Connected to database')
    await get_redis()

    state = get_app_state()
    if redis_available():
        try:
            redis = await get_redis()
            bridge = PgNotifyBridge(
                redis=redis,
                create_conn=db.conn.create_conn,
            )
            await bridge.start()
            if state:
                state.bridge = bridge
            log.info('PG notify bridge started')

            from services.redis_streams import StreamConsumer
            monitor = StreamMonitor(StreamConsumer(redis), poll_interval=15.0)
            monitor.register('events:ingestion', 'ingestion-service')
            set_stream_monitor(monitor)
            await monitor.start()
            if state:
                state.monitor = monitor
            log.info('Stream monitor started')

            if services is not None:
                from services.ingestion import IngestionHandler, IngestionWorker
                handler = IngestionHandler(
                    metadata=services.get_or_none(_MetadataServiceProtocol),
                    storage=services.get_or_none(_StorageServiceProtocol),
                    search=services.get_or_none(_SearchServiceProtocol),
                )
                worker = IngestionWorker(redis=redis, handler=handler)
                await worker.start()
                task = asyncio.create_task(worker.run())
                if state:
                    state.ingestion_worker = worker
                    state.ingestion_task = task
                log.info('Ingestion worker started')
        except Exception:
            log.warning('Failed to start bridge/monitor/worker', exc_info=True)
            if state:
                state.bridge = None
                state.monitor = None
                state.ingestion_worker = None
                state.ingestion_task = None

    _start_dicom()
    await _start_mllp()

    if sync_db:
        async with db.conn.get_conn() as conn:
            for t in Table.tables:
                try:
                    await t(conn).sync_db()
                except Exception:
                    log.error('Table sync failed: %s', t.name)
                    raise

            await Roles(conn).seed_built_in_roles()
            await Users(conn).add_superadmin()
            await _ensure_default_tenant(conn)
            log.info('Database schema synced')


async def _ensure_default_tenant(conn):
    """Seed the `default` tenant when the registry is empty. Its data store IS
    the main database, so db_* fields mirror the main config; the middleware
    short-circuits to the main pool for it. Existing users are NOT reassigned."""
    from db.tenants import Tenants
    try:
        count = await conn.fetchval('SELECT COUNT(*) FROM tenants')
        if count:
            return
        await Tenants(conn).create(
            name='Default',
            slug='default',
            db_name=config['db_database'],
            db_host=config['db_host'],
            db_port=int(config.get('db_port', '5432')),
            db_user=config['db_user'],
            db_password=config['db_password'],
            storage_quota_bytes=int(config.get('tenant_default_quota_bytes', '0')),
            status='active',
            plan='free',
        )
        log.info('Seeded default tenant (slug=default, data store=main database)')
    except Exception:
        # tenants table may not exist yet (migrations not run) — non-fatal.
        log.warning('Could not seed default tenant', exc_info=True)


async def teardown():
    state = get_app_state()
    _stop_dicom()
    _stop_mllp()
    if state:
        if state.ingestion_worker is not None:
            try:
                state.ingestion_worker._shutdown.set()
            except Exception:
                pass
        if state.ingestion_task is not None:
            try:
                state.ingestion_task.cancel()
                await state.ingestion_task
            except (asyncio.CancelledError, Exception):
                pass
            state.ingestion_task = None
        state.ingestion_worker = None
        if state.monitor is not None:
            try:
                await state.monitor.stop()
            except Exception:
                log.warning('Monitor stop error', exc_info=True)
            state.monitor = None
        if state.bridge is not None:
            try:
                await state.bridge.stop()
            except Exception:
                log.warning('Bridge stop error', exc_info=True)
            state.bridge = None
    await TenantConnectionPool.close_all()
    await db.conn.teardown()
    await es.teardown()
    from api.redis_client import close_client as close_redis
    await close_redis()

    try:
        from api.tracing import shutdown_tracing
        shutdown_tracing()
    except Exception:
        log.warning('Tracing shutdown error', exc_info=True)

    log.info('Shutdown complete')
