from contextlib import contextmanager
from unittest.mock import AsyncMock, patch

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.routing import Route
from starlette.testclient import TestClient
from starlette.exceptions import HTTPException

from api.auth import User
from api.validate import validation_exception_handler, _ValidationException


def _http_exception(request, exc):
    from starlette.responses import JSONResponse
    return JSONResponse(
        {'error': exc.detail if hasattr(exc, 'detail') else ''},
        status_code=exc.status_code,
    )


class _FakeAuth(BaseHTTPMiddleware):
    def __init__(self, app, user=None):
        super().__init__(app)
        self._user = user or User({'id': 1, 'permissions': []})

    async def dispatch(self, request, call_next):
        request.scope['user'] = self._user
        request.scope['auth'] = None
        return await call_next(request)


def _make_app(user=None):
    from api.reports import (
        ReadingListHandler, ExamReportHandler, ExamReportSignHandler,
        ExamReportSubmitHandler, ExamReportReturnHandler,
        ExamAssignHandler, ExamImagesHandler,
        ReportTemplatesHandler, PeerReviewReviewersHandler, PeerReviewsHandler,
        PeerReviewHandler, PeerReviewSubmitHandler,
        ReportVersionRestoreHandler,
    )
    return Starlette(
        routes=[
            Route('/reports/reading-list', endpoint=ReadingListHandler),
            Route('/reports/reading-list/{exam_id}/assign', endpoint=ExamAssignHandler),
            Route('/reports/templates', endpoint=ReportTemplatesHandler),
            Route('/reports/{exam_id}', endpoint=ExamReportHandler),
            Route('/reports/{exam_id}/sign', endpoint=ExamReportSignHandler),
            Route('/reports/{exam_id}/submit', endpoint=ExamReportSubmitHandler),
            Route('/reports/{exam_id}/return', endpoint=ExamReportReturnHandler),
            Route('/reports/{exam_id}/images', endpoint=ExamImagesHandler),
            Route('/peer-reviews/reviewers', endpoint=PeerReviewReviewersHandler),
            Route('/peer-reviews', endpoint=PeerReviewsHandler),
            Route('/peer-reviews/{id}', endpoint=PeerReviewHandler),
            Route('/peer-reviews/{id}/submit', endpoint=PeerReviewSubmitHandler),
            Route('/reports/{report_id}/versions/{version}/restore',
                  endpoint=ReportVersionRestoreHandler, methods=['POST']),
        ],
        middleware=[Middleware(_FakeAuth, user=user)],
        exception_handlers={
            HTTPException: _http_exception,
            _ValidationException: validation_exception_handler,
        },
    )


RAD = User({'id': 50, 'permissions': [
    'REPORT_READ', 'REPORT_WRITE', 'REPORT_SIGN',
    'PEER_REVIEW_READ', 'PEER_REVIEW_WRITE', 'EXAM_READ',
]})
READ_ONLY = User({'id': 51, 'permissions': ['REPORT_READ']})
NO_PERMS = User({'id': 52, 'permissions': []})


@contextmanager
def _audit_ok():
    with patch('api.reports.AuditLog') as audit_cls:
        audit_cls.return_value.log_event = AsyncMock()
        yield


@contextmanager
def _conn(fetchrow=None, fetch=None, fetchval=None, execute=None):
    conn = AsyncMock()
    # Sync callables (e.g. plain lambdas) must be awaited by the handler —
    # wrap them so `await conn.fetchrow(...)` works for callers that query
    # the connection directly.
    conn.fetchrow = AsyncMock(side_effect=fetchrow) if fetchrow is not None else conn.fetchrow
    if fetch is not None:
        conn.fetch = AsyncMock(side_effect=fetch) if not isinstance(fetch, AsyncMock) else fetch
    if fetchval is not None:
        conn.fetchval = AsyncMock(side_effect=fetchval) if not isinstance(fetchval, AsyncMock) else fetchval
    if execute is not None:
        conn.execute = execute
    conn.__aenter__ = AsyncMock(return_value=conn)
    conn.__aexit__ = AsyncMock(return_value=False)
    with patch('api.reports.get_conn', return_value=conn):
        yield conn


def _role_row(uid='user-77', slug='radiologist'):
    return {'id': uid, 'slug': slug}


def _assign_fetchrow(q, *a):
    # S-7 role check queries the users table; every other fetchrow call
    # in the assign flow is the exam lookup.
    if 'FROM users' in q:
        return _role_row()
    return _exam_row(status='completed')


def _exam_row(exam_id='exam-1', status='completed', priority='stat'):
    return {
        'id': exam_id, 'status': status, 'priority': priority,
        'patient_id': 'P1', 'patient_name': 'A^B',
        'accession_number': 'ACC1', 'modality': 'CT',
        'protocol_name': 'CT Head (Routine)', 'completed_at': None,
        'assigned_technologist': '',
    }


def _report_row(report_id='rep-1', exam_id='exam-1', status='draft', impression='', created_by='50', signed_by='', review_feedback=''):
    return {
        'id': report_id, 'exam_id': exam_id, 'status': status,
        'findings': 'Findings text', 'impression': impression,
        'recommendations': '', 'template_name': '', 'created_by': created_by,
        'signed_by': signed_by, 'signed_at': None, 'created_at': None, 'updated_at': None,
        'review_feedback': review_feedback,
    }


def _reading_row(exam_id='exam-1', priority='stat'):
    return {
        'exam_id': exam_id, 'patient_id': 'P1', 'patient_name': 'A^B',
        'patient_birth_date': '', 'patient_sex': '',
        'accession_number': 'ACC1', 'requested_procedure_desc': '',
        'modality': 'CT', 'priority': priority, 'protocol_name': '',
        'completed_at': None, 'assigned_technologist': '',
        'assigned_radiologist': '', 'referring_physician': '',
        'report_id': None, 'report_status': None, 'signed_by': None, 'signed_at': None,
    }


class TestReadingList:
    def test_requires_report_read(self):
        client = TestClient(_make_app(NO_PERMS))
        assert client.get('/reports/reading-list').status_code == 403

    def test_lists_completed_exams_without_final_report(self):
        client = TestClient(_make_app(RAD))
        async def fake_fetch(q, *a):
            return [_reading_row(exam_id='exam-1', priority='routine'),
                    _reading_row(exam_id='exam-2', priority='stat')]
        with _conn(fetch=fake_fetch):
            resp = client.get('/reports/reading-list')
        assert resp.status_code == 200
        data = resp.json()['data']
        # STAT sorts first.
        assert data[0]['exam_id'] == 'exam-2'
        assert data[1]['exam_id'] == 'exam-1'

    def test_me_resolves_to_requesting_user(self):
        """radiologist=me must resolve to the requesting user server-side."""
        client = TestClient(_make_app(RAD))
        with patch('api.reports.Reports') as reports_cls:
            reports = AsyncMock()
            reports.reading_list = AsyncMock(return_value=[])
            reports_cls.return_value = reports
            with _conn(fetchval=AsyncMock(return_value=1)):
                resp = client.get(
                    '/reports/reading-list'
                    '?radiologist=me&physician=Lee&date_from=2026-08-01&date_to=2026-08-31',
                )
        assert resp.status_code == 200
        kwargs = reports.reading_list.await_args.kwargs
        assert kwargs['radiologist'] == '50'  # RAD user id
        assert kwargs['physician'] == 'Lee'
        assert kwargs['date_from'] == '2026-08-01'
        assert kwargs['date_to'] == '2026-08-31'

    def test_review_filter_passes_to_reading_list(self):
        """review=1 selects the attending supervision queue (submitted
        reports); degenerate values normalize to None."""
        client = TestClient(_make_app(RAD))
        with patch('api.reports.Reports') as reports_cls:
            reports = AsyncMock()
            reports.reading_list = AsyncMock(return_value=[])
            reports_cls.return_value = reports
            with _conn():
                resp = client.get('/reports/reading-list?review=1')
        assert resp.status_code == 200
        assert reports.reading_list.await_args.kwargs['review'] == '1'

    def test_review_filter_false_values_normalize_to_none(self):
        client = TestClient(_make_app(RAD))
        with patch('api.reports.Reports') as reports_cls:
            reports = AsyncMock()
            reports.reading_list = AsyncMock(return_value=[])
            reports_cls.return_value = reports
            with _conn():
                resp = client.get('/reports/reading-list?review=0')
        assert resp.status_code == 200
        assert reports.reading_list.await_args.kwargs['review'] is None

    def test_returned_status_maps_to_draft_with_feedback(self):
        """R13 resident revision loop: a returned report is a draft carrying
        review_feedback (return_report() resets the status), so status=returned
        must bind that composite condition — not a raw status equality."""
        client = TestClient(_make_app(RAD))
        async def fake_fetch(q, *a):
            assert "r.review_feedback <> ''" in q
            assert "r.status = 'draft'" in q
            return []
        with _conn(fetch=fake_fetch):
            resp = client.get('/reports/reading-list?status=returned')
        assert resp.status_code == 200

    def test_claimed_today_only_for_own_queue(self):
        """radiologist=me carries claimed_today (drafts started today); any
        other radiologist query keeps the payload shape unchanged."""
        client = TestClient(_make_app(RAD))
        with patch('api.reports.Reports') as reports_cls:
            reports = AsyncMock()
            reports.reading_list = AsyncMock(return_value=[])
            reports_cls.return_value = reports
            async def fake_fetchval(q, *a):
                assert "created_by = $1" in q
                return 3
            with _conn(fetchval=fake_fetchval):
                mine = client.get('/reports/reading-list?radiologist=me')
                # radiologist=77: fetchval is never called (is_me False).
                other = client.get('/reports/reading-list?radiologist=77')
        assert mine.status_code == 200
        assert mine.json()['claimed_today'] == 3
        assert other.status_code == 200
        assert 'claimed_today' not in other.json()

    def test_search_binds_all_three_like_placeholders(self):
        """A search term must produce three distinct placeholders — the old
        single-$idx f-string passed 3 params for 1 placeholder and 500'd."""
        client = TestClient(_make_app(RAD))
        async def fake_fetch(q, *a):
            return []
        with _conn(fetch=fake_fetch):
            resp = client.get('/reports/reading-list?search=Lee')
        assert resp.status_code == 200

    def test_assigned_radiologist_rows_include_physicians(self):
        client = TestClient(_make_app(RAD))
        async def fake_fetch(q, *a):
            row = _reading_row(exam_id='exam-9')
            row['assigned_radiologist'] = '50'
            row['referring_physician'] = 'Lee^Kim'
            return [row]
        with _conn(fetch=fake_fetch):
            resp = client.get('/reports/reading-list?radiologist=50')
        assert resp.status_code == 200
        data = resp.json()['data']
        assert data[0]['assigned_radiologist'] == '50'
        assert data[0]['referring_physician'] == 'Lee^Kim'


class TestReadingListUnread:
    """R-01: unread=1 narrows the queue to exams never opened for reading
    (no report row yet) — the spec'd unread toggle."""

    def test_unread_filter_passes_to_reading_list(self):
        client = TestClient(_make_app(RAD))
        with patch('api.reports.Reports') as reports_cls:
            reports = AsyncMock()
            reports.reading_list = AsyncMock(return_value=[])
            reports_cls.return_value = reports
            with _conn():
                resp = client.get('/reports/reading-list?unread=1')
        assert resp.status_code == 200
        assert reports.reading_list.await_args.kwargs['unread'] == '1'

    def test_unread_false_values_normalize_to_none(self):
        client = TestClient(_make_app(RAD))
        with patch('api.reports.Reports') as reports_cls:
            reports = AsyncMock()
            reports.reading_list = AsyncMock(return_value=[])
            reports_cls.return_value = reports
            with _conn():
                resp = client.get('/reports/reading-list?unread=0')
        assert resp.status_code == 200
        assert reports.reading_list.await_args.kwargs['unread'] is None

    def test_unread_adds_never_opened_clause(self):
        client = TestClient(_make_app(RAD))

        async def fake_fetch(q, *a):
            assert 'r.id IS NULL' in q
            return []

        with _conn(fetch=fake_fetch):
            resp = client.get('/reports/reading-list?unread=1')
        assert resp.status_code == 200


class TestExamAssign:
    def test_assign_requires_report_write(self):
        client = TestClient(_make_app(READ_ONLY))
        resp = client.post('/reports/reading-list/exam-1/assign', json={})
        assert resp.status_code == 403

    def test_assign_defaults_to_requesting_user(self):
        """An empty radiologist_id assigns the exam to the requesting user."""
        client = TestClient(_make_app(RAD))
        def fake_fetchrow(q, *a):
            if 'FROM users' in q:
                return _role_row(uid='50')
            return _exam_row(exam_id='exam-1', status='completed')
        with patch('api.reports.Exams') as exams_cls, _conn(
                fetchrow=fake_fetchrow), _audit_ok():
            exams = AsyncMock()
            exams.get = AsyncMock(return_value=_exam_row(
                exam_id='exam-1', status='completed'))
            exams.assign_radiologist = AsyncMock(return_value=_exam_row(
                exam_id='exam-1', status='completed'))
            exams_cls.return_value = exams
            resp = client.post('/reports/reading-list/exam-1/assign', json={})
        assert resp.status_code == 200
        args = exams.assign_radiologist.await_args.args
        assert args == ('exam-1', '50')  # RAD user id

    def test_assign_explicit_radiologist(self):
        client = TestClient(_make_app(RAD))
        with patch('api.reports.Exams') as exams_cls, _conn(
                fetchrow=_assign_fetchrow), _audit_ok():
            exams = AsyncMock()
            exams.get = AsyncMock(return_value=_exam_row(status='completed'))
            exams.assign_radiologist = AsyncMock(return_value=_exam_row())
            exams_cls.return_value = exams
            resp = client.post('/reports/reading-list/exam-1/assign',
                               json={'radiologist_id': 'user-77'})
        assert resp.status_code == 200
        assert exams.assign_radiologist.await_args.args == ('exam-1', 'user-77')

    def test_assign_404_when_exam_missing(self):
        client = TestClient(_make_app(RAD))
        with patch('api.reports.Exams') as exams_cls, _conn(
                fetchrow=lambda q, *a: None), _audit_ok():
            exams_cls.return_value.get = AsyncMock(return_value=None)
            resp = client.post('/reports/reading-list/exam-1/assign', json={})
        assert resp.status_code == 404

    def test_assign_rejects_exam_not_completed(self):
        client = TestClient(_make_app(RAD))
        with patch('api.reports.Exams') as exams_cls, _conn(
                fetchrow=lambda q, *a: _exam_row(status='in_progress')), _audit_ok():
            exams_cls.return_value.get = AsyncMock(
                return_value=_exam_row(status='in_progress'))
            resp = client.post('/reports/reading-list/exam-1/assign', json={})
        assert resp.status_code == 400


    def test_assign_rejects_non_radiologist_user(self):
        """S-7: assignment must not accept an arbitrary user id — the
        target must exist and hold the radiologist role."""
        client = TestClient(_make_app(RAD))
        def fake_fetchrow(q, *a):
            if 'FROM users' in q:
                return _role_row(uid='user-99', slug='technician')
            return _exam_row(status='completed')
        with patch('api.reports.Exams') as exams_cls, _conn(
                fetchrow=fake_fetchrow), _audit_ok():
            exams_cls.return_value.get = AsyncMock(
                return_value=_exam_row(status='completed'))
            resp = client.post('/reports/reading-list/exam-1/assign',
                               json={'radiologist_id': 'user-99'})
        assert resp.status_code == 400

    def test_assign_accepts_radiologist_user(self):
        client = TestClient(_make_app(RAD))
        def _fetchrow(q, *a):
            if 'FROM users' in q:
                return {'id': 'user-77', 'slug': 'radiologist'}
            return _exam_row(status='completed')
        with patch('api.reports.Exams') as exams_cls, _conn(
                fetchrow=_fetchrow), _audit_ok():
            exams = AsyncMock()
            exams.get = AsyncMock(return_value=_exam_row(status='completed'))
            exams.assign_radiologist = AsyncMock(return_value=_exam_row())
            exams_cls.return_value = exams
            resp = client.post('/reports/reading-list/exam-1/assign',
                               json={'radiologist_id': 'user-77'})
        assert resp.status_code == 200
        assert exams.assign_radiologist.await_args.args == ('exam-1', 'user-77')

    def test_assign_accepts_resident_user(self):
        """RES-02: residents hold REPORT_WRITE and read from the same
        queue — an explicit resident claim must be accepted, not rejected
        by the radiologist-only role check."""
        client = TestClient(_make_app(RAD))
        def _fetchrow(q, *a):
            if 'FROM users' in q:
                return {'id': 'user-88', 'slug': 'resident'}
            return _exam_row(status='completed')
        with patch('api.reports.Exams') as exams_cls, _conn(
                fetchrow=_fetchrow), _audit_ok():
            exams = AsyncMock()
            exams.get = AsyncMock(return_value=_exam_row(status='completed'))
            exams.assign_radiologist = AsyncMock(return_value=_exam_row())
            exams_cls.return_value = exams
            resp = client.post('/reports/reading-list/exam-1/assign',
                               json={'radiologist_id': 'user-88'})
        assert resp.status_code == 200


class TestExamReport:
    def test_get_exam_and_report(self):
        client = TestClient(_make_app(RAD))
        async def fake_fetchrow(q, *a):
            if 'FROM exams' in q:
                return _exam_row()
            return _report_row()
        with _conn(fetchrow=fake_fetchrow):
            resp = client.get('/reports/exam-1')
        assert resp.status_code == 200
        body = resp.json()['data']
        assert body['exam']['id'] == 'exam-1'
        assert body['report']['status'] == 'draft'

    def test_get_404_when_exam_missing(self):
        client = TestClient(_make_app(RAD))
        with _conn(fetchrow=AsyncMock(return_value=None)):
            resp = client.get('/reports/nope')
        assert resp.status_code == 404

    def test_put_creates_draft_when_missing(self):
        client = TestClient(_make_app(RAD))
        created = _report_row(impression='Normal')
        async def fake_fetchrow(q, *a):
            if 'FROM exams' in q:
                return _exam_row()
            return None  # no existing report -> create path
        with _conn(fetchrow=fake_fetchrow), _audit_ok(), \
             patch('api.reports.Reports') as mock_reports_cls:
            mock_reports = AsyncMock()
            mock_reports.get_by_exam.return_value = None
            mock_reports.create.return_value = created
            mock_reports_cls.return_value = mock_reports
            resp = client.put('/reports/exam-1', json={
                'findings': 'Findings text',
                'impression': 'Normal',
                'status': 'draft',
            })
        assert resp.status_code == 200
        assert resp.json()['data']['status'] == 'draft'
        assert mock_reports.create.await_args.args[0] == 'exam-1'

    def test_put_updates_existing(self):
        client = TestClient(_make_app(RAD))
        async def fake_fetchrow(q, *a):
            if 'FROM exams' in q:
                return _exam_row()
            return None
        with _conn(fetchrow=fake_fetchrow), _audit_ok(), \
             patch('api.reports.Reports') as mock_reports_cls:
            mock_reports = AsyncMock()
            mock_reports.get_by_exam.return_value = _report_row()
            mock_reports.update.return_value = _report_row(impression='Normal', status='preliminary')
            mock_reports_cls.return_value = mock_reports
            resp = client.put('/reports/exam-1', json={
                'impression': 'Normal',
                'status': 'preliminary',
            })
        assert resp.status_code == 200
        assert resp.json()['data']['status'] == 'preliminary'
        # H10 / V-1: edits must be attributed to the editor, not the creator.
        _, kwargs = mock_reports.update.call_args
        assert kwargs.get('edited_by') == str(RAD.id)

    def test_put_requires_report_write(self):
        client = TestClient(_make_app(READ_ONLY))
        resp = client.put('/reports/exam-1', json={'findings': 'x'})
        assert resp.status_code == 403

    def test_put_rejects_final_report(self):
        """CR-4: a signed (final) report is locked — no edits, no status
        flip back to preliminary via the save endpoint."""
        client = TestClient(_make_app(RAD))
        async def fake_fetchrow(q, *a):
            if 'FROM exams' in q:
                return _exam_row()
            return None
        with _conn(fetchrow=fake_fetchrow), \
             patch('api.reports.Reports') as mock_reports_cls:
            mock_reports = AsyncMock()
            mock_reports.get_by_exam.return_value = _report_row(status='final')
            mock_reports_cls.return_value = mock_reports
            resp = client.put('/reports/exam-1', json={'impression': 'Edited'})
        assert resp.status_code == 400
        assert 'locked' in resp.json()['error']['message']

    def test_put_rejects_final_status_in_payload(self):
        """CR-4: the save schema must not accept `final` — final is only
        reachable through the sign endpoint (REPORT_SIGN permission)."""
        client = TestClient(_make_app(RAD))
        async def fake_fetchrow(q, *a):
            if 'FROM exams' in q:
                return _exam_row()
            return None
        with _conn(fetchrow=fake_fetchrow), _audit_ok(), \
             patch('api.reports.Reports') as mock_reports_cls:
            mock_reports = AsyncMock()
            mock_reports.get_by_exam.return_value = None
            mock_reports_cls.return_value = mock_reports
            resp = client.put('/reports/exam-1', json={
                'findings': 'Findings text',
                'impression': 'Normal',
                'status': 'final',
            })
        assert resp.status_code == 422 or resp.status_code == 400
        assert 'status' in str(resp.json())

    def test_put_rejects_preliminary_edit_of_final(self):
        """CR-4: reading console autosave sends preliminary — must 400."""
        client = TestClient(_make_app(RAD))
        async def fake_fetchrow(q, *a):
            if 'FROM exams' in q:
                return _exam_row()
            return None
        with _conn(fetchrow=fake_fetchrow), \
             patch('api.reports.Reports') as mock_reports_cls:
            mock_reports = AsyncMock()
            mock_reports.get_by_exam.return_value = _report_row(status='final')
            mock_reports_cls.return_value = mock_reports
            resp = client.put('/reports/exam-1', json={
                'findings': 'Edited findings',
                'status': 'preliminary',
            })
        assert resp.status_code == 400
        assert 'locked' in resp.json()['error']['message']

    def test_put_rejects_submitted_report(self):
        """R13 supervision lock: once submitted, a report is in the
        attending's hands — edits are refused until it is returned."""
        client = TestClient(_make_app(RAD))
        async def fake_fetchrow(q, *a):
            if 'FROM exams' in q:
                return _exam_row()
            return None
        with _conn(fetchrow=fake_fetchrow), \
             patch('api.reports.Reports') as mock_reports_cls:
            mock_reports = AsyncMock()
            mock_reports.get_by_exam.return_value = _report_row(status='submitted')
            mock_reports_cls.return_value = mock_reports
            resp = client.put('/reports/exam-1', json={'impression': 'Normal'})
        assert resp.status_code == 400
        assert 'locked' in resp.json()['error']['message']


class TestExamReportSign:
    def test_sign_requires_impression(self):
        client = TestClient(_make_app(RAD))
        async def fake_fetchrow(q, *a):
            if 'FROM exams' in q:
                return _exam_row()
            return _report_row(impression='')  # empty impression
        with _conn(fetchrow=fake_fetchrow):
            resp = client.post('/reports/exam-1/sign', json={'confirm': True})
        assert resp.status_code == 400
        assert 'Impression is required' in resp.json()['error']['message']

    def test_sign_portal_notify_survives_missing_report_id(self):
        """G-07: the portal link's `or report_id` fallback referenced an
        undefined name — a falsy report id raised NameError inside the try,
        silently skipping the patient notification. The fallback must be
        exam_id and the notify must fire."""
        client = TestClient(_make_app(RAD))
        signed = _report_row(report_id='', impression='Normal',
                             status='final', signed_by='50')

        async def fake_fetchrow(q, *a):
            if 'FROM exams' in q:
                return _exam_row()
            return _report_row(impression='Normal', report_id='')

        with _conn(fetchrow=fake_fetchrow), _audit_ok(), \
             patch('api.reports.Reports') as mock_reports_cls, \
             patch('api.reports.notify_patient_scoped',
                   new_callable=AsyncMock) as portal:
            mock_reports = AsyncMock()
            mock_reports.get_by_exam.return_value = _report_row(
                impression='Normal', report_id='')
            mock_reports.sign.return_value = signed
            mock_reports_cls.return_value = mock_reports
            resp = client.post('/reports/exam-1/sign', json={'confirm': True})
        assert resp.status_code == 200
        portal.assert_awaited_once()
        assert portal.await_args.args[5] == '/portal/results/exam-1'

    def test_sign_success(self):
        client = TestClient(_make_app(RAD))
        signed = _report_row(impression='Normal', status='final', signed_by='50')
        async def fake_fetchrow(q, *a):
            if 'FROM exams' in q:
                return _exam_row()
            return _report_row(impression='Normal')
        with _conn(fetchrow=fake_fetchrow), _audit_ok(), \
             patch('api.reports.Reports') as mock_reports_cls, \
             patch('api.reports.notify_role', new_callable=AsyncMock) as notify:
            mock_reports = AsyncMock()
            mock_reports.get_by_exam.return_value = _report_row(impression='Normal')
            mock_reports.sign.return_value = signed
            mock_reports_cls.return_value = mock_reports
            resp = client.post('/reports/exam-1/sign', json={'confirm': True})
        assert resp.status_code == 200
        assert resp.json()['data']['status'] == 'final'
        assert notify.await_count == 1

    def test_sign_invokes_results_distribution_engine(self):
        # CR-8: the sign path must call the real ResultsDistributionEngine
        # (replacing the S8-13 audit-only stub). Patch the engine class and
        # assert distribute_report is awaited on a successful sign.
        client = TestClient(_make_app(RAD))
        signed = _report_row(impression='Normal', status='final', signed_by='50')
        async def fake_fetchrow(q, *a):
            if 'FROM exams' in q:
                return _exam_row()
            return _report_row(impression='Normal')
        with _conn(fetchrow=fake_fetchrow), _audit_ok(), \
             patch('api.reports.Reports') as mock_reports_cls, \
             patch('api.reports.notify_role', new_callable=AsyncMock), \
             patch('api.reports.notify_user', new_callable=AsyncMock), \
             patch('api.reports.ResultsDistributionEngine') as mock_engine_cls:
            mock_engine = AsyncMock()
            mock_engine.distribute_report = AsyncMock()
            mock_engine_cls.return_value = mock_engine
            mock_reports = AsyncMock()
            mock_reports.get_by_exam.return_value = _report_row(impression='Normal')
            mock_reports.sign.return_value = signed
            mock_reports_cls.return_value = mock_reports
            resp = client.post('/reports/exam-1/sign', json={'confirm': True})
        assert resp.status_code == 200
        mock_engine.distribute_report.assert_awaited_once_with('rep-1')

    def test_sign_requires_report_sign_permission(self):
        client = TestClient(_make_app(READ_ONLY))
        resp = client.post('/reports/exam-1/sign', json={'confirm': True})
        assert resp.status_code == 403


class TestExamReportSubmit:
    def test_submit_requires_report_write(self):
        client = TestClient(_make_app(READ_ONLY))
        resp = client.post('/reports/exam-1/submit')
        assert resp.status_code == 403

    def test_submit_requires_impression(self):
        client = TestClient(_make_app(RAD))
        with patch('api.reports.Exams') as exams_cls, \
             patch('api.reports.Reports') as reports_cls, _conn():
            exams_cls.return_value.get = AsyncMock(return_value=_exam_row())
            reports = AsyncMock()
            reports.get_by_exam.return_value = _report_row(impression='')
            reports_cls.return_value = reports
            resp = client.post('/reports/exam-1/submit')
        assert resp.status_code == 400
        assert 'Impression is required' in resp.json()['error']['message']

    def test_submit_rejects_when_no_report_exists(self):
        client = TestClient(_make_app(RAD))
        with patch('api.reports.Exams') as exams_cls, \
             patch('api.reports.Reports') as reports_cls, _conn():
            exams_cls.return_value.get = AsyncMock(return_value=_exam_row())
            reports = AsyncMock()
            reports.get_by_exam.return_value = None
            reports_cls.return_value = reports
            resp = client.post('/reports/exam-1/submit')
        assert resp.status_code == 400
        assert 'No report exists' in resp.json()['error']['message']

    def test_submit_rejects_non_draft_status(self):
        """A submitted report cannot be submitted again; final is terminal."""
        client = TestClient(_make_app(RAD))
        with patch('api.reports.Exams') as exams_cls, \
             patch('api.reports.Reports') as reports_cls, _conn():
            exams_cls.return_value.get = AsyncMock(return_value=_exam_row())
            reports = AsyncMock()
            reports.get_by_exam.return_value = _report_row(status='submitted')
            reports_cls.return_value = reports
            resp = client.post('/reports/exam-1/submit')
        assert resp.status_code == 400
        assert 'only a draft can be submitted' in resp.json()['error']['message']

    def test_submit_404_when_exam_missing(self):
        client = TestClient(_make_app(RAD))
        with patch('api.reports.Exams') as exams_cls, _conn():
            exams_cls.return_value.get = AsyncMock(return_value=None)
            resp = client.post('/reports/exam-1/submit')
        assert resp.status_code == 404

    def test_submit_success_notifies_attendings(self):
        client = TestClient(_make_app(RAD))
        submitted = _report_row(impression='Normal', status='submitted')
        async def fake_fetchrow(q, *a):
            if 'FROM exams' in q:
                return _exam_row()
            return None
        with _conn(fetchrow=fake_fetchrow), _audit_ok(), \
             patch('api.reports.Reports') as reports_cls, \
             patch('api.reports.notify_role', new_callable=AsyncMock) as notify:
            reports = AsyncMock()
            reports.get_by_exam.return_value = _report_row(impression='Normal')
            reports.submit.return_value = submitted
            reports_cls.return_value = reports
            resp = client.post('/reports/exam-1/submit')
        assert resp.status_code == 200
        assert resp.json()['data']['status'] == 'submitted'
        assert reports.submit.await_args.args[0] == 'rep-1'
        notify.assert_awaited_once()
        assert notify.await_args.args[1] == 'radiologist'


class TestExamReportReturn:
    def test_return_requires_report_sign(self):
        """Only signers (attendings) may redirect a draft back for revision."""
        client = TestClient(_make_app(READ_ONLY))
        resp = client.post('/reports/exam-1/return', json={'feedback': 'x'})
        assert resp.status_code == 403

    def test_return_requires_submitted_status(self):
        client = TestClient(_make_app(RAD))
        with patch('api.reports.Exams') as exams_cls, \
             patch('api.reports.Reports') as reports_cls, _conn():
            exams_cls.return_value.get = AsyncMock(return_value=_exam_row())
            reports = AsyncMock()
            reports.get_by_exam.return_value = _report_row(status='draft')
            reports_cls.return_value = reports
            resp = client.post('/reports/exam-1/return', json={'feedback': 'x'})
        assert resp.status_code == 400
        assert 'submitted report can be returned' in \
            resp.json()['error']['message']

    def test_return_requires_feedback(self):
        """Returning without feedback would leave the resident without a
        reason to revise — the attending must say what to change."""
        client = TestClient(_make_app(RAD))
        with patch('api.reports.Exams') as exams_cls, \
             patch('api.reports.Reports') as reports_cls, _conn():
            exams_cls.return_value.get = AsyncMock(return_value=_exam_row())
            reports = AsyncMock()
            reports.get_by_exam.return_value = _report_row(status='submitted')
            reports_cls.return_value = reports
            resp = client.post('/reports/exam-1/return', json={'feedback': '  '})
        assert resp.status_code == 400
        assert 'feedback is required' in resp.json()['error']['message']

    def test_return_success_notifies_author(self):
        client = TestClient(_make_app(RAD))
        returned = _report_row(status='draft', review_feedback='Add comparison.')
        async def fake_fetchrow(q, *a):
            if 'FROM exams' in q:
                return _exam_row()
            return None
        with _conn(fetchrow=fake_fetchrow), _audit_ok(), \
             patch('api.reports.Reports') as reports_cls, \
             patch('api.reports.notify_user', new_callable=AsyncMock) as notify:
            reports = AsyncMock()
            reports.get_by_exam.return_value = _report_row(status='submitted')
            reports.return_report.return_value = returned
            reports_cls.return_value = reports
            resp = client.post(
                '/reports/exam-1/return',
                json={'feedback': 'Add comparison with prior CT.', 'confirm': True},
            )
        assert resp.status_code == 200
        assert resp.json()['data']['status'] == 'draft'
        args = reports.return_report.await_args.args
        assert args == ('rep-1', '50', 'Add comparison with prior CT.')
        notify.assert_awaited_once()
        assert notify.await_args.args[1] == '50'  # author

    def test_return_rejects_when_no_report_exists(self):
        client = TestClient(_make_app(RAD))
        with patch('api.reports.Exams') as exams_cls, \
             patch('api.reports.Reports') as reports_cls, _conn():
            exams_cls.return_value.get = AsyncMock(return_value=_exam_row())
            reports = AsyncMock()
            reports.get_by_exam.return_value = None
            reports_cls.return_value = reports
            resp = client.post('/reports/exam-1/return', json={'feedback': 'x'})
        assert resp.status_code == 400
        assert 'No report exists' in resp.json()['error']['message']

    def test_return_404_when_exam_missing(self):
        client = TestClient(_make_app(RAD))
        with patch('api.reports.Exams') as exams_cls, _conn():
            exams_cls.return_value.get = AsyncMock(return_value=None)
            resp = client.post('/reports/exam-1/return', json={'feedback': 'x'})
        assert resp.status_code == 404


class TestExamImages:
    def test_requires_report_read(self):
        client = TestClient(_make_app(NO_PERMS))
        assert client.get('/reports/exam-1/images').status_code == 403

    def test_404_when_exam_missing(self):
        client = TestClient(_make_app(RAD))
        with _conn(fetchrow=AsyncMock(return_value=None)):
            resp = client.get('/reports/exam-1/images')
        assert resp.status_code == 404

    def test_imaging_false_when_exam_has_no_accession(self):
        """Front-desk exams with no accession (no DICOM yet) get a marker."""
        client = TestClient(_make_app(RAD))
        exam = _exam_row()
        exam['accession_number'] = ''
        async def fake_fetchrow(q, *a):
            if 'FROM exams' in q:
                return exam
            return None
        with _conn(fetchrow=fake_fetchrow):
            resp = client.get('/reports/exam-1/images')
        assert resp.status_code == 200
        assert resp.json()['data']['imaging'] is False

    def test_imaging_false_when_no_study_matches(self):
        """No study stored under the exam accession -> imaging marker."""
        client = TestClient(_make_app(RAD))
        async def fake_fetchrow(q, *a):
            if 'FROM exams' in q:
                return _exam_row()
            return None  # patient lookup finds nothing
        with _conn(fetchrow=fake_fetchrow):
            resp = client.get('/reports/exam-1/images')
        assert resp.status_code == 200
        assert resp.json()['data']['imaging'] is False

    def test_returns_patient_studies_tree(self):
        """The payload mirrors /files/{id}: patient.studies[].series[].files[]."""
        client = TestClient(_make_app(RAD))
        patient = {
            'id': 7, 'patient_id': 'P1', 'name': 'A^B',
            'studies': [{
                'id': 1, 'study_id': 'ST-1', 'description': 'Chest',
                'study_instance_uid': '1.2.3.4', 'accession_number': 'ACC1',
                'series': [{
                    'id': 2, 'study_id': 1, 'number': 1, 'modality': 'CT',
                    'description': 'Axial', 'series_instance_uid': '1.2.3.4.5',
                    'files': [{
                        'id': 3, 'name': 'IM1', 'hash': 'h1',
                        'indexed': True, 'sop_instance_uid': '1.2.3.4.5.6',
                        'deleted': False, 'meta': None, 'tools_state': None,
                    }],
                }],
            }],
        }
        async def fake_fetchrow(q, *a):
            if 'FROM exams' in q:
                return _exam_row()
            return {'id': 7}
        with _conn(fetchrow=fake_fetchrow), \
             patch('api.reports.Patient') as patient_cls:
            patient_cls.return_value.get_extra = AsyncMock(return_value=patient)
            resp = client.get('/reports/exam-1/images')
        assert resp.status_code == 200
        body = resp.json()['data']
        assert body['imaging'] is True
        assert body['patient']['studies'][0]['accession_number'] == 'ACC1'
        assert body['patient']['studies'][0]['series'][0]['files'][0]['id'] == 3
        # The patient lookup only runs once the exam accession matched.
        patient_cls.return_value.get_extra.assert_awaited_once_with(7)

    def test_narrows_studies_to_matching_accession(self):
        """Priors with other accessions stay out of the console tree."""
        client = TestClient(_make_app(RAD))
        patient = {
            'id': 7, 'patient_id': 'P1', 'name': 'A^B',
            'studies': [
                {'id': 1, 'study_id': 'ST-1', 'description': 'Chest',
                 'study_instance_uid': 'u1', 'accession_number': 'ACC1', 'series': []},
                {'id': 9, 'study_id': 'ST-9', 'description': 'Prior',
                 'study_instance_uid': 'u9', 'accession_number': 'ACC-OLD', 'series': []},
            ],
        }
        async def fake_fetchrow(q, *a):
            if 'FROM exams' in q:
                return _exam_row()
            return {'id': 7}
        with _conn(fetchrow=fake_fetchrow), \
             patch('api.reports.Patient') as patient_cls:
            patient_cls.return_value.get_extra = AsyncMock(return_value=patient)
            resp = client.get('/reports/exam-1/images')
        assert resp.status_code == 200
        studies = resp.json()['data']['patient']['studies']
        assert [s['id'] for s in studies] == [1]


class TestReportTemplates:
    def test_templates_seed_and_list(self):
        client = TestClient(_make_app(RAD))
        async def fake_fetchval(q, *a):
            return 0  # not seeded -> seed then list
        async def fake_fetch(q, *a):
            return [{'name': 'CT Head — Routine', 'modality': 'CT'}]
        with _conn(fetchval=fake_fetchval, fetch=fake_fetch, execute=AsyncMock()):
            # H9: the handler must also seed ris_report_templates — the
            # table list_templates actually reads — not just the legacy
            # report_templates table.
            seed_defaults = AsyncMock()
            with patch('db.ris_templates.RisReportTemplates.seed_defaults',
                       seed_defaults):
                resp = client.get('/reports/templates')
        assert resp.status_code == 200
        assert resp.json()['data'][0]['name'] == 'CT Head — Routine'
        seed_defaults.assert_awaited_once()


class TestPeerReviews:
    def test_list_my_assignments(self):
        client = TestClient(_make_app(RAD))
        review = {
            'id': 'rev-1', 'report_id': 'rep-1', 'reviewer_id': '50',
            'status': 'assigned', 'discrepancy_level': '',
            'comment': '', 'assigned_at': None, 'completed_at': None,
            'created_at': None,
        }
        async def fake_fetch(q, *a):
            return [review]
        async def fake_fetchrow(q, *a):
            if 'FROM exams' in q:
                return _exam_row()
            return _report_row(status='final')
        with _conn(fetch=fake_fetch, fetchrow=fake_fetchrow):
            resp = client.get('/peer-reviews')
        assert resp.status_code == 200
        data = resp.json()['data']
        assert data[0]['status'] == 'assigned'
        assert data[0]['report']['status'] == 'final'
        assert data[0]['exam']['accession_number'] == 'ACC1'

    def test_create_requires_final_report(self):
        client = TestClient(_make_app(RAD))
        async def fake_fetchrow(q, *a):
            if 'FROM reports' in q:
                return _report_row(status='draft')
            return None
        with _conn(fetchrow=fake_fetchrow):
            resp = client.post('/peer-reviews', json={
                'report_id': 'rep-1', 'reviewer_id': 'user-x',
            })
        assert resp.status_code == 400
        assert 'final' in resp.json()['error']['message']

    def test_create_assignment(self):
        client = TestClient(_make_app(RAD))
        review = {
            'id': 'rev-1', 'report_id': 'rep-1', 'reviewer_id': 'user-x',
            'status': 'assigned', 'discrepancy_level': '',
            'comment': '', 'assigned_at': None, 'completed_at': None,
            'created_at': None,
        }
        async def fake_fetchrow(q, *a):
            if 'FROM reports' in q:
                return _report_row(status='final')
            if 'FROM users' in q:
                return {'id': 'user-x'}
            return review
        with _conn(fetchrow=fake_fetchrow), _audit_ok(), \
             patch('api.reports.PeerReviews') as mock_pr_cls, \
             patch('api.reports.notify_user', new_callable=AsyncMock) as notify:
            mock_pr = AsyncMock()
            mock_pr.create.return_value = review
            mock_pr_cls.return_value = mock_pr
            resp = client.post('/peer-reviews', json={
                'report_id': 'rep-1', 'reviewer_id': 'user-x',
            })
        assert resp.status_code == 201
        assert resp.json()['data']['status'] == 'assigned'
        assert notify.await_count == 1

    def test_submit_only_for_assigned_reviewer(self):
        client = TestClient(_make_app(RAD))  # RAD id is 50
        review = {
            'id': 'rev-1', 'report_id': 'rep-1', 'reviewer_id': 'other-user',
            'status': 'assigned', 'discrepancy_level': '', 'comment': '',
            'assigned_at': None, 'completed_at': None, 'created_at': None,
        }
        async def fake_fetchrow(q, *a):
            if 'FROM peer_reviews' in q:
                return review
            if 'FROM reports' in q:
                return _report_row(status='final')
            if 'FROM exams' in q:
                return _exam_row()
            return None
        with _conn(fetchrow=fake_fetchrow):
            resp = client.post('/peer-reviews/rev-1/submit', json={
                'discrepancy_level': 'minor', 'comment': 'Looks ok',
            })
        assert resp.status_code == 403

    def test_submit_success(self):
        client = TestClient(_make_app(RAD))
        submitted = {
            'id': 'rev-1', 'report_id': 'rep-1', 'reviewer_id': '50',
            'status': 'completed', 'discrepancy_level': 'minor',
            'comment': 'Looks ok', 'assigned_at': None, 'completed_at': None,
            'created_at': None,
        }
        async def fake_fetchrow(q, *a):
            if 'FROM peer_reviews' in q:
                return submitted
            if 'FROM reports' in q:
                return _report_row(status='final', created_by='50')
            if 'FROM exams' in q:
                return _exam_row()
            return None
        with _conn(fetchrow=fake_fetchrow), _audit_ok(), \
             patch('api.reports.PeerReviews') as mock_pr_cls, \
             patch('api.reports.notify_user', new_callable=AsyncMock) as notify:
            mock_pr = AsyncMock()
            mock_pr.get.return_value = submitted
            mock_pr.start.return_value = None
            mock_pr.submit.return_value = submitted
            mock_pr_cls.return_value = mock_pr
            resp = client.post('/peer-reviews/rev-1/submit', json={
                'discrepancy_level': 'minor', 'comment': 'Looks ok',
            })
        assert resp.status_code == 200
        assert resp.json()['data']['status'] == 'completed'
        assert notify.await_count == 1

    def test_reviewers_endpoint(self):
        client = TestClient(_make_app(RAD))
        async def fake_fetch(q, *a):
            return [{'id': 'u1', 'username': 'dr-smith'}]
        with _conn(fetch=fake_fetch):
            resp = client.get('/peer-reviews/reviewers')
        assert resp.status_code == 200
        assert resp.json()['data'][0]['username'] == 'dr-smith'

    def test_get_blocks_non_reviewer(self):
        """PHI guard: only the assigned reviewer (or author) can open a review."""
        client = TestClient(_make_app(READ_ONLY))  # id 51, not the reviewer
        review = {
            'id': 'rev-1', 'report_id': 'rep-1', 'reviewer_id': '50',
            'status': 'assigned', 'discrepancy_level': '', 'comment': '',
            'assigned_at': None, 'completed_at': None, 'created_at': None,
        }
        async def fake_fetchrow(q, *a):
            if 'FROM peer_reviews' in q:
                return review
            return _report_row(status='final', created_by='50')
        with _conn(fetchrow=fake_fetchrow):
            resp = client.get('/peer-reviews/rev-1')
        assert resp.status_code == 403

    def test_get_allows_assigned_reviewer(self):
        client = TestClient(_make_app(RAD))  # id 50 = assigned reviewer
        review = {
            'id': 'rev-1', 'report_id': 'rep-1', 'reviewer_id': '50',
            'status': 'assigned', 'discrepancy_level': '', 'comment': '',
            'assigned_at': None, 'completed_at': None, 'created_at': None,
        }
        async def fake_fetchrow(q, *a):
            if 'FROM peer_reviews' in q:
                return review
            if 'FROM reports' in q:
                return _report_row(status='final', created_by='50')
            return _exam_row()
        with _conn(fetchrow=fake_fetchrow):
            resp = client.get('/peer-reviews/rev-1')
        assert resp.status_code == 200
        assert resp.json()['data']['report']['status'] == 'final'


class TestReportVersionRestore:
    """R-06: restore a prior report version — POST
    /reports/{report_id}/versions/{version}/restore. Draft/preliminary
    only; restoring writes a NEW snapshot via Reports.update (history is
    append-only)."""

    def _app(self, user=None):
        from api.reports import ReportVersionRestoreHandler
        return Starlette(
            routes=[Route(
                '/reports/{report_id}/versions/{version}/restore',
                endpoint=ReportVersionRestoreHandler, methods=['POST'],
            )],
            middleware=[Middleware(_FakeAuth, user=user or RAD)],
            exception_handlers={
                HTTPException: _http_exception,
                _ValidationException: validation_exception_handler,
            },
        )

    def test_restore_requires_report_write(self):
        resp = TestClient(self._app(READ_ONLY)).post(
            '/reports/rep-1/versions/2/restore')
        assert resp.status_code == 403

    def test_restore_rejects_non_integer_version(self):
        resp = TestClient(self._app()).post(
            '/reports/rep-1/versions/abc/restore')
        assert resp.status_code == 400

    def test_restore_rejects_locked_report(self):
        async def fake_fetchrow(q, *a):
            if 'FROM reports' in q:
                return {'id': 'rep-1', 'status': 'final'}
            return None
        with _conn(fetchrow=fake_fetchrow):
            resp = TestClient(self._app()).post(
                '/reports/rep-1/versions/2/restore')
        assert resp.status_code == 409

    def test_restore_version_not_found(self):
        async def fake_fetchrow(q, *a):
            if 'FROM reports' in q:
                return {'id': 'rep-1', 'status': 'draft'}
            return None  # no such version row
        with _conn(fetchrow=fake_fetchrow):
            resp = TestClient(self._app()).post(
                '/reports/rep-1/versions/99/restore')
        assert resp.status_code == 404

    def test_restore_success_snapshots_and_audits(self):
        version_row = {
            'report_id': 'rep-1', 'version_number': 2,
            'findings': 'Old findings', 'impression': 'Old impression',
            'recommendations': 'Old recs',
        }

        async def fake_fetchrow(q, *a):
            if 'FROM reports' in q:
                return {'id': 'rep-1', 'status': 'draft'}
            if 'version_number' in q:
                return version_row
            return None

        with patch('api.reports.Reports') as reports_cls, \
             patch('api.reports.AuditLog') as audit_cls, \
             _conn(fetchrow=fake_fetchrow):
            reports = AsyncMock()
            updated = _report_row(impression='Old impression')
            reports.update = AsyncMock(return_value=updated)
            reports_cls.return_value = reports
            audit = AsyncMock()
            audit.log_event = AsyncMock()
            audit_cls.return_value = audit
            resp = TestClient(self._app()).post(
                '/reports/rep-1/versions/2/restore')
        assert resp.status_code == 200
        kwargs = reports.update.await_args.args[1]
        assert kwargs['findings'] == 'Old findings'
        assert kwargs['impression'] == 'Old impression'
        assert kwargs['recommendations'] == 'Old recs'
        assert audit.log_event.await_args.kwargs['event_type'] == \
            'report.version_restored'


class TestPriorReports:
    """R-07: prior report quick-view — GET /reports/priors returns the
    patient's earlier preliminary/final reports for the same modality,
    excluding the exam being read."""

    def _app(self, user=None):
        from api.reports import PriorReportsHandler
        return Starlette(
            routes=[Route('/reports/priors', endpoint=PriorReportsHandler)],
            middleware=[Middleware(_FakeAuth, user=user or RAD)],
            exception_handlers={
                HTTPException: _http_exception,
                _ValidationException: validation_exception_handler,
            },
        )

    def test_priors_requires_report_read(self):
        resp = TestClient(self._app(NO_PERMS)).get(
            '/reports/priors?patient_id=P1&modality=CT')
        assert resp.status_code == 403

    def test_priors_requires_patient_id(self):
        resp = TestClient(self._app()).get('/reports/priors')
        assert resp.status_code == 400

    def test_priors_passes_filters(self):
        with patch('api.reports.Reports') as reports_cls:
            reports = AsyncMock()
            reports.list_priors = AsyncMock(return_value=[])
            reports_cls.return_value = reports
            with _conn():
                resp = TestClient(self._app()).get(
                    '/reports/priors'
                    '?patient_id=P1&modality=CT&exclude_exam_id=e1')
        assert resp.status_code == 200
        kwargs = reports.list_priors.await_args.kwargs
        assert kwargs['patient_id'] == 'P1'
        assert kwargs['modality'] == 'CT'
        assert kwargs['exclude_exam_id'] == 'e1'

    def test_list_priors_queries_final_or_preliminary(self):
        captured = {}

        async def fake_fetch(q, *a):
            captured['q'] = q
            return [{
                'report_id': 'rep-9', 'exam_id': 'exam-9',
                'accession_number': 'ACC9', 'modality': 'CT',
                'status': 'final', 'completed_at': None,
                'impression_excerpt': 'Old impression text',
                'signed_at': None,
            }]

        with _conn(fetch=fake_fetch):
            resp = TestClient(self._app()).get(
                '/reports/priors?patient_id=P1&modality=CT&exclude_exam_id=e1')
        assert resp.status_code == 200
        q = captured['q']
        assert "r.status IN ('preliminary', 'final')" in q
        assert 'e.patient_id' in q and 'e.modality' in q
        row = resp.json()['data'][0]
        assert row['report_id'] == 'rep-9'
        assert row['impression_excerpt'] == 'Old impression text'


class TestReadingStats:
    """R-17/RES-04: personal reading statistics — GET /reports/reading-stats
    scoped to the requesting radiologist/resident."""

    def _app(self, user=None):
        from api.reports import ReadingStatsHandler
        return Starlette(
            routes=[
                Route('/reports/reading-stats', endpoint=ReadingStatsHandler),
            ],
            middleware=[Middleware(_FakeAuth, user=user or RAD)],
            exception_handlers={
                HTTPException: _http_exception,
                _ValidationException: validation_exception_handler,
            },
        )

    def test_stats_requires_report_read(self):
        resp = TestClient(self._app(NO_PERMS)).get('/reports/reading-stats')
        assert resp.status_code == 403

    def test_stats_scoped_to_requesting_user(self):
        stats = {
            'signed_today': 2,
            'avg_tat_seconds': {'stat': None},
            'stat_compliance_pct': None,
            'trend': [],
            'feedback_received': 1,
        }
        with patch('api.reports.Reports') as reports_cls:
            reports = AsyncMock()
            reports.reading_stats = AsyncMock(return_value=stats)
            reports_cls.return_value = reports
            with _conn():
                resp = TestClient(self._app()).get(
                    '/reports/reading-stats?days=14')
        assert resp.status_code == 200
        kwargs = reports.reading_stats.await_args.kwargs
        assert kwargs['user_id'] == '50'
        assert kwargs['days'] == 14
        assert resp.json()['data']['signed_today'] == 2

    def test_reading_stats_runs_aggregate_queries(self):
        captured = []

        async def fake_fetch(q, *a):
            captured.append(q)
            return []

        async def fake_fetchval(q, *a):
            captured.append(q)
            return 0

        async def fake_fetchrow(q, *a):
            captured.append(q)
            return {'stat': None, 'urgent': None, 'routine': None,
                    'stat_total': 0, 'stat_within_sla': 0}

        with _conn(fetch=fake_fetch, fetchval=fake_fetchval,
                   fetchrow=fake_fetchrow):
            resp = TestClient(self._app()).get('/reports/reading-stats')
        assert resp.status_code == 200
        data = resp.json()['data']
        assert data['signed_today'] == 0
        assert 'feedback_received' in data
        joined = ' '.join(captured)
        assert 'signed_by' in joined
        assert 'review_feedback' in joined
        assert 'GROUP BY' in joined or 'group by' in joined


class TestTeachingFiles:
    """R-11/RES-03: teaching file library — POST /teaching-files submits a
    completed case from the reading console (REPORT_WRITE); GET lists the
    curated library with modality/body-part/diagnosis/difficulty filters."""

    def _app(self, user=None):
        from api.reports import (
            TeachingFilesHandler, TeachingFileHandler,
        )
        return Starlette(
            routes=[
                Route('/teaching-files',
                      endpoint=TeachingFilesHandler,
                      methods=['GET', 'POST']),
                Route('/teaching-files/{id}',
                      endpoint=TeachingFileHandler),
            ],
            middleware=[Middleware(_FakeAuth, user=user or RAD)],
            exception_handlers={
                HTTPException: _http_exception,
                _ValidationException: validation_exception_handler,
            },
        )

    def test_create_requires_report_write(self):
        resp = TestClient(self._app(READ_ONLY)).post('/teaching-files', json={})
        assert resp.status_code == 403

    def test_list_requires_report_read(self):
        resp = TestClient(self._app(NO_PERMS)).get('/teaching-files')
        assert resp.status_code == 403

    def test_create_rejects_bad_difficulty(self):
        async def fake_fetchrow(q, *a):
            if 'FROM exams' in q:
                return _exam_row(status='completed')
            return None
        with _conn(fetchrow=fake_fetchrow):
            resp = TestClient(self._app()).post('/teaching-files', json={
                'exam_id': 'exam-1', 'title': 'Case',
                'difficulty': 'impossible',
            })
        assert resp.status_code in (400, 422)

    def test_create_success_audits_submission(self):
        async def fake_fetchrow(q, *a):
            if 'FROM exams' in q:
                return _exam_row(status='completed')
            return {'id': 'tf-1'}

        with patch('api.reports.AuditLog') as audit_cls, \
             _conn(fetchrow=fake_fetchrow):
            audit = AsyncMock()
            audit.log_event = AsyncMock()
            audit_cls.return_value = audit

            class FakeTF:
                def __init__(self, c):
                    pass

                async def create(self, data):
                    data['id'] = 'tf-1'
                    return data

                async def get(self, tf_id):
                    return {'id': tf_id}

            with patch('api.reports.TeachingFiles', FakeTF):
                resp = TestClient(self._app()).post('/teaching-files', json={
                    'exam_id': 'exam-1', 'title': 'Classic CT head',
                    'diagnosis': 'Subdural hematoma',
                    'difficulty': 'easy',
                })
        assert resp.status_code == 201
        assert resp.json()['data']['title'] == 'Classic CT head'
        assert audit.log_event.await_args.kwargs['event_type'] == \
            'teaching.submitted'

    def test_list_passes_filters(self):
        seen = {}

        class FakeTF:
            def __init__(self, c):
                pass

            async def list_files(self, **kw):
                seen.update(kw)
                return []

        with patch('api.reports.TeachingFiles', FakeTF), _conn():
            resp = TestClient(self._app()).get(
                '/teaching-files?modality=CT&body_part=Head&difficulty=easy')
        assert resp.status_code == 200
        assert seen['modality'] == 'CT'
        assert seen['body_part'] == 'Head'
        assert seen['difficulty'] == 'easy'

    def test_get_detail_not_found(self):
        class FakeTF:
            def __init__(self, c):
                pass

            async def get(self, tf_id):
                return None

        with patch('api.reports.TeachingFiles', FakeTF), _conn():
            resp = TestClient(self._app()).get('/teaching-files/nope')
        assert resp.status_code == 404
