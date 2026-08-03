from contextlib import contextmanager
from unittest.mock import AsyncMock, MagicMock, patch

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
    from api.exams import (
        ExamsHandler, ExamHandler, ExamIdentityHandler, ExamProtocolHandler,
        ExamAcquisitionsHandler, ExamAcquisitionDecisionHandler, ExamDoseHandler,
        ExamSafetyHandler, ExamCompleteHandler, ExamIncidentsHandler,
        ExamOverridesHandler, ProtocolsHandler,
    )
    return Starlette(
        routes=[
            Route('/exams', endpoint=ExamsHandler),
            Route('/exams/{id}', endpoint=ExamHandler),
            Route('/exams/{id}/identity-confirm', endpoint=ExamIdentityHandler),
            Route('/exams/{id}/protocol', endpoint=ExamProtocolHandler),
            Route('/exams/{id}/acquisitions', endpoint=ExamAcquisitionsHandler),
            Route('/exams/{id}/acquisitions/{aid}/{decision}', endpoint=ExamAcquisitionDecisionHandler),
            Route('/exams/{id}/dose', endpoint=ExamDoseHandler),
            Route('/exams/{id}/safety-checks', endpoint=ExamSafetyHandler),
            Route('/exams/{id}/complete', endpoint=ExamCompleteHandler),
            Route('/exams/{id}/incidents', endpoint=ExamIncidentsHandler),
            Route('/exams/{id}/overrides', endpoint=ExamOverridesHandler),
            Route('/protocols', endpoint=ProtocolsHandler),
        ],
        middleware=[Middleware(_FakeAuth, user=user)],
        exception_handlers={
            HTTPException: _http_exception,
            _ValidationException: validation_exception_handler,
        },
    )


TECH = User({'id': 42, 'permissions': ['EXAM_READ', 'EXAM_WRITE', 'WORKLIST_READ', 'WORKLIST_WRITE']})
READ_ONLY = User({'id': 43, 'permissions': ['EXAM_READ']})
NO_PERMS = User({'id': 44, 'permissions': []})


@contextmanager
def _audit_ok():
    """Patch AuditLog so every instance's log_event is an awaitable no-op."""
    with patch('api.exams.AuditLog') as audit_cls:
        audit_cls.return_value.log_event = AsyncMock()
        yield


@contextmanager
def _conn(fetchrow=None, fetch=None, fetchval=None):
    """Provide a fake async context-manager connection with optional handlers."""
    conn = AsyncMock()
    if fetchrow is not None:
        conn.fetchrow = fetchrow
    if fetch is not None:
        conn.fetch = fetch
    if fetchval is not None:
        conn.fetchval = fetchval
    conn.__aenter__ = AsyncMock(return_value=conn)
    conn.__aexit__ = AsyncMock(return_value=False)
    with patch('api.exams.get_conn', return_value=conn):
        yield conn


class TestExamPermissions:
    def test_list_requires_exam_read(self):
        client = TestClient(_make_app(NO_PERMS))
        resp = client.get('/exams')
        assert resp.status_code == 403

    def test_create_requires_exam_write(self):
        client = TestClient(_make_app(READ_ONLY))
        resp = client.post('/exams', json={'patient_id': 'P001'})
        assert resp.status_code == 403


class TestExamCreate:
    def test_create_requires_identity(self):
        client = TestClient(_make_app(TECH))
        with _audit_ok():
            resp = client.post('/exams', json={})
        assert resp.status_code == 422

    def test_create_success(self):
        client = TestClient(_make_app(TECH))
        with patch('api.exams.Exams') as mock_exams_cls, _audit_ok():
            mock_exams = AsyncMock()
            mock_exams.create.return_value = {
                'id': 'exam-uuid', 'patient_id': 'P001',
                'accession_number': 'ACC1', 'modality': 'CT', 'priority': 'stat',
            }
            mock_exams_cls.return_value = mock_exams
            with _conn():
                resp = client.post('/exams', json={
                    'patient_id': 'P001',
                    'patient_name': 'Test^Patient',
                    'modality': 'CT',
                    'priority': 'stat',
                })
        assert resp.status_code == 201
        data = resp.json()['data']
        assert data['id'] == 'exam-uuid'
        assert data['priority'] == 'stat'

    def test_create_adopts_worklist_entry(self):
        client = TestClient(_make_app(TECH))
        with patch('api.exams.Exams') as mock_exams_cls, _audit_ok():
            mock_exams = AsyncMock()
            mock_exams.create.return_value = {'id': 'exam-uuid'}
            mock_exams_cls.return_value = mock_exams
            async def fake_fetchrow(q, *a):
                if 'worklist_entries' in q:
                    return {'patient_id': 'P001', 'patient_name': 'A^B',
                            'accession_number': 'ACC9', 'modality': 'MR'}
                return None  # no exam already adopted from this entry
            with _conn(fetchrow=fake_fetchrow):
                resp = client.post('/exams', json={'worklist_entry_id': 'wl-1'})
        assert resp.status_code == 201
        kwargs = mock_exams.create.await_args.args[0]
        assert kwargs['patient_id'] == 'P001'
        assert kwargs['assigned_technologist'] == '42'

    def test_create_rejects_duplicate_adoption(self):
        """A worklist entry already adopted into an exam cannot be adopted again."""
        client = TestClient(_make_app(TECH))
        async def fake_fetchrow(q, *a):
            if 'worklist_entries' in q:
                return {'patient_id': 'P001', 'accession_number': 'ACC1'}
            return {'id': 'existing-exam'}  # already adopted
        with _conn(fetchrow=fake_fetchrow), _audit_ok():
            resp = client.post('/exams', json={'worklist_entry_id': 'wl-1'})
        assert resp.status_code == 400
        assert 'already adopted' in resp.json()['error']


class TestExamDetail:
    def test_get_returns_lifecycle_bundle(self):
        client = TestClient(_make_app(TECH))
        async def fake_fetchrow(q, *a):
            return {'id': 'e1', 'patient_id': 'P1', 'accession_number': 'A1'}
        async def fake_fetch(q, *a):
            return []
        with _conn(fetchrow=fake_fetchrow, fetch=fake_fetch):
            resp = client.get('/exams/e1')
        assert resp.status_code == 200
        body = resp.json()['data']
        assert body['id'] == 'e1'
        assert body['acquisitions'] == []
        assert body['dose'] is not None
        assert body['benchmark_dlp'] is None
        assert body['dose_level'] == 'ok'

    def test_get_includes_benchmark_and_level(self):
        """Detail response carries ACR benchmark + dose level for the console."""
        client = TestClient(_make_app(TECH))
        async def fake_fetchrow(q, *a):
            if 'protocols' in q:
                return {'name': 'CT Head (Routine)', 'acr_benchmark_dlp': 1300.0}
            return {'id': 'e1', 'patient_id': 'P1', 'protocol_name': 'CT Head (Routine)'}
        async def fake_fetch(q, *a):
            return []
        with _conn(fetchrow=fake_fetchrow, fetch=fake_fetch):
            resp = client.get('/exams/e1')
        assert resp.status_code == 200
        body = resp.json()['data']
        assert body['benchmark_dlp'] == 1300.0
        assert body['dose_level'] == 'ok'

    def test_get_404(self):
        client = TestClient(_make_app(TECH))
        with _conn(fetchrow=AsyncMock(return_value=None)):
            resp = client.get('/exams/nope')
        assert resp.status_code == 404


class TestExamIdentity:
    def test_confirm_updates_status(self):
        client = TestClient(_make_app(TECH))
        async def fake_fetchrow(q, *a):
            return {'id': 'e1', 'status': 'ready'}
        with _conn(fetchrow=fake_fetchrow), _audit_ok():
            resp = client.post('/exams/e1/identity-confirm', json={'confirmed': True})
        assert resp.status_code == 200
        assert resp.json()['data']['confirmed'] is True


class TestExamAcquisitions:
    def test_record_acquisition(self):
        client = TestClient(_make_app(TECH))
        async def fake_fetchrow(q, *a):
            if q.startswith('SELECT * FROM exams'):
                return {'id': 'e1'}
            return {'id': 'acq-1', 'exam_id': 'e1', 'dlp': 520.0, 'ctdivol': 12.5}
        with _conn(fetchrow=fake_fetchrow), _audit_ok():
            resp = client.post('/exams/e1/acquisitions', json={
                'series_number': 1, 'description': 'Axial Diagnostic',
                'kvp': 120, 'mas': 210, 'dlp': 520.0, 'ctdivol': 12.5,
            })
        assert resp.status_code == 201
        assert resp.json()['data']['id'] == 'acq-1'

    def test_reject_acquisition(self):
        client = TestClient(_make_app(TECH))
        async def fake_fetchrow(q, *a):
            if 'exams' in q:
                return {'id': 'e1'}
            return {'id': 'acq-1', 'exam_id': 'e1'}
        with _conn(fetchrow=fake_fetchrow, fetchval=AsyncMock(return_value=1)), _audit_ok():
            resp = client.post('/exams/e1/acquisitions/acq-1/reject', json={
                'reason': 'Patient motion',
            })
        assert resp.status_code == 200
        data = resp.json()['data']
        assert data['status'] == 'rejected'
        assert data['rejected_count'] == 1


class TestExamDose:
    def test_dose_levels(self):
        client = TestClient(_make_app(TECH))
        async def fake_fetchrow(q, *a):
            if 'exams' in q:
                return {'id': 'e1', 'protocol_name': 'CT Head (Routine)'}
            if 'protocols' in q:
                return {'name': 'CT Head (Routine)', 'acr_benchmark_dlp': 1300.0}
            return {'total_dlp': 1200.0, 'total_ctdivol': 28.0,
                    'total_mas': 0.0, 'total_exposure': 0.0}
        with _conn(fetchrow=fake_fetchrow):
            resp = client.get('/exams/e1/dose')
        assert resp.status_code == 200
        data = resp.json()['data']
        assert data['benchmark_dlp'] == 1300.0
        assert data['level'] == 'warning'  # 1200/1300 ≈ 0.92 → warning


class TestExamComplete:
    def test_complete_requires_dose_and_sequences(self):
        client = TestClient(_make_app(TECH))
        with _conn():
            resp = client.post('/exams/e1/complete', json={})
        assert resp.status_code == 400

    def test_complete_success(self):
        client = TestClient(_make_app(TECH))
        async def fake_fetchrow(q, *a):
            return {'id': 'e1', 'accession_number': 'ACC1',
                    'worklist_entry_id': 'wl-1', 'patient_name': 'A^B',
                    'modality': 'CT'}
        with _conn(fetchrow=fake_fetchrow), _audit_ok(), \
             patch('api.exams._notify_role', new_callable=AsyncMock):
            resp = client.post('/exams/e1/complete', json={
                'dose_recorded': True, 'sequences_complete': True,
            })
        assert resp.status_code == 200
        assert resp.json()['data']['status'] == 'completed'


class TestExamIncidents:
    def test_incident_high_notifies_qa(self):
        client = TestClient(_make_app(TECH))
        async def fake_fetchrow(q, *a):
            if 'exams' in q:
                return {'id': 'e1'}
            return {'id': 'inc-1', 'severity': 'critical'}
        with _conn(fetchrow=fake_fetchrow), _audit_ok(), \
             patch('api.exams._notify_role', new_callable=AsyncMock) as notify:
            resp = client.post('/exams/e1/incidents', json={
                'incident_type': 'contrast_reaction',
                'severity': 'critical',
                'description': 'Patient reacted to contrast',
            })
        assert resp.status_code == 201
        assert resp.json()['data']['severity'] == 'critical'
        assert notify.await_count == 1


class TestExamOverrides:
    def test_override_requires_justification(self):
        client = TestClient(_make_app(TECH))
        with _conn():
            resp = client.post('/exams/e1/overrides', json={})
        assert resp.status_code == 422

    def test_override_success(self):
        client = TestClient(_make_app(TECH))
        async def fake_fetchrow(q, *a):
            if 'exams' in q:
                return {'id': 'e1', 'protocol_name': 'CT Head (Routine)'}
            if 'protocols' in q:
                return {'parameters': {'kVp': 120, 'mAs': 340}}
            return {'id': 'ov-1', 'justification': 'Trauma patient',
                    'original_params': {'kVp': 120, 'mAs': 340},
                    'overridden_params': {'mAs': 120}}
        with _conn(fetchrow=fake_fetchrow), _audit_ok():
            resp = client.post('/exams/e1/overrides', json={
                'justification': 'Trauma patient - skipping contrast phase',
                'overridden_parameters': {'mAs': 120},
            })
        assert resp.status_code == 201
        assert resp.json()['data']['justification'].startswith('Trauma')


class TestProtocols:
    def test_protocols_list(self):
        client = TestClient(_make_app(TECH))
        async def fake_fetchval(q, *a):
            return 1  # already seeded
        async def fake_fetch(q, *a):
            return [{'name': 'CT Head (Routine)', 'modality': 'CT'}]
        with _conn(fetchval=fake_fetchval, fetch=fake_fetch):
            resp = client.get('/protocols')
        assert resp.status_code == 200
        assert resp.json()['data'][0]['name'] == 'CT Head (Routine)'
