"""Per-user reading presets (FR-R12-15).

Endpoints let a radiologist manage window/level and layout presets per
modality. Presets are scoped to the authenticated user (users.id is a bigint),
so they follow the user across workstations. Reading is gated on REPORT_READ
(same clinical tier as the reading worklist); mutations on REPORT_WRITE.
"""
from starlette.endpoints import HTTPEndpoint

from api.rbac import requires_permission
from api.permissions import Permission
from api.response import ok, created, not_found, validation_error, forbidden
from api.validate import parse_body
from api.schemas.reading_presets import (
    SaveReadingPresetRequest, UpdateReadingPresetRequest,
)
from db.audit_log import AuditLog
from db.conn import get_conn
from db.reading_presets import ReadingPresets
from log import request_id_var


class ReadingPresetsHandler(HTTPEndpoint):
    """List or create my presets (filterable by type/modality)."""

    @requires_permission(Permission.REPORT_READ)
    async def get(self, request):
        preset_type = request.query_params.get('preset_type') or \
            request.query_params.get('type')
        modality = request.query_params.get('modality')
        async with get_conn() as conn:
            presets = await ReadingPresets(conn).list_for_user(
                int(request.user.id), preset_type=preset_type, modality=modality,
            )
        return ok({'data': presets})

    @requires_permission(Permission.REPORT_WRITE)
    async def post(self, request):
        body = await parse_body(SaveReadingPresetRequest, request)
        async with get_conn() as conn:
            created_preset = await ReadingPresets(conn).create(
                request.user.id, body.preset_type, body.modality, body.name,
                body.config, body.is_default,
            )
            # The created row is authoritative — a re-fetch is only needed to
            # keep panel lists fresh, never for the response/audit id (the
            # list sorts by is_default, so [0] may be a different preset).
            await AuditLog(conn).log_event(
                event_type='reading_preset.saved',
                actor_id=request.user.id,
                resource_type='reading_preset',
                resource_id=str(created_preset['id']),
                details={
                    'preset_type': body.preset_type,
                    'modality': body.modality,
                    'name': body.name,
                },
                tenant=request.user.tenant,
                request_id=request_id_var.get(),
            )
        return created({'data': created_preset})


class ReadingPresetHandler(HTTPEndpoint):
    """Update or delete one of my presets."""

    async def _owned(self, conn, request, preset_id):
        preset = await ReadingPresets(conn).get(preset_id)
        if not preset:
            return None, not_found('Preset not found')
        if int(preset['user_id']) != int(request.user.id) and not request.user.admin:
            return None, forbidden('Only the owner can modify this preset')
        return preset, None

    @requires_permission(Permission.REPORT_WRITE)
    async def put(self, request):
        preset_id = request.path_params['id']
        body = await parse_body(UpdateReadingPresetRequest, request)
        async with get_conn() as conn:
            preset, err = await self._owned(conn, request, preset_id)
            if err:
                return err
            if body.is_default:
                await conn.execute(
                    "UPDATE reading_presets SET is_default = FALSE "
                    "WHERE user_id = $1 AND preset_type = $2 AND modality = $3 "
                    "AND id <> $4",
                    int(request.user.id), preset['preset_type'],
                    body.modality or preset['modality'], preset_id,
                )
            updated = await ReadingPresets(conn).update(
                preset_id,
                config=body.config, name=body.name,
                is_default=body.is_default, modality=body.modality,
            )
            await AuditLog(conn).log_event(
                event_type='reading_preset.updated',
                actor_id=request.user.id,
                resource_type='reading_preset',
                resource_id=preset_id,
                details={'name': body.name or preset['name']},
                tenant=request.user.tenant,
                request_id=request_id_var.get(),
            )
        return ok({'data': updated})

    @requires_permission(Permission.REPORT_WRITE)
    async def delete(self, request):
        preset_id = request.path_params['id']
        async with get_conn() as conn:
            preset, err = await self._owned(conn, request, preset_id)
            if err:
                return err
            await ReadingPresets(conn).delete(preset_id)
            await AuditLog(conn).log_event(
                event_type='reading_preset.deleted',
                actor_id=request.user.id,
                resource_type='reading_preset',
                resource_id=preset_id,
                details={'name': preset['name']},
                tenant=request.user.tenant,
                request_id=request_id_var.get(),
            )
        return ok({'data': {'deleted': True}})
