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
    from api.qa import (
        QAQueueHandler, QAReviewHandler, QAProtocolsHandler, QAProtocolHandler,
        QAIncidentsHandler, QAIncidentHandler, QACorrectiveActionsHandler,
        QACorrectiveActionHandler, QADashboardHandler, QAReviewersHandler,
    )
    return Starlette(
        routes=[
            Route('/qa/queue', endpoint=QAQueueHandler),
            Route('/qa/reviews/{exam_id}', endpoint=QAReviewHandler),
            Route('/qa/reviews', endpoint=QAReviewHandler, methods=['POST']),
            Route('/qa/protocols', endpoint=QAProtocolsHandler),
            Route('/qa/protocols/{id}', endpoint=QAProtocolHandler),
            Route('/qa/incidents', endpoint=QAIncidentsHandler),
            Route('/qa/incidents/{id}/resolve', endpoint=QAIncidentHandler),
            Route('/qa/corrective-actions', endpoint=QACorrectiveActionsHandler),
            Route('/qa/corrective-actions/{id}/resolve', endpoint=QACorrectiveActionHandler),
            Route('/qa/dashboard', endpoint=QADashboardHandler),
            Route('/qa/reviewers', endpoint=QAReviewersHandler),
        ],
        middleware=[Middleware(_FakeAuth, user=user)],
        exception_handlers={
            HTTPException: _http_exception,
            _ValidationException: validation_exception_handler,
        },
    )


QA = User({'id': 10, 'permissions': [
    'QA_READ', 'QA_WRITE', 'PROTOCOL_MANAGE', 'EXAM_READ',
]})
READ_ONLY = User({'id': 11, 'permissions': ['QA_READ', 'EXAM_READ']})
NO_PERMS = User({'id': 12, 'permissions': []})


@contextmanager
def _audit_ok():
    with patch('api.qa.AuditLog') as audit_cls:
        audit_cls.return_value.log_event = AsyncMock()
        yield audit_cls


def _fake_exam(exam_id='exam-1', **over):
    row = {
        'id': exam_id,
        'worklist_entry_id': None, 'patient_id': 'MRN1',
        'patient_name': 'QA^Test', 'patient_birth_date': '19900101',
        'patient_sex': 'F', 'accession_number': 'ACC001',
        'requested_procedure_desc': 'CT Head', 'modality': 'CT',
        'station_ae_title': 'CT1', 'priority': 'routine',
        'protocol_name': 'CT Head (Routine)', 'status': 'completed',
        'assigned_technologist': '7', 'identity_confirmed_at': None,
        'started_at': None, 'completed_at': None, 'created_by': '7',
        'created_at': None, 'updated_at': None,
    }
    row.update(over)
    return row


class _FakeExams:
    def __init__(self, conn=None):
        self.conn = conn

    async def get(self, exam_id):
        return _fake_exam(exam_id)

    async def create(self, data):
        return _fake_exam(data.get('patient_id'), **data)


def _score_row(exam_id='exam-1', pass_fail='pass'):
    return {
        'id': 'score-1', 'exam_id': exam_id, 'protocol_id': None,
        'pass_fail': pass_fail, 'discrepancy_level': 'none',
        'dose_dlp': 100, 'dose_ctdivol': 5, 'dose_kvp': 120, 'dose_mas': 200,
        'sequence_compliance': {'Axial': True}, 'comments': 'ok',
        'reviewed_by': '10', 'reviewed_at': None, 'created_at': None,
    }


def test_qa_requires_permission():
    app = _make_app(NO_PERMS)
    with TestClient(app) as client:
        r = client.get('/qa/queue')
        assert r.status_code == 403


def test_qa_queue_empty_for_missing_perms_handled():
    app = _make_app(QA)
    with TestClient(app) as client:
        with patch('api.qa.get_conn') as gc:
            conn = gc.return_value.__aenter__.return_value
            conn.fetch = AsyncMock(return_value=[])
            r = client.get('/qa/queue')
            assert r.status_code == 200
            body = r.json()
            assert body['data'] == []
            assert body['meta']['total'] == 0


def test_qa_queue_sorts_stat_first_and_filters():
    app = _make_app(QA)
    rows = [
        {'exam_id': 'e-routine', 'patient_id': 'M1', 'patient_name': 'R',
         'accession_number': 'ACC1', 'modality': 'CT', 'priority': 'routine',
         'qa_status': None, 'completed_at': None},
        {'exam_id': 'e-stat', 'patient_id': 'M2', 'patient_name': 'S',
         'accession_number': 'ACC2', 'modality': 'CT', 'priority': 'stat',
         'qa_status': None, 'completed_at': None},
        {'exam_id': 'e-mr', 'patient_id': 'M3', 'patient_name': 'M',
         'accession_number': 'ACC3', 'modality': 'MR', 'priority': 'routine',
         'qa_status': None, 'completed_at': None},
    ]
    with TestClient(app) as client:
        with patch('api.qa.get_conn') as gc:
            conn = gc.return_value.__aenter__.return_value
            conn.fetch = AsyncMock(return_value=rows)
            r = client.get('/qa/queue?modality=CT')
            body = r.json()
            ids = [e['exam_id'] for e in body['data']]
            assert ids == ['e-stat', 'e-routine']
            assert body['meta']['total'] == 2
            r2 = client.get('/qa/queue?status=completed')
            assert r2.status_code == 200


def test_qa_review_get_returns_exam_score_protocol():
    app = _make_app(QA)
    with TestClient(app) as client:
        with patch('api.qa.get_conn') as gc:
            conn = gc.return_value.__aenter__.return_value
            conn.fetchrow = AsyncMock(return_value=None)  # no protocol row
            with patch('api.qa.Exams', _FakeExams), \
                 patch('api.qa.QaScores') as qs:
                qs.return_value.get_by_exam = AsyncMock(return_value=None)
                r = client.get('/qa/reviews/exam-1')
                assert r.status_code == 200
                body = r.json()['data']
                assert body['exam']['accession_number'] == 'ACC001'
                assert body['score'] is None


def test_qa_review_submit_persists_score():
    app = _make_app(QA)
    with TestClient(app) as client:
        with patch('api.qa.get_conn') as gc:
            conn = gc.return_value.__aenter__.return_value
            conn.fetchrow = AsyncMock(return_value=None)
            with patch('api.qa.Exams', _FakeExams), \
                 patch('api.qa.QaScores') as qs, \
                 patch('api.qa.CorrectiveActions') as ca, \
                 _audit_ok():
                qs.return_value.get_by_exam = AsyncMock(return_value=None)
                qs.return_value.create = AsyncMock(return_value=_score_row())
                ca.return_value.create = AsyncMock(return_value={'id': 'ca1'})
                r = client.post('/qa/reviews', json={
                    'exam_id': 'exam-1', 'pass_fail': 'pass',
                    'discrepancy_level': 'none', 'comments': 'good',
                })
                assert r.status_code == 201
                assert r.json()['data']['pass_fail'] == 'pass'


def test_qa_review_rejects_duplicate():
    app = _make_app(QA)
    with TestClient(app) as client:
        with patch('api.qa.get_conn'):
            with patch('api.qa.Exams', _FakeExams), \
                 patch('api.qa.QaScores') as qs:
                qs.return_value.get_by_exam = AsyncMock(return_value=_score_row())
                r = client.post('/qa/reviews', json={
                    'exam_id': 'exam-1', 'pass_fail': 'pass',
                })
                assert r.status_code == 400
                assert 'already been QA-reviewed' in r.json()['error']['message']



def test_qa_review_fail_opens_corrective_action():
    app = _make_app(QA)
    with TestClient(app) as client:
        with patch('api.qa.get_conn'):
            with patch('api.qa.Exams', _FakeExams), \
                 patch('api.qa.QaScores') as qs, \
                 patch('api.qa.CorrectiveActions') as ca, \
                 _audit_ok():
                qs.return_value.get_by_exam = AsyncMock(return_value=None)
                qs.return_value.create = AsyncMock(return_value=_score_row(pass_fail='fail'))
                ca.return_value.create = AsyncMock(return_value={'id': 'ca1'})
                r = client.post('/qa/reviews', json={
                    'exam_id': 'exam-1', 'pass_fail': 'fail',
                    'discrepancy_level': 'major', 'comments': 'retake needed',
                })
                assert r.status_code == 201
                ca.return_value.create.assert_awaited_once()


def test_qa_protocol_create_requires_code_uniqueness():
    app = _make_app(QA)
    with TestClient(app) as client:
        with patch('api.qa.get_conn'):
            with patch('api.qa.ProtocolsQA') as pqa, _audit_ok():
                pqa.return_value.get_by_code = AsyncMock(return_value={'id': 'p1'})
                r = client.post('/qa/protocols', json={
                    'name': 'CT Head', 'protocol_code': 'CTH',
                    'modality': 'CT', 'sequences': [],
                })
                assert r.status_code == 400
                assert 'already exists' in r.json()['error']['message']


def test_qa_protocol_crud_create_update_delete():
    app = _make_app(QA)
    protocol_row = {
        'id': 'p1', 'name': 'CT Head', 'protocol_code': 'CTH',
        'modality': 'CT', 'body_part': 'Head', 'sequences': [],
        'parameters': {}, 'acr_benchmark_dlp': 1300.0,
        'acr_benchmark_ctdivol': None, 'acr_benchmark_min_snr': None,
        'is_default': True, 'updated_at': None, 'created_at': None,
    }
    with TestClient(app) as client:
        with patch('api.qa.get_conn'):
            with patch('api.qa.ProtocolsQA') as pqa, _audit_ok():
                pqa.return_value.get_by_code = AsyncMock(return_value=None)
                pqa.return_value.create = AsyncMock(return_value=protocol_row)
                r = client.post('/qa/protocols', json={
                    'name': 'CT Head', 'protocol_code': 'CTH',
                    'modality': 'CT', 'body_part': 'Head',
                    'acr_benchmark_dlp': 1300.0,
                })
                assert r.status_code == 201
                assert r.json()['data']['protocol_code'] == 'CTH'

                pqa.return_value.get = AsyncMock(return_value=protocol_row)
                pqa.return_value.update = AsyncMock(return_value={**protocol_row, 'name': 'CT Head 2'})
                r = client.put('/qa/protocols/p1', json={'name': 'CT Head 2'})
                assert r.status_code == 200
                assert r.json()['data']['name'] == 'CT Head 2'

                pqa.return_value.delete = AsyncMock()
                r = client.delete('/qa/protocols/p1')
                assert r.status_code == 200
                assert r.json()['data']['deleted'] is True


def test_qa_protocol_invalid_code_rejected():
    app = _make_app(QA)
    with TestClient(app) as client:
        r = client.post('/qa/protocols', json={
            'name': 'Bad', 'protocol_code': 'has space!', 'modality': 'CT',
        })
        assert r.status_code == 422


def test_qa_protocol_mutation_requires_protocol_manage():
    app = _make_app(READ_ONLY)
    with TestClient(app) as client:
        r = client.post('/qa/protocols', json={
            'name': 'CT Head', 'modality': 'CT',
        })
        assert r.status_code == 403


def test_qa_incident_log_and_resolve():
    app = _make_app(QA)
    incident = {
        'id': 'inc-1', 'exam_id': 'exam-1', 'incident_type': 'positioning',
        'severity': 'medium', 'description': 'misaligned', 'reported_by': '10',
        'study_uid': '', 'repeat_study_uid': '', 'status': 'open',
        'resolution_notes': '', 'created_at': None, 'resolved_at': None,
    }
    with TestClient(app) as client:
        with patch('api.qa.get_conn') as gc:
            conn = gc.return_value.__aenter__.return_value
            with patch('api.qa.Exams', _FakeExams), \
                 patch('api.qa.IncidentsQA') as iqa, _audit_ok():
                iqa.return_value.create = AsyncMock(return_value=incident)
                conn.execute = AsyncMock()
                r = client.post('/qa/incidents', json={
                    'exam_id': 'exam-1', 'incident_type': 'positioning',
                    'severity': 'medium', 'description': 'misaligned',
                })
                assert r.status_code == 201
                assert r.json()['data']['incident_type'] == 'positioning'

                iqa.return_value.mark_resolved = AsyncMock()
                conn.fetchrow = AsyncMock(return_value={'id': 'inc-1'})
                r = client.post('/qa/incidents/inc-1/resolve', json={'notes': 'fixed'})
                assert r.status_code == 200
                assert r.json()['data']['resolved'] is True


def test_qa_incident_resolve_notifies_reporter():
    """technologist review P2-2: resolving an incident notifies the author
    (reported_by) — the tech has no QA_READ, so the bell is the feedback loop."""
    app = _make_app(QA)
    with TestClient(app) as client:
        with patch('api.qa.get_conn') as gc:
            conn = gc.return_value.__aenter__.return_value
            with patch('api.qa.IncidentsQA') as iqa, _audit_ok(), \
                 patch('api.exams._notify_user') as notify:
                iqa.return_value.mark_resolved = AsyncMock()
                conn.fetchrow = AsyncMock(return_value={
                    'id': 'inc-1', 'reported_by': '37', 'incident_type': 'motion',
                    'exam_id': 'exam-1',
                })
                r = client.post('/qa/incidents/inc-1/resolve', json={'notes': 'fixed'})
                assert r.status_code == 200
                notify.assert_called_once()
                assert notify.call_args.args[1] == '37'
                assert notify.call_args.args[2] == 'incident.resolved'


def test_qa_incident_requires_exam_link():
    app = _make_app(QA)
    with TestClient(app) as client:
        # No exam_id — parse succeeds, the handler's exam-required check runs
        # before any DB access (schema validates the rest, so no pool needed).
        r = client.post('/qa/incidents', json={
            'incident_type': 'artifact', 'description': 'no exam',
        })
        assert r.status_code == 400
        assert 'exam_id is required' in r.json()['error']['message']


def test_qa_incident_invalid_type_rejected():
    app = _make_app(QA)
    with TestClient(app) as client:
        r = client.post('/qa/incidents', json={
            'exam_id': 'exam-1', 'incident_type': 'bogus', 'description': 'x',
        })
        assert r.status_code == 422


def test_qa_corrective_actions_create_list_resolve():
    app = _make_app(QA)
    action = {
        'id': 'ca1', 'source': 'R03', 'issue': 'low dose',
        'study_uids': ['1.2.3'], 'assigned_to': '10', 'status': 'open',
        'findings': '', 'actions_taken': '', 'created_by': '1',
        'created_at': None, 'resolved_at': None,
    }
    with TestClient(app) as client:
        with patch('api.qa.get_conn'):
            with patch('api.qa.CorrectiveActions') as ca, _audit_ok():
                ca.return_value.create = AsyncMock(return_value=action)
                r = client.post('/qa/corrective-actions', json={
                    'source': 'R03', 'issue': 'low dose', 'study_uids': ['1.2.3'],
                })
                assert r.status_code == 201
                assert r.json()['data']['status'] == 'open'

                ca.return_value.list = AsyncMock(return_value=[action])
                r = client.get('/qa/corrective-actions')
                assert r.status_code == 200
                assert r.json()['data'][0]['id'] == 'ca1'

                resolved = {**action, 'status': 'resolved'}
                ca.return_value.get = AsyncMock(return_value=action)
                ca.return_value.resolve = AsyncMock(return_value=resolved)
                r = client.post('/qa/corrective-actions/ca1/resolve', json={
                    'findings': 'confirmed', 'actions_taken': 'retrained',
                })
                assert r.status_code == 200
                assert r.json()['data']['status'] == 'resolved'


def test_qa_dashboard_returns_kpis():
    app = _make_app(QA)
    with TestClient(app) as client:
        with patch('api.qa.get_conn') as gc:
            conn = gc.return_value.__aenter__.return_value
            with patch('api.qa.QaScores') as qs, \
                 patch('api.qa.CorrectiveActions') as ca:
                qs.return_value.count = AsyncMock(return_value=5)
                ca.return_value.count_open = AsyncMock(return_value=2)
                conn.fetchval = AsyncMock(side_effect=[3, 80.0])
                conn.fetch = AsyncMock(return_value=[])
                r = client.get('/qa/dashboard')
                assert r.status_code == 200
                d = r.json()['data']
                assert d['exams_reviewed'] == 5
                assert d['open_actions'] == 2
                assert d['compliance_pct'] == 80.0


def test_qa_reviewers_returns_radiologists():
    app = _make_app(QA)
    with TestClient(app) as client:
        with patch('api.qa.get_conn') as gc:
            conn = gc.return_value.__aenter__.return_value
            conn.fetch = AsyncMock(return_value=[
                {'id': 50, 'username': 'dr_smith', 'role': 'radiologist'},
            ])
            r = client.get('/qa/reviewers')
            assert r.status_code == 200
            assert r.json()['data'][0]['username'] == 'dr_smith'
