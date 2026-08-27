"""Tests for B-08 Payer Contract Rates and B-09 Procedure Fee Schedule.

Uses a fake connection with captured SQL (like test_billing_api.py) and
patches get_conn. Covers list/edit/import/history for the fee schedule and
CRUD + comparison for payer contracts.
"""

from decimal import Decimal
from unittest.mock import patch

import pytest
from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.routing import Route
from starlette.testclient import TestClient

from api.auth import User
from api.permissions import Permission
from api.validate import _ValidationException, validation_exception_handler


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
    from api.billing import (
        FeeScheduleHandler, FeeScheduleUpdateHandler, FeeScheduleImportHandler,
        FeeScheduleHistoryHandler,
        PayerContractListHandler, PayerContractHandler,
        PayerContractComparisonHandler,
    )
    return Starlette(
        routes=[
            Route('/ris/billing/fee-schedule', endpoint=FeeScheduleHandler),
            Route('/ris/billing/fee-schedule/import', endpoint=FeeScheduleImportHandler,
                  methods=['POST']),
            Route('/ris/billing/fee-schedule/history/{code}', endpoint=FeeScheduleHistoryHandler),
            Route('/ris/billing/fee-schedule/{code}', endpoint=FeeScheduleUpdateHandler,
                  methods=['PUT']),
            Route('/ris/billing/contracts/comparison', endpoint=PayerContractComparisonHandler),
            Route('/ris/billing/contracts/{id}', endpoint=PayerContractHandler),
            Route('/ris/billing/contracts', endpoint=PayerContractListHandler),
        ],
        middleware=[Middleware(_FakeAuth, user=user or User({'id': 1, 'permissions': []}))],
        exception_handlers={
            HTTPException: _http_exception,
            _ValidationException: validation_exception_handler,
        },
    )


def _user(*perms):
    return User({'id': 1, 'permissions': list(perms)})


class _Conn:
    """In-memory asyncpg-like connection capturing SQL + results."""

    def __init__(self):
        self.calls = []
        self._fetch = []
        self._fetchrow = None
        self._fetchval = None

    def set_fetch(self, rows):
        self._fetch = rows

    def set_fetchrow(self, row):
        self._fetchrow = row

    def set_fetchval(self, v):
        self._fetchval = v

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def execute(self, sql, *args):
        self.calls.append(('execute', sql, args))

    async def fetch(self, sql, *args):
        self.calls.append(('fetch', sql, args))
        return self._fetch

    async def fetchrow(self, sql, *args):
        self.calls.append(('fetchrow', sql, args))
        return self._fetchrow

    async def fetchval(self, sql, *args):
        self.calls.append(('fetchval', sql, args))
        return self._fetchval


@pytest.fixture
def conn():
    return _Conn()


class TestFeeSchedule:
    """B-09: fee schedule list / edit / import / history."""

    def test_list_requires_billing_read(self, conn):
        client = TestClient(_make_app(_user()))
        with patch('api.billing.get_conn', return_value=conn):
            resp = client.get('/ris/billing/fee-schedule')
        assert resp.status_code == 403

    def test_list_returns_catalog(self, conn):
        conn.set_fetch([
            {'id': 'p1', 'procedure_code': '71250', 'description': 'CT Chest',
             'list_price': Decimal('350.00'), 'active': True},
        ])
        client = TestClient(_make_app(_user(Permission.BILLING_READ)))
        with patch('api.billing.get_conn', return_value=conn):
            resp = client.get('/ris/billing/fee-schedule?code=71250')
        assert resp.status_code == 200
        assert resp.json()['data'][0]['procedure_code'] == '71250'
        assert resp.json()['data'][0]['list_price'] == 350.0

    def test_update_requires_billing_write(self, conn):
        client = TestClient(_make_app(_user(Permission.BILLING_READ)))
        with patch('api.billing.get_conn', return_value=conn):
            resp = client.put('/ris/billing/fee-schedule/71250', json={'list_price': 400})
        assert resp.status_code == 403

    def test_update_404_when_missing(self, conn):
        conn.set_fetchrow(None)
        client = TestClient(_make_app(_user(Permission.BILLING_WRITE)))
        with patch('api.billing.get_conn', return_value=conn):
            resp = client.put('/ris/billing/fee-schedule/MISSING', json={'list_price': 400})
        assert resp.status_code == 404

    def test_update_records_history(self, conn):
        conn.set_fetchrow({'id': 'p1', 'procedure_code': '71250',
                           'description': 'CT Chest', 'list_price': Decimal('400.00'),
                           'active': True})
        client = TestClient(_make_app(_user(Permission.BILLING_WRITE)))
        with patch('api.billing.get_conn', return_value=conn):
            resp = client.put('/ris/billing/fee-schedule/71250', json={'list_price': 400})
        assert resp.status_code == 200
        assert resp.json()['data']['list_price'] == 400.0
        # The handler must issue both UPDATE and INSERT into history.
        sqls = [c[1] for c in conn.calls]
        assert any('UPDATE procedure_pricing_catalog' in s for s in sqls)
        assert any('ris_fee_schedule_history' in s for s in sqls)

    def test_import_upserts_and_histories(self, conn):
        client = TestClient(_make_app(_user(Permission.BILLING_WRITE)))
        with patch('api.billing.get_conn', return_value=conn):
            resp = client.post('/ris/billing/fee-schedule/import', json={
                'rows': [
                    {'procedure_code': '71250', 'description': 'CT Chest',
                     'list_price': 350},
                    {'procedure_code': '72125', 'description': 'CT Head',
                     'list_price': 320},
                ],
            })
        assert resp.status_code == 201
        assert resp.json()['data']['imported'] == 2
        sqls = [c[1] for c in conn.calls]
        assert sum('ris_fee_schedule_history' in s for s in sqls) == 2

    def test_import_rejects_empty_rows(self, conn):
        client = TestClient(_make_app(_user(Permission.BILLING_WRITE)))
        with patch('api.billing.get_conn', return_value=conn):
            resp = client.post('/ris/billing/fee-schedule/import', json={'rows': []})
        assert resp.status_code == 422

    def test_history_returns_version_rows(self, conn):
        conn.set_fetch([
            {'procedure_code': '71250', 'description': 'CT Chest',
             'list_price': Decimal('400.00'), 'changed_by': '1',
             'changed_at': '2026-08-27T00:00:00Z'},
        ])
        client = TestClient(_make_app(_user(Permission.BILLING_READ)))
        with patch('api.billing.get_conn', return_value=conn):
            resp = client.get('/ris/billing/fee-schedule/history/71250')
        assert resp.status_code == 200
        assert resp.json()['data'][0]['list_price'] == 400.0


class TestPayerContracts:
    """B-08: payer contract rates CRUD + comparison."""

    def test_list_requires_billing_read(self, conn):
        client = TestClient(_make_app(_user()))
        with patch('api.billing.get_conn', return_value=conn):
            resp = client.get('/ris/billing/contracts')
        assert resp.status_code == 403

    def test_list_returns_contracts(self, conn):
        conn.set_fetch([
            {'id': 'c1', 'payer_id': 'AETNA', 'payer_name': 'Aetna',
             'procedure_code': '71250', 'contracted_rate': Decimal('280.00'),
             'active': True},
        ])
        client = TestClient(_make_app(_user(Permission.BILLING_READ)))
        with patch('api.billing.get_conn', return_value=conn):
            resp = client.get('/ris/billing/contracts?payer_id=AETNA')
        assert resp.status_code == 200
        assert resp.json()['data'][0]['contracted_rate'] == 280.0

    def test_create_contract(self, conn):
        conn.set_fetchrow({'id': 'c1', 'payer_id': 'AETNA', 'payer_name': 'Aetna',
                           'procedure_code': '71250',
                           'contracted_rate': Decimal('280.00'), 'active': True})
        client = TestClient(_make_app(_user(Permission.BILLING_WRITE)))
        with patch('api.billing.get_conn', return_value=conn):
            resp = client.post('/ris/billing/contracts', json={
                'payer_id': 'AETNA', 'payer_name': 'Aetna',
                'procedure_code': '71250', 'contracted_rate': 280,
            })
        assert resp.status_code == 201
        assert resp.json()['data']['contracted_rate'] == 280.0

    def test_create_rejects_negative_rate(self, conn):
        client = TestClient(_make_app(_user(Permission.BILLING_WRITE)))
        with patch('api.billing.get_conn', return_value=conn):
            resp = client.post('/ris/billing/contracts', json={
                'payer_id': 'AETNA', 'procedure_code': '71250',
                'contracted_rate': -10,
            })
        assert resp.status_code == 422

    def test_update_contract(self, conn):
        conn.set_fetchval('c1')
        conn.set_fetchrow({'id': 'c1', 'payer_id': 'AETNA', 'procedure_code': '71250',
                           'contracted_rate': Decimal('300.00'), 'active': True})
        client = TestClient(_make_app(_user(Permission.BILLING_WRITE)))
        with patch('api.billing.get_conn', return_value=conn):
            resp = client.put('/ris/billing/contracts/c1', json={'contracted_rate': 300})
        assert resp.status_code == 200
        assert resp.json()['data']['contracted_rate'] == 300.0

    def test_update_404_when_missing(self, conn):
        conn.set_fetchval(None)
        client = TestClient(_make_app(_user(Permission.BILLING_WRITE)))
        with patch('api.billing.get_conn', return_value=conn):
            resp = client.put('/ris/billing/contracts/missing', json={'contracted_rate': 300})
        assert resp.status_code == 404

    def test_delete_deactivates(self, conn):
        conn.set_fetchval('c1')
        client = TestClient(_make_app(_user(Permission.BILLING_WRITE)))
        with patch('api.billing.get_conn', return_value=conn):
            resp = client.delete('/ris/billing/contracts/c1')
        assert resp.status_code == 200
        assert resp.json()['data']['active'] is False
        assert any('active = FALSE' in c[1] for c in conn.calls)

    def test_comparison_flags_over_charge(self, conn):
        conn.set_fetch([
            {'charge_id': 'ch1', 'procedure_code': '71250', 'payer_name': 'Aetna',
             'charged_amount': Decimal('400.00'),
             'contracted_rate': Decimal('280.00'),
             'created_at': '2026-08-27T00:00:00Z'},
        ])
        client = TestClient(_make_app(_user(Permission.BILLING_READ)))
        with patch('api.billing.get_conn', return_value=conn):
            resp = client.get('/ris/billing/contracts/comparison')
        assert resp.status_code == 200
        item = resp.json()['data'][0]
        assert item['flag'] == 'over_charge'
        assert item['variance'] == 120.0

    def test_comparison_flags_under_charge(self, conn):
        conn.set_fetch([
            {'charge_id': 'ch1', 'procedure_code': '71250', 'payer_name': 'Aetna',
             'charged_amount': Decimal('200.00'),
             'contracted_rate': Decimal('280.00'),
             'created_at': '2026-08-27T00:00:00Z'},
        ])
        client = TestClient(_make_app(_user(Permission.BILLING_READ)))
        with patch('api.billing.get_conn', return_value=conn):
            resp = client.get('/ris/billing/contracts/comparison')
        assert resp.status_code == 200
        assert resp.json()['data'][0]['flag'] == 'under_charge'
