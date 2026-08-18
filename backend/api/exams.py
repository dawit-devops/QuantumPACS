"""Exam lifecycle endpoints for the R06 Radiology Technologist workflow.

Covers the full exam lifecycle (FR-R06-01..10): adoption from the modality
worklist, patient identity verification, protocol selection + emergency
override, image acquisition + QA (accept/reject), dose documentation with ACR
benchmarks, pre-contrast safety checks, completion + handoff to the
radiologist, and incident logging (with QA notification on high/critical).
"""
import uuid
from datetime import datetime, timezone

from db.conn import get_tenant_slug
from starlette.endpoints import HTTPEndpoint

from api.rbac import requires_permission
from api.permissions import Permission
from api.response import not_found, ok, created, validation_error
from api.validate import parse_body
from api.schemas.exams import (
    CreateExamRequest, IdentityConfirmRequest, StartProtocolRequest,
    CreateAcquisitionRequest, AcquisitionDecisionRequest, SafetyCheckRequest,
    CompleteExamRequest, IncidentRequest, OverrideRequest, CriticalFlagRequest,
)
from db.audit_log import AuditLog
from db.conn import get_conn
from db.exams import (
    Exams, Acquisitions, SafetyChecks, Incidents, ProtocolOverrides, Protocols,
)
from db.patient import Patient
from db.notifications import Notifications
# C11: the console mounts the real viewer when the exam's study has been
# stored, reusing the same accession+MRN imaging bridge the reading console
# uses. Imported lazily-safe: api.reports never imports api.exams, so no cycle.
from api.reports import _exam_imaging
from log import request_id_var
from api.tenant_middleware import effective_tenant

DEFAULT_PROTOCOLS = [
    {
        'name': 'CT Head (Routine)', 'modality': 'CT', 'body_part': 'Head',
        'sequences': [
            {'name': 'Localizer', 'required': True},
            {'name': 'Axial Non-Contrast', 'required': True},
            {'name': 'Contrast (if ordered)', 'required': False},
        ],
        'parameters': {'kVp': 120, 'mAs': 340, 'slice_thickness_mm': 5},
        'acr_benchmark_dlp': 1300.0, 'is_default': True,
    },
    {
        'name': 'CT Chest (Routine)', 'modality': 'CT', 'body_part': 'Chest',
        'sequences': [
            {'name': 'Localizer', 'required': True},
            {'name': 'Axial Diagnostic', 'required': True},
        ],
        'parameters': {'kVp': 120, 'mAs': 210, 'slice_thickness_mm': 1.25},
        'acr_benchmark_dlp': 1000.0, 'is_default': False,
    },
    {
        'name': 'MRI Brain (Routine)', 'modality': 'MR', 'body_part': 'Brain',
        'sequences': [
            {'name': 'Localizer', 'required': True},
            {'name': 'Axial T1', 'required': True},
            {'name': 'Axial T2', 'required': True},
            {'name': 'FLAIR', 'required': True},
            {'name': 'DWI', 'required': True},
        ],
        'parameters': {'TR_ms': 2000, 'TE_ms': 90, 'flip_angle_deg': 90},
        'acr_benchmark_dlp': None, 'is_default': True,
    },
    {
        'name': 'PET Whole Body', 'modality': 'PET', 'body_part': 'Whole Body',
        'sequences': [
            {'name': 'Dose Calibration', 'required': True},
            {'name': 'Uptake Period', 'required': True},
            {'name': 'Emission Scan', 'required': True},
        ],
        'parameters': {'dose_mCi': 15, 'uptake_min': 60},
        'acr_benchmark_dlp': None, 'is_default': True,
    },
    {
        'name': 'DX Chest PA/LAT', 'modality': 'DX', 'body_part': 'Chest',
        'sequences': [
            {'name': 'PA', 'required': True},
            {'name': 'Lateral', 'required': True},
        ],
        'parameters': {'kVp': 125, 'mAs': 4},
        'acr_benchmark_dlp': None, 'is_default': True,
    },
    {
        'name': 'US Abdomen Complete', 'modality': 'US', 'body_part': 'Abdomen',
        'sequences': [
            {'name': 'Real-time Capture', 'required': True},
        ],
        'parameters': {'probe': 'Curvilinear 2-5MHz'},
        'acr_benchmark_dlp': None, 'is_default': True,
    },
]


async def _seed_protocols(conn):
    """Idempotently seed the protocol registry on first access."""
    count = await conn.fetchval('SELECT count(*) FROM protocols')
    if count:
        return
    import json as _json
    for p in DEFAULT_PROTOCOLS:
        # asyncpg requires JSON strings for jsonb parameters.
        await conn.execute(
            """INSERT INTO protocols (name, modality, body_part, sequences,
               parameters, acr_benchmark_dlp, is_default, tenant_id)
               VALUES ($1, $2, $3, $4::jsonb, $5::jsonb, $6, $7, $8) """,
            p['name'], p['modality'], p['body_part'],
            _json.dumps(p['sequences']), _json.dumps(p['parameters']),
            p['acr_benchmark_dlp'],
            p['is_default'],
            get_tenant_slug() or 'default',
        )


def _prior_studies(patient, accession):
    """Compact list of the patient's prior DICOM studies (FR-R06-02).

    Takes the already-fetched `Patient.get_extra` tree (the exam GET shares
    one lookup between this and `_exam_imaging`), so it is a pure
    projection. The identity card needs a comparison link, so each prior
    carries the first file id to open in the viewer (`/files/{id}`). The
    current exam's own accession is excluded so "prior" means what a
    technologist would compare against, not the study being acquired.
    """
    priors = []
    for study in patient.get('studies', []):
        if accession and (study.get('accession_number') or '') == accession:
            continue
        series = study.get('series', []) or []
        files = [f for s in series for f in (s.get('files', []) or [])]
        priors.append({
            'id': study['id'],
            'description': study.get('description') or '',
            'accession_number': study.get('accession_number') or '',
            'study_instance_uid': study.get('study_instance_uid') or '',
            'modality': ','.join(
                dict.fromkeys(s.get('modality') for s in series if s.get('modality')),
            ),
            'series_count': len(series),
            'file_count': len(files),
            'first_file_id': files[0]['id'] if files else None,
        })
    return priors


async def _notify_role(conn, role_slug, event_type, title, body, link):
    """Create a notification for every user with the given role slug."""
    role = await conn.fetchrow(
        "SELECT id FROM roles WHERE slug = $1", role_slug,
    )
    if not role:
        return
    rows = await conn.fetch(
        "SELECT id FROM users WHERE role_id = $1", role['id'],
    )
    n = Notifications(conn)
    for row in rows:
        await n.create(row['id'], event_type, title, body, link)


async def _notify_user(conn, user_id, event_type, title, body, link):
    """Create a single-user notification (technologist review P2-2: incident
    authors get told when QA resolves their report)."""
    if not user_id:
        return
    await Notifications(conn).create(user_id, event_type, title, body, link)


class ExamsHandler(HTTPEndpoint):
    """Adopt a worklist entry (or create an exam) and drive its lifecycle."""

    @staticmethod
    def _hl7_priority_to_exam(hl7_priority):
        """Map HL7 OBR-27.7 priority codes onto the exam priority scale.

        The worklist stores the raw HL7 code (S/A/U/R...); exams use
        routine/urgent/stat (ME-04 priority flow: ORM -> worklist -> exam).
        """
        code = (hl7_priority or '').upper().strip()
        if code in ('S', 'STAT'):
            return 'stat'
        if code in ('A', 'ASAP', 'U', 'URGENT', 'T'):
            return 'urgent'
        return 'routine'

    @requires_permission(Permission.EXAM_READ)
    async def get(self, request):
        status = request.query_params.get('status')
        modality = request.query_params.get('modality')
        priority = request.query_params.get('priority')
        search = request.query_params.get('search')
        # P1-2: 'mine' / 'pool' narrows the assignment union; None keeps the
        # default (assigned-to-me + unassigned pool).
        assigned = request.query_params.get('assigned')
        # User.id is the only stable technologist identity on the request object.
        username = str(request.user.id)
        async with get_conn() as conn:
            await _seed_protocols(conn)
            exams = await Exams(conn).list_for_technologist(
                username=username, status=status, modality=modality,
                priority=priority, search=search, assigned=assigned,
            )
        return ok({'data': exams})

    @requires_permission(Permission.EXAM_WRITE)
    async def post(self, request):
        body = await parse_body(CreateExamRequest, request)
        async with get_conn() as conn:
            # Adopt from a worklist entry when provided.
            entry = None
            if body.worklist_entry_id:
                row = await conn.fetchrow(
                    "SELECT * FROM worklist_entries WHERE id = $1",
                    body.worklist_entry_id,
                )
                if not row:
                    return not_found('Worklist entry not found')
                # A worklist entry may only be adopted into a single exam.
                existing = await conn.fetchrow(
                    "SELECT id FROM exams WHERE worklist_entry_id = $1",
                    body.worklist_entry_id,
                )
                if existing:
                    return validation_error(
                        'Worklist entry already adopted into exam ' + str(existing['id']),
                    )
                entry = dict(row)
            # ME-04 priority flow: a default-routine exam adopted from a
            # worklist entry inherits the HL7 priority (OBR-27.7) the ORM
            # message carried, mapped onto the exam scale.
            exam_priority = body.priority
            entry_priority = (entry or {}).get('requested_procedure_priority', '')
            if exam_priority == 'routine' and entry_priority:
                exam_priority = self._hl7_priority_to_exam(entry_priority)
            exam = await Exams(conn).create({
                'worklist_entry_id': body.worklist_entry_id,
                'patient_id': body.patient_id or (entry or {}).get('patient_id', ''),
                'patient_name': body.patient_name or (entry or {}).get('patient_name', ''),
                'patient_birth_date': body.patient_birth_date or (entry or {}).get('patient_birth_date', ''),
                'patient_sex': body.patient_sex or (entry or {}).get('patient_sex', ''),
                'accession_number': body.accession_number or (entry or {}).get('accession_number', ''),
                'requested_procedure_desc': body.requested_procedure_desc or (entry or {}).get('requested_procedure_desc', ''),
                'modality': body.modality or (entry or {}).get('modality', ''),
                'station_ae_title': body.station_ae_title or (entry or {}).get('station_ae_title', ''),
                'priority': exam_priority,
                'protocol_name': body.protocol_name,
                # Denormalize the referring physician from the adopted entry
                # (OBR-16) so the reading worklist can filter on it.
                'referring_physician': body.referring_physician or (entry or {}).get('referring_physician', ''),
                'assigned_technologist': str(request.user.id),
                'created_by': str(request.user.id),
            })
            await AuditLog(conn).log_event(
                event_type='exam.created',
                actor_id=request.user.id,
                resource_type='exam',
                resource_id=exam['id'],
                details={
                    'accession_number': exam.get('accession_number'),
                    'modality': exam.get('modality'),
                    'priority': exam.get('priority'),
                },
                tenant=effective_tenant(request),
                request_id=request_id_var.get(),
            )
        return created({'data': exam})


class ExamHandler(HTTPEndpoint):
    @requires_permission(Permission.EXAM_READ)
    async def get(self, request):
        exam_id = request.path_params['id']
        async with get_conn() as conn:
            exam = await Exams(conn).get(exam_id)
            if not exam:
                return not_found('Exam not found')
            acquisitions = await Acquisitions(conn).list_for_exam(exam_id)
            safety_checks = await SafetyChecks(conn).list_for_exam(exam_id)
            incidents = await Incidents(conn).list_for_exam(exam_id)
            overrides = await ProtocolOverrides(conn).list_for_exam(exam_id)
            dose = await Acquisitions(conn).dose_totals(exam_id)
            # The console reads benchmark_dlp / dose_level directly off the
            # exam payload (the /dose endpoint serves the same fields).
            benchmark = None
            level = 'ok'
            if exam.get('protocol_name'):
                protocol = await conn.fetchrow(
                    "SELECT * FROM protocols WHERE name = $1", exam['protocol_name'],
                )
                if protocol:
                    benchmark = protocol['acr_benchmark_dlp']
                    if benchmark and dose.get('total_dlp'):
                        ratio = dose['total_dlp'] / benchmark
                        if ratio >= 1.0:
                            level = 'danger'
                        elif ratio >= 0.8:
                            level = 'warning'
            # FR-R06-02 + C11: prior-study comparison links and the real
            # DICOM tree both project from the patient's studies, so the
            # (expensive, study→series→file incl. f.meta) get_extra tree is
            # fetched once and shared instead of per-helper.
            mrn = (exam.get('patient_id') or '').strip()
            patient_extra = None
            if mrn:
                prow = await conn.fetchrow(
                    'SELECT id FROM patients WHERE patient_id = $1', mrn,
                )
                if prow:
                    patient_extra = await Patient(conn).get_extra(prow['id'])
            accession = (exam.get('accession_number') or '').strip()
            prior_studies = (
                _prior_studies(patient_extra, accession)
                if patient_extra else []
            )
            imaging_patient = await _exam_imaging(
                conn, exam, patient=patient_extra,
            )
            # technologist review P1-3: the completed-exam feedback loop — the
            # tech's worklist shows the read state of exams they completed.
            # reports.status machine: draft -> preliminary -> submitted -> final.
            report_status = await conn.fetchval(
                "SELECT status FROM reports WHERE exam_id = $1", exam_id,
            )
            # P1-3: QA flags on the tech's images = open incidents for this exam.
            qa_flags = await conn.fetchval(
                "SELECT count(*) FROM incidents WHERE exam_id = $1 "
                "AND status != 'resolved'", exam_id,
            ) or 0
            # P2-3: prior safety/contrast screening for the same patient
            # (excluding this exam) so the tech sees documented reactions
            # before scanning. Rows carry checked item, answer, who, when.
            prior_safety_checks = []
            if mrn:
                prior_safety_checks = await conn.fetch(
                    """SELECT sc.check_item, sc.answer, sc.checked_by, sc.checked_at,
                            e.accession_number, e.created_at AS exam_date
                       FROM safety_checks sc
                       JOIN exams e ON e.id = sc.exam_id
                       WHERE e.patient_id = $1 AND e.id != $2
                       ORDER BY sc.checked_at DESC""",
                    mrn, exam_id,
                )
        return ok({
            'data': {
                **exam,
                'acquisitions': acquisitions,
                'safety_checks': safety_checks,
                'incidents': incidents,
                'overrides': overrides,
                'dose': dose,
                'benchmark_dlp': benchmark,
                'dose_level': level,
                'prior_studies': prior_studies,
                'imaging': imaging_patient is not None,
                'imaging_patient': imaging_patient,
                'report_status': report_status,
                'qa_flags': qa_flags,
                'prior_safety_checks': [dict(r) for r in prior_safety_checks],
            },
        })


class ExamClaimHandler(HTTPEndpoint):
    """technologist review P1-2: claim an unassigned exam.

    The worklist lists exams with `assigned_technologist = ''` in every
    technologist's queue; claiming assigns it to the caller so ownership is
    explicit and auditable. Rejected with a conflict when already assigned to
    someone else, so two techs can't both take the same STAT.
    """

    @requires_permission(Permission.EXAM_WRITE)
    async def post(self, request):
        exam_id = request.path_params['id']
        async with get_conn() as conn:
            exam = await Exams(conn).get(exam_id)
            if not exam:
                return not_found('Exam not found')
            current = exam.get('assigned_technologist') or ''
            if current and current != str(request.user.id):
                return validation_error(
                    'Exam already claimed by another technologist',
                )
            if not current:
                await conn.execute(
                    "UPDATE exams SET assigned_technologist = $2, updated_at = now() "
                    "WHERE id = $1",
                    exam_id, str(request.user.id),
                )
                await AuditLog(conn).log_event(
                    event_type='exam.claimed',
                    actor_id=request.user.id,
                    resource_type='exam',
                    resource_id=exam_id,
                    details={'accession_number': exam.get('accession_number') or ''},
                    tenant=effective_tenant(request),
                    request_id=request_id_var.get(),
                )
        return ok({'data': {'claimed': True}})


class ExamIdentityHandler(HTTPEndpoint):
    @requires_permission(Permission.EXAM_WRITE)
    async def post(self, request):
        exam_id = request.path_params['id']
        body = await parse_body(IdentityConfirmRequest, request)
        async with get_conn() as conn:
            exam = await Exams(conn).get(exam_id)
            if not exam:
                return not_found('Exam not found')
            if body.confirmed:
                await Exams(conn).update_status(
                    exam_id, 'in_progress',
                    identity_confirmed_at=datetime.now(timezone.utc),
                )
            await AuditLog(conn).log_event(
                event_type='exam.identity_confirmed' if body.confirmed else 'exam.identity_failed',
                actor_id=request.user.id,
                resource_type='exam',
                resource_id=exam_id,
                details={'notes': body.notes},
                tenant=effective_tenant(request),
                request_id=request_id_var.get(),
            )
        return ok({'data': {'confirmed': body.confirmed}})


class ExamProtocolHandler(HTTPEndpoint):
    @requires_permission(Permission.EXAM_WRITE)
    async def post(self, request):
        exam_id = request.path_params['id']
        body = await parse_body(StartProtocolRequest, request)
        async with get_conn() as conn:
            exam = await Exams(conn).get(exam_id)
            if not exam:
                return not_found('Exam not found')
            name = body.protocol_name or exam.get('protocol_name')
            await conn.execute(
                "UPDATE exams SET protocol_name = $2, updated_at = now() WHERE id = $1",
                exam_id, name,
            )
            await AuditLog(conn).log_event(
                event_type='exam.protocol_started',
                actor_id=request.user.id,
                resource_type='exam',
                resource_id=exam_id,
                details={'protocol_name': name},
                tenant=effective_tenant(request),
                request_id=request_id_var.get(),
            )
        return ok({'data': {'protocol_name': name}})


class ExamAcquisitionsHandler(HTTPEndpoint):
    @requires_permission(Permission.EXAM_WRITE)
    async def post(self, request):
        exam_id = request.path_params['id']
        body = await parse_body(CreateAcquisitionRequest, request)
        async with get_conn() as conn:
            exam = await Exams(conn).get(exam_id)
            if not exam:
                return not_found('Exam not found')
            instance_uid = body.instance_uid or f'1.2.826.0.1.3680043.9.{uuid.uuid4().int}'
            acquisition = await Acquisitions(conn).create({
                'exam_id': exam_id,
                'series_number': body.series_number,
                'instance_uid': instance_uid,
                'description': body.description,
                'kvp': body.kvp, 'mas': body.mas, 'dlp': body.dlp,
                'ctdivol': body.ctdivol, 'exposure_time': body.exposure_time,
                'status': 'pending',
            })
            # Auto-accept when no dose/QA concerns; rejection happens explicitly.
            await AuditLog(conn).log_event(
                event_type='exam.acquisition_recorded',
                actor_id=request.user.id,
                resource_type='acquisition',
                resource_id=acquisition['id'],
                details={'description': body.description},
                tenant=effective_tenant(request),
                request_id=request_id_var.get(),
            )
        return created({'data': acquisition})


class ExamAcquisitionDecisionHandler(HTTPEndpoint):
    @requires_permission(Permission.EXAM_WRITE)
    async def post(self, request):
        exam_id = request.path_params['id']
        acq_id = request.path_params['aid']
        decision = request.path_params.get('decision', 'accept')
        body = await parse_body(AcquisitionDecisionRequest, request)
        async with get_conn() as conn:
            acquisition = await Acquisitions(conn).get(acq_id)
            # exam_id comes back as uuid.UUID from asyncpg; compare as strings.
            if not acquisition or str(acquisition['exam_id']) != exam_id:
                return not_found('Acquisition not found')
            status = 'accepted' if decision == 'accept' else 'rejected'
            await Acquisitions(conn).set_status(
                acq_id, status, reject_reason=body.reason if decision == 'reject' else '',
            )
            rejected = await Acquisitions(conn).rejected_count(exam_id)
            await AuditLog(conn).log_event(
                event_type=f'exam.acquisition_{status}',
                actor_id=request.user.id,
                resource_type='acquisition',
                resource_id=acq_id,
                details={'reason': body.reason},
                tenant=effective_tenant(request),
                request_id=request_id_var.get(),
            )
        return ok({'data': {'status': status, 'rejected_count': rejected}})


class ExamDoseHandler(HTTPEndpoint):
    @requires_permission(Permission.EXAM_READ)
    async def get(self, request):
        exam_id = request.path_params['id']
        async with get_conn() as conn:
            exam = await Exams(conn).get(exam_id)
            if not exam:
                return not_found('Exam not found')
            totals = await Acquisitions(conn).dose_totals(exam_id)
            protocol = None
            if exam.get('protocol_name'):
                protocol = await conn.fetchrow(
                    "SELECT * FROM protocols WHERE name = $1", exam['protocol_name'],
                )
            benchmark = (dict(protocol) if protocol else {}).get('acr_benchmark_dlp')
            level = 'ok'
            if benchmark and totals.get('total_dlp'):
                ratio = totals['total_dlp'] / benchmark
                if ratio >= 1.0:
                    level = 'danger'
                elif ratio >= 0.8:
                    level = 'warning'
        return ok({'data': {'dose': totals, 'benchmark_dlp': benchmark, 'level': level}})


class ExamSafetyHandler(HTTPEndpoint):
    @requires_permission(Permission.EXAM_WRITE)
    async def post(self, request):
        exam_id = request.path_params['id']
        body = await parse_body(SafetyCheckRequest, request)
        async with get_conn() as conn:
            exam = await Exams(conn).get(exam_id)
            if not exam:
                return not_found('Exam not found')
            for check in body.checks:
                await SafetyChecks(conn).create({
                    'exam_id': exam_id,
                    'check_item': check['check_item'],
                    'answer': check['answer'],
                    'notes': check.get('notes', ''),
                    'checked_by': str(request.user.id),
                })
            await AuditLog(conn).log_event(
                event_type='exam.safety_checks_recorded',
                actor_id=request.user.id,
                resource_type='exam',
                resource_id=exam_id,
                details={'count': len(body.checks)},
                tenant=effective_tenant(request),
                request_id=request_id_var.get(),
            )
        return ok({'data': {'recorded': len(body.checks)}})


class ExamCompleteHandler(HTTPEndpoint):
    @requires_permission(Permission.EXAM_WRITE)
    async def post(self, request):
        exam_id = request.path_params['id']
        body = await parse_body(CompleteExamRequest, request)
        if not body.dose_recorded or not body.sequences_complete:
            return validation_error(
                'Dose data and sequence compliance are required before completion',
            )
        async with get_conn() as conn:
            exam = await Exams(conn).get(exam_id)
            if not exam:
                return not_found('Exam not found')
            await Exams(conn).update_status(
                exam_id, 'completed',
                completed_at=datetime.now(timezone.utc),
            )
            # Hand off to the radiologist worklist (FR-R06-07): the source
            # worklist entry moves from scheduled -> performed.
            accession = exam.get('accession_number') or ''
            if exam.get('worklist_entry_id'):
                await conn.execute(
                    "UPDATE worklist_entries SET status = 'performed', performed_at = now(), "
                    "updated_at = now() WHERE id = $1", exam['worklist_entry_id'],
                )
            await _notify_role(
                conn, 'radiologist', 'exam.completed',
                f'Exam complete: {accession}',
                f'{exam.get("patient_name") or exam.get("patient_id")} — '
                f'{exam.get("modality")} exam completed and ready for review.',
                f'/reading/{exam_id}',
            )
            await AuditLog(conn).log_event(
                event_type='exam.completed',
                actor_id=request.user.id,
                resource_type='exam',
                resource_id=exam_id,
                details={'accession_number': accession},
                tenant=effective_tenant(request),
                request_id=request_id_var.get(),
            )
        return ok({'data': {'status': 'completed'}})


class ExamCriticalFlagHandler(HTTPEndpoint):
    """technologist review P1-1: flag an exam for immediate radiology read.

    Converts the dead CRITICAL_RESULTS_WRITE grant into a live, auditable
    safety action: the technologist marks an alarming finding during
    acquisition and the radiologist worklist surfaces it above routine work.
    Re-flagging is an upsert (idempotent, updates severity/note).
    """

    @requires_permission(Permission.CRITICAL_RESULTS_WRITE)
    async def post(self, request):
        exam_id = request.path_params['id']
        body = await parse_body(CriticalFlagRequest, request)
        async with get_conn() as conn:
            exam = await Exams(conn).get(exam_id)
            if not exam:
                return not_found('Exam not found')
            await conn.execute(
                "UPDATE exams SET critical_flag = $2, critical_flag_note = $3, "
                "critical_flagged_at = now(), critical_flagged_by = $4, "
                "updated_at = now() WHERE id = $1",
                exam_id, body.severity, body.note, str(request.user.id),
            )
            await AuditLog(conn).log_event(
                event_type='exam.critical_flagged',
                actor_id=request.user.id,
                resource_type='exam',
                resource_id=exam_id,
                details={'severity': body.severity, 'note': body.note[:120]},
                tenant=effective_tenant(request),
                request_id=request_id_var.get(),
            )
            accession = exam.get('accession_number') or ''
            await _notify_role(
                conn, 'radiologist', 'exam.critical_flagged',
                f'CRITICAL: {accession}',
                f'{body.severity.upper()} — {body.note[:120]}',
                f'/reading/{exam_id}',
            )
        return created({'data': {'flagged': True, 'severity': body.severity}})


class ExamIncidentsHandler(HTTPEndpoint):
    @requires_permission(Permission.EXAM_WRITE)
    async def post(self, request):
        exam_id = request.path_params['id']
        body = await parse_body(IncidentRequest, request)
        async with get_conn() as conn:
            exam = await Exams(conn).get(exam_id)
            if not exam:
                return not_found('Exam not found')
            incident = await Incidents(conn).create({
                'exam_id': exam_id,
                'incident_type': body.incident_type,
                'severity': body.severity,
                'description': body.description,
                'reported_by': str(request.user.id),
            })
            await AuditLog(conn).log_event(
                event_type='exam.incident_logged',
                actor_id=request.user.id,
                resource_type='incident',
                resource_id=incident['id'],
                details={'severity': body.severity, 'incident_type': body.incident_type},
                tenant=effective_tenant(request),
                request_id=request_id_var.get(),
            )
            if body.severity in ('high', 'critical'):
                await _notify_role(
                    conn, 'qa', 'incident.reported',
                    f'{body.severity.upper()} incident reported',
                    f'{body.incident_type}: {body.description[:120]}',
                    f'/exams/{exam_id}',
                )
        return created({'data': incident})


class ExamOverridesHandler(HTTPEndpoint):
    @requires_permission(Permission.EXAM_WRITE)
    async def post(self, request):
        exam_id = request.path_params['id']
        body = await parse_body(OverrideRequest, request)
        async with get_conn() as conn:
            exam = await Exams(conn).get(exam_id)
            if not exam:
                return not_found('Exam not found')
            original = {}
            if exam.get('protocol_name'):
                row = await conn.fetchrow(
                    "SELECT parameters FROM protocols WHERE name = $1",
                    exam['protocol_name'],
                )
                if row:
                    original = row['parameters'] or {}
            override = await ProtocolOverrides(conn).create({
                'exam_id': exam_id,
                'justification': body.justification,
                'original_params': original,
                'overridden_params': body.overridden_parameters,
                'overridden_by': str(request.user.id),
            })
            await AuditLog(conn).log_event(
                event_type='exam.protocol_overridden',
                actor_id=request.user.id,
                resource_type='protocol_override',
                resource_id=override['id'],
                details={'justification': body.justification},
                tenant=effective_tenant(request),
                request_id=request_id_var.get(),
            )
        return created({'data': override})


class ProtocolsHandler(HTTPEndpoint):
    @requires_permission(Permission.EXAM_READ)
    async def get(self, request):
        modality = request.query_params.get('modality')
        async with get_conn() as conn:
            await _seed_protocols(conn)
            protocols = await Protocols(conn).list_by_modality(modality)
        return ok({'data': protocols})
