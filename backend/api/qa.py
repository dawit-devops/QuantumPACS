"""QA endpoints for the R05 QI/QA Team workflow.

Covers the QA review queue (FR-R05-01), QA scoring (FR-R05-02/04), protocol
registry CRUD (FR-R05-03), corrective-action inbox (FR-R05-05), incident
logging + resolution (FR-R05-06), and a personal compliance dashboard feed.
Reads are gated on QA_READ; mutations on QA_WRITE / PROTOCOL_MANAGE.
"""
from starlette.endpoints import HTTPEndpoint

from api.rbac import requires_permission
from api.permissions import Permission
from api.response import ok, created, not_found, validation_error
from api.validate import parse_body
from api.schemas.qa import (
    SubmitQAScoreRequest, SaveProtocolRequest, UpdateProtocolRequest,
    LogQAIncidentRequest, CreateCorrectiveActionRequest,
    ResolveCorrectiveActionRequest, ResolveIncidentRequest,
)
from db.audit_log import AuditLog
from db.conn import get_conn
from db.exams import Exams
from db.qa import QaScores, CorrectiveActions, IncidentsQA, ProtocolsQA
from log import request_id_var
from api.tenant_middleware import effective_tenant

# R05-06 incident types (matches the schema whitelist for the UI dropdown).
INCIDENT_TYPES = [
    'positioning', 'artifact', 'protocol_deviation', 'patient_motion',
    'equipment_malfunction', 'contrast_extravasation',
]


class QAQueueHandler(HTTPEndpoint):
    """Filterable queue of completed exams awaiting QA review (FR-R05-01)."""

    @requires_permission(Permission.QA_READ)
    async def get(self, request):
        modality = request.query_params.get('modality')
        status = request.query_params.get('status')
        priority = request.query_params.get('priority')
        search = request.query_params.get('search')
        page = max(1, int(request.query_params.get('page', 1)))
        page_size = min(100, max(1, int(request.query_params.get('page_size', 50))))
        async with get_conn() as conn:
            rows = await conn.fetch(
                """SELECT e.id AS exam_id, e.patient_id, e.patient_name,
                          e.patient_birth_date, e.accession_number,
                          e.requested_procedure_desc, e.modality, e.priority,
                          e.protocol_name, e.completed_at, e.assigned_technologist,
                          q.pass_fail AS qa_status
                   FROM exams e
                   LEFT JOIN qa_scores q ON q.exam_id = e.id
                   WHERE e.status = 'completed'""",
            )
            exams = [dict(r) for r in rows]
            # Client-side filter + sort keeps the handler simple for the
            # moderate volumes the QA queue handles.
            if modality:
                exams = [e for e in exams if e.get('modality') == modality]
            if status:
                exams = [e for e in exams if (e.get('qa_status') or 'pending') == status]
            if priority:
                exams = [e for e in exams if e.get('priority') == priority]
            if search:
                s = search.lower()
                exams = [
                    e for e in exams
                    if s in (e.get('patient_name') or '').lower()
                    or s in (e.get('patient_id') or '').lower()
                    or s in (e.get('accession_number') or '').lower()
                ]
            priority_order = {'stat': 0, 'urgent': 1, 'routine': 2}
            exams.sort(key=lambda r: (
                priority_order.get(r.get('priority') or 'routine', 9),
                r.get('qa_status') is not None,
                str(r.get('completed_at') or ''),
            ))
            total = len(exams)
            start = (page - 1) * page_size
            page_items = exams[start:start + page_size]
        return ok({
            'data': page_items,
            'meta': {
                'total': total, 'page': page, 'page_size': page_size,
                'total_pages': (total + page_size - 1) // page_size,
            },
        })


class QAReviewHandler(HTTPEndpoint):
    """Submit or fetch a QA score for an exam (FR-R05-02/04)."""

    @requires_permission(Permission.QA_READ)
    async def get(self, request):
        exam_id = request.path_params['exam_id']
        async with get_conn() as conn:
            exam = await Exams(conn).get(exam_id)
            if not exam:
                return not_found('Exam not found')
            score = await QaScores(conn).get_by_exam(exam_id)
            protocol = None
            if exam.get('protocol_name'):
                row = await conn.fetchrow(
                    "SELECT * FROM protocols WHERE name = $1", exam['protocol_name'],
                )
                if row:
                    protocol = dict(row)
        return ok({'data': {'exam': exam, 'score': score, 'protocol': protocol}})

    @requires_permission(Permission.QA_WRITE)
    async def post(self, request):
        body = await parse_body(SubmitQAScoreRequest, request)
        exam_id = body.exam_id
        async with get_conn() as conn:
            exam = await Exams(conn).get(exam_id)
            if not exam:
                return not_found('Exam not found')
            existing = await QaScores(conn).get_by_exam(exam_id)
            if existing:
                return validation_error('This exam has already been QA-reviewed')
            protocol_id = None
            if body.protocol_id:
                protocol_id = body.protocol_id
            elif exam.get('protocol_name'):
                row = await conn.fetchrow(
                    "SELECT id FROM protocols WHERE name = $1", exam['protocol_name'],
                )
                if row:
                    protocol_id = row['id']
            score = await QaScores(conn).create({
                'exam_id': exam_id,
                'protocol_id': protocol_id,
                'pass_fail': body.pass_fail,
                'discrepancy_level': body.discrepancy_level,
                'dose_dlp': body.dose_dlp,
                'dose_ctdivol': body.dose_ctdivol,
                'dose_kvp': body.dose_kvp,
                'dose_mas': body.dose_mas,
                'sequence_compliance': body.sequence_compliance,
                'comments': body.comments,
                'reviewed_by': str(request.user.id),
            })
            await AuditLog(conn).log_event(
                event_type='qa.score_submitted',
                actor_id=request.user.id,
                resource_type='qa_score',
                resource_id=score['id'],
                details={
                    'exam_id': exam_id,
                    'pass_fail': body.pass_fail,
                    'discrepancy_level': body.discrepancy_level,
                },
                tenant=effective_tenant(request),
                request_id=request_id_var.get(),
            )
            if body.pass_fail == 'fail':
                await self._open_corrective_action(conn, exam, body, request)
        return created({'data': score})

    @staticmethod
    async def _open_corrective_action(conn, exam, body, request):
        """A failed review opens a corrective action for the QA team (FR-R05-05)."""
        await CorrectiveActions(conn).create({
            'source': 'R05_self',
            'issue': (f'Failed QA review: {exam.get("accession_number") or exam.get("patient_id")} '
                      f'— {body.comments[:200]}'),
            'study_uids': [],
            'assigned_to': '',
            'created_by': str(request.user.id),
        })


class QAProtocolsHandler(HTTPEndpoint):
    """Protocol registry list/create (FR-R05-03)."""

    @requires_permission(Permission.QA_READ)
    async def get(self, request):
        modality = request.query_params.get('modality')
        search = request.query_params.get('search')
        async with get_conn() as conn:
            protocols = await ProtocolsQA(conn).list_all(modality, search)
        return ok({'data': protocols})

    @requires_permission(Permission.PROTOCOL_MANAGE)
    async def post(self, request):
        body = await parse_body(SaveProtocolRequest, request)
        async with get_conn() as conn:
            if body.protocol_code:
                existing = await ProtocolsQA(conn).get_by_code(body.protocol_code)
                if existing:
                    return validation_error(f'Protocol code {body.protocol_code} already exists')
            protocol = await ProtocolsQA(conn).create({
                'name': body.name,
                'protocol_code': body.protocol_code,
                'modality': body.modality,
                'body_part': body.body_part,
                'sequences': body.sequences,
                'parameters': body.parameters,
                'acr_benchmark_dlp': body.acr_benchmark_dlp,
                'acr_benchmark_ctdivol': body.acr_benchmark_ctdivol,
                'acr_benchmark_min_snr': body.acr_benchmark_min_snr,
                'is_default': body.is_default,
            })
            await AuditLog(conn).log_event(
                event_type='qa.protocol_created',
                actor_id=request.user.id,
                resource_type='protocol',
                resource_id=protocol['id'],
                details={'code': body.protocol_code, 'modality': body.modality},
                tenant=effective_tenant(request),
                request_id=request_id_var.get(),
            )
        return created({'data': protocol})


class QAProtocolHandler(HTTPEndpoint):
    """Update/delete one protocol (FR-R05-03)."""

    @requires_permission(Permission.PROTOCOL_MANAGE)
    async def put(self, request):
        protocol_id = request.path_params['id']
        body = await parse_body(UpdateProtocolRequest, request)
        async with get_conn() as conn:
            protocol = await ProtocolsQA(conn).get(protocol_id)
            if not protocol:
                return not_found('Protocol not found')
            if body.protocol_code:
                dup = await ProtocolsQA(conn).get_by_code(body.protocol_code)
                if dup and str(dup['id']) != protocol_id:
                    return validation_error(f'Protocol code {body.protocol_code} already exists')
            updated = await ProtocolsQA(conn).update(
                protocol_id, body.model_dump(exclude_none=True),
            )
            await AuditLog(conn).log_event(
                event_type='qa.protocol_updated',
                actor_id=request.user.id,
                resource_type='protocol',
                resource_id=protocol_id,
                details={'name': updated.get('name')},
                tenant=effective_tenant(request),
                request_id=request_id_var.get(),
            )
        return ok({'data': updated})

    @requires_permission(Permission.PROTOCOL_MANAGE)
    async def delete(self, request):
        protocol_id = request.path_params['id']
        async with get_conn() as conn:
            protocol = await ProtocolsQA(conn).get(protocol_id)
            if not protocol:
                return not_found('Protocol not found')
            await ProtocolsQA(conn).delete(protocol_id)
            await AuditLog(conn).log_event(
                event_type='qa.protocol_deleted',
                actor_id=request.user.id,
                resource_type='protocol',
                resource_id=protocol_id,
                details={'name': protocol.get('name')},
                tenant=effective_tenant(request),
                request_id=request_id_var.get(),
            )
        return ok({'data': {'deleted': True}})


class QAIncidentsHandler(HTTPEndpoint):
    """List/log QA incidents (FR-R05-06)."""

    @requires_permission(Permission.QA_READ)
    async def get(self, request):
        incident_type = request.query_params.get('incident_type')
        status = request.query_params.get('status')
        search = request.query_params.get('search')
        async with get_conn() as conn:
            incidents = await IncidentsQA(conn).list(incident_type, status, search)
        return ok({'data': incidents})

    @requires_permission(Permission.QA_WRITE)
    async def post(self, request):
        body = await parse_body(LogQAIncidentRequest, request)
        # incidents.exam_id is NOT NULL; require an exam link for QA logging.
        # The UI always passes one from the queue/review flow.
        if not body.exam_id:
            return validation_error('exam_id is required to log an incident')
        async with get_conn() as conn:
            exam_id = body.exam_id
            exam = await Exams(conn).get(exam_id)
            if not exam:
                return not_found('Exam not found')
            incident = await IncidentsQA(conn).create({
                'exam_id': exam_id,
                'incident_type': body.incident_type,
                'severity': body.severity,
                'description': body.description,
                'reported_by': str(request.user.id),
            })
            if body.study_uid or body.repeat_study_uid:
                await conn.execute(
                    "UPDATE incidents SET study_uid = $2, repeat_study_uid = $3 "
                    "WHERE id = $1",
                    incident['id'], body.study_uid, body.repeat_study_uid,
                )
            await AuditLog(conn).log_event(
                event_type='qa.incident_logged',
                actor_id=request.user.id,
                resource_type='incident',
                resource_id=incident['id'],
                details={'type': body.incident_type, 'severity': body.severity},
                tenant=effective_tenant(request),
                request_id=request_id_var.get(),
            )
        return created({'data': incident})


class QAIncidentHandler(HTTPEndpoint):
    """Resolve a QA incident (FR-R05-06)."""

    @requires_permission(Permission.QA_WRITE)
    async def post(self, request):
        incident_id = request.path_params['id']
        body = await parse_body(ResolveIncidentRequest, request)
        async with get_conn() as conn:
            row = await conn.fetchrow(
                "SELECT id, reported_by, incident_type, exam_id FROM incidents "
                "WHERE id = $1",
                incident_id,
            )
            if not row:
                return not_found('Incident not found')
            await IncidentsQA(conn).mark_resolved(incident_id, body.notes)
            # technologist review P2-2: tell the incident author (usually the
            # technologist who logged it) that QA closed their report — the
            # author has no QA_READ, so the event is the only feedback loop.
            reported_by = row.get('reported_by') or ''
            if reported_by and reported_by != str(request.user.id):
                from api.exams import _notify_user
                await _notify_user(
                    conn, reported_by, 'incident.resolved',
                    'Incident resolved',
                    f'Your {row.get("incident_type") or ""} report was resolved: '
                    f'{body.notes[:120]}',
                    f'/exams/{row.get("exam_id") or incident_id}',
                )
            await AuditLog(conn).log_event(
                event_type='qa.incident_resolved',
                actor_id=request.user.id,
                resource_type='incident',
                resource_id=incident_id,
                details={'notes': body.notes[:120]},
                tenant=effective_tenant(request),
                request_id=request_id_var.get(),
            )
        return ok({'data': {'resolved': True}})


class QACorrectiveActionsHandler(HTTPEndpoint):
    """List/create corrective actions (FR-R05-05)."""

    @requires_permission(Permission.QA_READ)
    async def get(self, request):
        status = request.query_params.get('status')
        async with get_conn() as conn:
            actions = await CorrectiveActions(conn).list(status)
        return ok({'data': actions})

    @requires_permission(Permission.QA_WRITE)
    async def post(self, request):
        body = await parse_body(CreateCorrectiveActionRequest, request)
        async with get_conn() as conn:
            action = await CorrectiveActions(conn).create({
                'source': body.source,
                'issue': body.issue,
                'study_uids': body.study_uids,
                'assigned_to': body.assigned_to,
                'created_by': str(request.user.id),
            })
            await AuditLog(conn).log_event(
                event_type='qa.corrective_action_created',
                actor_id=request.user.id,
                resource_type='corrective_action',
                resource_id=action['id'],
                details={'source': body.source},
                tenant=effective_tenant(request),
                request_id=request_id_var.get(),
            )
        return created({'data': action})


class QACorrectiveActionHandler(HTTPEndpoint):
    """Resolve a corrective action (FR-R05-05)."""

    @requires_permission(Permission.QA_WRITE)
    async def post(self, request):
        action_id = request.path_params['id']
        body = await parse_body(ResolveCorrectiveActionRequest, request)
        async with get_conn() as conn:
            action = await CorrectiveActions(conn).get(action_id)
            if not action:
                return not_found('Corrective action not found')
            resolved = await CorrectiveActions(conn).resolve(
                action_id, body.findings, body.actions_taken,
            )
            await AuditLog(conn).log_event(
                event_type='qa.corrective_action_resolved',
                actor_id=request.user.id,
                resource_type='corrective_action',
                resource_id=action_id,
                details={'findings': body.findings[:120]},
                tenant=effective_tenant(request),
                request_id=request_id_var.get(),
            )
        return ok({'data': resolved})


class QADashboardHandler(HTTPEndpoint):
    """Personal compliance dashboard (FR-R05-07 / US-R05-07)."""

    @requires_permission(Permission.QA_READ)
    async def get(self, request):
        async with get_conn() as conn:
            reviewed = await QaScores(conn).count()
            open_actions = await CorrectiveActions(conn).count_open()
            open_incidents = await conn.fetchval(
                "SELECT count(*) FROM incidents WHERE status != 'resolved'",
            ) or 0
            compliance = await conn.fetchval(
                """SELECT CASE WHEN count(*) = 0 THEN 0
                       ELSE 100.0 * count(*) FILTER (WHERE pass_fail = 'pass') / count(*)
                     END FROM qa_scores""",
            ) or 0
            recent = await conn.fetch(
                """SELECT q.reviewed_at, q.pass_fail, e.modality
                   FROM qa_scores q JOIN exams e ON e.id = q.exam_id
                   ORDER BY q.reviewed_at DESC LIMIT 10""",
            )
        return ok({
            'data': {
                'exams_reviewed': reviewed,
                'compliance_pct': round(float(compliance), 1),
                'open_incidents': open_incidents,
                'open_actions': open_actions,
                'recent_reviews': [
                    {
                        'reviewed_at': str(r['reviewed_at']),
                        'pass_fail': r['pass_fail'],
                        'modality': r['modality'],
                    } for r in recent
                ],
            },
        })


class QAReviewersHandler(HTTPEndpoint):
    """Radiologists available for QA peer-review assignment (FR-R05-10)."""

    @requires_permission(Permission.QA_READ)
    async def get(self, request):
        async with get_conn() as conn:
            rows = await conn.fetch(
                """SELECT u.id, u.username, r.slug AS role
                   FROM users u JOIN roles r ON r.id = u.role_id
                   WHERE r.slug = 'radiologist'
                   ORDER BY u.username""",
            )
        return ok({'data': [
            {'id': str(r['id']), 'username': r['username']} for r in rows
        ]})


# ---------------------------------------------------------------------------
# QA Analytics endpoints (QA-02 through QA-07)
# Gated on QA_ANALYTICS_READ — read-only aggregations of existing QA data.
# ---------------------------------------------------------------------------


class QARejectAnalysisHandler(HTTPEndpoint):
    """QA-02: Reject analysis — fail rate by modality, tech, protocol, reason."""

    @requires_permission(Permission.QA_ANALYTICS_READ)
    async def get(self, request):
        modality = request.query_params.get('modality')
        async with get_conn() as conn:
            # Reject rate by modality
            by_modality = await conn.fetch(
                """SELECT e.modality,
                          COUNT(*) AS total,
                          COUNT(*) FILTER (WHERE q.pass_fail = 'fail') AS fails,
                          ROUND(100.0 * COUNT(*) FILTER (WHERE q.pass_fail = 'fail')
                                / NULLIF(COUNT(*), 0), 1) AS reject_rate
                   FROM qa_scores q
                   JOIN exams e ON e.id = q.exam_id
                   GROUP BY e.modality
                   ORDER BY reject_rate DESC""",
            )
            # Reject rate by technologist
            by_tech = await conn.fetch(
                """SELECT e.assigned_technologist AS tech,
                          COUNT(*) AS total,
                          COUNT(*) FILTER (WHERE q.pass_fail = 'fail') AS fails,
                          ROUND(100.0 * COUNT(*) FILTER (WHERE q.pass_fail = 'fail')
                                / NULLIF(COUNT(*), 0), 1) AS reject_rate
                   FROM qa_scores q
                   JOIN exams e ON e.id = q.exam_id
                   WHERE e.assigned_technologist != ''
                   GROUP BY e.assigned_technologist
                   ORDER BY reject_rate DESC""",
            )
            # Reject rate by protocol
            by_protocol = await conn.fetch(
                """SELECT p.name AS protocol_name, p.modality,
                          COUNT(*) AS total,
                          COUNT(*) FILTER (WHERE q.pass_fail = 'fail') AS fails,
                          ROUND(100.0 * COUNT(*) FILTER (WHERE q.pass_fail = 'fail')
                                / NULLIF(COUNT(*), 0), 1) AS reject_rate
                   FROM qa_scores q
                   JOIN protocols p ON p.id = q.protocol_id
                   GROUP BY p.name, p.modality
                   ORDER BY reject_rate DESC""",
            )
            # Reject rate by discrepancy level
            by_discrepancy = await conn.fetch(
                """SELECT discrepancy_level, COUNT(*) AS n
                   FROM qa_scores
                   WHERE pass_fail = 'fail'
                   GROUP BY discrepancy_level
                   ORDER BY n DESC""",
            )
        return ok({
            'data': {
                'by_modality': [dict(r) for r in by_modality],
                'by_technologist': [dict(r) for r in by_tech],
                'by_protocol': [dict(r) for r in by_protocol],
                'by_discrepancy': [dict(r) for r in by_discrepancy],
            },
        })


class QADoseTrackingHandler(HTTPEndpoint):
    """QA-03: Dose tracking — metrics by modality/protocol vs ACR benchmarks."""

    @requires_permission(Permission.QA_ANALYTICS_READ)
    async def get(self, request):
        async with get_conn() as conn:
            # Dose metrics by modality with ACR benchmarks
            by_modality = await conn.fetch(
                """SELECT e.modality,
                          COUNT(*) AS n,
                          ROUND(AVG(q.dose_dlp), 1) AS avg_dlp,
                          ROUND(MAX(q.dose_dlp), 1) AS max_dlp,
                          ROUND(AVG(q.dose_ctdivol), 1) AS avg_ctdivol,
                          ROUND(MAX(q.dose_ctdivol), 1) AS max_ctdivol,
                          p.acr_benchmark_dlp,
                          p.acr_benchmark_ctdivol,
                          COUNT(*) FILTER (
                            WHERE q.dose_dlp > 0 AND p.acr_benchmark_dlp IS NOT NULL
                            AND q.dose_dlp > p.acr_benchmark_dlp
                          ) AS dlp_exceedances
                   FROM qa_scores q
                   JOIN exams e ON e.id = q.exam_id
                   LEFT JOIN protocols p ON p.id = q.protocol_id
                   WHERE q.dose_dlp > 0 OR q.dose_ctdivol > 0
                   GROUP BY e.modality, p.acr_benchmark_dlp, p.acr_benchmark_ctdivol
                   ORDER BY e.modality""",
            )
            # Dose exceedances by protocol
            exceedances = await conn.fetch(
                """SELECT p.name AS protocol_name, p.modality,
                          p.acr_benchmark_dlp,
                          q.dose_dlp,
                          q.dose_ctdivol,
                          e.accession_number,
                          q.reviewed_at
                   FROM qa_scores q
                   JOIN exams e ON e.id = q.exam_id
                   JOIN protocols p ON p.id = q.protocol_id
                   WHERE q.dose_dlp > 0
                     AND p.acr_benchmark_dlp IS NOT NULL
                     AND q.dose_dlp > p.acr_benchmark_dlp
                   ORDER BY q.dose_dlp DESC
                   LIMIT 50""",
            )
        return ok({
            'data': {
                'by_modality': [dict(r) for r in by_modality],
                'exceedances': [dict(r) for r in exceedances],
            },
        })


class QATechMetricsHandler(HTTPEndpoint):
    """QA-05: Technologist performance metrics -- reject rate, dose, protocol adherence."""

    @requires_permission(Permission.QA_ANALYTICS_READ)
    async def get(self, request):
        async with get_conn() as conn:
            # protocol_adherence_pct: share of reviews where sequence_compliance
            # has at least one entry (non-empty JSONB = protocol was evaluated).
            # We avoid the literal '{}' pattern in triple-quoted strings due to
            # Python 3.14 parsing strictness; use jsonb_typeof instead.
            sql = (
                'SELECT e.assigned_technologist AS tech, '
                'COUNT(*) AS total_reviewed, '
                'COUNT(*) FILTER (WHERE q.pass_fail = $1) AS passed, '
                'COUNT(*) FILTER (WHERE q.pass_fail = $2) AS failed, '
                'ROUND(100.0 * COUNT(*) FILTER (WHERE q.pass_fail = $2) '
                '/ NULLIF(COUNT(*), 0), 1) AS reject_rate, '
                'ROUND(AVG(q.dose_dlp), 1) AS avg_dlp, '
                'ROUND(100.0 * COUNT(*) FILTER (WHERE jsonb_array_length(q.sequence_compliance) > 0) '
                '/ NULLIF(COUNT(*), 0), 1) AS protocol_adherence_pct '
                'FROM qa_scores q '
                'JOIN exams e ON e.id = q.exam_id '
                'WHERE e.assigned_technologist != $3 '
                'GROUP BY e.assigned_technologist '
                'ORDER BY reject_rate DESC'
            )
            metrics = await conn.fetch(sql, 'pass', 'fail', '')
        return ok({'data': [dict(r) for r in metrics]})


class QAProtocolComplianceHandler(HTTPEndpoint):
    """QA-06: Protocol compliance rate — adherence % by protocol."""

    @requires_permission(Permission.QA_ANALYTICS_READ)
    async def get(self, request):
        async with get_conn() as conn:
            compliance = await conn.fetch(
                """SELECT p.id AS protocol_id, p.name AS protocol_name,
                          p.modality, p.body_part,
                          p.acr_benchmark_dlp, p.acr_benchmark_ctdivol,
                          COUNT(q.id) AS total_reviews,
                          COUNT(*) FILTER (WHERE q.pass_fail = 'pass') AS passed,
                          COUNT(*) FILTER (WHERE q.pass_fail = 'fail') AS failed,
                          ROUND(100.0 * COUNT(*) FILTER (WHERE q.pass_fail = 'pass')
                                / NULLIF(COUNT(q.id), 0), 1) AS compliance_pct,
                          ROUND(AVG(q.dose_dlp), 1) AS avg_dlp,
                          ROUND(AVG(q.dose_ctdivol), 1) AS avg_ctdivol
                   FROM protocols p
                   LEFT JOIN qa_scores q ON q.protocol_id = p.id
                   GROUP BY p.id, p.name, p.modality, p.body_part,
                            p.acr_benchmark_dlp, p.acr_benchmark_ctdivol
                   HAVING COUNT(q.id) > 0
                   ORDER BY compliance_pct ASC""",
            )
        return ok({'data': [dict(r) for r in compliance]})


class QATrendsHandler(HTTPEndpoint):
    """QA-07: Trending — daily reject rate and dose trends."""

    @requires_permission(Permission.QA_ANALYTICS_READ)
    async def get(self, request):
        granularity = request.query_params.get('granularity', 'daily')
        if granularity not in ('daily', 'weekly', 'monthly'):
            granularity = 'daily'
        date_trunc = {'daily': 'day', 'weekly': 'week', 'monthly': 'month'}[granularity]
        async with get_conn() as conn:
            trends = await conn.fetch(
                f"""SELECT date_trunc('{date_trunc}', q.reviewed_at) AS period,
                          COUNT(*) AS total,
                          COUNT(*) FILTER (WHERE q.pass_fail = 'pass') AS passed,
                          COUNT(*) FILTER (WHERE q.pass_fail = 'fail') AS failed,
                          ROUND(100.0 * COUNT(*) FILTER (WHERE q.pass_fail = 'fail')
                                / NULLIF(COUNT(*), 0), 1) AS reject_rate,
                          ROUND(AVG(q.dose_dlp), 1) AS avg_dlp,
                          ROUND(AVG(q.dose_ctdivol), 1) AS avg_ctdivol
                   FROM qa_scores q
                   WHERE q.reviewed_at IS NOT NULL
                   GROUP BY period
                   ORDER BY period DESC
                   LIMIT 90""",
            )
        return ok({'data': [dict(r) for r in trends], 'granularity': granularity})
