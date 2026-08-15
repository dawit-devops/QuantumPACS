"""Platform-admin operations API (super_admin review).

Maintenance mode (P1-2), whitelisted config (P2-3) and metadata backups
(P2-1). All mutation endpoints are gated SYSTEM_ADMIN — the only built-in
that holds it is super_admin. The maintenance write-gate reads the
in-process mirror updated here and loaded at startup (app.py lifespan).
"""

import io
import json
import uuid
from datetime import datetime, timezone

from starlette.endpoints import HTTPEndpoint
from starlette.responses import Response, FileResponse

from api.rbac import requires_permission
from api.permissions import Permission
from api.response import ok, api_error, not_found
from api.validate import parse_body
from api.schemas.admin import MaintenanceRequest, ConfigUpdateRequest
from db.conn import get_conn
from db.audit_log import AuditLog
from db.platform_state import PlatformState
from db.system_settings import SystemSettings
from db.backups import Backups
from db.replica import Replica
from storage.storage import Storage
from config import config
from log import get_logger

log = get_logger(__name__)


# ---------------------------------------------------------------------------
# Maintenance mode
# ---------------------------------------------------------------------------

# In-process mirror of the platform_state 'maintenance' row: the request
# gate must not hit the DB per write, so the toggle endpoint and the
# startup loader keep this dict in sync with the source of truth.
_maintenance = {'active': False, 'reason': '', 'since': None}

_MAINTENANCE_KEY = 'maintenance'

# Writes that must stay reachable while maintenance is on: the auth grant
# endpoints (users must be able to log in/out) and the maintenance control
# itself (the only way to turn it off). Everything else POST/PUT/DELETE on
# /api is blocked with a readable 503.
_MAINTENANCE_EXEMPT_PREFIXES = (
    '/api/login',
    '/api/v2/login',
    '/api/auth/refresh',
    '/api/v2/auth/refresh',
    '/api/auth/logout',
    '/api/v2/auth/logout',
    '/api/admin/maintenance',
    '/api/v2/admin/maintenance',
)


def maintenance_active() -> bool:
    return bool(_maintenance.get('active'))


def maintenance_exempt(path: str) -> bool:
    return path.startswith(_MAINTENANCE_EXEMPT_PREFIXES)


async def load_maintenance_state():
    """Load the durable maintenance flag at startup (non-fatal)."""
    try:
        async with get_conn() as conn:
            st = await PlatformState(conn).get(_MAINTENANCE_KEY, {})
        if st and st.get('active'):
            _maintenance.update({
                'active': True,
                'reason': st.get('reason', ''),
                'since': st.get('since'),
            })
    except Exception:
        log.warning('Failed to load maintenance state at startup', exc_info=True)


def maintenance_snapshot():
    if not _maintenance.get('active'):
        return {'active': False}
    return {
        'active': True,
        'reason': _maintenance.get('reason', ''),
        'since': _maintenance.get('since'),
    }


class AdminStatusHandler(HTTPEndpoint):
    async def get(self, request):
        """Public status (maintenance state only — non-sensitive, status-page
        style). Public so the login page can render the maintenance banner."""
        return ok({'maintenance': maintenance_snapshot()})


class AdminMaintenanceHandler(HTTPEndpoint):
    @requires_permission(Permission.SYSTEM_ADMIN)
    async def post(self, request):
        body = await parse_body(MaintenanceRequest, request)
        since = datetime.now(timezone.utc).isoformat()
        if body.active:
            if not body.reason.strip():
                return api_error(
                    'VALIDATION',
                    'A reason is required when entering maintenance mode',
                    status=422,
                )
            new_state = {'active': True, 'reason': body.reason.strip(), 'since': since}
        else:
            new_state = {'active': False, 'reason': '', 'since': None}

        async with get_conn() as conn:
            await PlatformState(conn).set(_MAINTENANCE_KEY, new_state)
            await AuditLog(conn).log_event(
                event_type='system.maintenance_mode',
                actor_id=request.user.id,
                resource_type='platform',
                resource_id='maintenance',
                details={
                    'active': body.active,
                    'reason': body.reason.strip(),
                    'description': (
                        f'Maintenance mode {"enabled" if body.active else "disabled"}'
                        + (f': {body.reason.strip()}' if body.reason.strip() else '')
                    ),
                },
                request_id=getattr(request.state, 'request_id', None),
            )
        _maintenance.update(new_state)
        return ok({'maintenance': maintenance_snapshot()})


# ---------------------------------------------------------------------------
# Whitelisted config (P2-3)
# ---------------------------------------------------------------------------

# Whitelisted, editable platform settings. restart=True keys are stored and
# surfaced with a "restart required" tag; restart=False keys are applied to
# the live config dict immediately (the app reads them per-request).
CONFIG_WHITELIST = {
    'max_upload_size_mb': {'type': 'int', 'restart': False},
    'max_stow_size_mb': {'type': 'int', 'restart': False},
    'tenant_usage_retention_days': {'type': 'int', 'restart': False},
    # tokens.py reads this from the live config dict per token mint, so the
    # change applies without a restart.
    'token_expiry_days': {'type': 'int', 'restart': False},
    'allowed_hosts': {'type': 'str', 'restart': True},
    'cors_origins': {'type': 'str', 'restart': True},
    'cookie_secure': {'type': 'bool', 'restart': True},
}


def _coerce_config_value(key, raw):
    spec = CONFIG_WHITELIST[key]
    if spec['type'] == 'int':
        return int(raw)
    if spec['type'] == 'bool':
        if isinstance(raw, bool):
            return raw
        return str(raw).lower() in ('1', 'true', 'yes', 'on')
    return str(raw)


class AdminConfigHandler(HTTPEndpoint):
    @requires_permission(Permission.SYSTEM_ADMIN)
    async def get(self, request):
        out = {}
        for key, spec in CONFIG_WHITELIST.items():
            out[key] = {
                'value': config.get(key),
                'type': spec['type'],
                'restart': spec['restart'],
            }
        return ok({'settings': out})

    @requires_permission(Permission.SYSTEM_ADMIN)
    async def put(self, request):
        body = await parse_body(ConfigUpdateRequest, request)
        changed = []
        errors = []
        async with get_conn() as conn:
            settings = SystemSettings(conn)
            for key, item in body.settings.items():
                if key not in CONFIG_WHITELIST:
                    errors.append(f'Unknown setting: {key}')
                    continue
                try:
                    new_val = _coerce_config_value(key, item.value)
                except (TypeError, ValueError):
                    errors.append(f'Invalid value for {key}')
                    continue
                old_val = config.get(key)
                await settings.set(key, new_val)
                if not CONFIG_WHITELIST[key]['restart']:
                    # Live keys are read from the module dict per request —
                    # updating it applies the change immediately.
                    config[key] = new_val
                changed.append({'key': key, 'old': old_val, 'new': new_val})
            if errors:
                return api_error(
                    'VALIDATION',
                    '; '.join(errors),
                    status=422,
                )
            if changed:
                await AuditLog(conn).log_event(
                    event_type='system.config_changed',
                    actor_id=request.user.id,
                    resource_type='platform',
                    resource_id='config',
                    details={
                        'changes': changed,
                        'description': f'Updated {len(changed)} platform setting(s)',
                    },
                    request_id=getattr(request.state, 'request_id', None),
                )
        return ok({'updated': [c['key'] for c in changed]})


# ---------------------------------------------------------------------------
# Backups (P2-1) — metadata-manifest artifacts on the master replica storage
# ---------------------------------------------------------------------------

def _json_safe(obj):
    if isinstance(obj, (datetime,)):
        return obj.isoformat()
    if isinstance(obj, uuid.UUID):
        return str(obj)
    raise TypeError(f'{type(obj)} not serializable')


async def _manifest_filedata(bid):
    """Storage path components for a backup artifact (deterministic per id)."""
    return {
        'patient_id': 'backup',
        'study_id': 'manifest',
        'series_number': '',
        'name': f'{bid}.json',
    }


async def _gather_manifest(conn):
    """Point-in-time metadata manifest of the archive (no pixel data)."""
    files = await conn.fetch(
        'SELECT * FROM files WHERE deleted = FALSE ORDER BY id',
    )
    file_rows = []
    for f in files:
        d = dict(f)
        meta = d.pop('meta', None)
        d['meta'] = meta if isinstance(meta, (dict, list, str)) else None
        d['tools_state'] = None  # never carry per-user tool state into backups
        file_rows.append(d)
    replica = await Replica(conn).master()
    counts = {
        'files': len(file_rows),
        'bytes': sum(int((r.get('size') or 0)) for r in file_rows),
    }
    return {
        'kind': 'metadata',
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'counts': counts,
        'master_replica': replica['id'] if replica else None,
        'files': file_rows,
    }


class AdminBackupsHandler(HTTPEndpoint):
    @requires_permission(Permission.SYSTEM_ADMIN)
    async def get(self, request):
        async with get_conn() as conn:
            rows = await Backups(conn).list_all()
        return ok({'data': rows})

    @requires_permission(Permission.SYSTEM_ADMIN)
    async def post(self, request):
        async with get_conn() as conn:
            bid = await Backups(conn).create(created_by=request.user.id)
            try:
                manifest = await _gather_manifest(conn)
                replica = await Replica(conn).master()
                if not replica:
                    raise RuntimeError('No master replica configured')
                storage = await Storage.get(replica)
                raw = json.dumps(manifest, default=_json_safe).encode('utf-8')
                buf = io.BytesIO(raw)
                filedata = await _manifest_filedata(bid)
                await storage.copy(buf, filedata)
                # LocalStorage returns {'location': path}; providers may vary —
                # size is authoritative from the buffer regardless.
                await Backups(conn).finish(
                    bid, 'completed', artifact_key=f'backup/{bid}.json',
                    size_bytes=len(raw), files_count=manifest['counts']['files'],
                    bytes_count=manifest['counts']['bytes'],
                )
                await AuditLog(conn).log_event(
                    event_type='system.backup_completed',
                    actor_id=request.user.id,
                    resource_type='backup',
                    resource_id=bid,
                    details={
                        'files': manifest['counts']['files'],
                        'bytes': manifest['counts']['bytes'],
                        'description': f"Backup {bid} completed ({manifest['counts']['files']} files)",
                    },
                    request_id=getattr(request.state, 'request_id', None),
                )
            except Exception as e:
                await Backups(conn).finish(bid, 'failed')
                await AuditLog(conn).log_event(
                    event_type='system.backup_failed',
                    actor_id=request.user.id,
                    resource_type='backup',
                    resource_id=bid,
                    details={'error': str(e)[:300], 'description': f'Backup {bid} failed'},
                    request_id=getattr(request.state, 'request_id', None),
                )
                log.exception('Backup %s failed', bid)
                return api_error('BACKUP_FAILED', 'Backup failed — see audit log', status=500)
            row = await Backups(conn).get(bid)
        return ok({'data': row})


class AdminBackupHandler(HTTPEndpoint):
    @requires_permission(Permission.SYSTEM_ADMIN)
    async def get(self, request):
        """Download the backup artifact (the recovery path)."""
        bid = request.path_params['id']
        async with get_conn() as conn:
            row = await Backups(conn).get(bid)
            if not row:
                return not_found('Backup not found')
            if row['status'] != 'completed' or not row['artifact_key']:
                return api_error('BACKUP_UNAVAILABLE', 'Backup artifact not available', status=409)
            replica = await Replica(conn).master()
            if not replica:
                return api_error('BACKUP_UNAVAILABLE', 'No master replica configured', status=503)
            storage = await Storage.get(replica)
            filedata = await _manifest_filedata(bid)
            try:
                path = await storage.fetch(filedata)
            except Exception:
                return api_error('BACKUP_UNAVAILABLE', 'Backup artifact missing from storage', status=404)
        if isinstance(path, str):
            return FileResponse(
                path,
                media_type='application/json',
                filename=f'quantumpacs-backup-{bid}.json',
            )
        return Response(content=path, media_type='application/json')

    @requires_permission(Permission.SYSTEM_ADMIN)
    async def delete(self, request):
        bid = request.path_params['id']
        async with get_conn() as conn:
            row = await Backups(conn).get(bid)
            if not row:
                return not_found('Backup not found')
            if row['status'] == 'completed' and row['artifact_key']:
                try:
                    replica = await Replica(conn).master()
                    if replica:
                        storage = await Storage.get(replica)
                        await storage.delete(await _manifest_filedata(bid))
                except Exception:
                    log.warning('Failed to delete backup artifact %s', bid, exc_info=True)
            await Backups(conn).delete(bid)
            await AuditLog(conn).log_event(
                event_type='backup.deleted',
                actor_id=request.user.id,
                resource_type='backup',
                resource_id=bid,
                details={'description': f'Backup {bid} deleted'},
                request_id=getattr(request.state, 'request_id', None),
            )
        return ok({'message': 'Backup deleted'})


class AdminBackupRestoreHandler(HTTPEndpoint):
    @requires_permission(Permission.SYSTEM_ADMIN)
    async def post(self, request):
        """Restore verification (dry-run report), not destructive rehydration.

        Safety: re-importing file metadata over a live archive is a
        destructive platform action and is deliberately out of scope for the
        review feature. This endpoint validates the artifact parses and
        reports exactly what it contains (files, bytes, generated_at) so an
        operator can audit the artifact before downloading it as the recovery
        path. In-place restore is a documented follow-up (05-implementation.md).
        """
        bid = request.path_params['id']
        async with get_conn() as conn:
            row = await Backups(conn).get(bid)
            if not row:
                return not_found('Backup not found')
            if row['status'] != 'completed' or not row['artifact_key']:
                return api_error('BACKUP_UNAVAILABLE', 'Backup artifact not available', status=409)
            replica = await Replica(conn).master()
            if not replica:
                return api_error('BACKUP_UNAVAILABLE', 'No master replica configured', status=503)
            storage = await Storage.get(replica)
            try:
                path = await storage.fetch(await _manifest_filedata(bid))
            except Exception:
                return api_error('BACKUP_UNAVAILABLE', 'Backup artifact missing from storage', status=404)
        try:
            if isinstance(path, str):
                with open(path, 'rb') as f:
                    manifest = json.loads(f.read())
            else:
                manifest = json.loads(path)
        except (json.JSONDecodeError, OSError, TypeError):
            return api_error('BACKUP_CORRUPT', 'Backup artifact is corrupt or unreadable', status=500)
        counts = manifest.get('counts', {})
        return ok({
            'verification': {
                'backup_id': bid,
                'kind': manifest.get('kind'),
                'generated_at': manifest.get('generated_at'),
                'files': counts.get('files', 0),
                'bytes': counts.get('bytes', 0),
                'master_replica': manifest.get('master_replica'),
                'valid': True,
            },
            'message': 'Artifact verified — download it to recover this snapshot',
        })
