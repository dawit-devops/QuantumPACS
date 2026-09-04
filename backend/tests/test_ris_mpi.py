"""S3-11 — MPI: trigram fuzzy search, merge flow, undo, audit.

Spec §4.1 patients API + §5.1 MPI: fuzzy search by name (pg_trgm similarity),
merge two patient records (surviving + merged), undo merge, and audit every
mutation. The PATIENT_MERGE permission gates merge/undo endpoints.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.routing import Route
from starlette.testclient import TestClient

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


def _conn_ctx():
    conn = AsyncMock()
    conn.__aenter__ = AsyncMock(return_value=conn)
    conn.__aexit__ = AsyncMock(return_value=False)
    return conn


def _patient_row(patient_id='MRN-001', name='Jane Doe'):
    return {
        'id': 1, 'patient_id': patient_id, 'name': name,
        'birth_date': '1980-01-01', 'sex': 'F', 'meta': None,
        'tenant_id': 'default',
    }


def _make_app(user=None):
    from api.frontdesk import (
        RisPatientsMergeHandler, RisPatientsUndoMergeHandler,
        RisPatientEligibilityHandler,
    )
    return Starlette(
        routes=[
            Route('/ris/patients/merge', endpoint=RisPatientsMergeHandler, methods=['POST']),
            Route('/ris/patients/undo-merge', endpoint=RisPatientsUndoMergeHandler, methods=['POST']),
            Route('/ris/patients/{id}/eligibility', endpoint=RisPatientEligibilityHandler),
        ],
        middleware=[Middleware(_FakeAuth, user=user)],
        exception_handlers={
            HTTPException: _http_exception,
            _ValidationException: validation_exception_handler,
        },
    )


@pytest.fixture
def mpi_patches():
    patchers = [
        patch('api.frontdesk.get_conn'),
        patch('api.frontdesk.FrontDesk'),
        patch('api.frontdesk.AuditLog'),
    ]
    started = [p.start() for p in patchers]
    yield {
        'get_conn': started[0],
        'FrontDesk': started[1],
        'AuditLog': started[2],
    }
    for p in patchers:
        p.stop()


def _fd(mpi_patches):
    fd = AsyncMock()
    mpi_patches['FrontDesk'].return_value = fd
    return fd


# ── Fuzzy Search ─────────────────────────────────────────────────────────

class TestFuzzySearch:
    """S3-11 — pg_trgm fuzzy search for probable MPI matches.

    These test the FrontDesk DB layer directly; the API layer doesn't
    expose fuzzy search as a standalone endpoint (it's used internally
    by MPI duplicate detection).
    """

    @pytest.mark.asyncio
    async def test_fuzzy_search_returns_scored_results(self):
        from db.frontdesk import FrontDesk
        conn = AsyncMock()
        conn.fetch.return_value = [
            {'id': 1, 'patient_id': 'MRN-001', 'name': 'Jane Doe',
             'birth_date': '1980-01-01', 'sex': 'F', 'sim': 0.85},
        ]
        fd = FrontDesk(conn)
        results = await fd.search_patients_fuzzy('jane doe', threshold=0.3)

        assert len(results) == 1
        assert results[0]['sim'] == 0.85

    @pytest.mark.asyncio
    async def test_fuzzy_search_filters_by_threshold(self):
        from db.frontdesk import FrontDesk
        conn = AsyncMock()
        conn.fetch.return_value = []
        fd = FrontDesk(conn)
        results = await fd.search_patients_fuzzy('xyz', threshold=0.5)
        assert results == []


# ── Merge ────────────────────────────────────────────────────────────────

class TestMergePatients:
    """S3-11 — POST /ris/patients/merge: merge two patient records."""

    def test_merge_combines_surviving_and_merged(self, mpi_patches):
        fd = _fd(mpi_patches)
        fd.get_patient.side_effect = [
            _patient_row('MRN-001', 'Jane Doe'),
            _patient_row('MRN-002', 'Jane M. Doe'),
        ]
        fd.merge_patients.return_value = {
            'surviving_patient_id': 'MRN-001',
            'merged_patient_id': 'MRN-002',
        }
        audit_instance = AsyncMock()
        mpi_patches['AuditLog'].return_value = audit_instance

        client = TestClient(_make_app(User({'id': 1, 'permissions': ['PATIENT_MERGE']})))
        resp = client.post('/ris/patients/merge', json={
            'surviving_patient_id': 'MRN-001',
            'merged_patient_id': 'MRN-002',
            'reason': 'Duplicate MPI entry',
        })

        assert resp.status_code == 200
        data = resp.json()['data']
        assert data['surviving_patient_id'] == 'MRN-001'
        assert data['merged_patient_id'] == 'MRN-002'
        fd.merge_patients.assert_awaited_once_with(
            'MRN-001', 'MRN-002', reason='Duplicate MPI entry',
        )

    def test_merge_requires_patient_merge_permission(self, mpi_patches):
        client = TestClient(_make_app(User({'id': 1, 'permissions': []})))
        resp = client.post('/ris/patients/merge', json={
            'surviving_patient_id': 'MRN-001',
            'merged_patient_id': 'MRN-002',
        })
        assert resp.status_code == 403

    def test_merge_surviving_patient_not_found(self, mpi_patches):
        fd = _fd(mpi_patches)
        fd.get_patient.return_value = None

        client = TestClient(_make_app(User({'id': 1, 'permissions': ['PATIENT_MERGE']})))
        resp = client.post('/ris/patients/merge', json={
            'surviving_patient_id': 'NOPE',
            'merged_patient_id': 'MRN-002',
        })
        assert resp.status_code == 404

    def test_merge_merged_patient_not_found(self, mpi_patches):
        fd = _fd(mpi_patches)
        fd.get_patient.side_effect = [
            _patient_row('MRN-001'),
            None,  # merged patient doesn't exist
        ]

        client = TestClient(_make_app(User({'id': 1, 'permissions': ['PATIENT_MERGE']})))
        resp = client.post('/ris/patients/merge', json={
            'surviving_patient_id': 'MRN-001',
            'merged_patient_id': 'NOPE',
        })
        assert resp.status_code == 404

    def test_merge_same_patient_rejected(self, mpi_patches):
        fd = _fd(mpi_patches)
        fd.get_patient.return_value = _patient_row('MRN-001')

        client = TestClient(_make_app(User({'id': 1, 'permissions': ['PATIENT_MERGE']})))
        resp = client.post('/ris/patients/merge', json={
            'surviving_patient_id': 'MRN-001',
            'merged_patient_id': 'MRN-001',
        })
        assert resp.status_code == 400
        assert resp.json()['error']['code'] == 'SAME_PATIENT'

    def test_merge_audits_the_action(self, mpi_patches):
        fd = _fd(mpi_patches)
        fd.get_patient.side_effect = [
            _patient_row('MRN-001'),
            _patient_row('MRN-002'),
        ]
        fd.merge_patients.return_value = {
            'surviving_patient_id': 'MRN-001',
            'merged_patient_id': 'MRN-002',
        }
        audit_instance = AsyncMock()
        mpi_patches['AuditLog'].return_value = audit_instance

        client = TestClient(_make_app(User({'id': 1, 'permissions': ['PATIENT_MERGE']})))
        client.post('/ris/patients/merge', json={
            'surviving_patient_id': 'MRN-001',
            'merged_patient_id': 'MRN-002',
            'reason': 'MPI cleanup',
        })

        audit_instance.log_event.assert_awaited_once()
        call_kwargs = audit_instance.log_event.call_args.kwargs
        assert call_kwargs['event_type'] == 'mpi.patient_merged'
        assert call_kwargs['details']['surviving_patient_id'] == 'MRN-001'
        assert call_kwargs['details']['merged_patient_id'] == 'MRN-002'


# ── Undo Merge ───────────────────────────────────────────────────────────

class TestUndoMerge:
    """S3-11 — POST /ris/patients/undo-merge: revert a previous merge."""

    def test_undo_merge_restores_patient(self, mpi_patches):
        fd = _fd(mpi_patches)
        fd.get_patient.return_value = _patient_row('MRN-002')
        fd.undo_merge.return_value = {
            'patient_id': 'MRN-002',
            'status': 'active',
        }
        audit_instance = AsyncMock()
        mpi_patches['AuditLog'].return_value = audit_instance

        client = TestClient(_make_app(User({'id': 1, 'permissions': ['PATIENT_MERGE']})))
        resp = client.post('/ris/patients/undo-merge', json={
            'patient_id': 'MRN-002',
            'reason': 'Incorrect merge',
        })

        assert resp.status_code == 200
        assert resp.json()['data']['status'] == 'active'
        fd.undo_merge.assert_awaited_once_with('MRN-002', reason='Incorrect merge')

    def test_undo_merge_requires_permission(self, mpi_patches):
        client = TestClient(_make_app(User({'id': 1, 'permissions': []})))
        resp = client.post('/ris/patients/undo-merge', json={
            'patient_id': 'MRN-002',
        })
        assert resp.status_code == 403

    def test_undo_merge_patient_not_found(self, mpi_patches):
        fd = _fd(mpi_patches)
        fd.get_patient.return_value = None

        client = TestClient(_make_app(User({'id': 1, 'permissions': ['PATIENT_MERGE']})))
        resp = client.post('/ris/patients/undo-merge', json={
            'patient_id': 'NOPE',
        })
        assert resp.status_code == 404

    def test_undo_merge_audits(self, mpi_patches):
        fd = _fd(mpi_patches)
        fd.get_patient.return_value = _patient_row('MRN-002')
        fd.undo_merge.return_value = {'patient_id': 'MRN-002', 'status': 'active'}
        audit_instance = AsyncMock()
        mpi_patches['AuditLog'].return_value = audit_instance

        client = TestClient(_make_app(User({'id': 1, 'permissions': ['PATIENT_MERGE']})))
        client.post('/ris/patients/undo-merge', json={
            'patient_id': 'MRN-002', 'reason': 'Wrong merge',
        })

        audit_instance.log_event.assert_awaited_once()
        call_kwargs = audit_instance.log_event.call_args.kwargs
        assert call_kwargs['event_type'] == 'mpi.patient_unmerged'
        assert call_kwargs['details']['patient_id'] == 'MRN-002'


# ── DB Layer ─────────────────────────────────────────────────────────────

class TestFrontDeskMPI:
    """S3-11 — FrontDesk DB methods: merge, undo."""

    @pytest.mark.asyncio
    async def test_merge_patients_sets_meta(self):
        from db.frontdesk import FrontDesk
        conn = AsyncMock()
        conn.transaction = MagicMock()
        conn.transaction.return_value.__aenter__ = AsyncMock(return_value=conn)
        conn.transaction.return_value.__aexit__ = AsyncMock(return_value=None)
        fd = FrontDesk(conn)
        await fd.merge_patients('MRN-001', 'MRN-002', reason='Duplicate')

        # Should execute two updates inside a transaction: set merged_into
        # on merged patient, set active=false on merged patient
        conn.transaction.assert_called_once()
        assert conn.execute.await_count == 2
        calls = conn.execute.call_args_list
        # First call: set merged_into
        assert 'merged_into' in calls[0].args[0]
        # Second call: set active=false
        assert 'active' in calls[1].args[0]

    @pytest.mark.asyncio
    async def test_undo_merge_clears_meta(self):
        from db.frontdesk import FrontDesk
        conn = AsyncMock()
        conn.transaction = MagicMock()
        conn.transaction.return_value.__aenter__ = AsyncMock(return_value=conn)
        conn.transaction.return_value.__aexit__ = AsyncMock(return_value=None)
        fd = FrontDesk(conn)
        await fd.undo_merge('MRN-002', reason='Wrong merge')

        conn.transaction.assert_called_once()
        assert conn.execute.await_count == 2
        calls = conn.execute.call_args_list
        # Should remove merged_into and set active=true
        call_sql = ' '.join(c.args[0] for c in calls)
        assert 'merged_into' in call_sql
        assert 'active' in call_sql


class TestHl7MergePropagation:
    """B3 (GAP_AUDIT_TDD_PIPELINE.md): the HL7 A40/A06 merge only stamped
    meta.merged_into + deactivated the loser — orders, appointments and
    worklist entries kept referencing the merged-away MRN, so schedulers
    and techs lost sight of live work (plan S3-12 acceptance: 'merges
    propagate'). The merge must re-point RIS references in one transaction
    and audit the counts."""

    @pytest.fixture(autouse=True)
    async def setup_db(self):
        from db.conn import database
        try:
            await database.setup()
        except Exception:
            pytest.skip('dev database unavailable')
        yield
        await database.close()

    @pytest.mark.asyncio
    async def test_merge_repoints_orders_appointments_worklist(self):
        import uuid
        from db.conn import get_conn

        tag = uuid.uuid4().hex[:6]
        loser = f'MRN-B3-L-{tag}'
        survivor = f'MRN-B3-S-{tag}'
        async with get_conn() as conn:
            from db.patient import Patient as PatientModel
            pmodel = PatientModel(conn)
            for mrn in (survivor, loser):
                await pmodel.insert_or_select({
                    'patient_id': mrn,
                    'patient_name': f'Patient {mrn}',
                    'patient_birth_date': '1990-01-01',
                    'patient_sex': 'F',
                })
            order_row = await conn.fetchrow(
                "INSERT INTO ris_orders (tenant_id, patient_id,"
                " accession_number) VALUES ('default', $1, $2)"
                " RETURNING id",
                loser, f'ACC-B3-{tag}',
            )
            appt_row = await conn.fetchrow(
                "INSERT INTO ris_appointments (tenant_id, patient_id,"
                " start_time, end_time)"
                " VALUES ('default', $1, now() + interval '1 day',"
                " now() + interval '1 day 30 minutes') RETURNING id",
                loser,
            )
            entry_row = await conn.fetchrow(
                "INSERT INTO worklist_entries (patient_id, patient_name,"
                " accession_number, status) VALUES ($1, 'L Patient', $2,"
                " 'scheduled') RETURNING id",
                loser, f'ACC-B3-W-{tag}',
            )
            try:
                from services.ingestion.hl7_server import _merge_patients

                ok = await _merge_patients(
                    survivor,
                    {'patient_name': 'S Patient', 'birth_date': '1990-01-01',
                     'sex': 'F'},
                    loser,
                )
                assert ok, 'merge reported failure'

                order_pid = await conn.fetchval(
                    'SELECT patient_id FROM ris_orders WHERE id = $1',
                    order_row['id'])
                assert order_pid == survivor, (
                    'ris_orders must re-point to the surviving MRN')

                appt_pid = await conn.fetchval(
                    'SELECT patient_id FROM ris_appointments WHERE id = $1',
                    appt_row['id'])
                assert appt_pid == survivor, (
                    'ris_appointments must re-point to the surviving MRN')

                entry_pid = await conn.fetchval(
                    'SELECT patient_id FROM worklist_entries WHERE id = $1',
                    entry_row['id'])
                assert entry_pid == survivor, (
                    'worklist_entries must re-point to the surviving MRN')

                merged_into = await conn.fetchval(
                    "SELECT meta->>'merged_into' FROM patients"
                    ' WHERE patient_id = $1', loser)
                assert merged_into == survivor
                active = await conn.fetchval(
                    "SELECT meta->>'active' FROM patients"
                    ' WHERE patient_id = $1', loser)
                assert active == 'false'

                audited = await conn.fetchval(
                    "SELECT 1 FROM logs WHERE log::jsonb->>'event' ="
                    " 'mpi.hl7_merged'"
                    " AND log::jsonb->'detail'->>'orders' IS NOT NULL"
                    ' LIMIT 1')
                assert audited, (
                    'merge propagation must be audited with re-point counts')
            finally:
                await conn.execute(
                    'DELETE FROM ris_appointments WHERE patient_id = $1',
                    survivor)
                await conn.execute(
                    'DELETE FROM ris_orders WHERE accession_number = $1',
                    f'ACC-B3-{tag}')
                await conn.execute(
                    'DELETE FROM worklist_entries WHERE accession_number = $1',
                    f'ACC-B3-W-{tag}')
                for mrn in (survivor, loser):
                    await conn.execute(
                        'DELETE FROM patients WHERE patient_id = $1', mrn)
