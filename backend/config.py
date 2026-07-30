import os

import yaml

from exceptions import ConfigurationError

_DEFAULT_SECRET = 'quantumpacs-default-secret-32-bytes-long!!'
_DEFAULT_DB_PASSWORD = 'pa55w0rd'
_DEFAULT_SUPERADMIN_PASS = 'pa55w0rd'

default_config = {
    'secret': _DEFAULT_SECRET,
    'superadmin_pass': _DEFAULT_SUPERADMIN_PASS,
    'db_host': '127.0.0.1',
    'db_port': '5432',
    'db_database': 'quantumpacs',
    'db_user': 'quantumpacs',
    'db_password': _DEFAULT_DB_PASSWORD,
    'es_host': 'localhost',
    'cors_origins': 'http://localhost:5173',
    'allowed_hosts': 'localhost,127.0.0.1',
    'redis_host': 'localhost',
    'redis_port': '6379',
    'redis_password': '',
    'db_pool_size': '8',
    'sentry_dsn': '',
    'sentry_traces_sample_rate': '1.0',
    'oauth_issuer': '',
    'oauth_client_id': '',
    'oauth_client_secret': '',
    'oauth_redirect_uri': '',
    'oauth_jwks_uri': '',
    'oauth_token_url': '',
    'oauth_default_role': 'radiologist',
    'oauth_scope': 'openid email profile',
    'dicom_ae_title': 'QUANTUMPACS',
    'dicom_cstore_port': '11112',
    'dicom_mwl_port': '11113',
    'dicom_cmove_port': '11114',
    'hl7_mllp_port': '12579',
    'hl7_mllp_tls_cert': '',
    'hl7_mllp_tls_key': '',
    'hl7_mllp_allowed_ips': '',
    'otel_exporter_otlp_endpoint': '',
    'otel_service_name': 'quantumpacs-backend',
    'otel_deployment_environment': 'development',
    'otel_sampler': 'always_on',
    'otel_bsp_schedule_delay': '5000',
    'otel_bsp_max_queue_size': '2048',
    'otel_bsp_max_export_batch_size': '512',
    'prometheus_enabled': 'true',
    'max_upload_size_mb': '500',
    'b2_cors_origins': 'http://localhost:5173',
    'ingestion_stream': 'events:ingestion',
    'ingestion_group': 'ingestion-service',
    'ingestion_consumer': 'worker-1',
    'ingestion_poll_count': '10',
    'ingestion_poll_block_ms': '5000',
    'ingestion_max_retries': '3',
    'oauth_secret_encryption_key': '',
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

    if cfg['secret'] in ('default', ):
        cfg['secret'] = _DEFAULT_SECRET

    return cfg


config = load_config()


def assert_production_secret():
    if config['secret'] in ('default', 'pa55w0rd', _DEFAULT_SECRET):
        raise ConfigurationError(
            'SECURITY: Using default secret. Set SECRET env var or config.local.yaml secret.'
        )


def is_docker():
    return bool(os.getenv('QUANTUMPACS_DOCKER'))
