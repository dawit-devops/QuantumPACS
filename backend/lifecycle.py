import asyncio
import sys
import threading
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Optional

import asyncpg

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
    mwl_sync_thread: Optional[threading.Thread] = None
    dcm4chee_sync_thread: Optional[threading.Thread] = None


def _run_dicom_mwl_scp(port):
    """Serve the MWL C-FIND model on a dedicated port.

    Runs in its own thread with its own AE. It must NOT touch
    dcm.server._loop — the main DICOM thread owns the (running) loop and the
    MWL handler bridges onto it via run_coroutine_threadsafe.
    """
    from pynetdicom import AE
    from pynetdicom.presentation import build_context
    from pynetdicom.sop_class import ModalityWorklistInformationFind
    import dcm.server as _dcm_server
    ae = AE()
    ae.ae_title = config.get('dicom_ae_title', 'QUANTUMPACS')
    _dcm_server.apply_association_policy(ae)
    ae.supported_contexts = [build_context(ModalityWorklistInformationFind)]
    server = ae.start_server(('', port), evt_handlers=_dcm_server.handlers, block=False)
    log.info('DICOM MWL server started on port %s', port)
    server.serve_forever()


def _run_dicom(loop=None):
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
        # The event handlers bridge into the async app with
        # asyncio.run_coroutine_threadsafe(coro, _dcm_server._loop). The
        # asyncpg pool / redis / ES clients are all bound to uvicorn's MAIN
        # loop — scheduling the coroutine on a second, foreign loop raises
        # "Future attached to a different loop", and a never-run loop makes
        # every C-FIND/C-STORE time out silently. So _start_dicom passes the
        # main loop in; tests may call _run_dicom() directly and get a
        # throwaway loop.
        if loop is not None:
            _dcm_server._loop = loop
        else:
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
        # block=False returns the server immediately; the subsequent
        # serve_forever() keeps this thread alive and lets _stop_dicom() call
        # shutdown() (block=True would block inside start_server, never set
        # state.dicom_scp and make graceful shutdown impossible).
        server = ae.start_server(('', port), evt_handlers=_dcm_server.handlers, block=False)
        if state:
            state.dicom_scp = server
        log.info('DICOM C-STORE server started on port %s', port)

        # Optional dedicated MWL listener: some modalities expect the
        # worklist on a separate port (e.g. 11113) while C-STORE stays on
        # 11112. Daemon thread dies with the process.
        mwl_port = config.get('dicom_mwl_port', '')
        if mwl_port and int(mwl_port) != port:
            threading.Thread(target=_run_dicom_mwl_scp, args=(int(mwl_port),), daemon=True).start()

        server.serve_forever()
    except Exception:
        log.warning('Failed to start DICOM server', exc_info=True)


def _start_dicom():
    state = get_app_state()
    try:
        # Hand the uvicorn main loop to the SCP thread so DB pool / redis /
        # ES lookups inside the DICOM handlers run on the loop that owns
        # those clients.
        main_loop = asyncio.get_running_loop()
    except RuntimeError:
        main_loop = None
    thread = threading.Thread(target=_run_dicom, args=(main_loop,), daemon=True)
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
        from services.hl7_engine.service import Hl7InterfaceEngine
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
        # Single engine entry point (S3-18): the wire must exercise the same
        # parse -> persist -> route -> alert pipeline as the HTTP receiver,
        # so dashboard, exception queue, and failure alerts see MLLP feeds too.
        server = MllpServer(
            host='', port=port, ssl_context=ssl_context, allowed_ips=allowed_ips,
            handler=Hl7InterfaceEngine().receive_message,
        )

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
                tenant_conns=await _tenant_notify_factories(),
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

    # ADR-028 Phase 3: mirror worklist_entries to dcm4chee via MWL-RS when the
    # DICOMweb proxy is enabled. start_mwl_sync no-ops otherwise.
    try:
        from api.mwl_sync import start_mwl_sync
        thread = start_mwl_sync()
        state_mwl = get_app_state()
        if state_mwl and thread is not None:
            state_mwl.mwl_sync_thread = thread
    except Exception:
        log.warning('Failed to start MWL-RS sync worker', exc_info=True)

    # ADR-028 Phase 3: self-heal the archive→feed path — scan dcm4chee
    # QIDO-RS and request export REST for studies QuantumPACS does not know
    # (stored while the feed SCP was down). No-ops when dicom_proxy=false.
    try:
        from services.dcm4chee_sync import start_dcm4chee_sync
        thread = start_dcm4chee_sync()
        state_d4c = get_app_state()
        if state_d4c and thread is not None:
            state_d4c.dcm4chee_sync_thread = thread
    except Exception:
        log.warning('Failed to start dcm4chee self-heal sync worker', exc_info=True)

    # Registry bootstrap must not ride the sync_db gate: CI e2e and container
    # entrypoints boot uvicorn with sync_db=False, and until the `default`
    # tenant's registry row exists every tenant-scoped request fails closed
    # with 403 "Tenant not available" (tenant_middleware R5-04). Its data
    # store IS the main database, so the row is pure registry metadata.
    # Idempotent (no-op once tenants exist) and non-fatal pre-migration.
    # Pool guard: the no-services lifecycle unit test boots without a pool.
    if db.conn.get_database().pool is not None:
        async with db.conn.get_conn() as conn:
            await _ensure_default_tenant(conn)

            # The superadmin account gets the same treatment: CI/dev/docker
            # boots never sync_db, and without the admin row the admin-login
            # e2e specs (and any bare deployment's first login) dead-end at
            # the login page. Idempotent — skipped when the row already
            # exists — and keyed to config superadmin_pass so password parity
            # holds across environments.
            await Users(conn).add_superadmin()

    if sync_db:
        async with db.conn.get_conn() as conn:
            for t in Table.tables:
                try:
                    await t(conn).sync_db()
                except Exception:
                    log.error('Table sync failed: %s', t.name)
                    raise

            await Roles(conn).seed_built_in_roles()
            log.info('Database schema synced')


async def _tenant_notify_factories():
    """Per-tenant PG NOTIFY listener factories (HI-04).

    Tenant databases run the same schema as the main database — including the
    notify_event trigger — so file writes there would otherwise be invisible
    to the ingestion pipeline. Each active, non-main-store tenant gets its
    own dedicated listener connection; the bridge tags its events with the
    tenant slug. The tenant_info dict is bound via a default arg so the
    closure does not capture the loop variable.
    """
    from db.tenants import uses_main_database
    factories: list[tuple[str, Callable[[], Awaitable[Any]]]] = []
    try:
        async with db.conn.get_conn() as conn:
            rows = await conn.fetch(
                'SELECT slug, db_name, db_host, db_port, db_user, db_password'
                ' FROM tenants WHERE status = $1',
                'active',
            )
        for row in rows:
            info = dict(row)
            if uses_main_database(info):
                continue
            slug = info['slug']

            async def _factory(_info=info):
                return await asyncpg.connect(
                    user=_info['db_user'],
                    password=_info['db_password'],
                    database=_info['db_name'],
                    host=_info.get('db_host') or config['db_host'],
                    port=int(_info.get('db_port') or config.get('db_port', '5432')),
                )

            factories.append((slug, _factory))
    except Exception:
        log.warning('Could not build tenant notify listeners', exc_info=True)
    return factories


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
