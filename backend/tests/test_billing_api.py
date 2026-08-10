from datetime import datetime, timezone
from decimal import Decimal
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
    from api.billing import (
        BillingPricingHandler, BillingInvoicesHandler, BillingInvoiceHandler,
        BillingPaymentsHandler, BillingReceiptHandler, BillingClaimsHandler,
        BillingClaimHandler, BillingRefundsHandler, BillingRefundHandler,
        BillingQuotesHandler, BillingPaymentPlansHandler, BillingReconciliationHandler,
    )
    return Starlette(
        routes=[
            Route('/billing/pricing', endpoint=BillingPricingHandler),
            Route('/billing/invoices', endpoint=BillingInvoicesHandler),
            Route('/billing/invoices/{id}', endpoint=BillingInvoiceHandler),
            Route('/billing/invoices/{id}/payments', endpoint=BillingPaymentsHandler),
            Route('/billing/payments/{payment_id}/receipt', endpoint=BillingReceiptHandler),
            Route('/billing/invoices/{id}/claims', endpoint=BillingClaimsHandler),
            Route('/billing/claims/{id}', endpoint=BillingClaimHandler),
            Route('/billing/refunds', endpoint=BillingRefundsHandler),
            Route('/billing/invoices/{id}/refunds', endpoint=BillingRefundsHandler),
            Route('/billing/refunds/{id}', endpoint=BillingRefundHandler),
            Route('/billing/quotes', endpoint=BillingQuotesHandler),
            Route('/billing/invoices/{id}/plans', endpoint=BillingPaymentPlansHandler),
            Route('/billing/reconciliation', endpoint=BillingReconciliationHandler),
            Route('/billing/reconciliation/close', endpoint=BillingReconciliationHandler),
        ],
        middleware=[Middleware(_FakeAuth, user=user)],
        exception_handlers={
            HTTPException: _http_exception,
            _ValidationException: validation_exception_handler,
        },
    )


def _now():
    return datetime.now(timezone.utc)


def _invoice_row(amount='100.00', paid='0.00', status='open', invoice_id='inv-1'):
    return {
        'id': invoice_id, 'patient_id': 'P001', 'status': status,
        'total_amount': Decimal(amount), 'paid_amount': Decimal(paid),
        'balance': Decimal(str(round(float(amount) - float(paid), 2))),
        'created_by': '1', 'created_at': _now(), 'updated_at': _now(),
    }


class TestInvoiceCreate:
    def test_create_requires_billing_write(self):
        user = User({'id': 1, 'permissions': []})
        client = TestClient(_make_app(user))
        resp = client.post('/billing/invoices', json={
            'patient_id': 'P001',
            'lines': [{'procedure_code': 'DXCHEST'}],
        })
        assert resp.status_code == 403

    def test_create_prices_from_catalog_and_returns_floats(self):
        user = User({'id': 1, 'permissions': ['BILLING_WRITE']})
        client = TestClient(_make_app(user))
        mock_conn = AsyncMock()
        mock_conn.__aenter__.return_value = mock_conn
        mock_conn.fetchrow.side_effect = [
            {'description': 'X-ray Chest 2 views', 'list_price': Decimal('120.00')},
            _invoice_row('120.00', '0.00', 'open'),
            {
                'id': 'ln-1', 'invoice_id': 'inv-1', 'procedure_code': 'DXCHEST',
                'description': 'X-ray Chest 2 views', 'quantity': 2,
                'unit_price': Decimal('120.00'), 'discount_amount': Decimal('10.00'),
                'line_total': Decimal('230.00'), 'created_at': _now(),
            },
        ]
        with patch('api.billing.get_conn', return_value=mock_conn):
            resp = client.post('/billing/invoices', json={
                'patient_id': 'P001',
                'lines': [{'procedure_code': 'DXCHEST', 'quantity': 2}],
            })
        assert resp.status_code == 201
        data = resp.json()['data']
        assert data['invoice']['total_amount'] == 120.0
        assert isinstance(data['invoice']['total_amount'], float)
        assert data['lines'][0]['line_total'] == 230.0
        assert isinstance(data['lines'][0]['unit_price'], float)

    def test_list_requires_billing_read(self):
        user = User({'id': 1, 'permissions': []})
        client = TestClient(_make_app(user))
        resp = client.get('/billing/invoices')
        assert resp.status_code == 403

    def test_detail_not_found(self):
        user = User({'id': 1, 'permissions': ['BILLING_READ']})
        client = TestClient(_make_app(user))
        mock_conn = AsyncMock()
        mock_conn.__aenter__.return_value = mock_conn
        mock_conn.fetchrow.return_value = None
        with patch('api.billing.get_conn', return_value=mock_conn):
            resp = client.get('/billing/invoices/missing')
        assert resp.status_code == 404


class TestPayments:
    def test_payment_requires_billing_write(self):
        user = User({'id': 1, 'permissions': []})
        client = TestClient(_make_app(user))
        resp = client.post('/billing/invoices/inv-1/payments', json={
            'method': 'cash', 'amount': 50, 'idempotency_key': 'k-1',
        })
        assert resp.status_code == 403

    def test_duplicate_idempotency_key_returns_existing(self):
        user = User({'id': 1, 'permissions': ['BILLING_WRITE']})
        client = TestClient(_make_app(user))
        mock_conn = AsyncMock()
        mock_conn.__aenter__.return_value = mock_conn
        existing = {
            'id': 'pay-1', 'invoice_id': 'inv-1', 'method': 'cash',
            'amount': Decimal('50.00'), 'payment_date': _now(), 'operator_id': 1,
            'processor_token': '', 'idempotency_key': 'k-1',
            'split_group_id': '', 'created_at': _now(),
        }
        mock_conn.fetchrow.return_value = existing
        with patch('api.billing.get_conn', return_value=mock_conn):
            resp = client.post('/billing/invoices/inv-1/payments', json={
                'method': 'cash', 'amount': 50, 'idempotency_key': 'k-1',
            })
        assert resp.status_code == 200
        data = resp.json()
        assert data['duplicate'] is True
        assert data['data']['id'] == 'pay-1'
        assert data['data']['amount'] == 50.0
        assert isinstance(data['data']['amount'], float)

    def test_payment_over_balance_rejected(self):
        user = User({'id': 1, 'permissions': ['BILLING_WRITE']})
        client = TestClient(_make_app(user))
        mock_conn = AsyncMock()
        mock_conn.__aenter__.return_value = mock_conn
        mock_conn.fetchrow.side_effect = [None, _invoice_row('50.00', '0.00', 'open')]
        with patch('api.billing.get_conn', return_value=mock_conn):
            resp = client.post('/billing/invoices/inv-1/payments', json={
                'method': 'cash', 'amount': 100, 'idempotency_key': 'k-2',
            })
        assert resp.status_code == 400
        assert 'exceeds' in resp.json()['error']['message']

    def test_payment_success_creates_receipt(self):
        user = User({'id': 1, 'permissions': ['BILLING_WRITE']})
        client = TestClient(_make_app(user))
        mock_conn = AsyncMock()
        mock_conn.__aenter__.return_value = mock_conn
        mock_conn.fetchrow.side_effect = [
            None,
            _invoice_row('100.00', '0.00', 'open'),
            {
                'id': 'pay-1', 'invoice_id': 'inv-1', 'method': 'card',
                'amount': Decimal('100.00'), 'payment_date': _now(), 'operator_id': 1,
                'processor_token': 'tok_123', 'idempotency_key': 'k-3',
                'split_group_id': '', 'created_at': _now(),
            },
            _invoice_row('100.00', '100.00', 'paid'),
            {
                'id': 'rcpt-1', 'payment_id': 'pay-1',
                'receipt_number': 'RCP-20260804-1234', 'generated_at': _now(),
                'emailed_at': None, 'created_at': _now(),
            },
        ]
        with patch('api.billing.get_conn', return_value=mock_conn):
            resp = client.post('/billing/invoices/inv-1/payments', json={
                'method': 'card', 'amount': 100, 'idempotency_key': 'k-3',
                'processor_token': 'tok_123',
            })
        assert resp.status_code == 201
        data = resp.json()['data']
        assert data['receipt']['receipt_number'].startswith('RCP-')
        assert data['payment']['amount'] == 100.0
        assert data['invoice']['status'] == 'paid'


class TestRefunds:
    def test_refund_requires_billing_write(self):
        user = User({'id': 1, 'permissions': []})
        client = TestClient(_make_app(user))
        resp = client.post('/billing/invoices/inv-1/refunds', json={
            'amount': 100, 'reason': 'overcharge',
        })
        assert resp.status_code == 403

    def test_refund_above_threshold_pending_approval(self):
        user = User({'id': 1, 'permissions': ['BILLING_WRITE']})
        client = TestClient(_make_app(user))
        mock_conn = AsyncMock()
        mock_conn.__aenter__.return_value = mock_conn
        mock_conn.fetchrow.return_value = {
            'id': 'ref-1', 'invoice_id': 'inv-1', 'payment_id': None,
            'amount': Decimal('600.00'), 'reason': 'billing error',
            'status': 'pending_approval', 'threshold_exceeded': True,
            'approved_by': '', 'approved_at': None, 'created_by': '1',
            'created_at': _now(), 'updated_at': _now(),
        }
        with patch('api.billing.get_conn', return_value=mock_conn):
            resp = client.post('/billing/invoices/inv-1/refunds', json={
                'amount': 600, 'reason': 'billing error',
            })
        assert resp.status_code == 201
        data = resp.json()['data']
        assert data['status'] == 'pending_approval'
        assert data['threshold_exceeded'] is True
        assert data['amount'] == 600.0

    def test_refund_action_requires_billing_admin(self):
        user = User({'id': 1, 'permissions': ['BILLING_WRITE']})
        client = TestClient(_make_app(user))
        resp = client.put('/billing/refunds/ref-1', json={'action': 'approve'})
        assert resp.status_code == 403

    def test_refund_reject_requires_billing_admin(self):
        user = User({'id': 1, 'permissions': ['BILLING_ADMIN']})
        client = TestClient(_make_app(user))
        mock_conn = AsyncMock()
        mock_conn.__aenter__.return_value = mock_conn
        mock_conn.fetchrow.return_value = {
            'id': 'ref-1', 'invoice_id': 'inv-1', 'payment_id': None,
            'amount': Decimal('600.00'), 'reason': 'billing error',
            'status': 'rejected', 'threshold_exceeded': True,
            'approved_by': '', 'approved_at': None, 'created_by': '1',
            'created_at': _now(), 'updated_at': _now(),
        }
        with patch('api.billing.get_conn', return_value=mock_conn):
            resp = client.put('/billing/refunds/ref-1', json={'action': 'reject'})
        assert resp.status_code == 200
        assert resp.json()['data']['status'] == 'rejected'


class TestQuotes:
    def test_quote_created_from_catalog_price(self):
        user = User({'id': 1, 'permissions': ['BILLING_WRITE']})
        client = TestClient(_make_app(user))
        mock_conn = AsyncMock()
        mock_conn.__aenter__.return_value = mock_conn
        mock_conn.fetchval.return_value = Decimal('1100.00')
        mock_conn.fetchrow.return_value = {
            'id': 'q-1', 'patient_id': 'P001', 'invoice_id': None,
            'procedure_code': 'MRBRAIN', 'total': Decimal('1100.00'),
            'estimated_patient_responsibility': Decimal('1100.00'),
            'quoted_by': '1', 'quoted_at': _now(), 'created_at': _now(),
        }
        with patch('api.billing.get_conn', return_value=mock_conn):
            resp = client.post('/billing/quotes', json={
                'patient_id': 'P001', 'procedure_code': 'MRBRAIN',
            })
        assert resp.status_code == 201
        data = resp.json()['data']
        assert data['total'] == 1100.0
        assert data['estimated_patient_responsibility'] == 1100.0


class TestReconciliation:
    def test_get_expected_totals_returns_floats(self):
        user = User({'id': 1, 'permissions': ['BILLING_READ']})
        client = TestClient(_make_app(user))
        mock_conn = AsyncMock()
        mock_conn.__aenter__.return_value = mock_conn
        mock_conn.fetch.return_value = [
            {'method': 'cash', 'total': Decimal('100.00')},
            {'method': 'card', 'total': Decimal('50.00')},
        ]
        with patch('api.billing.get_conn', return_value=mock_conn):
            resp = client.get('/billing/reconciliation')
        assert resp.status_code == 200
        data = resp.json()['data']
        assert data['expected_totals'] == {'cash': 100.0, 'card': 50.0, 'check': 0.0}
        assert data['total'] == 150.0

    def test_get_reconciliation_requires_billing_read(self):
        user = User({'id': 1, 'permissions': []})
        client = TestClient(_make_app(user))
        resp = client.get('/billing/reconciliation')
        assert resp.status_code == 403

    def test_close_with_variance_and_no_reason_rejected(self):
        user = User({'id': 1, 'permissions': ['BILLING_WRITE']})
        client = TestClient(_make_app(user))
        mock_conn = AsyncMock()
        mock_conn.__aenter__.return_value = mock_conn
        mock_conn.fetch.return_value = [
            {'method': 'cash', 'total': Decimal('100.00')},
        ]
        with patch('api.billing.get_conn', return_value=mock_conn):
            resp = client.post('/billing/reconciliation/close', json={
                'shift_date': '2026-08-04',
                'counted_cash': {'cash': 150, 'card': 0, 'check': 0},
                'variance_reason': '',
            })
        assert resp.status_code == 400
        assert 'Variance reason' in resp.json()['error']['message']

    def test_close_success(self):
        user = User({'id': 1, 'permissions': ['BILLING_WRITE']})
        client = TestClient(_make_app(user))
        mock_conn = AsyncMock()
        mock_conn.__aenter__.return_value = mock_conn
        mock_conn.fetch.return_value = [
            {'method': 'cash', 'total': Decimal('100.00')},
        ]
        mock_conn.fetchrow.return_value = {
            'id': 'rec-1', 'cashier_id': 1, 'shift_date': '2026-08-04',
            'expected_totals': {'cash': 100.0, 'card': 0.0, 'check': 0.0},
            'counted_cash': Decimal('100.00'), 'variance': Decimal('0.00'),
            'variance_reason': '', 'closed_at': _now(), 'created_at': _now(),
        }
        with patch('api.billing.get_conn', return_value=mock_conn):
            resp = client.post('/billing/reconciliation/close', json={
                'shift_date': '2026-08-04',
                'counted_cash': {'cash': 100, 'card': 0, 'check': 0},
                'variance_reason': '',
            })
        assert resp.status_code == 201
        data = resp.json()['data']
        assert data['counted_cash'] == 100.0
        assert data['variance'] == 0.0
