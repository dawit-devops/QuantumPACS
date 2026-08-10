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
        ExamAssignHandler,
        ReportTemplatesHandler, PeerReviewReviewersHandler, PeerReviewsHandler,
        PeerReviewHandler, PeerReviewSubmitHandler,
    )
    return Starlette(
        routes=[
            Route('/reports/reading-list', endpoint=ReadingListHandler),
            Route('/reports/reading-list/{exam_id}/assign', endpoint=ExamAssignHandler),
            Route('/reports/templates', endpoint=ReportTemplatesHandler),
            Route('/reports/{exam_id}', endpoint=ExamReportHandler),
            Route('/reports/{exam_id}/sign', endpoint=ExamReportSignHandler),
            Route('/peer-reviews/reviewers', endpoint=PeerReviewReviewersHandler),
            Route('/peer-reviews', endpoint=PeerReviewsHandler),
            Route('/peer-reviews/{id}', endpoint=PeerReviewHandler),
            Route('/peer-reviews/{id}/submit', endpoint=PeerReviewSubmitHandler),
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
    if fetchrow is not None:
        conn.fetchrow = fetchrow
    if fetch is not None:
        conn.fetch = fetch
    if fetchval is not None:
        conn.fetchval = fetchval
    if execute is not None:
        conn.execute = execute
    conn.__aenter__ = AsyncMock(return_value=conn)
    conn.__aexit__ = AsyncMock(return_value=False)
    with patch('api.reports.get_conn', return_value=conn):
        yield conn


def _exam_row(exam_id='exam-1', status='completed', priority='stat'):
    return {
        'id': exam_id, 'status': status, 'priority': priority,
        'patient_id': 'P1', 'patient_name': 'A^B',
        'accession_number': 'ACC1', 'modality': 'CT',
        'protocol_name': 'CT Head (Routine)', 'completed_at': None,
        'assigned_technologist': '',
    }


def _report_row(report_id='rep-1', exam_id='exam-1', status='draft', impression='', created_by='50', signed_by=''):
    return {
        'id': report_id, 'exam_id': exam_id, 'status': status,
        'findings': 'Findings text', 'impression': impression,
        'recommendations': '', 'template_name': '', 'created_by': created_by,
        'signed_by': signed_by, 'signed_at': None, 'created_at': None, 'updated_at': None,
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
            with _conn():
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


class TestExamAssign:
    def test_assign_requires_report_write(self):
        client = TestClient(_make_app(READ_ONLY))
        resp = client.post('/reports/reading-list/exam-1/assign', json={})
        assert resp.status_code == 403

    def test_assign_defaults_to_requesting_user(self):
        """An empty radiologist_id assigns the exam to the requesting user."""
        client = TestClient(_make_app(RAD))
        async def fake_fetchrow(q, *a):
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
                fetchrow=lambda q, *a: _exam_row(status='completed')), _audit_ok():
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

    def test_put_requires_report_write(self):
        client = TestClient(_make_app(READ_ONLY))
        resp = client.put('/reports/exam-1', json={'findings': 'x'})
        assert resp.status_code == 403


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

    def test_sign_requires_report_sign_permission(self):
        client = TestClient(_make_app(READ_ONLY))
        resp = client.post('/reports/exam-1/sign', json={'confirm': True})
        assert resp.status_code == 403


class TestReportTemplates:
    def test_templates_seed_and_list(self):
        client = TestClient(_make_app(RAD))
        async def fake_fetchval(q, *a):
            return 0  # not seeded -> seed then list
        async def fake_fetch(q, *a):
            return [{'name': 'CT Head — Routine', 'modality': 'CT'}]
        with _conn(fetchval=fake_fetchval, fetch=fake_fetch, execute=AsyncMock()):
            resp = client.get('/reports/templates')
        assert resp.status_code == 200
        assert resp.json()['data'][0]['name'] == 'CT Head — Routine'


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
