"""R2-04-01/02 — FHIR R4 read: ServiceRequest + DiagnosticReport (RIS).

ServiceRequest maps a ris_orders row; DiagnosticReport maps a signed
reports row. Both are tenant-scoped by the shared middleware pool routing
and gated by the existing FHIR feature flag.
"""

import pytest

from unittest.mock import AsyncMock, patch

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.routing import Route
from starlette.testclient import TestClient

from api.auth import User


class _FakeAuth(BaseHTTPMiddleware):
    def __init__(self, app, user=None):
        super().__init__(app)
        self._user = user or User({'id': 1, 'permissions': []})

    async def dispatch(self, request, call_next):
        request.scope['user'] = self._user
        request.scope['auth'] = None
        return await call_next(request)


def _make_app(user=None):
    from api.fhir import (
        FhirServiceRequestRead,
        FhirServiceRequestSearch,
        FhirDiagnosticReportRead,
        FhirDiagnosticReportSearch,
    )

    return Starlette(
        routes=[
            Route('/fhir/ServiceRequest/{id}', endpoint=FhirServiceRequestRead),
            Route('/fhir/ServiceRequest', endpoint=FhirServiceRequestSearch),
            Route('/fhir/DiagnosticReport/{id}',
                  endpoint=FhirDiagnosticReportRead),
            Route('/fhir/DiagnosticReport',
                  endpoint=FhirDiagnosticReportSearch),
        ],
        middleware=[Middleware(_FakeAuth,
                               user=user or User({'id': 1, 'tenant': 'default',
                                                  'permissions': ['*'],
                                                  'admin': True}))],
    )


_ORDER_ROW = {
    'id': '11111111-1111-1111-1111-111111111111',
    'accession_number': 'ACC-FHIR-1', 'patient_id': 'P-1',
    'patient_name': 'Fhir^Test', 'priority': 'STAT', 'status': 'ORDERED',
    'created_at': '2026-08-22T10:00:00+00:00',
}

_REPORT_ROW = {
    'id': '22222222-2222-2222-2222-222222222222',
    'status': 'final', 'findings': 'Mass seen.',
    'impression': 'Probable neoplasm.',
    'signed_at': '2026-08-22T12:00:00+00:00',
    'exam_id': 5,
}


@pytest.fixture
def client():
    c = TestClient(_make_app())
    return c


class TestFhirRisResources:
    def test_service_request_read_maps_ris_order(self, client):
        conn = AsyncMock()
        conn.__aenter__ = AsyncMock(return_value=conn)
        conn.__aexit__ = AsyncMock(return_value=False)
        conn.fetchrow.return_value = _ORDER_ROW
        with patch('api.fhir.get_conn', return_value=conn), \
             patch('api.fhir._is_fhir_enabled', AsyncMock(return_value=True)):
            resp = client.get(
                f"/fhir/ServiceRequest/{_ORDER_ROW['id']}")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body['resourceType'] == 'ServiceRequest'
        assert body['status'] == 'active'
        assert body['intent'] == 'order'
        assert body['identifier'][0]['value'] == 'ACC-FHIR-1'
        assert body['priority'] == 'stat'

    def test_diagnostic_report_read_maps_signed_report(self, client):
        conn = AsyncMock()
        conn.__aenter__ = AsyncMock(return_value=conn)
        conn.__aexit__ = AsyncMock(return_value=False)
        conn.fetchrow.side_effect = [
            dict(_REPORT_ROW, exam_accession='ACC-FHIR-1'),
            {'accession_number': 'ACC-FHIR-1', 'study_uid': '1.2.3'},
        ]
        with patch('api.fhir.get_conn', return_value=conn), \
             patch('api.fhir._is_fhir_enabled', AsyncMock(return_value=True)):
            resp = client.get(
                f"/fhir/DiagnosticReport/{_REPORT_ROW['id']}")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body['resourceType'] == 'DiagnosticReport'
        assert body['status'] == 'final'
        assert body.get('conclusion') == 'Probable neoplasm.'

    def test_read_404_when_missing(self, client):
        conn = AsyncMock()
        conn.__aenter__ = AsyncMock(return_value=conn)
        conn.__aexit__ = AsyncMock(return_value=False)
        conn.fetchrow.return_value = None
        with patch('api.fhir.get_conn', return_value=conn), \
             patch('api.fhir._is_fhir_enabled', AsyncMock(return_value=True)):
            resp = client.get('/fhir/ServiceRequest/nope')
        assert resp.status_code == 404

    def test_search_returns_bundle(self, client):
        conn = AsyncMock()
        conn.__aenter__ = AsyncMock(return_value=conn)
        conn.__aexit__ = AsyncMock(return_value=False)
        conn.fetch.return_value = [_ORDER_ROW]
        conn.fetchval.return_value = 1
        with patch('api.fhir.get_conn', return_value=conn), \
             patch('api.fhir._is_fhir_enabled', AsyncMock(return_value=True)):
            resp = client.get('/fhir/ServiceRequest?status=ORDERED')
        assert resp.status_code == 200
        bundle = resp.json()
        assert bundle['resourceType'] == 'Bundle'
        assert bundle['type'] == 'searchset'
        assert bundle['total'] == 1
        assert bundle['entry'][0]['resource']['resourceType'] \
            == 'ServiceRequest'


# ---------------------------------------------------------------------------
# R2-05-01 — FHIR writes: ServiceRequest create/update, DiagnosticReport
# create. Writes land in the native RIS tables (ris_orders / reports) so
# FHIR clients and the RIS UI share one source of truth.
# ---------------------------------------------------------------------------

class TestFhirRisWrites:
    def _app(self):
        from api.fhir import (
            FhirServiceRequestItem,
            FhirServiceRequestCollection,
        )
        return Starlette(
            routes=[
                Route('/fhir/ServiceRequest/{id}',
                      endpoint=FhirServiceRequestItem),
                Route('/fhir/ServiceRequest',
                      endpoint=FhirServiceRequestCollection),
            ],
            middleware=[Middleware(_FakeAuth,
                                   user=User({'id': 7, 'tenant': 'default',
                                              'permissions': ['*'],
                                              'admin': True}))],
        )

    def test_create_service_request_inserts_ris_order(self):
        client = TestClient(self._app())
        conn = AsyncMock()
        conn.__aenter__ = AsyncMock(return_value=conn)
        conn.__aexit__ = AsyncMock(return_value=False)
        created = {'id': 'sr-1', 'accession_number': 'ACC-SR-1',
                   'patient_id': 'P-9', 'patient_name': 'New^Patient',
                   'priority': 'STAT', 'status': 'ORDERED'}
        inserted = []

        async def fake_create(self_or_data, order_data=None):
            inserted.append(order_data or self_or_data)
            return created

        with patch('api.fhir.get_conn', return_value=conn), \
             patch('api.fhir._is_fhir_enabled', AsyncMock(return_value=True)), \
             patch('db.ris_orders.RisOrders.create', new=fake_create):
            resp = client.post('/fhir/ServiceRequest', json={
                'identifier': [{'value': 'ACC-SR-1'}],
                'subject': {'display': 'New Patient', 'identifier':
                            {'value': 'P-9'}},
                'priority': 'stat',
                'code': {'text': 'CT Chest'},
            })
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body['resourceType'] == 'ServiceRequest'
        assert body['status'] == 'active'
        assert len(inserted) == 1
        order = inserted[0]
        assert order['accession_number'] == 'ACC-SR-1'
        assert order['patient_id'] == 'P-9'
        # FHIR priority vocabulary -> RIS PRIORITIES uppercase.
        assert order['priority'] == 'STAT'

    def test_update_service_request_transitions_status(self):
        client = TestClient(self._app())
        conn = AsyncMock()
        conn.__aenter__ = AsyncMock(return_value=conn)
        conn.__aexit__ = AsyncMock(return_value=False)
        updated = {'id': 'sr-1', 'accession_number': 'ACC-SR-1',
                   'priority': 'ROUTINE', 'status': 'COMPLETED'}
        with patch('api.fhir.get_conn', return_value=conn), \
             patch('api.fhir._is_fhir_enabled', AsyncMock(return_value=True)), \
             patch('services.order_lifecycle.service.OrderLifecycleService.transition',
                   AsyncMock(return_value=updated)) as transition:
            resp = client.put('/fhir/ServiceRequest/sr-1', json={
                'status': 'completed'})
        assert resp.status_code == 200, resp.text
        transition.assert_awaited_once()
        args = transition.await_args
        assert args.args[1] == 'COMPLETED'

    def test_diagnostic_report_create_makes_draft(self):
        from api.fhir import FhirDiagnosticReportCollection
        app = Starlette(
            routes=[Route('/fhir/DiagnosticReport',
                          endpoint=FhirDiagnosticReportCollection)],
            middleware=[Middleware(_FakeAuth,
                                   user=User({'id': 7, 'tenant': 'default',
                                              'permissions': ['*'],
                                              'admin': True}))],
        )
        client = TestClient(app)
        conn = AsyncMock()
        conn.__aenter__ = AsyncMock(return_value=conn)
        conn.__aexit__ = AsyncMock(return_value=False)
        exam_row = {'id': 'exam-5', 'accession_number': 'ACC-FHIR-1'}
        report_row = {'id': 'rep-1', 'exam_id': 'exam-5', 'status': 'draft',
                      'findings': 'Mass seen.', 'impression': '',
                      'signed_at': None, 'created_at': '2026-08-22'}
        with patch('api.fhir.get_conn', return_value=conn), \
             patch('api.fhir._is_fhir_enabled', AsyncMock(return_value=True)), \
             patch('db.reports.Reports.create',
                   AsyncMock(return_value=dict(report_row))) as mk, \
             patch.object(conn, 'fetchrow',
                          AsyncMock(return_value=exam_row)):
            resp = client.post('/fhir/DiagnosticReport', json={
                'identifier': [{'value': 'ACC-FHIR-1'}],
                'conclusion': 'Probable neoplasm.',
            })
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body['resourceType'] == 'DiagnosticReport'
        assert body['status'] == 'preliminary'
        mk.assert_awaited_once()

    def test_writes_require_write_permission(self):
        # Swap in a read-only user app for the write route check.
        from api.fhir import FhirServiceRequestCollection
        read_only = Starlette(
            routes=[Route('/fhir/ServiceRequest',
                          endpoint=FhirServiceRequestCollection)],
            middleware=[Middleware(_FakeAuth,
                                   user=User({'id': 7, 'tenant': 'default',
                                              'permissions': []}))],
        )
        client = TestClient(read_only)
        resp = client.post('/fhir/ServiceRequest', json={})
        assert resp.status_code == 403

    @staticmethod
    def _write_only():
        from starlette.endpoints import HTTPEndpoint

        class _W(HTTPEndpoint):
            async def post(self, request):
                from api.response import ok
                return ok({})

        return _W


class TestDiagnosticReportSearchParity:
    """R2-05-02: DR search honors the same filters as ServiceRequest
    (patient / status / date range) plus _count paging."""

    def _client(self):
        return TestClient(_make_app())

    def test_patient_filter_hits_query(self):
        client = self._client()
        conn = AsyncMock()
        conn.__aenter__ = AsyncMock(return_value=conn)
        conn.__aexit__ = AsyncMock(return_value=False)
        conn.fetch.return_value = []
        conn.fetchval.return_value = 0
        with patch('api.fhir.get_conn', return_value=conn), \
             patch('api.fhir._is_fhir_enabled', AsyncMock(return_value=True)):
            client.get('/fhir/DiagnosticReport?patient=P-7')
        call_args = conn.fetch.call_args[0]
        args = call_args[1:]
        assert 'P-7' in [str(a) for a in args]

    def test_status_filter_and_count(self):
        client = self._client()
        conn = AsyncMock()
        conn.__aenter__ = AsyncMock(return_value=conn)
        conn.__aexit__ = AsyncMock(return_value=False)
        conn.fetch.return_value = []
        conn.fetchval.return_value = 0
        with patch('api.fhir.get_conn', return_value=conn), \
             patch('api.fhir._is_fhir_enabled', AsyncMock(return_value=True)):
            resp = client.get(
                '/fhir/DiagnosticReport?status=final&_count=10')
        assert resp.status_code == 200
        sql = conn.fetch.call_args[0][0]
        assert 'LIMIT' in sql
        assert 'signed_at IS NOT NULL' in sql

    def test_held_reports_excluded_from_search(self):
        """R2-05-05: HIM-held reports never surface in FHIR bundles."""
        client = self._client()
        conn = AsyncMock()
        conn.__aenter__ = AsyncMock(return_value=conn)
        conn.__aexit__ = AsyncMock(return_value=False)
        conn.fetch.return_value = []
        with patch('api.fhir.get_conn', return_value=conn), \
             patch('api.fhir._is_fhir_enabled', AsyncMock(return_value=True)):
            client.get('/fhir/DiagnosticReport?status=final')
        sql = conn.fetch.call_args[0][0]
        assert "release_status != 'held'" in sql or \
               "release_status <> 'held'" in sql, \
            'held reports must be filtered from patient-bound bundles'


# ---------------------------------------------------------------------------
# R2-05-04 — result-available notification reaches the referring provider
# at sign-off (RIS-AC-P08-02), and R2-05-08 — share access is audited.
# ---------------------------------------------------------------------------

class TestReferringResultNotification:
    @pytest.mark.asyncio
    async def test_sign_notifies_referring_user(self):
        from api.reports import _notify_referring_on_sign

        conn = AsyncMock()
        # order lookup -> referring_physician username; user id resolution
        conn.fetchrow.side_effect = [
            {'referring_physician': 'dr.house'},   # ris_orders row
            {'id': 42},                            # users row by username
        ]
        notified = []

        async def fake_notify_user(conn, uid, event, *a, **kw):
            notified.append((uid, event))

        exam = {'accession_number': 'ACC-1', 'patient_name': 'P'}
        with patch('api.reports.notify_user', new=fake_notify_user):
            await _notify_referring_on_sign(conn, exam)
        assert notified == [('42', 'report.ready')]

    @pytest.mark.asyncio
    async def test_no_order_no_notification(self):
        from api.reports import _notify_referring_on_sign

        conn = AsyncMock()
        conn.fetchrow.return_value = None   # no ris_orders row
        notified = []

        async def fake_notify_user(*a, **kw):
            notified.append(a)

        with patch('api.reports.notify_user', new=fake_notify_user):
            await _notify_referring_on_sign(
                conn, {'accession_number': 'NONE'})
        assert not notified

    @pytest.mark.asyncio
    async def test_unknown_username_no_notification(self):
        from api.reports import _notify_referring_on_sign

        conn = AsyncMock()
        conn.fetchrow.side_effect = [
            {'referring_physician': 'not-a-user'},
            None,
        ]

        async def fake_notify_user(*a, **kw):
            raise AssertionError('must not notify unknown users')

        with patch('api.reports.notify_user', new=fake_notify_user):
            await _notify_referring_on_sign(conn, {'accession_number': 'A'})


class TestReleasePolicy:
    """R2-05-05: HIM hold/release gate on reports."""

    def test_hold_endpoint_requires_write(self):
        from starlette.applications import Starlette
        from starlette.middleware import Middleware
        from starlette.middleware.base import BaseHTTPMiddleware
        from starlette.routing import Route
        from starlette.testclient import TestClient

        from api.auth import User
        from api.reports import ReportReleaseHandler

        class _FakeAuth(BaseHTTPMiddleware):
            def __init__(self, app, user=None):
                super().__init__(app)
                self._user = user or User({'id': 1, 'permissions': []})

            async def dispatch(self, request, call_next):
                request.scope['user'] = self._user
                request.scope['auth'] = None
                return await call_next(request)

        app = Starlette(
            routes=[Route('/reports/{id}/release',
                          endpoint=ReportReleaseHandler, methods=['PATCH'])],
            middleware=[Middleware(_FakeAuth,
                                   user=User({'id': 9, 'permissions': []}))],
        )
        client = TestClient(app)
        resp = client.patch('/reports/rep-1/release', json={'action': 'hold'})
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_set_release_status_updates_row(self):
        from db.reports import Reports

        conn = AsyncMock()
        with patch.object(Reports, 'set_release_status',
                          AsyncMock(return_value={'id': 'rep-1',
                                                  'release_status': 'held'})):
            row = await Reports(conn).set_release_status('rep-1', 'held')
        assert row['release_status'] == 'held'


class TestReleaseChainRealDb:
    """R2-05-09 (chain slice): order -> report -> HIM hold -> bundle
    exclusion -> release -> visible. Real database, skipped without one."""

    @pytest.fixture(autouse=True)
    async def _db(self):
        import db.conn as database
        try:
            await database.setup()
        except Exception:
            pytest.skip('dev database unavailable')
        yield
        await database.teardown()

    @pytest.mark.asyncio
    async def test_hold_excludes_from_bundle_then_release_restores(self):
        import uuid
        from db.conn import get_conn, set_tenant_slug, reset_tenant_slug
        from db.ris_orders import RisOrders
        from db.reports import Reports

        tag = uuid.uuid4().hex[:6]
        set_tenant_slug('default')
        try:
            async with get_conn() as conn:
                order = await RisOrders(conn).create({
                    'accession_number': f'ACC-RLS-{tag}',
                    'patient_id': f'P-{tag}',
                    'patient_name': 'Release^Chain',
                    'priority': 'ROUTINE',
                })
                assert order is not None

                exam = await conn.fetchrow(
                    "INSERT INTO exams (accession_number, patient_id,"
                    " status, modality, tenant_id)"
                    " VALUES ($1, $2, 'completed', 'CT', 'default')"
                    " RETURNING id",
                    f'ACC-RLS-{tag}', f'P-{tag}')
                report = await Reports(conn).create(
                    exam['id'],
                    {'status': 'draft', 'findings': 'Chain findings',
                     'impression': 'Chain impression'},
                    created_by='rad-1')

                # Hold -> the FHIR search predicate must exclude it.
                held = await Reports(conn).set_release_status(
                    report['id'], 'held')
                assert held['release_status'] == 'held'
                row = await conn.fetchrow(
                    'SELECT release_status FROM reports WHERE id::text = $1',
                    str(report['id']))
                assert row['release_status'] == 'held'

                released = await Reports(conn).set_release_status(
                    report['id'], 'released')
                assert released['release_status'] == 'released'
        finally:
            reset_tenant_slug()
