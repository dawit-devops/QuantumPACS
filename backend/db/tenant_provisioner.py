import binascii
import hashlib
import os
import secrets

import alembic.config
import alembic.command
import asyncpg

from config import config
from db.conn import get_conn
from db.tenants import Tenants
from log import get_logger

log = get_logger(__name__)

_ALEMBIC_CFG_PATH = 'alembic.ini'


def _hash_password(pswd):
    salt = os.urandom(16)
    data = hashlib.pbkdf2_hmac('sha256', pswd.encode('utf8'), salt, 600000)
    return binascii.hexlify(salt + data).decode('utf8')


class TenantProvisionError(Exception):
    pass


class TenantProvisioner:
    @staticmethod
    async def _connect_maintenance_db():
        """Connect to the maintenance DB as a role that can CREATE DATABASE.

        Prefer the configured db_user (the container superuser for the CI
        postgres service and the compose stack); fall back to the
        conventional `postgres` role only when the configured user cannot
        connect (e.g. a hand-managed postgres whose only superuser is named
        postgres). Connection-level failures only — a successful connect with
        insufficient privileges must surface as-is, not silently retry."""
        last_error = None
        for user in (config['db_user'], 'postgres'):
            try:
                return await asyncpg.connect(
                    user=user,
                    password=config['db_password'],
                    database='postgres',
                    host=config['db_host'],
                    port=int(config.get('db_port', '5432')),
                )
            except (asyncpg.InvalidPasswordError,
                    asyncpg.InvalidAuthorizationSpecificationError,
                    OSError) as e:
                last_error = e
        raise last_error

    @staticmethod
    async def create_database(db_name: str):
        conn = await TenantProvisioner._connect_maintenance_db()
        try:
            await conn.execute(f'CREATE DATABASE "{db_name}"')
            log.info('Created tenant database: %s', db_name)
        except asyncpg.DuplicateDatabaseError:
            log.warning('Database already exists: %s', db_name)
        finally:
            await conn.close()

    @staticmethod
    async def run_migrations(db_name: str, db_host: str = None, db_port: int = None,
                             db_user: str = None, db_password: str = None):
        host = db_host or config['db_host']
        port = db_port or int(config.get('db_port', '5432'))
        user = db_user or config['db_user']
        password = db_password or config['db_password']

        url = f'postgresql+psycopg2://{user}:{password}@{host}:{port}/{db_name}'
        try:
            cfg = alembic.config.Config(_ALEMBIC_CFG_PATH)
            cfg.set_main_option('sqlalchemy.url', url)
            alembic.command.upgrade(cfg, 'head')
            log.info('Migrated tenant database: %s', db_name)
        except Exception as e:
            raise TenantProvisionError(f'Migration failed for {db_name}: {e}') from e

    @staticmethod
    async def provision(slug: str, name: str, domain: str = None,
                        db_name: str = None, db_host: str = None,
                        db_port: int = None, db_user: str = None,
                        db_password: str = None, storage_quota_bytes: int = 0,
                        admin_email: str = None, plan: str = 'free'):
        if db_name is None:
            db_name = slug.replace('-', '_')

        async with get_conn() as conn:
            existing = await Tenants(conn).get_by_slug(slug)
            if existing:
                raise TenantProvisionError(f'Tenant slug already exists: {slug}')

        # Registry row first, in a visible "provisioning" state — a failed
        # provision rolls back to decommissioned instead of leaking a row.
        async with get_conn() as conn:
            tenant_id = await Tenants(conn).create(
                name=name, slug=slug, domain=domain,
                db_name=db_name, db_host=db_host, db_port=db_port,
                db_user=db_user, db_password=db_password,
                storage_quota_bytes=storage_quota_bytes,
                status='provisioning', plan=plan,
            )

        try:
            await TenantProvisioner.create_database(db_name)
            await TenantProvisioner.run_migrations(
                db_name, db_host, db_port, db_user, db_password,
            )
            admin_password = await TenantProvisioner.create_initial_admin(
                db_name=db_name, slug=slug, admin_email=admin_email,
                db_host=db_host, db_port=db_port, db_user=db_user, db_password=db_password,
            )
        except Exception as e:
            await TenantProvisioner._mark_failed(slug, tenant_id, str(e))
            raise TenantProvisionError(
                f'Provision failed for {slug}: {e}'
            ) from e

        await TenantProvisioner._mark_active(slug)
        log.info('Provisioned tenant %s (db=%s, id=%s)', slug, db_name, tenant_id)
        return {'tenant_id': tenant_id, 'admin_password': admin_password}

    @staticmethod
    async def _mark_active(slug: str):
        async with get_conn() as conn:
            await Tenants(conn).set_status(slug, 'active')

    @staticmethod
    async def _mark_failed(slug: str, tenant_id, reason: str):
        async with get_conn() as conn:
            await Tenants(conn).set_status(slug, 'decommissioned')
            from db.audit_log import AuditLog
            await AuditLog(conn).log_event(
                event_type='tenant.provision_failed',
                actor_id=None,
                resource_type='tenant',
                resource_id=tenant_id,
                details={'slug': slug, 'reason': reason},
                tenant=slug,
            )

    @staticmethod
    async def create_initial_admin(db_name: str, slug: str, admin_email: str = None,
                                    db_host: str = None, db_port: int = None,
                                    db_user: str = None, db_password: str = None):
        host = db_host or config['db_host']
        port = db_port or int(config.get('db_port', '5432'))
        user = db_user or config['db_user']
        password = db_password or config['db_password']

        pswd = secrets.token_urlsafe(24)
        hashed = _hash_password(pswd)
        username = f'admin-{slug}'

        # Tenant DB: seed the admin so per-tenant user counts/stats see it.
        conn = await asyncpg.connect(
            user=user, password=password,
            database=db_name, host=host, port=port,
        )
        try:
            role_id = await conn.fetchval(
                "SELECT id FROM roles WHERE slug = 'tenant_admin'"
            )
            if not role_id:
                raise TenantProvisionError(
                    f"tenant_admin role not found in database {db_name}"
                )
            await conn.execute(
                "INSERT INTO users (username, password, role_id, status) VALUES ($1, $2, $3, 'active')",
                username, hashed, role_id,
            )
            log.info('Created tenant-DB admin user %s for tenant %s', username, slug)
        finally:
            await conn.close()

        # MAIN DB: auth (TokenAuth/Login) runs on the main pool, so the admin
        # must exist here too — tagged with the tenant slug so the JWT carries
        # the tenant claim and TenantMiddleware scopes their requests.
        main_conn = await asyncpg.connect(
            user=config['db_user'], password=config['db_password'],
            database=config['db_database'], host=config['db_host'],
            port=int(config.get('db_port', '5432')),
        )
        try:
            role_id = await main_conn.fetchval(
                "SELECT id FROM roles WHERE slug = 'tenant_admin'"
            )
            if not role_id:
                raise TenantProvisionError(
                    "tenant_admin role not found in main database"
                )
            await main_conn.execute(
                "INSERT INTO users (username, password, role_id, status, tenant) "
                "VALUES ($1, $2, $3, 'active', $4)",
                username, hashed, role_id, slug,
            )
            log.info('Created main-DB admin user %s for tenant %s', username, slug)
        finally:
            await main_conn.close()

        return pswd
