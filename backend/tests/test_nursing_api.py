"""API tests for §2.11 nursing endpoints (N-01..N-04 + prep-list).

Gate contract (G3 decisions): reads pass any-of [NURSING_READ, EXAM_READ]
(spec N-04 — tech/radiologist see records through EXAM_READ), writes are
strictly NURSING_WRITE, and every write is audited under `nursing.*`.
Handlers derive patient_id from the exam row — never trust the client.
"""
from unittest.mock import AsyncMock, MagicMock, patch

from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.routing import Route
from starlette.testclient import TestClient

from api.auth import User
from api.nursing import (
    ConsentHandler,
    NurseNotesHandler,
    NursingPrepListHandler,
    PrepChecklistHandler,
    VitalsHandler,
)
from api.validate import validation_exception_handler, _ValidationException

EXAM_ROW = {'id': 'e-1', 'patient_id': 'P-1', 'patient_name': 'Jane Doe',
            'modality': 'CT', 'status': 'ready'}


class _FakeAuth(BaseHTTPMiddleware):
    def __init__(self, app, user=None):
        super().__init__(app)
        self._user = user

    async def dispatch(self, request, call_next):
        request.scope['user'] = self._user
        request.scope['auth'] = None
        return await call_next(request)


def _http_exception(request, exc):
    from starlette.responses import JSONResponse

    return JSONResponse({'error': exc.detail}, status_code=exc.status_code)


def _make_app(routes, user):
    return Starlette(
        routes=routes,
        middleware=[Middleware(_FakeAuth, user=user)],
        exception_handlers={
            HTTPException: _http_exception,
            _ValidationException: validation_exception_handler,
        },
    )


def _conn_ctx(mock_conn):
    return patch(
        'api.nursing.get_conn',
        return_value=MagicMock(
            __aenter__=AsyncMock(return_value=mock_conn),
            __aexit__=AsyncMock(return_value=None),
        ),
    )


def _patch_exam(side_effect_row=EXAM_ROW):
    mock_exams = MagicMock()
    if side_effect_row is None:
        mock_exams.get = AsyncMock(return_value=None)
    else:
        mock_exams.get = AsyncMock(return_value=side_effect_row)
    return (
        patch('api.nursing.Exams', return_value=mock_exams),
        mock_exams,
    )


def _patch_audit():
    mock_audit = MagicMock()
    mock_audit.log_event = AsyncMock()
    return patch('api.nursing.AuditLog', return_value=mock_audit), mock_audit


READER = lambda: User({'id': 3, 'permissions': ['EXAM_READ']})  # noqa: E731
WRITER = lambda: User({'id': 2, 'permissions': [  # noqa: E731
    'NURSING_READ', 'NURSING_WRITE', 'EXAM_READ']})
OUTSIDER = lambda: User({'id': 4, 'permissions': ['PATIENT_READ']})  # noqa: E731


class TestVitalsEndpoint:
    def _app(self, user):
        return _make_app(
            [Route('/exams/{id}/vitals', endpoint=VitalsHandler)], user,
        )

    def test_get_visible_with_exam_read_only(self):
        """Spec N-04 visibility: EXAM_READ alone passes the read gate."""
        mock_conn = MagicMock()
        mock_conn.fetch = AsyncMock(return_value=[{'id': 'v1'}])
        pe, _ = _patch_exam()
        with pe, _conn_ctx(mock_conn):
            client = TestClient(self._app(READER()))
            resp = client.get('/exams/e-1/vitals')
        assert resp.status_code == 200
        assert resp.json()['data'] == [{'id': 'v1'}]

    def test_get_denied_without_nursing_or_exam_read(self):
        mock_conn = MagicMock()
        pe, _ = _patch_exam()
        with pe, _conn_ctx(mock_conn):
            client = TestClient(self._app(OUTSIDER()))
            resp = client.get('/exams/e-1/vitals')
        assert resp.status_code == 403

    def test_post_requires_nursing_write(self):
        mock_conn = MagicMock()
        pe, _ = _patch_exam()
        pa, _ = _patch_audit()
        with pe, pa, _conn_ctx(mock_conn):
            client = TestClient(self._app(READER()))
            resp = client.post('/exams/e-1/vitals', json={'spo2': 97})
        assert resp.status_code == 403

    def test_post_records_vitals_with_server_timestamp(self):
        mock_conn = MagicMock()
        mock_conn.fetchrow = AsyncMock(return_value={'id': 'v9'})
        pe, exams = _patch_exam()
        pa, audit = _patch_audit()
        with pe, pa, _conn_ctx(mock_conn):
            client = TestClient(self._app(WRITER()))
            resp = client.post(
                '/exams/e-1/vitals',
                json={
                    'bp_systolic': 118, 'bp_diastolic': 76, 'heart_rate': 70,
                    'spo2': 99, 'temperature_c': 36.6, 'respiration': 14,
                    'weight_kg': 72.5, 'height_cm': 180,
                },
            )
        assert resp.status_code == 201
        assert exams.get.await_args.args[0] == 'e-1'
        event = audit.log_event.await_args.kwargs['event_type']
        assert event == 'nursing.vitals_recorded'

    def test_post_rejects_physiologically_implausible_values(self):
        mock_conn = MagicMock()
        pe, _ = _patch_exam()
        with pe, _conn_ctx(mock_conn):
            client = TestClient(self._app(WRITER()))
            resp = client.post('/exams/e-1/vitals', json={'spo2': 140})
        assert resp.status_code == 422

    def test_missing_exam_returns_404(self):
        mock_conn = MagicMock()
        pe, _ = _patch_exam(side_effect_row=None)
        with pe, _conn_ctx(mock_conn):
            client = TestClient(self._app(WRITER()))
            resp = client.post('/exams/nope/vitals', json={'spo2': 97})
        assert resp.status_code == 404


class TestPrepChecklistEndpoint:
    def _app(self, user):
        return _make_app(
            [Route('/exams/{id}/pre-procedure-checklist',
                   endpoint=PrepChecklistHandler)],
            user,
        )

    def _patches(self, existing=None):
        mock_conn = MagicMock()
        mock_checklists = MagicMock()

        async def get_or_create(**kwargs):
            return existing or {
                'id': 'c1', 'items': [
                    {'key': 'allergy_verification', 'label': 'Allergy verification',
                     'required': True, 'checked': False},
                    {'key': 'id_band_verified', 'label': 'ID band verified',
                     'required': True, 'checked': False},
                ],
                'status': 'in_progress',
            }

        mock_checklists.get_or_create = AsyncMock(side_effect=get_or_create)
        mock_checklists.update_items = AsyncMock(
            return_value={'id': 'c1', 'status': 'in_progress'})
        mock_checklists.confirm = AsyncMock(
            return_value={'id': 'c1', 'status': 'complete'})
        return (
            patch('api.nursing.PrepChecklists', return_value=mock_checklists),
            mock_checklists,
            mock_conn,
        )

    def test_get_seeds_and_returns_checklist(self):
        p, _, conn = self._patches()
        pe, _ = _patch_exam()
        with pe, p, _conn_ctx(conn):
            client = TestClient(self._app(WRITER()))
            resp = client.get('/exams/e-1/pre-procedure-checklist')
        assert resp.status_code == 200
        assert resp.json()['data']['status'] == 'in_progress'

    def test_put_confirm_blocked_until_required_items_checked(self):
        p, checklists, conn = self._patches()
        pe, _ = _patch_exam()
        with pe, p, _conn_ctx(conn):
            client = TestClient(self._app(WRITER()))
            resp = client.put(
                '/exams/e-1/pre-procedure-checklist',
                json={
                    'items': [
                        {'key': 'allergy_verification', 'label': 'Allergy verification',
                         'required': True, 'checked': True},
                    ],
                    'confirmed': True,
                },
            )
        assert resp.status_code == 400
        # The unmet item was NOT in the payload — the merge against the
        # stored checklist must still catch it (live-smoke regression: a
        # partial echo used to confirm with the rest unchecked).
        assert 'ID band verified' in resp.json()['error']['message']
        checklists.confirm.assert_not_awaited()

    def test_put_confirm_persists_merged_items(self):
        p, checklists, conn = self._patches()
        pe, _ = _patch_exam()
        pa, audit = _patch_audit()
        with pe, pa, p, _conn_ctx(conn):
            client = TestClient(self._app(WRITER()))
            resp = client.put(
                '/exams/e-1/pre-procedure-checklist',
                json={
                    'items': [
                        {'key': 'allergy_verification', 'label': 'Allergy verification',
                         'required': True, 'checked': True},
                        {'key': 'id_band_verified', 'label': 'ID band verified',
                         'required': True, 'checked': True},
                    ],
                    'confirmed': True,
                },
            )
        assert resp.status_code == 200
        checklists.update_items.assert_awaited_once()
        merged = checklists.update_items.await_args.args[1]
        assert len(merged) == 2 and all(i['checked'] for i in merged)
        checklists.confirm.assert_awaited_once()

    def test_put_confirm_succeeds_when_required_items_checked(self):
        p, checklists, conn = self._patches()
        pe, _ = _patch_exam()
        pa, audit = _patch_audit()
        with pe, pa, p, _conn_ctx(conn):
            client = TestClient(self._app(WRITER()))
            resp = client.put(
                '/exams/e-1/pre-procedure-checklist',
                json={
                    'items': [
                        {'key': 'allergy_verification', 'label': 'Allergy verification',
                         'required': True, 'checked': True},
                        {'key': 'id_band_verified', 'label': 'ID band verified',
                         'required': True, 'checked': True},
                    ],
                    'confirmed': True,
                },
            )
        assert resp.status_code == 200
        checklists.confirm.assert_awaited_once()
        event = audit.log_event.await_args.kwargs['event_type']
        assert event == 'nursing.checklist_confirmed'


class TestConsentAndNotesEndpoints:
    def _app(self, user):
        return _make_app([
            Route('/exams/{id}/consent', endpoint=ConsentHandler),
            Route('/exams/{id}/nurse-notes', endpoint=NurseNotesHandler),
        ], user)

    def test_consent_accept_stores_signature(self):
        mock_conn = MagicMock()
        mock_consents = MagicMock()
        mock_consents.create = AsyncMock(return_value={'id': 'k1'})
        pe, _ = _patch_exam()
        pa, audit = _patch_audit()
        sig = 'data:image/png;base64,' + 'A' * 100
        with (
            pe, pa, _conn_ctx(mock_conn),
            patch('api.nursing.ContrastConsents', return_value=mock_consents),
        ):
            client = TestClient(self._app(WRITER()))
            resp = client.post(
                '/exams/e-1/consent',
                json={'accepted': True, 'signature_png': sig,
                      'consent_text_version': 'v1'},
            )
        assert resp.status_code == 201
        event = audit.log_event.await_args.kwargs['event_type']
        assert event == 'nursing.consent_signed'

    def test_consent_accept_requires_png_signature(self):
        mock_conn = MagicMock()
        mock_consents = MagicMock()
        mock_consents.create = AsyncMock()
        pe, _ = _patch_exam()
        with (
            pe, _conn_ctx(mock_conn),
            patch('api.nursing.ContrastConsents', return_value=mock_consents),
        ):
            client = TestClient(self._app(WRITER()))
            resp = client.post(
                '/exams/e-1/consent', json={'accepted': True},
            )
        assert resp.status_code == 422
        mock_consents.create.assert_not_awaited()

    def test_consent_decline_requires_reason(self):
        mock_conn = MagicMock()
        mock_consents = MagicMock()
        mock_consents.create = AsyncMock()
        pe, _ = _patch_exam()
        with (
            pe, _conn_ctx(mock_conn),
            patch('api.nursing.ContrastConsents', return_value=mock_consents),
        ):
            client = TestClient(self._app(WRITER()))
            resp = client.post(
                '/exams/e-1/consent',
                json={'accepted': False, 'declined_reason': ''},
            )
        assert resp.status_code == 422

    def test_note_add_audited(self):
        mock_conn = MagicMock()
        mock_notes = MagicMock()
        mock_notes.add = AsyncMock(return_value={'id': 'n1'})
        pe, _ = _patch_exam()
        pa, audit = _patch_audit()
        with (
            pe, pa, _conn_ctx(mock_conn),
            patch('api.nursing.ExamNotes', return_value=mock_notes),
        ):
            client = TestClient(self._app(WRITER()))
            resp = client.post(
                '/exams/e-1/nurse-notes',
                json={'note': 'Patient prepped, IV in place.'},
            )
        assert resp.status_code == 201
        event = audit.log_event.await_args.kwargs['event_type']
        assert event == 'nursing.note_added'

    def test_note_write_blocked_from_read_only_holder(self):
        mock_conn = MagicMock()
        pe, _ = _patch_exam()
        with pe, _conn_ctx(mock_conn):
            client = TestClient(self._app(READER()))
            resp = client.post(
                '/exams/e-1/nurse-notes', json={'note': 'x'},
            )
        assert resp.status_code == 403


class TestPrepListEndpoint:
    def _app(self, user):
        return _make_app(
            [Route('/nursing/prep-list', endpoint=NursingPrepListHandler)],
            user,
        )

    def test_gated_on_nursing_read_only(self):
        mock_conn = MagicMock()
        mock_conn.fetch = AsyncMock(return_value=[])
        # EXAM_READ must NOT unlock the standalone nursing worklist — it is
        # the coordinator/nurse surface, not an acquisition surface.
        with _conn_ctx(mock_conn):
            client = TestClient(self._app(READER()))
            resp = client.get('/nursing/prep-list')
        assert resp.status_code == 403

    def test_lists_todays_exams_with_checklist_state(self):
        mock_conn = MagicMock()
        mock_conn.fetch = AsyncMock(return_value=[
            {'exam_id': 'e-1', 'patient_name': 'Jane Doe', 'modality': 'CT',
             'checklist_status': 'in_progress'},
        ])
        with _conn_ctx(mock_conn):
            client = TestClient(self._app(WRITER()))
            resp = client.get('/nursing/prep-list')
        assert resp.status_code == 200
        assert resp.json()['data'][0]['exam_id'] == 'e-1'
