import alembic.config
import alembic.command
import asyncpg

from config import config
from db.conn import get_conn
from db.tenants import Tenants
from log import get_logger

log = get_logger(__name__)

_ALEMBIC_CFG_PATH = 'alembic.ini'


class TenantProvisionError(Exception):
    pass


class TenantProvisioner:
    @staticmethod
    async def create_database(db_name: str):
        conn = await asyncpg.connect(
            user='postgres',
            password=config['db_password'],
            database='postgres',
            host=config['db_host'],
            port=int(config.get('db_port', '5432')),
        )
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
                        db_password: str = None, storage_quota_bytes: int = 0):
        if db_name is None:
            db_name = slug.replace('-', '_')

        await TenantProvisioner.create_database(db_name)
        await TenantProvisioner.run_migrations(
            db_name, db_host, db_port, db_user, db_password,
        )

        async with get_conn() as conn:
            existing = await Tenants(conn).get_by_slug(slug)
            if existing:
                raise TenantProvisionError(f'Tenant slug already exists: {slug}')

            tenant_id = await Tenants(conn).create(
                name=name, slug=slug, domain=domain,
                db_name=db_name, db_host=db_host, db_port=db_port,
                db_user=db_user, db_password=db_password,
                storage_quota_bytes=storage_quota_bytes,
            )

        log.info('Provisioned tenant %s (db=%s, id=%s)', slug, db_name, tenant_id)
        return tenant_id
