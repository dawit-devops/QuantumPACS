"""§2.11 nursing endpoints (N-01..N-04) — exam-linked vitals, pre-procedure
checklist, contrast consent and nurse notes, plus the /nursing prep list.

Gate contract (G3, human-approved 2026-08-25):
* Reads on exam-linked records pass any-of [NURSING_READ, EXAM_READ] —
  spec N-04 makes nurse notes/vitals visible to technologist and radiologist,
  who hold EXAM_READ; no further matrix changes needed.
* All writes are strictly NURSING_WRITE (held by care_coordinator per G3).
* GET /nursing/prep-list is NURSING_READ-only: it is the coordinator's prep
  queue, not an acquisition surface.
Every handler resolves the exam first and derives patient_id from it — the
client never supplies patient identity for an exam-scoped record.
"""
from starlette.endpoints import HTTPEndpoint

from api.rbac import requires_permission
from api.permissions import Permission
from api.response import created, not_found, ok, validation_error
from api.validate import parse_body
from api.schemas.nursing import (
    ChecklistUpdateRequest,
    ContrastConsentRequest,
    NurseNoteRequest,
    VitalsRequest,
)
from db.audit_log import AuditLog
from db.conn import get_conn
from db.exams import Exams
from db.nursing import (
    ContrastConsents,
    ExamNotes,
    ExamVitals,
    NursingPrepList,
    PrepChecklists,
)
from log import get_logger, request_id_var

log = get_logger(__name__)

# Read visibility: nursing records ride the exam context (spec N-04).
_NURSING_OR_EXAM_READ = [Permission.NURSING_READ, Permission.EXAM_READ]


def _tenant(request):
    from api.tenant_middleware import effective_tenant

    return effective_tenant(request) or 'default'


async def _exam_or_404(conn, request):
    exam = await Exams(conn).get(request.path_params['exam_id'])
    if not exam:
        return None
    return exam


class VitalsHandler(HTTPEndpoint):
    """N-01 — timestamped vitals recorded before a procedure."""

    @requires_permission(_NURSING_OR_EXAM_READ)
    async def get(self, request):
        async with get_conn() as conn:
            exam = await _exam_or_404(conn, request)
            if exam is None:
                return not_found('Exam not found')
            rows = await ExamVitals(conn).list_for_exam(
                exam['id'], tenant_id=_tenant(request),
            )
        return ok({'data': rows})

    @requires_permission(Permission.NURSING_WRITE)
    async def post(self, request):
        body = await parse_body(VitalsRequest, request)
        async with get_conn() as conn:
            exam = await _exam_or_404(conn, request)
            if exam is None:
                return not_found('Exam not found')
            row = await ExamVitals(conn).record(
                exam_id=exam['id'],
                patient_id=exam['patient_id'],
                bp_systolic=body.bp_systolic,
                bp_diastolic=body.bp_diastolic,
                heart_rate=body.heart_rate,
                spo2=body.spo2,
                temperature_c=body.temperature_c,
                respiration=body.respiration,
                weight_kg=body.weight_kg,
                height_cm=body.height_cm,
                by=str(request.user.id),
                tenant_id=_tenant(request),
            )
            await AuditLog(conn).log_event(
                event_type='nursing.vitals_recorded',
                actor_id=request.user.id,
                resource_type='vitals',
                resource_id=exam['id'],
                details={'patient_id': exam['patient_id']},
                request_id=request_id_var.get(),
            )
        return created({'data': row})


class PrepChecklistHandler(HTTPEndpoint):
    """N-02 — interactive pre-procedure checklist; confirm is refused until
    every required item is checked."""

    @requires_permission(_NURSING_OR_EXAM_READ)
    async def get(self, request):
        async with get_conn() as conn:
            exam = await _exam_or_404(conn, request)
            if exam is None:
                return not_found('Exam not found')
            row = await PrepChecklists(conn).get_or_create(
                exam_id=exam['id'],
                patient_id=exam['patient_id'],
                tenant_id=_tenant(request),
            )
        return ok({'data': row})

    @requires_permission(Permission.NURSING_WRITE)
    async def put(self, request):
        body = await parse_body(ChecklistUpdateRequest, request)
        async with get_conn() as conn:
            exam = await _exam_or_404(conn, request)
            if exam is None:
                return not_found('Exam not found')
            checklists = PrepChecklists(conn)
            existing = await checklists.get_or_create(
                exam_id=exam['id'],
                patient_id=exam['patient_id'],
                tenant_id=_tenant(request),
            )
            items = [item.model_dump() for item in body.items]
            unmet = [
                i['label'] for i in items
                if i.get('required') and not i.get('checked')
            ]
            if body.confirmed and unmet:
                # Spec N-02: required items MUST be checked before the
                # checklist can be confirmed complete.
                return validation_error(
                    'Required checklist items are not checked: '
                    + ', '.join(unmet)
                )
            if body.confirmed:
                row = await checklists.confirm(
                    existing['id'], by=str(request.user.id),
                )
                await AuditLog(conn).log_event(
                    event_type='nursing.checklist_confirmed',
                    actor_id=request.user.id,
                    resource_type='prep_checklist',
                    resource_id=exam['id'],
                    details={'patient_id': exam['patient_id']},
                    request_id=request_id_var.get(),
                )
            else:
                row = await checklists.update_items(existing['id'], items)
                await AuditLog(conn).log_event(
                    event_type='nursing.checklist_updated',
                    actor_id=request.user.id,
                    resource_type='prep_checklist',
                    resource_id=exam['id'],
                    request_id=request_id_var.get(),
                )
        return ok({'data': row})


class ConsentHandler(HTTPEndpoint):
    """N-03 — digital contrast consent with signature capture."""

    @requires_permission(_NURSING_OR_EXAM_READ)
    async def get(self, request):
        async with get_conn() as conn:
            exam = await _exam_or_404(conn, request)
            if exam is None:
                return not_found('Exam not found')
            row = await ContrastConsents(conn).get_for_exam(
                exam['id'], tenant_id=_tenant(request),
            )
        return ok({'data': row})

    @requires_permission(Permission.NURSING_WRITE)
    async def post(self, request):
        body = await parse_body(ContrastConsentRequest, request)
        async with get_conn() as conn:
            exam = await _exam_or_404(conn, request)
            if exam is None:
                return not_found('Exam not found')
            row = await ContrastConsents(conn).create(
                exam_id=exam['id'],
                patient_id=exam['patient_id'],
                accepted=body.accepted,
                signature_png=body.signature_png,
                declined_reason=body.declined_reason,
                consent_text_version=body.consent_text_version,
                witnessed_by=body.witnessed_by,
                by=str(request.user.id),
                tenant_id=_tenant(request),
            )
            await AuditLog(conn).log_event(
                event_type=(
                    'nursing.consent_signed' if body.accepted
                    else 'nursing.consent_declined'
                ),
                actor_id=request.user.id,
                resource_type='contrast_consent',
                resource_id=exam['id'],
                details={'patient_id': exam['patient_id']},
                request_id=request_id_var.get(),
            )
        return created({'data': row})


class NurseNotesHandler(HTTPEndpoint):
    """N-04 — attributed free-text notes on an exam."""

    @requires_permission(_NURSING_OR_EXAM_READ)
    async def get(self, request):
        async with get_conn() as conn:
            exam = await _exam_or_404(conn, request)
            if exam is None:
                return not_found('Exam not found')
            rows = await ExamNotes(conn).list_for_exam(
                exam['id'], tenant_id=_tenant(request),
            )
        return ok({'data': rows})

    @requires_permission(Permission.NURSING_WRITE)
    async def post(self, request):
        body = await parse_body(NurseNoteRequest, request)
        async with get_conn() as conn:
            exam = await _exam_or_404(conn, request)
            if exam is None:
                return not_found('Exam not found')
            row = await ExamNotes(conn).add(
                exam_id=exam['id'],
                patient_id=exam['patient_id'],
                note=body.note,
                author_id=str(request.user.id),
                tenant_id=_tenant(request),
            )
            await AuditLog(conn).log_event(
                event_type='nursing.note_added',
                actor_id=request.user.id,
                resource_type='exam_note',
                resource_id=exam['id'],
                details={'patient_id': exam['patient_id']},
                request_id=request_id_var.get(),
            )
        return created({'data': row})


class NursingPrepListHandler(HTTPEndpoint):
    """Today's exams awaiting prep, with checklist state — the coordinator's
    entry queue that deep-links into the exam console."""

    @requires_permission(Permission.NURSING_READ)
    async def get(self, request):
        async with get_conn() as conn:
            rows = await NursingPrepList(conn).list(tenant_id=_tenant(request))
        return ok({'data': rows})
