"""Alembic migration environment.
Supports TENANT_SLUG env var to target a specific tenant's database.

Usage:
    TENANT_SLUG=my-clinic alembic upgrade head
    ./manage tenant migrate
"""
import asyncio
import os
import threading
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlalchemy.engine import URL
from sqlalchemy.ext.asyncio import async_engine_from_config

from migrations.tenant_url import get_tenant_url, _tenant_slug

config = context.config
if config.config_file_name is not None:
    # disable_existing_loggers=False keeps application loggers (backend.log
    # module loggers) alive when alembic runs in-process during tenant
    # provisioning — otherwise they are silently disabled and pytest caplog
    # stops seeing their records.
    fileConfig(config.config_file_name, disable_existing_loggers=False)

def _ini_file_url() -> str:
    """Read sqlalchemy.url from alembic.ini on disk. In-process callers
    (tenant provisioning) run set_main_option() before env.py is imported,
    so the in-memory file_config already carries the override — the
    override baseline must come from the file, not the parser."""
    import configparser

    path = config.config_file_name
    if not path:
        return ''
    parser = configparser.ConfigParser()
    parser.read(path)
    return parser.get('alembic', 'sqlalchemy.url', fallback='')


# Baseline for override detection; see _ini_file_url().
_INI_SQLALCHEMY_URL = _ini_file_url()


def _env_url() -> str | None:
    """Container deployments pass DB_* env vars; prefer them over the dev
    URL in alembic.ini (which points at 127.0.0.1 and only works on the host).
    Uses asyncpg — psycopg2 is not installed in the backend image. URL.create
    percent-encodes each component (generated passwords contain +/= chars)."""
    host = os.environ.get('DB_HOST')
    if not host:
        return None
    user = os.environ.get('DB_USER', 'quantumpacs')
    password = os.environ.get('DB_PASSWORD', '')
    if not password:
        raise RuntimeError(
            'DB_PASSWORD must be set when DB_HOST is set (container migrations)'
        )
    port = os.environ.get('DB_PORT', '5432')
    if not port.isdigit():
        raise RuntimeError(f'DB_PORT must be numeric, got {port!r}')
    database = os.environ.get('DB_DATABASE', 'quantumpacs')
    url = URL.create(
        'postgresql+asyncpg',
        username=user,
        password=password,
        host=host,
        port=int(port),
        database=database,
    )
    return url.render_as_string(hide_password=False)


def _caller_overrode_url() -> bool:
    """In-process callers (tenant provisioning) set the URL via
    set_main_option(); the env path must never replace their explicit target.
    Compared against the on-disk ini URL (see _ini_file_url())."""
    return (config.get_main_option('sqlalchemy.url')
            != _INI_SQLALCHEMY_URL)


def _use_async_engine(cfg: dict) -> bool:
    """asyncpg-dialect URLs need the async engine + run_sync pattern; the
    sync engine_from_config path below would raise MissingGreenlet."""
    return cfg.get('sqlalchemy.url', '').startswith('postgresql+asyncpg:')


def _run_migrations_blocking(cfg: dict) -> None:
    """Run the async engine pattern; callable from CLI (asyncio.run) or from
    inside an already-running event loop (worker thread)."""
    async def _run() -> None:
        connectable = async_engine_from_config(
            cfg, prefix='sqlalchemy.', poolclass=pool.NullPool,
        )
        async with connectable.connect() as connection:
            await connection.run_sync(_do_run_migrations)
        await connectable.dispose()
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        asyncio.run(_run())
    else:
        raised: list[BaseException] = []
        def _target() -> None:
            try:
                asyncio.run(_run())
            except BaseException as exc:
                raised.append(exc)
        worker = threading.Thread(target=_target)
        worker.start()
        worker.join()
        if raised:
            raise raised[0]


def run_migrations_offline() -> None:
    if _tenant_slug:
        url = get_tenant_url()
    elif not _caller_overrode_url():
        url = _env_url() or config.get_main_option('sqlalchemy.url')
    else:
        url = config.get_main_option('sqlalchemy.url')
    context.configure(
        url=url,
        target_metadata=None,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def _do_run_migrations(connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=None,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    cfg = config.get_section(config.config_ini_section, {})
    if _tenant_slug:
        cfg['sqlalchemy.url'] = get_tenant_url()
    elif (env_url := _env_url()) and not _caller_overrode_url():
        # asyncpg dialect requires the async engine + run_sync pattern;
        # the sync engine_from_config path below would raise MissingGreenlet.
        cfg['sqlalchemy.url'] = env_url
        _run_migrations_blocking(cfg)
        return
    if _use_async_engine(cfg):
        # Tenant provisioning (in-process) and TENANT_SLUG flows pass
        # postgresql+asyncpg URLs — the image has no psycopg2 driver.
        _run_migrations_blocking(cfg)
        return
    connectable = engine_from_config(
        cfg, prefix='sqlalchemy.', poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        _do_run_migrations(connection)


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
