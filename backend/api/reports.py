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
from log import request_id_var
from api.tenant_middleware import effective_tenant

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
        if radiologist == 'me':
            radiologist = str(request.user.id)
        physician = request.query_params.get('physician')
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        review = request.query_params.get('review')
        if review in ('0', 'false', ''):
            review = None
        async with get_conn() as conn:
            items = await Reports(conn).reading_list(
                status=status, modality=modality, search=search,
                radiologist=radiologist, physician=physician,
                date_from=date_from, date_to=date_to, review=review,
            )
        return ok({'data': items})


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
            report = dict(report) if report else None
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
            if existing and existing.get('status') == 'submitted':
                # R13 supervision lock: a submitted report is in the
                # attending's hands — the resident must get it returned
                # (POST /reports/{id}/return) before editing again.
                return validation_error(
                    'Report is submitted for attending review — it must be '
                    'returned before it can be edited',
                )
            if existing:
                report = await Reports(conn).update(
                    existing['id'], body.model_dump(),
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
            # Notify QA that a report is final and ready for any scheduled
            # peer review (R05 consumes signed reports for quality sampling).
            await notify_role(
                conn, 'qa', 'report.signed',
                f'Report signed: {exam.get("accession_number") or exam_id}',
                f'{exam.get("patient_name") or exam.get("patient_id")} — final '
                f'report signed by radiologist.',
                f'/reading/{exam_id}',
            )
            # R13 co-sign: when an attending signs a resident's submitted
            # draft, tell the resident author their report was co-signed.
            if report.get('created_by') and \
                    report['created_by'] != str(request.user.id):
                await notify_user(
                    conn, report['created_by'], 'report.co-signed',
                    'Report co-signed',
                    f'Your draft was co-signed as FINAL by the attending.',
                    f'/reading/{exam_id}',
                )
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
            templates = await ReportTemplates(conn).list_by_modality(modality)
        return ok({'data': templates})


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
