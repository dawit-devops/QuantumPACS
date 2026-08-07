"""Alembic migration environment.
Supports TENANT_SLUG env var to target a specific tenant's database.

Usage:
    TENANT_SLUG=my-clinic alembic upgrade head
    ./manage tenant migrate
"""
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from migrations.tenant_url import get_tenant_url, _tenant_slug

config = context.config
if config.config_file_name is not None:
    # disable_existing_loggers=False keeps application loggers (backend.log
    # module loggers) alive when alembic runs in-process during tenant
    # provisioning — otherwise they are silently disabled and pytest caplog
    # stops seeing their records.
    fileConfig(config.config_file_name, disable_existing_loggers=False)


def run_migrations_offline() -> None:
    url = get_tenant_url() if _tenant_slug else config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=None,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    if _tenant_slug:
        url = get_tenant_url()
        cfg = config.get_section(config.config_ini_section, {})
        cfg['sqlalchemy.url'] = url
        connectable = engine_from_config(
            cfg, prefix="sqlalchemy.", poolclass=pool.NullPool,
        )
    else:
        connectable = engine_from_config(
            config.get_section(config.config_ini_section, {}),
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
        )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=None,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
