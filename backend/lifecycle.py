import asyncio
import sys
import threading

from es import es
import db.conn
from db.roles import Roles
from db.table import Table
from db.tenants import TenantConnectionPool
from db.users import Users
from config import config
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
_bridge: PgNotifyBridge | None = None
_monitor: StreamMonitor | None = None
_dicom_thread: threading.Thread | None = None
_ingestion_worker = None
_ingestion_task: asyncio.Task | None = None
_dicom_scp = None
_mllp_task: asyncio.Task | None = None


def _start_dicom():
    global _dicom_scp
    try:
        from pynetdicom import AE, StoragePresentationContexts
        from pynetdicom.sop_class import (
            ModalityWorklistInformationFind,
            PatientRootQueryRetrieveInformationModelMove,
            StudyRootQueryRetrieveInformationModelMove,
            PatientRootQueryRetrieveInformationModelGet,
            StudyRootQueryRetrieveInformationModelGet,
        )
        import dcm.server as _dcm_server
        try:
            _dcm_server._loop = asyncio.get_running_loop()
        except RuntimeError:
            _dcm_server._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(_dcm_server._loop)
        ae = AE()
        ae.ae_title = config.get('dicom_ae_title', 'QUANTUMPACS')
        ae.supported_contexts = (
            StoragePresentationContexts
            + [ModalityWorklistInformationFind]
            + [
                PatientRootQueryRetrieveInformationModelMove,
                StudyRootQueryRetrieveInformationModelMove,
                PatientRootQueryRetrieveInformationModelGet,
                StudyRootQueryRetrieveInformationModelGet,
            ]
        )
        port = int(config.get('dicom_cstore_port', '11112'))
        _dicom_scp = ae.start_server(('', port), evt_handlers=_dcm_server.handlers)
        log.info('DICOM server started on port %s (C-STORE + MWL C-FIND)', port)
    except Exception:
        log.warning('Failed to start DICOM server', exc_info=True)
        _dicom_scp = None


def _run_dicom():
    global _dicom_thread, _dicom_scp
    try:
        from pynetdicom import AE, StoragePresentationContexts
        from dcm.server import handlers
        ae = AE()
        ae.ae_title = config.get('dicom_ae_title', 'QUANTUMPACS')
        ae.supported_contexts = StoragePresentationContexts
        port = int(config.get('dicom_cstore_port', '11112'))
        server = ae.start_server(('', port), evt_handlers=handlers)
        _dicom_scp = server
        log.info('DICOM C-STORE server started on port %s', port)
        server.serve_forever()
    except Exception:
        log.warning('Failed to start DICOM server', exc_info=True)
        _dicom_scp = None


def _start_dicom():
    global _dicom_thread
    _dicom_thread = threading.Thread(target=_run_dicom, daemon=True)
    _dicom_thread.start()


def _stop_dicom():
    global _dicom_scp, _dicom_thread
    if _dicom_scp is not None:
        try:
            _dicom_scp.shutdown()
            log.info('DICOM server stopped')
        except Exception:
            log.warning('DICOM server shutdown error', exc_info=True)
        _dicom_scp = None
    _dicom_thread = None


async def _start_mllp():
    global _mllp_task
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

        _mllp_task = asyncio.create_task(_run())
        log.info('MLLP server started on port %s', port)
    except Exception:
        log.warning('Failed to start MLLP server', exc_info=True)
        _mllp_task = None


def _stop_mllp():
    global _mllp_task
    if _mllp_task is not None:
        _mllp_task.cancel()
        _mllp_task = None
        log.info('MLLP server stopped')


async def setup(db_pool_size=None, sync_db=False, services=None):
    from api.tracing import setup_tracing
    setup_tracing()

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
            sys.exit(1)
        await asyncio.sleep(1)

    if not success:
        log.critical("Can't connect to database or elasticsearch: %s", last_exc)
        await teardown()
        sys.exit(1)

    log.info('Connected to database')
    await get_redis()

    global _bridge, _monitor, _ingestion_worker, _ingestion_task
    if redis_available():
        try:
            redis = await get_redis()
            _bridge = PgNotifyBridge(
                redis=redis,
                create_conn=db.conn.create_conn,
            )
            await _bridge.start()
            log.info('PG notify bridge started')

            from services.redis_streams import StreamConsumer
            _monitor = StreamMonitor(StreamConsumer(redis), poll_interval=15.0)
            _monitor.register('events:ingestion', 'ingestion-service')
            set_stream_monitor(_monitor)
            await _monitor.start()
            log.info('Stream monitor started')

            if services is not None:
                from services.ingestion import IngestionHandler, IngestionWorker
                handler = IngestionHandler(
                    metadata=services.get_or_none(_MetadataServiceProtocol),
                    storage=services.get_or_none(_StorageServiceProtocol),
                    search=services.get_or_none(_SearchServiceProtocol),
                )
                _ingestion_worker = IngestionWorker(redis=redis, handler=handler)
                await _ingestion_worker.start()
                _ingestion_task = asyncio.create_task(_ingestion_worker.run())
                log.info('Ingestion worker started')
        except Exception:
            log.warning('Failed to start bridge/monitor/worker', exc_info=True)
            _bridge = None
            _monitor = None
            _ingestion_worker = None
            _ingestion_task = None

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
            log.info('Database schema synced')


async def teardown():
    global _bridge, _monitor, _ingestion_worker, _ingestion_task
    _stop_dicom()
    _stop_mllp()
    if _ingestion_worker is not None:
        try:
            _ingestion_worker._shutdown.set()
        except Exception:
            pass
    if _ingestion_task is not None:
        try:
            _ingestion_task.cancel()
            await _ingestion_task
        except (asyncio.CancelledError, Exception):
            pass
        _ingestion_task = None
    _ingestion_worker = None
    if _monitor is not None:
        try:
            await _monitor.stop()
        except Exception:
            log.warning('Monitor stop error', exc_info=True)
        _monitor = None
    if _bridge is not None:
        try:
            await _bridge.stop()
        except Exception:
            log.warning('Bridge stop error', exc_info=True)
        _bridge = None
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
