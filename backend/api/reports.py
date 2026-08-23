"""R12 Staff Radiologist endpoints: reading worklist, reports, peer review.

Covers FR-R12-01 (priority-sorted reading worklist fed by exam handoff),
FR-R12-09 (structured reporting: draft/preliminary/final + sign-off) and the
peer-review workflow shared with R05 (discrepancy-level QA of signed reports).
"""

from starlette.endpoints import HTTPEndpoint

from api.rbac import requires_permission
from api.permissions import Permission
from api.response import ok, created, not_found, validation_error, forbidden
from api.validate import parse_body
from api.schemas.reports import (
    SaveReportRequest, SignReportRequest, ReturnReportRequest,
    AssignRadiologistRequest, CreatePeerReviewRequest, SubmitPeerReviewRequest,
)
from db.audit_log import AuditLog
from db.conn import get_conn
from db.exams import Exams
from db.patient import Patient
from db.reports import Reports, ReportTemplates, PeerReviews
from api.notify import notify_role, notify_user
from log import request_id_var, get_logger
from api.tenant_middleware import effective_tenant
from services.results_distribution.service import ResultsDistributionEngine

log = get_logger(__name__)

DEFAULT_REPORT_TEMPLATES = [
    {
        'name': 'CT Head — Routine', 'modality': 'CT', 'body_part': 'Head',
        'findings_template': (
            'Technique: Non-contrast head CT.\n'
            'Ventricles: [normal size and position].\n'
            'Midline: [no shift].\n'
            'Parenchyma: [no acute intracranial hemorrhage, mass, or infarct].'
        ),
        'impression_template': 'No acute intracranial abnormality.',
        'is_default': True,
    },
    {
        'name': 'CT Chest — Routine', 'modality': 'CT', 'body_part': 'Chest',
        'findings_template': (
            'Technique: Contrast-enhanced chest CT.\n'
            'Lungs: [no nodules, consolidation, or effusion].\n'
            'Mediastinum: [no lymphadenopathy or mass].\n'
            'Pleura: [clear].'
        ),
        'impression_template': 'No acute cardiopulmonary abnormality.',
        'is_default': False,
    },
    {
        'name': 'MRI Brain — Routine', 'modality': 'MR', 'body_part': 'Brain',
        'findings_template': (
            'Technique: Multiplanar brain MRI (T1, T2, FLAIR, DWI).\n'
            'Parenchyma: [no acute infarct, mass, or demyelinating lesion].\n'
            'Ventricles: [normal].\n'
            'Vascular: [no acute occlusion].'
        ),
        'impression_template': 'No acute intracranial abnormality.',
        'is_default': True,
    },
    {
        'name': 'DX Chest PA/LAT — Routine', 'modality': 'DX', 'body_part': 'Chest',
        'findings_template': (
            'Lungs: [clear, no focal opacity].\n'
            'Cardiac silhouette: [normal size].\n'
            'Bones: [no acute fracture].'
        ),
        'impression_template': 'No acute cardiopulmonary abnormality.',
        'is_default': True,
    },
    {
        'name': 'US Abdomen — Complete', 'modality': 'US', 'body_part': 'Abdomen',
        'findings_template': (
            'Liver: [normal echotexture, no mass].\n'
            'Gallbladder: [no stones or wall thickening].\n'
            'Pancreas/spleen/kidneys: [unremarkable].\n'
            'No free fluid.'
        ),
        'impression_template': 'Normal abdominal ultrasound.',
        'is_default': False,
    },
    {
        'name': 'PET Whole Body — Routine', 'modality': 'PET', 'body_part': 'Whole Body',
        'findings_template': (
            'No abnormal FDG-avid focus to suggest malignancy.\n'
            'Physiologic distribution of tracer.'
        ),
        'impression_template': 'Negative whole-body PET.',
        'is_default': True,
    },
]


async def _seed_report_templates(conn):
    """Idempotently seed the report template library on first access."""
    if await ReportTemplates(conn).count():
        return
    for t in DEFAULT_REPORT_TEMPLATES:
        await conn.execute(
            """INSERT INTO report_templates (name, modality, body_part,
               findings_template, impression_template, is_default)
               VALUES ($1, $2, $3, $4, $5, $6)""",
            t['name'], t['modality'], t['body_part'],
            t['findings_template'], t['impression_template'],
            t['is_default'],
        )


class ReadingListHandler(HTTPEndpoint):
    """Priority-sorted reading worklist of handed-off exams (FR-R12-01).

    Filters (ME-04): radiologist=me resolves to the requesting user so the
    frontend needs no client-side identity; physician and date_from/date_to
    bound the queue further.
    """

    @requires_permission(Permission.REPORT_READ)
    async def get(self, request):
        status = request.query_params.get('status')
        modality = request.query_params.get('modality')
        search = request.query_params.get('search')
        radiologist = request.query_params.get('radiologist')
        # R13 resident home: "Claimed today" counts drafts the resident
        # started today (claim = first draft autosave, created_by=user).
        # Only computed for the requester's own queue so other consumers
        # of the reading list (worklist page) see no extra field.
        is_me = radiologist == 'me'
        if radiologist == 'me':
            radiologist = str(request.user.id)
        physician = request.query_params.get('physician')
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        review = request.query_params.get('review')
        if review in ('0', 'false', ''):
            review = None
        # D1: server-side pagination (page/per_page). Absent params mean
        # "unpaged" — never coerce them to an implicit page of 1×1.
        try:
            page = max(1, int(request.query_params.get('page')))
        except (TypeError, ValueError):
            page = None
        try:
            per_page = min(200, max(1, int(
                request.query_params.get('per_page'))))
        except (TypeError, ValueError):
            per_page = None
        async with get_conn() as conn:
            result = await Reports(conn).reading_list(
                status=status, modality=modality, search=search,
                radiologist=radiologist, physician=physician,
                date_from=date_from, date_to=date_to, review=review,
                page=page, per_page=per_page,
            )
            if isinstance(result, tuple):
                items, total = result
            else:  # legacy unpaged callers
                items, total = result, len(result)
            # R13 resident home: "Claimed today" counts drafts the resident
            # started today (claim = first draft autosave, created_by=user).
            # Only computed for the requester's own queue so other consumers
            # of the reading list (worklist page) see no extra field.
            claimed_today = 0
            if is_me:
                claimed_today = await conn.fetchval(
                    "SELECT count(*) FROM reports "
                    "WHERE created_by = $1 "
                    "AND created_at >= date_trunc('day', now())",
                    str(request.user.id),
                ) or 0
            # claimed_today is resident-home-only (R13); other consumers of
            # the reading list (worklist page) keep the payload shape.
            payload = {'data': items}
            if isinstance(result, tuple):
                payload['total'] = total
                payload['page'] = page or 1
                payload['per_page'] = per_page
            if is_me:
                payload['claimed_today'] = claimed_today
        return ok(payload)


class ExamAssignHandler(HTTPEndpoint):
    """Assign (or unassign) a radiologist to a reading-list exam (ME-04).

    The per-physician worklist pattern: a radiologist claims an exam, and
    the queue filter radiologist=me narrows the list to their own claims.
    """

    @requires_permission(Permission.REPORT_WRITE)
    async def post(self, request):
        exam_id = request.path_params['exam_id']
        body = await parse_body(AssignRadiologistRequest, request)
        radiologist_id = body.radiologist_id or str(request.user.id)
        async with get_conn() as conn:
            exam = await Exams(conn).get(exam_id)
            if not exam:
                return not_found('Exam not found')
            if exam.get('status') != 'completed':
                return validation_error(
                    'Only completed exams on the reading worklist can be assigned',
                )
            # S-7: the target must exist and hold the radiologist role —
            # assignment is a claim on the reading worklist, so an arbitrary
            # user id must not be accepted (it would vanish from every
            # radiologist's queue and orphan the exam).
            target = await conn.fetchrow(
                "SELECT u.id, r.slug FROM users u "
                "JOIN roles r ON r.id = u.role_id "
                "WHERE u.id = $1",
                radiologist_id,
            )
            if not target or target['slug'] != 'radiologist':
                return validation_error(
                    'Assigned user must be a radiologist',
                )
            updated = await Exams(conn).assign_radiologist(exam_id, radiologist_id)
            await AuditLog(conn).log_event(
                event_type='exam.radiologist_assigned',
                actor_id=request.user.id,
                resource_type='exam',
                resource_id=str(exam_id),
                details={
                    'radiologist_id': radiologist_id,
                    'accession_number': exam.get('accession_number'),
                },
                tenant=effective_tenant(request),
                request_id=request_id_var.get(),
            )
        return ok({'data': updated})


async def _notify_referring_on_sign(conn, exam):
    """R2-05-04: tell the referring provider their result is ready.

    Resolves the ordering physician from the RIS order by accession and
    only notifies when that field maps to a real user account — free-text
    external names cannot be fanned out safely. Best-effort: callers wrap
    this so a lookup failure never blocks sign-off.
    """
    accession = exam.get('accession_number') or ''
    if not accession:
        return
    order = await conn.fetchrow(
        'SELECT referring_physician FROM ris_orders'
        ' WHERE accession_number = $1 LIMIT 1',
        str(accession),
    )
    if not order or not order.get('referring_physician'):
        return
    user = await conn.fetchrow(
        'SELECT id FROM users WHERE username = $1',
        str(order['referring_physician']),
    )
    if not user:
        return
    await notify_user(
        conn, str(user['id']), 'report.ready',
        'Result available',
        f"Report for {exam.get('patient_name') or accession} is signed"
        ' and available.',
        f"/reading/{exam.get('id', '')}",
    )


async def _with_person_names(conn, report):
    """Resolve the report's user-id columns to usernames for display.

    reports.signed_by / reviewed_by / created_by store users.id; the console
    renders them on the FINAL alert ("Signed by …") and the returned-report
    banner. A single IN query maps the ids to usernames, attached as
    *_by_name so the raw ids stay in the API contract for callers that
    key off them.
    """
    if not report:
        return report
    ids = {report.get(k) for k in ('signed_by', 'reviewed_by', 'created_by')}
    ids.discard(None)
    ids.discard('')
    names = {}
    if ids:
        numeric = []
        for value in ids:
            try:
                numeric.append(int(value))
            except (TypeError, ValueError):
                pass
        if numeric:
            rows = await conn.fetch(
                'SELECT id, username FROM users WHERE id = ANY($1::bigint[])',
                numeric,
            )
            names = {str(row['id']): row['username'] for row in rows}
    for key in ('signed_by', 'reviewed_by', 'created_by'):
        raw = report.get(key)
        report[f'{key}_name'] = names.get(str(raw)) if raw else ''
    return report


class ExamReportHandler(HTTPEndpoint):
    """Get or update the report for a handed-off exam."""

    @requires_permission(Permission.REPORT_READ)
    async def get(self, request):
        exam_id = request.path_params['exam_id']
        async with get_conn() as conn:
            exam = await Exams(conn).get(exam_id)
            if not exam:
                return not_found('Exam not found')
            report = await Reports(conn).get_by_exam(exam_id)
            report = await _with_person_names(conn, dict(report) if report else None)
        return ok({'data': {'exam': exam, 'report': report}})

    @requires_permission(Permission.REPORT_WRITE)
    async def put(self, request):
        exam_id = request.path_params['exam_id']
        body = await parse_body(SaveReportRequest, request)
        async with get_conn() as conn:
            exam = await Exams(conn).get(exam_id)
            if not exam:
                return not_found('Exam not found')
            existing = await Reports(conn).get_by_exam(exam_id)
            if existing and existing.get('status') in ('submitted', 'final'):
                # R13 supervision lock + CR-4: a submitted report is in the
                # attending's hands and a signed (final) report is locked.
                # Neither may be edited through the save endpoint — the
                # former must be returned first, the latter can only change
                # via return-for-revision.
                return validation_error(
                    'Report is submitted or signed — it is locked and cannot '
                    'be edited. A submitted report must be returned for '
                    'revision first; a signed final report requires an '
                    'amendment flow.',
                )
            if existing:
                report = await Reports(conn).update(
                    existing['id'], body.model_dump(),
                    edited_by=str(request.user.id),
                )
            else:
                report = await Reports(conn).create(
                    exam_id, body.model_dump(),
                    created_by=str(request.user.id),
                )
            await AuditLog(conn).log_event(
                event_type='report.saved',
                actor_id=request.user.id,
                resource_type='report',
                resource_id=report['id'],
                details={
                    'exam_id': exam_id,
                    'status': report.get('status'),
                    'accession_number': exam.get('accession_number'),
                },
                tenant=effective_tenant(request),
                request_id=request_id_var.get(),
            )
        return ok({'data': report})


class ExamReportSignHandler(HTTPEndpoint):
    """Sign a report into final status (FR-R12-09 sign-off)."""

    @requires_permission(Permission.REPORT_SIGN)
    async def post(self, request):
        exam_id = request.path_params['exam_id']
        body = await parse_body(SignReportRequest, request)
        if not body.confirm:
            return validation_error('Signing requires explicit confirmation')
        async with get_conn() as conn:
            exam = await Exams(conn).get(exam_id)
            if not exam:
                return not_found('Exam not found')
            report = await Reports(conn).get_by_exam(exam_id)
            if not report:
                return validation_error('No report exists yet for this exam')
            if not (report.get('impression') or '').strip():
                return validation_error(
                    'Impression is required before the report can be signed',
                )
            report = await Reports(conn).sign(report['id'], str(request.user.id))
            # S12-33: TAT metric — from exam completion to sign, labelled by
            # exam priority so the manager dashboard distinguishes STAT from
            # routine turnarounds. A missing completed_at falls back to the
            # report's creation time; must never block or fail the sign.
            try:
                from datetime import datetime, timezone
                from api import telemetry
                signed_at = datetime.now(timezone.utc)
                start_marker = exam.get('completed_at') or report.get('created_at')
                if start_marker:
                    tat = (signed_at - start_marker).total_seconds()
                    priority = exam.get('priority') or 'routine'
                    telemetry.ris_report_tat_seconds.labels(
                        priority=priority).observe(max(tat, 0))
            except Exception:
                log.warning('report TAT metric failed for %s', report['id'],
                            exc_info=True)
            await AuditLog(conn).log_event(
                event_type='report.signed',
                actor_id=request.user.id,
                resource_type='report',
                resource_id=report['id'],
                details={
                    'exam_id': exam_id,
                    'accession_number': exam.get('accession_number'),
                },
                tenant=effective_tenant(request),
                request_id=request_id_var.get(),
            )
            # S8-13/CR-8: ORU^R01 distribution — real engine wired in (module import
            # above keeps it patchable in tests). Runs after the conn block so
            # a transmission failure never rolls back the signed report; the
            # engine records its own SENT/FAILED row and the retry manager
            # handles backoff.
            try:
                await ResultsDistributionEngine().distribute_report(report['id'])
            except Exception:
                log.warning(
                    'ORU^R01 distribution failed for report %s (will retry)',
                    report['id'], exc_info=True,
                )
            # S11-03: Real auto charge drop — CPT/ICD-10 suggested from the
            # procedure description + clinical indication (replaces the S8-14
            # stub). A transmission/DB failure must never block the signed
            # report, so the charge drop is best-effort like distribution.
            try:
                from db.ris_charges import drop_charge
                await drop_charge(
                    conn,
                    report_id=report['id'],
                    exam_id=exam_id,
                    accession_number=exam.get('accession_number', ''),
                    patient_id=exam.get('patient_id', ''),
                    patient_name=exam.get('patient_name', ''),
                    procedure_desc=exam.get('requested_procedure_desc', ''),
                    indication=report.get('clinical_indication', '') or '',
                    radiologist_id=str(request.user.id),
                    tenant_id=effective_tenant(request),
                )
            except Exception:
                log.warning(
                    'charge drop failed for report %s (billing queue will not show it)',
                    report['id'], exc_info=True,
                )
            # Notify QA that a report is final and ready for any scheduled
            # peer review (R05 consumes signed reports for quality sampling).
            await notify_role(
                conn, 'qa', 'report.signed',
                f'Report signed: {exam.get("accession_number") or exam_id}',
                f'{exam.get("patient_name") or exam.get("patient_id")} — final '
                f'report signed by radiologist.',
                f'/reading/{exam_id}',
            )
            # R2-05-04: result-available ping to the referring provider.
            try:
                await _notify_referring_on_sign(conn, exam)
            except Exception:
                log.warning('referring-provider notify failed for %s',
                            exam_id, exc_info=True)
            # R13 co-sign: when an attending signs a resident's submitted
            # draft, tell the resident author their report was co-signed.
            if report.get('created_by') and \
                    report['created_by'] != str(request.user.id):
                await notify_user(
                    conn, report['created_by'], 'report.co-signed',
                    'Report co-signed',
                    'Your draft was co-signed as FINAL by the attending.',
                    f'/reading/{exam_id}',
                )
            report = await _with_person_names(conn, report)
        return ok({'data': report})


class ExamReportSubmitHandler(HTTPEndpoint):
    """R13 resident submits a draft for the supervising attending to co-sign.

    Only a draft/preliminary report can be submitted; once submitted the
    report is locked (PUT is rejected) until the attending either signs it
    (co-sign → final) or returns it for revision (→ draft). Attendings pick
    submitted reports up via the worklist review filter (review=1).
    """

    @requires_permission(Permission.REPORT_WRITE)
    async def post(self, request):
        exam_id = request.path_params['exam_id']
        async with get_conn() as conn:
            exam = await Exams(conn).get(exam_id)
            if not exam:
                return not_found('Exam not found')
            report = await Reports(conn).get_by_exam(exam_id)
            if not report:
                return validation_error('No report exists yet for this exam')
            if report['status'] not in ('draft', 'preliminary'):
                return validation_error(
                    f'Report is {report["status"]} — only a draft can be '
                    f'submitted for review',
                )
            if not (report.get('impression') or '').strip():
                return validation_error(
                    'Impression is required before submitting for review',
                )
            report = await Reports(conn).submit(report['id'])
            await AuditLog(conn).log_event(
                event_type='report.submitted',
                actor_id=request.user.id,
                resource_type='report',
                resource_id=report['id'],
                details={
                    'exam_id': exam_id,
                    'accession_number': exam.get('accession_number'),
                },
                tenant=effective_tenant(request),
                request_id=request_id_var.get(),
            )
            # Supervising attendings see the submission in their review queue
            # (reading worklist, Awaiting review filter).
            await notify_role(
                conn, 'radiologist', 'report.submitted',
                f'Report submitted for review: '
                f'{exam.get("accession_number") or exam_id}',
                f'{exam.get("patient_name") or exam.get("patient_id")} — a '
                f'resident submitted their draft for co-sign.',
                    f'/reading/{exam_id}',
                )
            report = await _with_person_names(conn, report)
        return ok({'data': report})


class ExamReportReturnHandler(HTTPEndpoint):
    """Attending returns a submitted resident draft for revision.

    The report re-opens as an editable draft for its author, carrying the
    attending's feedback so the resident's console can show what to fix.
    Scoped to REPORT_SIGN — the same signers who can co-sign may redirect
    a draft back instead.
    """

    @requires_permission(Permission.REPORT_SIGN)
    async def post(self, request):
        exam_id = request.path_params['exam_id']
        body = await parse_body(ReturnReportRequest, request)
        async with get_conn() as conn:
            exam = await Exams(conn).get(exam_id)
            if not exam:
                return not_found('Exam not found')
            report = await Reports(conn).get_by_exam(exam_id)
            if not report:
                return validation_error('No report exists yet for this exam')
            if report['status'] != 'submitted':
                return validation_error(
                    'Only a submitted report can be returned for revision',
                )
            if not body.feedback.strip():
                return validation_error(
                    'Return feedback is required so the resident knows '
                    'what to revise',
                )
            report = await Reports(conn).return_report(
                report['id'], str(request.user.id), body.feedback,
            )
            await AuditLog(conn).log_event(
                event_type='report.returned',
                actor_id=request.user.id,
                resource_type='report',
                resource_id=report['id'],
                details={
                    'exam_id': exam_id,
                    'accession_number': exam.get('accession_number'),
                },
                tenant=effective_tenant(request),
                request_id=request_id_var.get(),
            )
            if report.get('created_by'):
                await notify_user(
                    conn, report['created_by'], 'report.returned',
                    'Report returned for revision',
                    f'Your attending returned your draft: '
                    f'{body.feedback[:120]}',
                    f'/reading/{exam_id}',
                )
            report = await _with_person_names(conn, report)
        return ok({'data': report})


async def _exam_imaging(conn, exam, patient=None):
    """Build the patient studies tree for an exam's imaging (or None).

    Bridges the exam lifecycle (front-desk / technologist) to the DICOM
    store: studies were stored under the accession the technologist
    performed, so the match is studies.accession_number = exams.accession
    (with the patient MRN as a second key, since accessions can collide
    across patients). Returns None when the exam has no DICOM yet — front-
    desk exams legitimately reach the worklist before the modality stores
    anything — so the console renders the report full-width instead of an
    empty viewport.

    `patient` may carry the already-fetched get_extra tree (the exam detail
    endpoint shares one lookup with prior-studies); when given, the
    accession check happens against the tree instead of the JOIN query.
    """
    accession = (exam.get('accession_number') or '').strip()
    mrn = exam.get('patient_id')
    if not accession or not mrn:
        return None
    if patient is None:
        row = await conn.fetchrow(
            """SELECT p.id FROM patients p
               JOIN studies s ON s.patient_id = p.id
               WHERE s.accession_number = $1 AND p.patient_id = $2
               ORDER BY s.id LIMIT 1""",
            accession, mrn,
        )
        if not row:
            return None
        patient = await Patient(conn).get_extra(row['id'])
    if not patient:
        return None
    # A patient can carry several studies (priors, other accessions); the
    # console reads the study that belongs to this exam, not the whole file.
    # With a pre-fetched tree this filter doubles as the existence check the
    # JOIN query would have done.
    matched = [
        s for s in patient.get('studies', [])
        if (s.get('accession_number') or '') == accession
    ]
    if not matched:
        return None
    patient['studies'] = matched
    return patient


class ExamImagesHandler(HTTPEndpoint):
    """Resolve the DICOM study/series/file tree for a reading-list exam.

    The reading console renders viewer + report on one screen, so the
    frontend needs the same FileRecord.patient.studies[].series[].files[]
    tree that /files/{id} returns — selected by exam accession instead of a
    file id. `imaging: False` signals an exam with no DICOM yet.
    """

    @requires_permission(Permission.REPORT_READ)
    async def get(self, request):
        exam_id = request.path_params['exam_id']
        async with get_conn() as conn:
            exam = await Exams(conn).get(exam_id)
            if not exam:
                return not_found('Exam not found')
            patient = await _exam_imaging(conn, exam)
        if patient is None:
            return ok({'data': {'imaging': False}})
        return ok({'data': {'imaging': True, 'patient': patient}})


class ReportTemplatesHandler(HTTPEndpoint):
    """Report template library, filterable by modality."""

    @requires_permission(Permission.REPORT_READ)
    async def get(self, request):
        modality = request.query_params.get('modality')
        async with get_conn() as conn:
            await _seed_report_templates(conn)
            from db.ris_templates import RisReportTemplates
            # H9: list_templates reads ris_report_templates, which is never
            # seeded by migrations — seed it here (idempotent) or a fresh
            # database serves an empty template library while the legacy
            # report_templates table fills up unused.
            await RisReportTemplates(conn).seed_defaults()
            templates = await RisReportTemplates(conn).list_templates(modality)
        return ok({'data': templates})

    @requires_permission(Permission.REPORT_WRITE)
    async def post(self, request):
        data = await request.json()
        if not data.get('name') or not data.get('modality'):
            return validation_error('name and modality are required')
        async with get_conn() as conn:
            from db.ris_templates import RisReportTemplates
            tpl = await RisReportTemplates(conn).create_template(data)
        return created({'data': tpl})


class ReportVersionsHandler(HTTPEndpoint):
    """S8-08 Report version history & diffs."""

    @requires_permission(Permission.REPORT_READ)
    async def get(self, request):
        report_id = request.path_params['report_id']
        v1 = request.query_params.get('v1')
        v2 = request.query_params.get('v2')
        async with get_conn() as conn:
            from db.ris_report_versions import RisReportVersions
            rv = RisReportVersions(conn)
            if v1 and v2:
                # B-7: int() on garbage query params raised ValueError -> 500;
                # a bad version number is a client error, not a crash.
                try:
                    v1n, v2n = int(v1), int(v2)
                except ValueError:
                    return validation_error('v1 and v2 must be integers')
                diff = await rv.get_version_diff(report_id, v1n, v2n)
                return ok({'data': diff})
            versions = await rv.get_history(report_id)
        return ok({'data': versions})


class PeerReviewReviewersHandler(HTTPEndpoint):
    """Radiologist users eligible to receive a peer-review assignment."""

    @requires_permission(Permission.PEER_REVIEW_READ)
    async def get(self, request):
        async with get_conn() as conn:
            rows = await conn.fetch(
                """SELECT u.id, u.username FROM users u
                   JOIN roles r ON r.id = u.role_id
                   WHERE r.slug = 'radiologist' ORDER BY u.username""",
            )
        return ok({'data': [dict(r) for r in rows]})


class PeerReviewsHandler(HTTPEndpoint):
    """List my peer-review assignments, or request one for a signed report."""

    @requires_permission(Permission.PEER_REVIEW_READ)
    async def get(self, request):
        status = request.query_params.get('status')
        async with get_conn() as conn:
            reviews = await PeerReviews(conn).list_for_reviewer(
                str(request.user.id), status=status,
            )
            items = []
            for rev in reviews:
                report = await Reports(conn).get(rev['report_id'])
                exam = await Exams(conn).get(report['exam_id']) if report else None
                items.append({
                    **rev,
                    'report': report,
                    'exam': {
                        'id': exam['id'], 'patient_id': exam['patient_id'],
                        'patient_name': exam['patient_name'],
                        'accession_number': exam['accession_number'],
                        'modality': exam['modality'], 'priority': exam['priority'],
                    } if exam else None,
                })
        return ok({'data': items})

    @requires_permission(Permission.PEER_REVIEW_WRITE)
    async def post(self, request):
        body = await parse_body(CreatePeerReviewRequest, request)
        async with get_conn() as conn:
            report = await Reports(conn).get(body.report_id)
            if not report:
                return not_found('Report not found')
            if report['status'] != 'final':
                return validation_error(
                    'Only final signed reports can be peer-reviewed',
                )
            # users.id is a bigint; compare via text cast (string payload).
            reviewer = await conn.fetchrow(
                "SELECT id FROM users WHERE id::text = $1", body.reviewer_id,
            )
            if not reviewer:
                return not_found('Reviewer user not found')
            review = await PeerReviews(conn).create(
                body.report_id, body.reviewer_id,
            )
            await AuditLog(conn).log_event(
                event_type='peer_review.assigned',
                actor_id=request.user.id,
                resource_type='peer_review',
                resource_id=review['id'],
                details={'report_id': report['id']},
                tenant=effective_tenant(request),
                request_id=request_id_var.get(),
            )
            await notify_user(
                conn, body.reviewer_id, 'peer_review.assigned',
                'Peer review assigned',
                f'You have a peer review for report on '
                f'{report.get("exam_id")}.',
                f'/peer-review/{review["id"]}',
            )
        return created({'data': review})


class PeerReviewHandler(HTTPEndpoint):
    """Open a peer review with full report + exam context."""

    @requires_permission(Permission.PEER_REVIEW_READ)
    async def get(self, request):
        review_id = request.path_params['id']
        async with get_conn() as conn:
            review = await PeerReviews(conn).get(review_id)
            if not review:
                return not_found('Peer review not found')
            # PHI guard: only the assigned reviewer (or the report author) may
            # open a review and its full report content.
            report = await Reports(conn).get(review['report_id'])
            is_reviewer = review['reviewer_id'] == str(request.user.id)
            is_author = bool(report) and report.get('created_by') == str(request.user.id)
            if not (is_reviewer or is_author or request.user.admin):
                return forbidden('Only the assigned reviewer can open this review')
            exam = await Exams(conn).get(report['exam_id']) if report else None
        return ok({
            'data': {
                **review,
                'report': report,
                'exam': exam,
            },
        })


class PeerReviewSubmitHandler(HTTPEndpoint):
    """Submit a peer-review outcome (discrepancy level + comment)."""

    @requires_permission(Permission.PEER_REVIEW_WRITE)
    async def post(self, request):
        review_id = request.path_params['id']
        body = await parse_body(SubmitPeerReviewRequest, request)
        async with get_conn() as conn:
            review = await PeerReviews(conn).get(review_id)
            if not review:
                return not_found('Peer review not found')
            if review['reviewer_id'] and review['reviewer_id'] != str(request.user.id):
                return forbidden('Only the assigned reviewer can submit this review')
            if review['status'] == 'assigned':
                await PeerReviews(conn).start(review_id)
            review = await PeerReviews(conn).submit(
                review_id, body.discrepancy_level, body.comment,
            )
            report = await Reports(conn).get(review['report_id'])
            exam = await Exams(conn).get(report['exam_id']) if report else None
            await AuditLog(conn).log_event(
                event_type='peer_review.submitted',
                actor_id=request.user.id,
                resource_type='peer_review',
                resource_id=review_id,
                details={
                    'discrepancy_level': body.discrepancy_level,
                    'report_id': review['report_id'],
                },
                tenant=effective_tenant(request),
                request_id=request_id_var.get(),
            )
            # Notify the original report author that their review is complete.
            if report and report.get('created_by'):
                await notify_user(
                    conn, report['created_by'], 'peer_review.completed',
                    'Peer review completed',
                    f'Discrepancy: {body.discrepancy_level}. '
                    f'{body.comment[:120]}',
                    f'/reading/{exam["id"] if exam else ""}',
                )
        return ok({'data': review})


class TemplateVersionsHandler(HTTPEndpoint):
    """R2-02-07: GET /ris/report-templates/{id}/versions — history."""

    @requires_permission(Permission.REPORT_READ)
    async def get(self, request):
        from db.conn import get_tenant_slug
        template_id = request.path_params['id']
        tenant = get_tenant_slug() or 'default'
        async with get_conn() as conn:
            from db.ris_templates import RisReportTemplates
            rows = await RisReportTemplates(conn).list_versions(
                template_id, tenant)
        return ok({'data': [dict(r) for r in rows]})


class TemplatePublishHandler(HTTPEndpoint):
    """R2-02-09: POST .../publish — snapshot + activate a new version."""

    @requires_permission(Permission.REPORT_WRITE)
    async def post(self, request):
        from api.validate import parse_body
        from api.schemas.reports import PublishTemplateRequest
        from db.conn import get_tenant_slug
        template_id = request.path_params['id']
        body = await parse_body(PublishTemplateRequest, request)
        tenant = get_tenant_slug() or 'default'
        async with get_conn() as conn:
            from db.ris_templates import RisReportTemplates
            row = await RisReportTemplates(conn).publish_version(
                template_id,
                findings=body.findings,
                impression=body.impression,
                published_by=str(getattr(request.user, 'id', '')),
                tenant_id=tenant,
            )
        return ok({'data': dict(row)})


class TemplateRollbackHandler(HTTPEndpoint):
    """R2-02-09: POST .../rollback — one-click re-activation."""

    @requires_permission(Permission.REPORT_WRITE)
    async def post(self, request):
        from api.validate import parse_body
        from api.schemas.reports import RollbackTemplateRequest
        from db.conn import get_tenant_slug
        template_id = request.path_params['id']
        body = await parse_body(RollbackTemplateRequest, request)
        tenant = get_tenant_slug() or 'default'
        async with get_conn() as conn:
            from db.ris_templates import RisReportTemplates
            row = await RisReportTemplates(conn).rollback_to_version(
                template_id, body.version, tenant_id=tenant)
        if not row:
            return not_found('Version not found')
        return ok({'data': dict(row)})


class ReportReleaseHandler(HTTPEndpoint):
    """R2-05-05: PATCH /reports/{id}/release — HIM hold/release gate.

    held reports are excluded from patient-bound FHIR bundles; releasing
    clears the hold. Every transition is audited.
    """

    @requires_permission(Permission.REPORT_WRITE)
    async def patch(self, request):
        from api.validate import parse_body
        from api.schemas.reports import ReleaseActionRequest
        body = await parse_body(ReleaseActionRequest, request)
        new_status = {'hold': 'held', 'release': 'released',
                      'auto': 'auto'}[body.action]
        async with get_conn() as conn:
            row = await Reports(conn).set_release_status(
                request.path_params['id'], new_status)
            if not row:
                return not_found('Report not found')
            await AuditLog(conn).log_event(
                event_type=f'report.{"held" if new_status == "held" else "released"}',
                actor_id=str(getattr(request.user, 'id', '')),
                resource_type='reports',
                resource_id=request.path_params['id'],
            )
        return ok({'data': dict(row)})
