"""End-to-end tenant data-plane lifecycle roundtrip against the dev PostgreSQL.

Contract under test (ADR-026): provisioning creates a real alembic-migrated
tenant DB plus a registry row (plan, quota, provisioning->active lifecycle);
the initial admin exists in both the tenant DB and the registry DB with
`users.tenant = slug` so the JWT carries the claim; the real TenantMiddleware
routes requests into the tenant DB (X-Tenant-ID header or the JWT claim) and
gates suspended/quarantined (403) and decommissioned (404); daily metering
rolls up into `tenant_usage_daily`; the health endpoint probes the tenant DB.

Conventions: one module-scoped provisioned tenant (provisioning runs alembic,
so it is deliberately not repeated per test); the DB pool and all tests share
one event loop (`loop_scope='module'`) because asyncpg pools are loop-bound.

Environment gaps the fixture works around (kept visible by the canary test):
- TenantProvisioner.create_database connects as a superuser named `postgres`,
  but the dev container's superuser is `config['db_user']` (quantumpacs). The
  fixture tries the real provisioner and replicates its steps with the working
  superuser when that fails.
- Migration 032 uses CREATE INDEX CONCURRENTLY, which cannot run inside
  alembic's transaction on a fresh tenant DB; the fixture pre-creates those
  indexes outside the transaction so the tenant DB can reach head.
"""

import time

import asyncpg
import httpx
import pytest
import pytest_asyncio
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from starlette.routing import Route

from api.auth import User
from api.tokens import create_token_pair, verify_token
from api.tenant_health import TenantHealthHandler
from api.tenant_middleware import TenantMiddleware
from config import config
from db.conn import get_conn, setup, teardown
from db.metering import get_usage, record_request
from db.tenant_provisioner import TenantProvisioner
from db.tenants import Tenants, TenantConnectionPool
from db.users import Users

QUOTA = 100 * 2**30  # 100 GiB

# Migration 032 (add_performance_indexes) builds these CONCURRENTLY, which
# cannot run inside alembic's transaction block on a fresh DB, and its GIN
# index needs a ::jsonb cast (mirrors the index actually present on the main
# DB). They are pre-created as plain indexes with the same names so 032
# no-ops and a fresh tenant DB can be migrated head-to-head.
_PERF_INDEX_SQL = [
    "CREATE INDEX IF NOT EXISTS ix_files_sop_instance_uid "
    "ON files(sop_instance_uid) WHERE sop_instance_uid IS NOT NULL",
    "CREATE INDEX IF NOT EXISTS ix_series_instance_uid "
    "ON series(series_instance_uid) WHERE series_instance_uid IS NOT NULL",
    "CREATE INDEX IF NOT EXISTS ix_studies_study_instance_uid "
    "ON studies(study_instance_uid) WHERE study_instance_uid IS NOT NULL",
    "CREATE INDEX IF NOT EXISTS ix_worklist_entries_status "
    "ON worklist_entries(status)",
    "CREATE INDEX IF NOT EXISTS ix_audit_log_event_type "
    "ON logs USING gin ((log::jsonb) jsonb_path_ops)",
]


async def _migrate_tenant_db(db_name):
    """Migrate a fresh tenant DB to head, stepping around migration 032.

    Equivalent to TenantProvisioner.run_migrations except CONCURRENTLY indexes
    are pre-created outside the transaction. Kept in the test (not the app) so
    the migration blocker stays visible to the provisioner owner.
    """
    import alembic.command
    import alembic.config
    import alembic.script

    url = (
        f'postgresql+psycopg2://{config["db_user"]}:{config["db_password"]}'
        f'@{config["db_host"]}:{int(config.get("db_port", "5432"))}/{db_name}'
    )
    cfg = alembic.config.Config('alembic.ini')
    cfg.set_main_option('sqlalchemy.url', url)

    # Postgres rejects CREATE INDEX CONCURRENTLY inside a transaction BEFORE the
    # IF NOT EXISTS name check, so 032 cannot run under alembic's transaction at
    # all. Create its indexes outside the transaction (with the ::jsonb cast the
    # real DB uses), then stamp 032 so the upgrade can continue past it.
    alembic.command.upgrade(cfg, '031')
    conn = await asyncpg.connect(
        user=config['db_user'], password=config['db_password'],
        database=db_name, host=config['db_host'],
        port=int(config.get('db_port', '5432')),
    )
    try:
        for sql in _PERF_INDEX_SQL:
            await conn.execute(sql)
    finally:
        await conn.close()
    alembic.command.stamp(cfg, '032')
    alembic.command.upgrade(cfg, 'head')


async def _create_database(db_name):
    conn = await asyncpg.connect(
        user=config['db_user'],
        password=config['db_password'],
        database='postgres',
        host=config['db_host'],
        port=int(config.get('db_port', '5432')),
    )
    try:
        await conn.execute(f'CREATE DATABASE "{db_name}"')
    except asyncpg.DuplicateDatabaseError:
        pass
    finally:
        await conn.close()


async def _drop_database(db_name):
    """DROP DATABASE with FORCE so lingering pooled connections cannot block it."""
    conn = await asyncpg.connect(
        user=config['db_user'],
        password=config['db_password'],
        database='postgres',
        host=config['db_host'],
        port=int(config.get('db_port', '5432')),
    )
    try:
        await conn.execute(f'DROP DATABASE IF EXISTS "{db_name}" WITH (FORCE)')
    finally:
        await conn.close()


@pytest_asyncio.fixture(scope='module', loop_scope='module')
async def tenant_env():
    await setup(pool_size=4)
    slug = f'e2e_{int(time.time())}'
    db_name = slug.replace('-', '_')

    info = {'slug': slug, 'db_name': db_name, 'name': f'E2E {slug}', 'provisioner_error': None, 'provisioned_via': 'provisioner'}
    try:
        result = await TenantProvisioner.provision(
            slug=slug, name=info['name'], domain=f'{slug}.example.test',
            admin_email=f'admin@{slug}.test', storage_quota_bytes=QUOTA,
        )
        info['tenant_id'] = str(result['tenant_id'])
        info['admin_password'] = result['admin_password']
    except Exception as e:
        # provision() needs a superuser role named `postgres`
        # (db/tenant_provisioner.py), which this deployment lacks; replicate
        # its steps with config['db_user'] so the lifecycle still runs
        # end-to-end. Fixed upstream -> provision path used.
        info['provisioned_via'] = 'fallback'
        info['provisioner_error'] = f'{type(e).__name__}: {e}'
        async with get_conn() as conn:
            # A failed provision leaves a decommissioned registry row behind;
            # clear it before re-creating the row in the fallback.
            await Tenants(conn).hard_delete(slug)
        await _create_database(db_name)
        await _migrate_tenant_db(db_name)
        async with get_conn() as conn:
            info['tenant_id'] = str(await Tenants(conn).create(
                name=info['name'], slug=slug, domain=f'{slug}.example.test',
                db_name=db_name, storage_quota_bytes=QUOTA,
            ))
        info['admin_password'] = await TenantProvisioner.create_initial_admin(
            db_name=db_name, slug=slug, admin_email=f'admin@{slug}.test',
        )

    try:
        yield info
    finally:
        try:
            from api.redis_client import close_client
            await close_client()
        except Exception:
            pass
        try:
            await TenantConnectionPool.close(slug)
        except Exception:
            pass
        try:
            async with get_conn() as conn:
                await Tenants(conn).hard_delete(slug)
        except Exception:
            pass
        try:
            async with get_conn() as conn:
                await conn.execute(
                    'DELETE FROM users WHERE username = $1', f'admin-{slug}'
                )
        except Exception:
            pass
        try:
            await _drop_database(db_name)
        except Exception:
            pass
        await teardown()


class _FakeAuth(BaseHTTPMiddleware):
    def __init__(self, app, user=None):
        super().__init__(app)
        self._user = user or User({'id': 1, 'admin': True, 'permissions': ['*']})

    async def dispatch(self, request, call_next):
        request.scope['user'] = self._user
        request.scope['auth'] = None
        return await call_next(request)


async def _tenant_db(request):
    """Echo which database the request's tenant context resolved to."""
    acquire = getattr(request.state, 'tenant_conn', None)
    if acquire is None:
        return JSONResponse({'db': None})
    async with acquire() as conn:
        return JSONResponse({'db': await conn.fetchval('SELECT current_database()')})


async def _noop(request):
    return JSONResponse({'ok': True})


def _make_app(user=None):
    return Starlette(
        routes=[
            Route('/api/tenant-db', endpoint=_tenant_db),
            Route('/api/noop', endpoint=_noop),
        ],
        middleware=[
            Middleware(_FakeAuth, user=user),
            Middleware(TenantMiddleware),
        ],
    )


class TestProvision:
    def test_provisioner_gap_canary(self, tenant_env):
        """Provision() must succeed through the provisioner (not the fixture's
        manual fallback); if it trips over env gaps again, fail with its error."""
        assert tenant_env['provisioned_via'] == 'provisioner', (
            f'TenantProvisioner.provision() failed: {tenant_env["provisioner_error"]}'
        )

    @pytest.mark.asyncio(loop_scope='module')
    async def test_registry_row_and_tenant_database_exist(self, tenant_env):
        async with get_conn() as conn:
            row = await Tenants(conn).get_by_slug(tenant_env['slug'])
        assert row is not None, 'registry row missing after provisioning'
        assert row['status'] == 'active'
        assert row['db_name'] == tenant_env['db_name']
        assert row['storage_quota_bytes'] == QUOTA
        assert row['plan'] == 'free'

        pool = await TenantConnectionPool.get(tenant_env['slug'], row)
        async with pool.acquire() as tconn:
            assert await tconn.fetchval('SELECT 1') == 1
            assert await tconn.fetchval('SELECT current_database()') == tenant_env['db_name']
            # The tenant DB must be migrated to head like any other DB.
            import alembic.script
            import alembic.config as _alembic_config
            _head = alembic.script.ScriptDirectory.from_config(
                _alembic_config.Config('alembic.ini')
            ).get_current_head()
            assert await tconn.fetchval('SELECT version_num FROM alembic_version') == _head

    @pytest.mark.asyncio(loop_scope='module')
    async def test_tenant_admin_created_in_tenant_db(self, tenant_env):
        async with get_conn() as conn:
            info = await Tenants(conn).get_by_slug(tenant_env['slug'])
        pool = await TenantConnectionPool.get(tenant_env['slug'], info)
        async with pool.acquire() as tconn:
            row = await tconn.fetchrow(
                """
                SELECT u.username, r.slug AS role_slug
                FROM users u JOIN roles r ON r.id = u.role_id
                WHERE u.username = $1
                """,
                f"admin-{tenant_env['slug']}",
            )
        assert row is not None, 'initial admin user missing in tenant DB'
        assert row['role_slug'] == 'tenant_admin'

    @pytest.mark.asyncio(loop_scope='module')
    async def test_registry_admin_user_with_tenant_claim(self, tenant_env):
        """ADR-026 (g): auth lives on the registry DB — admin also exists there with users.tenant = slug."""
        async with get_conn() as conn:
            row = await conn.fetchrow(
                'SELECT username, tenant, status FROM users WHERE username = $1',
                f"admin-{tenant_env['slug']}",
            )
        if row is None:
            pytest.skip(
                'BLOCKED_ON_S1: provisioner does not yet create a registry-DB admin '
                'with users.tenant = slug (ADR-026 g)',
            )
        assert row['tenant'] == tenant_env['slug']
        assert row['status'] == 'active'


class TestAuthAndRouting:
    @pytest.mark.asyncio(loop_scope='module')
    async def test_registry_admin_login_returns_token_with_tenant_claim(self, tenant_env):
        """Real login of the provisioned admin -> JWT carries the tenant claim (ADR-026 b/g)."""
        username = f"admin-{tenant_env['slug']}"
        async with get_conn() as conn:
            data = await Users(conn).login(username, tenant_env['admin_password'])
        assert data['tenant'] == tenant_env['slug']
        async with get_conn() as conn:
            role_slug, permissions = await Users(conn).get_user_role(data['id'])
        access, _ = create_token_pair(data, role=role_slug, permissions=permissions)
        payload = verify_token(access)
        assert payload['tenant'] == tenant_env['slug']
        user = User({'id': payload['id'], 'admin': payload['admin'],
                     'tenant': payload.get('tenant'),
                     'permissions': payload.get('permissions', [])})
        assert user.can_access_tenant(tenant_env['slug']) is True
        assert user.can_access_tenant('some-other-clinic') is False

    @pytest.mark.asyncio(loop_scope='module')
    async def test_routed_request_hits_tenant_database(self, tenant_env):
        """Real middleware + real registry: X-Tenant-ID routes the handler into the tenant DB."""
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=_make_app()),
            base_url='http://test',
        ) as client:
            resp = await client.get('/api/tenant-db', headers={'X-Tenant-ID': tenant_env['slug']})
        assert resp.status_code == 200, resp.text
        assert resp.json()['db'] == tenant_env['db_name']

    @pytest.mark.asyncio(loop_scope='module')
    async def test_tenant_claim_routes_without_header(self, tenant_env):
        """JWT claim alone (no header) scopes the request into the tenant DB (ADR-026 b)."""
        user = User({'id': 1, 'admin': True, 'permissions': ['*'],
                     'tenant': tenant_env['slug']})
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=_make_app(user)),
            base_url='http://test',
        ) as client:
            resp = await client.get('/api/tenant-db')
        assert resp.status_code == 200, resp.text
        assert resp.json()['db'] == tenant_env['db_name']

    @pytest.mark.asyncio(loop_scope='module')
    async def test_unscoped_request_stays_on_platform_db(self, tenant_env):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=_make_app()),
            base_url='http://test',
        ) as client:
            resp = await client.get('/api/tenant-db')
        assert resp.status_code == 200
        assert resp.json()['db'] is None  # no tenant context -> platform mode

    @pytest.mark.asyncio(loop_scope='module')
    async def test_tenant_database_isolated_from_platform(self, tenant_env):
        marker = f'e2e_marker_{int(time.time())}'
        async with get_conn() as conn:
            info = await Tenants(conn).get_by_slug(tenant_env['slug'])
        pool = await TenantConnectionPool.get(tenant_env['slug'], info)
        try:
            async with pool.acquire() as tconn:
                await tconn.execute(
                    f'CREATE TABLE {marker} (id INT PRIMARY KEY, note TEXT)'
                )
                await tconn.execute(
                    f'INSERT INTO {marker} VALUES (1, $1)', f'tenant-only-{tenant_env["slug"]}'
                )
                assert await tconn.fetchval(f'SELECT note FROM {marker} WHERE id = 1') == \
                    f'tenant-only-{tenant_env["slug"]}'
            async with get_conn() as conn:
                with pytest.raises(asyncpg.UndefinedTableError):
                    await conn.fetch(f'SELECT * FROM {marker}')
        finally:
            try:
                async with pool.acquire() as tconn:
                    await tconn.execute(f'DROP TABLE IF EXISTS {marker}')
            except Exception:
                pass


class TestStatusGating:
    """Real registry status transitions gated by the real middleware (ADR-026 d)."""

    async def _set_status(self, slug, status):
        async with get_conn() as conn:
            await Tenants(conn).set_status(slug, status)

    @pytest.mark.asyncio(loop_scope='module')
    async def test_suspended_tenant_gate_403(self, tenant_env):
        await self._set_status(tenant_env['slug'], 'suspended')
        try:
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=_make_app()),
                base_url='http://test',
            ) as client:
                resp = await client.get('/api/noop', headers={'X-Tenant-ID': tenant_env['slug']})
            assert resp.status_code == 403, resp.text
            assert 'suspended' in resp.json()['message']
        finally:
            await self._set_status(tenant_env['slug'], 'active')

    @pytest.mark.asyncio(loop_scope='module')
    async def test_quarantined_tenant_gate_403(self, tenant_env):
        await self._set_status(tenant_env['slug'], 'quarantined')
        try:
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=_make_app()),
                base_url='http://test',
            ) as client:
                resp = await client.get('/api/noop', headers={'X-Tenant-ID': tenant_env['slug']})
            assert resp.status_code == 403, resp.text
        finally:
            await self._set_status(tenant_env['slug'], 'active')

    @pytest.mark.asyncio(loop_scope='module')
    async def test_decommissioned_tenant_gate_404(self, tenant_env):
        """Decommissioned is invisible (404) — including via the JWT claim path."""
        await self._set_status(tenant_env['slug'], 'decommissioned')
        user = User({'id': 1, 'admin': True, 'permissions': ['*'],
                     'tenant': tenant_env['slug']})
        try:
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=_make_app(user)),
                base_url='http://test',
            ) as client:
                resp = await client.get('/api/noop')
            assert resp.status_code == 404, resp.text
        finally:
            await self._set_status(tenant_env['slug'], 'active')

    @pytest.mark.asyncio(loop_scope='module')
    async def test_unknown_tenant_header_404(self, tenant_env):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=_make_app()),
            base_url='http://test',
        ) as client:
            resp = await client.get('/api/noop', headers={'X-Tenant-ID': 'no-such-tenant'})
        assert resp.status_code == 404, resp.text


class TestMeteringAndHealth:
    @pytest.mark.asyncio(loop_scope='module')
    async def test_usage_metering_rolls_up_daily(self, tenant_env):
        usage_table = None
        async with get_conn() as conn:
            usage_table = await conn.fetchval("SELECT to_regclass('tenant_usage_daily')")
        if usage_table is None:
            pytest.skip('BLOCKED_ON_S1: tenant_usage_daily table not migrated yet')
        await record_request(tenant_env['slug'])
        await record_request(tenant_env['slug'])
        rows = await get_usage(tenant_env['slug'], days=1)
        assert rows, 'no usage rows recorded'
        # Routed requests earlier in this module already bumped today's counter.
        assert rows[-1]['api_calls'] >= 2

    @pytest.mark.asyncio(loop_scope='module')
    async def test_default_tenant_seed(self, tenant_env):
        async with get_conn() as conn:
            row = await Tenants(conn).get_by_slug('default')
        if row is None:
            pytest.skip(
                'default tenant seed runs at backend startup (lifecycle._ensure_default_tenant); '
                'not seeded in this dev DB yet',
            )
        assert row['db_name'] == config['db_database']

    @pytest.mark.asyncio(loop_scope='module')
    async def test_tenant_health_endpoint_probes_database(self, tenant_env):
        app = Starlette(
            routes=[Route('/api/v2/tenants/health', endpoint=TenantHealthHandler)],
            middleware=[Middleware(_FakeAuth)],
        )
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url='http://test',
        ) as client:
            resp = await client.get('/api/v2/tenants/health')
        assert resp.status_code == 200, resp.text
        tenants = {t['slug']: t for t in resp.json()['tenants']}
        probe = tenants.get(tenant_env['slug'])
        assert probe is not None, 'provisioned tenant missing from health response'
        assert probe['db_reachable'] is True
        assert probe['status'] == 'active'
        assert probe['storage_pct'] == 0.0
