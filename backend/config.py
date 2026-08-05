import os
import sys

import yaml

default_config = {
    'secret': 'default',
    'superadmin_pass': 'pa55w0rd',
    'db_host': '127.0.0.1',
    'db_port': '5432',
    'db_database': 'quantumpacs',
    'db_user': 'quantumpacs',
    'db_password': 'pa55w0rd',
    'es_host': 'localhost',
    'cors_origins': '*',
    'allowed_hosts': 'localhost,127.0.0.1',
    'redis_host': 'localhost',
    'redis_port': '6379',
    'redis_password': '',
    'db_pool_size': '8',
    'sentry_dsn': '',
}


def load_config(overrides=None):
    cfg = default_config.copy()
    try:
        with open('config.local.yaml') as f:
            local_config = yaml.safe_load(f.read())
        for k, v in cfg.items():
            if k in local_config:
                cfg[k] = local_config[k]
    except Exception:
        pass

    for k in default_config.keys():
        kenv = k.upper()
        env_val = os.getenv(kenv)
        if env_val:
            cfg[k] = env_val

    if overrides:
        cfg.update(overrides)

    if cfg['secret'] == 'default':
        cfg['secret'] = cfg['db_password']

    return cfg


config = load_config()


def assert_production_secret():
    if config['secret'] in ('default', 'pa55w0rd'):
        import logging
        logging.getLogger(__name__).critical(
            'SECURITY: Using default secret. Set SECRET env var or config.local.yaml secret.'
        )
        sys.exit(1)


is_docker = bool(os.getenv('QUANTUMPACS_DOCKER'))
