import os

import yaml

from exceptions import ConfigurationError

_DEFAULT_SECRET = 'quantumpacs-default-secret-32-bytes-long!!'
_DEFAULT_DB_PASSWORD = 'pa55w0rd'
_DEFAULT_SUPERADMIN_PASS = 'pa55w0rd'

# Any of these grants full admin-token forgery — none may ever run in any
# environment. Values that shipped in the repo are known to attackers.
_KNOWN_INSECURE_SECRETS = frozenset({
    'default',
    'pa55w0rd',
    _DEFAULT_SECRET,
    'quantumpacs-dev-secret-replace-in-production-32b',
    'quantum-local-dev-secret-replace-in-prod-2026-07-28',
    'quantumpacs-docker-compose-dev-secret-change-me',
})

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
    'clinic_timezone': 'UTC',
    # S10-10/B-6: EMR endpoint for ORU^R01 delivery; empty = no endpoint
    # reachable, so distribution attempts record FAILED honestly.
    'distribution_endpoint': '',
    'tenant_default_quota_bytes': '0',
    'sentry_dsn': '',
    'sentry_traces_sample_rate': '1.0',
    'oauth_issuer': '',
    'oauth_client_id': '',
    'oauth_client_secret': '',
    'oauth_redirect_uri': '',
    'oauth_jwks_uri': '',
    'oauth_token_url': '',
    'oauth_default_role': 'patient',
    'oauth_scope': 'openid email profile',
    # Access-token lifetime in days; the Settings page (P2-3) can surface a
    # stored override. Reads live from tokens.py (runtime-safe).
    'token_expiry_days': '14',
    # R2-M5: single source of truth for the JWT `iss` claim — the OIDC
    # discovery document advertises this value too. Empty = legacy
    # 'quantumpacs' issuer (minted iss and discovery both fall back).
    'token_issuer': '',
    # Path to the RSA signing key (PEM) used for RS256 access/refresh tokens.
    # Auto-generated on first use; jwks_uri serves the matching public key.
    'jwt_key_path': 'certs/jwt-rsa.pem',
    'dicom_ae_title': 'QUANTUMPACS',
    'dicom_cstore_port': '11112',
    # Optional dedicated MWL listener port. Empty = MWL served on the
    # C-STORE port (single SCP). Non-empty + different = a second AE serves
    # Modality Worklist C-FIND on this port (lifecycle._run_dicom).
    'dicom_mwl_port': '',
    # C3 drift fix: the MPPS AE port previously existed only as an inline
    # fallback in lifecycle.py — surface it here like its siblings.
    'dicom_mpps_port': '11114',
    # C3: forward modality MPPS N-CREATE/N-SET to a remote PACS (S6-09).
    # Off by default; enabling points exam-status updates at the peer AE.
    'mpps_forward_enabled': False,
    'mpps_forward_host': '',
    'mpps_forward_port': '',
    'mpps_forward_called_ae': '',
    'dicom_aet_allowed': '',
    'dicom_allowed_ips': '',
    'dicom_require_called_aet': 'false',
    # AE-title -> tenant slug mapping for the DICOM SCP: comma-separated
    # `AE:slug` pairs, e.g. 'CT_ROOM_A:b,MR_ROOM_A:c'. A calling AE absent
    # from the map falls back to the seeded `default` tenant (documented).
    'dicom_ae_tenant_map': '',
    # When true AND dicom_ae_tenant_map is non-empty, a calling AE that is
    # not mapped to any tenant is refused (association rejected, store fails)
    # instead of being silently routed to the default tenant's store (G-1).
    # Off by default so single-tenant / dev setups keep the historical
    # fallback behaviour.
    'dicom_reject_unmapped_ae': 'false',
    # ADR-028 (dcm4chee archive migration). dcm4chee_url: base URL of the
    # archive's REST service (dev override localhost:8082; container
    # deployments must use the container DNS http://dcm4chee-arc:8080/dcm4chee-arc).
    'dcm4chee_url': 'http://localhost:8082/dcm4chee-arc',
    'dcm4chee_ae': 'DCM4CHEE',
    # C-ECHO SCU target (S6-09): connectivity probe fired after an MPPS
    # COMPLETED. Empty host = no PACS configured, probe is a silent no-op.
    'pacs_echo_host': '',
    'pacs_echo_port': '11112',
    'pacs_echo_ae': 'DCM4CHEE',
    # When true, the /dicomweb/* surface proxies QIDO-RS/WADO-RS/frames/
    # WADO-URI to dcm4chee (archive owns pixels); when false, QuantumPACS
    # serves its own DICOMweb implementation from the files table.
    'dicom_proxy': 'false',
    # Weasis integration: launch buttons are shown only when weasis_enabled.
    'weasis_enabled': 'false',
    'weasis_launch_url': 'http://localhost:8082/weasis-pacs-connector',
    # MWL-RS mirror sync (ADR-028 Phase 3): when dicom_proxy=true a
    # background worker mirrors worklist_entries to dcm4chee. Poll interval.
    'mwl_sync_interval': '10',
    # Archive→feed self-heal sync (ADR-028 Phase 3): when dicom_proxy=true a
    # background worker scans dcm4chee QIDO-RS and re-exports studies
    # QuantumPACS does not know (e.g. stored while the feed SCP was down).
    'dcm4chee_sync_interval': '30',
    # Minimum seconds between export re-requests for a study that never lands
    # in QP (bounds archive export-queue growth when the feed SCP is down).
    'dcm4chee_sync_cooldown': '300',
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
    'max_stow_size_mb': '2048',
    'b2_cors_origins': 'http://localhost:5173',
    'ingestion_stream': 'events:ingestion',
    'ingestion_group': 'ingestion-service',
    'ingestion_consumer': 'worker-1',
    'ingestion_poll_count': '10',
    'ingestion_poll_block_ms': '5000',
    'ingestion_max_retries': '3',
    'oauth_secret_encryption_key': '',
    'tenant_usage_retention_days': '365',
    # Cookie `Secure` flag. Default false so the documented plain-HTTP
    # localhost dev topology keeps working; set true (COOKIE_SECURE=true /
    # config.local.yaml) for any TLS deployment so the HttpOnly auth cookies
    # are never sent over cleartext.
    'cookie_secure': 'false',
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
    if config['secret'] in _KNOWN_INSECURE_SECRETS:
        raise ConfigurationError(
            'SECURITY: Using a known/committed secret. Set SECRET env var or '
            'config.local.yaml secret to a fresh random value.'
        )
    if config['superadmin_pass'] in ('pa55w0rd', _DEFAULT_SUPERADMIN_PASS):
        raise ConfigurationError(
            'SECURITY: Using the default superadmin password. Set SUPERADMIN_PASS '
            'env var or config.local.yaml superadmin_pass to a fresh random value.'
        )
    if config['db_password'] in ('pa55w0rd', _DEFAULT_DB_PASSWORD):
        raise ConfigurationError(
            'SECURITY: Using the default database password. Set DB_PASSWORD '
            'env var or config.local.yaml db_password to a fresh random value.'
        )


def is_docker():
    return bool(os.getenv('QUANTUMPACS_DOCKER'))


def cookie_secure() -> bool:
    """Whether auth cookies should be marked Secure (HTTPS-only).

    Driven by the `cookie_secure` config key so plain-HTTP dev does not break
    while TLS deployments can enforce the flag.
    """
    return str(config.get('cookie_secure', 'false')).lower() in ('1', 'true', 'yes', 'on')
