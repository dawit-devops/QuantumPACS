"""R09 Cashier/Billing endpoints (FR-R09-01..08).

Invoices with catalog-priced lines, idempotent tokenized payments,
receipts, insurance claims, refunds with BILLING_ADMIN approval,
quotes, payment plans, and shift reconciliation. All money columns are
NUMERIC(12,2) in the database; every response converts them with
db.billing.money() because asyncpg returns Decimal, which the JSON
encoder (allow_nan=False, no Decimal default) cannot serialize.
"""
import random
from datetime import datetime, timezone

from starlette.endpoints import HTTPEndpoint

from api.validate import parse_body
from api.rbac import requires_permission
from api.permissions import Permission
from api.response import (
    ok, created, not_found, validation_error, api_error,
)
from api.schemas.billing import (
    PricingItemRequest, CreateInvoiceRequest, PaymentRequest,
    CreateClaimRequest, UpdateClaimRequest, CreateRefundRequest,
    RefundActionRequest, CreateQuoteRequest, CreatePaymentPlanRequest,
    ReconciliationCloseRequest,
)
from db.audit_log import AuditLog
from db.billing import money
from db.conn import get_conn
from log import request_id_var
from api.tenant_middleware import effective_tenant

from api.telemetry import (
    ris_unbilled_over_5d, ris_unbilled_over_10d,
)


def _json_row(row):
    """asyncpg Row -> JSON-safe dict (UUID/datetime -> str)."""
    from datetime import date, datetime, time
    from uuid import UUID
    d = dict(row)
    for k, v in d.items():
        if isinstance(v, (date, datetime, time, UUID)):
            d[k] = str(v)
    return d


# Refunds above this amount require BILLING_ADMIN approval (FR-R09-05).
REFUND_THRESHOLD = 500.00

# Invoices with a residual balance at or below this are treated as paid —
# guards against floating point dust after partial payments.
_BALANCE_EPSILON = 0.005


async def drop_charge_stub(conn, report_id, exam_id, accession_number, radiologist_id):
    """S8-14 charge drop stub — creates placeholder charge record.

    S11: the ris_charges schema now comes from migration 077 (no runtime
    CREATE TABLE); this stub still inserts a placeholder PENDING row and
    stays idempotent per report until S11-03 replaces it with the full
    auto-charge-drop (CPT/ICD-10 from CodingService).
    """
    try:
        # V-3: idempotent — a report signed twice (or co-signed) must not
        # insert a second charge row. The NOT EXISTS guard makes the
        # INSERT a no-op for an already-charged report instead of relying
        # on a unique constraint the inline schema never declared.
        await conn.execute("""
            INSERT INTO ris_charges (report_id, exam_id, accession_number, created_by)
            SELECT $1, $2, $3, $4
            WHERE NOT EXISTS (
                SELECT 1 FROM ris_charges WHERE report_id = $1
            )
        """, str(report_id), str(exam_id), str(accession_number), str(radiologist_id))
    except Exception:
        pass



def _now():
    return datetime.now(timezone.utc)


def _receipt_number():
    return f"RCP-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{random.randint(1000, 9999)}"


def _recompute_status(total, paid):
    """Invoice status after a money movement: paid once the balance is dust."""
    balance = money(total - paid)
    if balance <= _BALANCE_EPSILON:
        return 'paid', balance
    return ('partially_paid' if money(paid) > 0 else 'open'), balance


def _invoice_row(row):
    d = dict(row)
    d['total_amount'] = money(d['total_amount'])
    d['paid_amount'] = money(d['paid_amount'])
    d['balance'] = money(d['balance'])
    return d


def _payment_row(row):
    d = dict(row)
    d['amount'] = money(d['amount'])
    return d


def _line_row(row):
    d = dict(row)
    d['unit_price'] = money(d['unit_price'])
    d['discount_amount'] = money(d['discount_amount'])
    d['line_total'] = money(d['line_total'])
    return d


def _refund_row(row):
    d = dict(row)
    d['amount'] = money(d['amount'])
    return d


def _quote_row(row):
    d = dict(row)
    d['total'] = money(d['total'])
    d['estimated_patient_responsibility'] = money(d['estimated_patient_responsibility'])
    return d


def _installment_row(row):
    d = dict(row)
    d['amount'] = money(d['amount'])
    return d


class BillingPricingHandler(HTTPEndpoint):
    """Procedure pricing catalog (FR-R09-01)."""

    @requires_permission(Permission.BILLING_READ)
    async def get(self, request):
        async with get_conn() as conn:
            rows = await conn.fetch(
                """SELECT * FROM procedure_pricing_catalog
                   WHERE active = TRUE
                   ORDER BY procedure_code""",
            )
        items = [dict(r) | {'list_price': money(r['list_price'])} for r in rows]
        return ok({'data': items})

    @requires_permission(Permission.BILLING_WRITE)
    async def post(self, request):
        body = await parse_body(PricingItemRequest, request)
        async with get_conn() as conn:
            row = await conn.fetchrow(
                """INSERT INTO procedure_pricing_catalog
                       (procedure_code, description, list_price, active)
                   VALUES ($1, $2, $3, $4)
                   ON CONFLICT (procedure_code) DO UPDATE
                       SET description = EXCLUDED.description,
                           list_price = EXCLUDED.list_price,
                           active = EXCLUDED.active
                   RETURNING *""",
                body.procedure_code, body.description, money(body.list_price), body.active,
            )
        item = dict(row) | {'list_price': money(row['list_price'])}
        return created({'data': item})


class BillingInvoicesHandler(HTTPEndpoint):
    """Invoice list + creation (FR-R09-02)."""

    @requires_permission(Permission.BILLING_READ)
    async def get(self, request):
        patient_id = request.query_params.get('patient_id')
        status = request.query_params.get('status')
        page = max(1, int(request.query_params.get('page', '1')))
        per_page = max(1, int(request.query_params.get('per_page', '20')))

        where = []
        params = []
        idx = 1
        if patient_id:
            where.append(f"patient_id = ${idx}")
            params.append(patient_id)
            idx += 1
        if status:
            where.append(f"status = ${idx}")
            params.append(status)
            idx += 1
        where_sql = f"WHERE {' AND '.join(where)}" if where else ''

        async with get_conn() as conn:
            rows = await conn.fetch(
                f"""SELECT * FROM invoice {where_sql}
                    ORDER BY created_at DESC
                    LIMIT ${idx} OFFSET ${idx + 1}""",
                *params, per_page, (page - 1) * per_page,
            )
            total = await conn.fetchval(
                f"SELECT COUNT(1) FROM invoice {where_sql}", *params,
            ) or 0
        invoices = [_invoice_row(r) for r in rows]
        return ok({'data': invoices, 'total': total, 'page': page, 'per_page': per_page})

    @requires_permission(Permission.BILLING_WRITE)
    async def post(self, request):
        body = await parse_body(CreateInvoiceRequest, request)
        async with get_conn() as conn:
            computed = []
            for line in body.lines:
                unit_price = line.unit_price
                description = line.description
                if line.procedure_code:
                    catalog = await conn.fetchrow(
                        """SELECT description, list_price
                           FROM procedure_pricing_catalog
                           WHERE procedure_code = $1""",
                        line.procedure_code,
                    )
                    if catalog:
                        unit_price = float(catalog['list_price'])
                        if not description:
                            description = catalog['description'] or ''
                line_total = money((money(unit_price) * line.quantity) - line.discount_amount)
                computed.append((line, unit_price, description, line_total))

            total = money(sum(lt for _, _, _, lt in computed))
            invoice = await conn.fetchrow(
                """INSERT INTO invoice
                       (patient_id, total_amount, paid_amount, balance, status, created_by)
                   VALUES ($1, $2, 0, $2, 'open', $3)
                   RETURNING *""",
                body.patient_id, total, str(request.user.id),
            )
            lines = []
            for line, unit_price, description, line_total in computed:
                row = await conn.fetchrow(
                    """INSERT INTO invoice_line
                           (invoice_id, procedure_code, description, quantity,
                            unit_price, discount_amount, line_total)
                       VALUES ($1, $2, $3, $4, $5, $6, $7)
                       RETURNING *""",
                    invoice['id'], line.procedure_code, description, line.quantity,
                    money(unit_price), money(line.discount_amount), line_total,
                )
                lines.append(_line_row(row))
            await AuditLog(conn).log_event(
                event_type='billing.invoice_created',
                actor_id=request.user.id,
                resource_type='invoice',
                resource_id=invoice['id'],
                details={'patient_id': body.patient_id, 'total': total, 'line_count': len(lines)},
                tenant=effective_tenant(request),
                request_id=request_id_var.get(),
            )
        return created({'data': {'invoice': _invoice_row(invoice), 'lines': lines}})


class BillingInvoiceHandler(HTTPEndpoint):
    """Invoice detail with lines, payments and claims (FR-R09-02/03)."""

    @requires_permission(Permission.BILLING_READ)
    async def get(self, request):
        invoice_id = request.path_params['id']
        async with get_conn() as conn:
            invoice = await conn.fetchrow(
                "SELECT * FROM invoice WHERE id = $1", invoice_id,
            )
            if not invoice:
                return not_found('Invoice not found')
            lines = await conn.fetch(
                "SELECT * FROM invoice_line WHERE invoice_id = $1 ORDER BY created_at",
                invoice_id,
            )
            payments = await conn.fetch(
                "SELECT * FROM payment WHERE invoice_id = $1 ORDER BY payment_date",
                invoice_id,
            )
            claims = await conn.fetch(
                "SELECT * FROM claim WHERE invoice_id = $1 ORDER BY created_at",
                invoice_id,
            )
        return ok({
            'data': {
                'invoice': _invoice_row(invoice),
                'lines': [_line_row(r) for r in lines],
                'payments': [_payment_row(r) for r in payments],
                'claims': [dict(r) for r in claims],
            },
        })


class BillingPaymentsHandler(HTTPEndpoint):
    """Idempotent payment collection + receipt generation (FR-R09-03)."""

    @requires_permission(Permission.BILLING_WRITE)
    async def post(self, request):
        invoice_id = request.path_params['id']
        body = await parse_body(PaymentRequest, request)

        async with get_conn() as conn:
            existing = await conn.fetchrow(
                "SELECT * FROM payment WHERE idempotency_key = $1",
                body.idempotency_key,
            )
            if existing:
                return ok({'data': _payment_row(existing), 'duplicate': True})

            invoice = await conn.fetchrow(
                "SELECT * FROM invoice WHERE id = $1", invoice_id,
            )
            if not invoice:
                return not_found('Invoice not found')

            balance = money(invoice['balance'])
            if body.amount > balance:
                return validation_error('Payment exceeds outstanding balance')

            payment = await conn.fetchrow(
                """INSERT INTO payment
                       (invoice_id, method, amount, operator_id,
                        processor_token, idempotency_key, split_group_id)
                   VALUES ($1, $2, $3, $4, $5, $6, $7)
                   RETURNING *""",
                invoice_id, body.method, money(body.amount), request.user.id,
                body.processor_token, body.idempotency_key, body.split_group_id,
            )

            new_paid = money(money(invoice['paid_amount']) + body.amount)
            status, new_balance = _recompute_status(money(invoice['total_amount']), new_paid)
            invoice = await conn.fetchrow(
                """UPDATE invoice
                   SET paid_amount = $2, balance = $3, status = $4, updated_at = now()
                   WHERE id = $1
                   RETURNING *""",
                invoice_id, new_paid, new_balance, status,
            )

            receipt = await conn.fetchrow(
                """INSERT INTO receipt (payment_id, receipt_number)
                   VALUES ($1, $2)
                   RETURNING *""",
                payment['id'], _receipt_number(),
            )

            await AuditLog(conn).log_event(
                event_type='billing.payment_collected',
                actor_id=request.user.id,
                resource_type='payment',
                resource_id=payment['id'],
                details={'method': body.method, 'amount': money(body.amount), 'invoice_id': invoice_id},
                tenant=effective_tenant(request),
                request_id=request_id_var.get(),
            )
        return created({'data': {
            'payment': _payment_row(payment),
            'receipt': dict(receipt),
            'invoice': _invoice_row(invoice),
        }})


class BillingReceiptHandler(HTTPEndpoint):
    """Receipt lookup/regeneration for a payment (FR-R09-03)."""

    @requires_permission(Permission.BILLING_READ)
    async def get(self, request):
        payment_id = request.path_params['payment_id']
        async with get_conn() as conn:
            payment = await conn.fetchrow(
                "SELECT * FROM payment WHERE id = $1", payment_id,
            )
            if not payment:
                return not_found('Payment not found')

            receipt = await conn.fetchrow(
                "SELECT * FROM receipt WHERE payment_id = $1", payment_id,
            )
            if not receipt:
                receipt = await conn.fetchrow(
                    """INSERT INTO receipt (payment_id, receipt_number)
                       VALUES ($1, $2)
                       RETURNING *""",
                    payment_id, _receipt_number(),
                )

            invoice = await conn.fetchrow(
                "SELECT * FROM invoice WHERE id = $1", payment['invoice_id'],
            )
            patient_name = await conn.fetchval(
                "SELECT name FROM patients WHERE patient_id = $1", invoice['patient_id'],
            ) or ''

        return ok({'data': {
            'receipt_number': receipt['receipt_number'],
            'generated_at': receipt['generated_at'],
            'amount': money(payment['amount']),
            'method': payment['method'],
            'invoice_id': payment['invoice_id'],
            'patient_name': patient_name,
            'payment_date': payment['payment_date'],
        }})


class BillingClaimsHandler(HTTPEndpoint):
    """Claims for an invoice (FR-R09-04)."""

    @requires_permission(Permission.BILLING_READ)
    async def get(self, request):
        invoice_id = request.path_params['id']
        async with get_conn() as conn:
            rows = await conn.fetch(
                "SELECT * FROM claim WHERE invoice_id = $1 ORDER BY created_at",
                invoice_id,
            )
        return ok({'data': [dict(r) for r in rows]})

    @requires_permission(Permission.BILLING_WRITE)
    async def post(self, request):
        invoice_id = request.path_params['id']
        body = await parse_body(CreateClaimRequest, request)
        action_required = body.status == 'denied'
        async with get_conn() as conn:
            row = await conn.fetchrow(
                """INSERT INTO claim
                       (invoice_id, status, action_required, source, external_claim_id)
                   VALUES ($1, $2, $3, $4, $5)
                   RETURNING *""",
                invoice_id, body.status, action_required, body.source, body.external_claim_id,
            )
            await AuditLog(conn).log_event(
                event_type='billing.claim_created',
                actor_id=request.user.id,
                resource_type='claim',
                resource_id=row['id'],
                details={'status': body.status, 'invoice_id': invoice_id},
                tenant=effective_tenant(request),
                request_id=request_id_var.get(),
            )
        return created({'data': dict(row)})


class BillingClaimHandler(HTTPEndpoint):
    """Claim status updates (FR-R09-04)."""

    @requires_permission(Permission.BILLING_WRITE)
    async def put(self, request):
        claim_id = request.path_params['id']
        body = await parse_body(UpdateClaimRequest, request)
        updates = body.model_dump(exclude_none=True)
        if not updates:
            return ok({})
        # A denial always demands follow-up unless the caller says otherwise.
        if updates.get('status') == 'denied' and 'action_required' not in updates:
            updates['action_required'] = True
        async with get_conn() as conn:
            existing = await conn.fetchval(
                "SELECT id FROM claim WHERE id = $1", claim_id,
            )
            if not existing:
                return not_found('Claim not found')
            keys = list(updates) + ['updated_at']
            values = list(updates.values()) + [_now()]
            set_clause = ', '.join(f"{k} = ${i + 2}" for i, k in enumerate(keys))
            await conn.execute(
                f"UPDATE claim SET {set_clause} WHERE id = $1",
                claim_id, *values,
            )
            await AuditLog(conn).log_event(
                event_type='billing.claim_updated',
                actor_id=request.user.id,
                resource_type='claim',
                resource_id=claim_id,
                details=updates,
                tenant=effective_tenant(request),
                request_id=request_id_var.get(),
            )
        return ok({})


class BillingRefundsHandler(HTTPEndpoint):
    """Refund list + submission with approval threshold (FR-R09-05)."""

    @requires_permission(Permission.BILLING_READ)
    async def get(self, request):
        status = request.query_params.get('status')
        async with get_conn() as conn:
            if status:
                rows = await conn.fetch(
                    "SELECT * FROM refund WHERE status = $1 ORDER BY created_at",
                    status,
                )
            else:
                rows = await conn.fetch(
                    "SELECT * FROM refund ORDER BY created_at",
                )
        return ok({'data': [_refund_row(r) for r in rows]})

    @requires_permission(Permission.BILLING_WRITE)
    async def post(self, request):
        invoice_id = request.path_params['id']
        body = await parse_body(CreateRefundRequest, request)
        threshold_exceeded = body.amount > REFUND_THRESHOLD
        status = 'pending_approval' if threshold_exceeded else 'approved'
        async with get_conn() as conn:
            refund = await conn.fetchrow(
                """INSERT INTO refund
                       (invoice_id, payment_id, amount, reason, status,
                        threshold_exceeded, created_by)
                   VALUES ($1, $2, $3, $4, $5, $6, $7)
                   RETURNING *""",
                invoice_id, body.payment_id, money(body.amount), body.reason,
                status, threshold_exceeded, str(request.user.id),
            )
            if not threshold_exceeded:
                await _apply_refund(
                    conn, invoice_id, refund['amount'],
                    request, event_type='billing.refund_applied',
                )
            await AuditLog(conn).log_event(
                event_type='billing.refund_submitted',
                actor_id=request.user.id,
                resource_type='refund',
                resource_id=refund['id'],
                details={
                    'amount': money(refund['amount']), 'reason': body.reason,
                    'threshold_exceeded': threshold_exceeded,
                },
                tenant=effective_tenant(request),
                request_id=request_id_var.get(),
            )
        return created({'data': _refund_row(refund)})


class BillingRefundHandler(HTTPEndpoint):
    """Refund approval workflow — gated on BILLING_ADMIN (FR-R09-05)."""

    @requires_permission(Permission.BILLING_ADMIN)
    async def put(self, request):
        refund_id = request.path_params['id']
        body = await parse_body(RefundActionRequest, request)
        async with get_conn() as conn:
            refund = await conn.fetchrow(
                "SELECT * FROM refund WHERE id = $1", refund_id,
            )
            if not refund:
                return not_found('Refund not found')

            if body.action == 'reject':
                refund = await conn.fetchrow(
                    """UPDATE refund
                       SET status = 'rejected', updated_at = now()
                       WHERE id = $1
                       RETURNING *""",
                    refund_id,
                )
                await AuditLog(conn).log_event(
                    event_type='billing.refund_rejected',
                    actor_id=request.user.id,
                    resource_type='refund',
                    resource_id=refund_id,
                    details={'amount': money(refund['amount'])},
                    tenant=effective_tenant(request),
                    request_id=request_id_var.get(),
                )
            else:
                original_status = refund['status']
                refund = await conn.fetchrow(
                    """UPDATE refund
                       SET status = 'approved', approved_by = $2,
                           approved_at = now(), updated_at = now()
                       WHERE id = $1
                       RETURNING *""",
                    refund_id, str(request.user.id),
                )
                # Auto-approved refunds (below threshold) were applied at
                # creation — only pending/rejected ones deduct on approval.
                if original_status in ('pending_approval', 'rejected'):
                    await _apply_refund(
                        conn, refund['invoice_id'], refund['amount'],
                        request, event_type='billing.refund_applied',
                    )
        return ok({'data': _refund_row(refund)})


async def _apply_refund(conn, invoice_id, amount, request, event_type):
    """Deduct a refund from the invoice and recompute balance/status.

    Returns the updated invoice row, or None when the invoice is missing.
    """
    invoice = await conn.fetchrow(
        "SELECT * FROM invoice WHERE id = $1", invoice_id,
    )
    if not invoice:
        return None
    new_paid = money(max(0, money(invoice['paid_amount']) - money(amount)))
    status, new_balance = _recompute_status(money(invoice['total_amount']), new_paid)
    updated = await conn.fetchrow(
        """UPDATE invoice
           SET paid_amount = $2, balance = $3, status = $4, updated_at = now()
           WHERE id = $1
           RETURNING *""",
        invoice_id, new_paid, new_balance, status,
    )
    await AuditLog(conn).log_event(
        event_type=event_type,
        actor_id=request.user.id,
        resource_type='refund',
        resource_id=None,
        details={'invoice_id': invoice_id, 'amount': money(amount)},
        tenant=effective_tenant(request),
        request_id=request_id_var.get(),
    )
    return updated


class BillingQuotesHandler(HTTPEndpoint):
    """Procedure quotes priced from the catalog (FR-R09-06)."""

    @requires_permission(Permission.BILLING_READ)
    async def get(self, request):
        patient_id = request.query_params.get('patient_id')
        async with get_conn() as conn:
            if patient_id:
                rows = await conn.fetch(
                    "SELECT * FROM quote WHERE patient_id = $1 ORDER BY quoted_at",
                    patient_id,
                )
            else:
                rows = await conn.fetch(
                    "SELECT * FROM quote ORDER BY quoted_at",
                )
        return ok({'data': [_quote_row(r) for r in rows]})

    @requires_permission(Permission.BILLING_WRITE)
    async def post(self, request):
        body = await parse_body(CreateQuoteRequest, request)
        async with get_conn() as conn:
            price = await conn.fetchval(
                "SELECT list_price FROM procedure_pricing_catalog WHERE procedure_code = $1",
                body.procedure_code,
            )
            if price is None:
                return validation_error('Procedure code not found in pricing catalog')
            total = money(price)
            estimated = money(body.estimated_patient_responsibility) if body.estimated_patient_responsibility is not None else total
            row = await conn.fetchrow(
                """INSERT INTO quote
                       (patient_id, invoice_id, procedure_code, total,
                        estimated_patient_responsibility, quoted_by)
                   VALUES ($1, $2, $3, $4, $5, $6)
                   RETURNING *""",
                body.patient_id, body.invoice_id, body.procedure_code,
                total, estimated, str(request.user.id),
            )
            await AuditLog(conn).log_event(
                event_type='billing.quote_created',
                actor_id=request.user.id,
                resource_type='quote',
                resource_id=row['id'],
                details={'procedure_code': body.procedure_code, 'total': total},
                tenant=effective_tenant(request),
                request_id=request_id_var.get(),
            )
        return created({'data': _quote_row(row)})


class BillingPaymentPlansHandler(HTTPEndpoint):
    """Payment plans with installments (FR-R09-07)."""

    @requires_permission(Permission.BILLING_READ)
    async def get(self, request):
        invoice_id = request.path_params['id']
        async with get_conn() as conn:
            plans = await conn.fetch(
                "SELECT * FROM payment_plan WHERE invoice_id = $1 ORDER BY created_at",
                invoice_id,
            )
            result = []
            for plan in plans:
                installments = await conn.fetch(
                    """SELECT * FROM payment_plan_installment
                       WHERE plan_id = $1 ORDER BY installment_no""",
                    plan['id'],
                )
                result.append({
                    **dict(plan),
                    'installments': [_installment_row(r) for r in installments],
                })
        return ok({'data': result})

    @requires_permission(Permission.BILLING_WRITE)
    async def post(self, request):
        invoice_id = request.path_params['id']
        body = await parse_body(CreatePaymentPlanRequest, request)
        async with get_conn() as conn:
            plan = await conn.fetchrow(
                """INSERT INTO payment_plan (invoice_id, status, created_by)
                   VALUES ($1, 'active', $2)
                   RETURNING *""",
                invoice_id, str(request.user.id),
            )
            installments = []
            for index, inst in enumerate(body.installments, start=1):
                row = await conn.fetchrow(
                    """INSERT INTO payment_plan_installment
                           (plan_id, installment_no, amount, due_date, status)
                       VALUES ($1, $2, $3, $4, 'pending')
                       RETURNING *""",
                    plan['id'], index, money(inst.amount), inst.due_date,
                )
                installments.append(_installment_row(row))
            await AuditLog(conn).log_event(
                event_type='billing.plan_created',
                actor_id=request.user.id,
                resource_type='payment_plan',
                resource_id=plan['id'],
                details={
                    'invoice_id': invoice_id,
                    'installment_count': len(installments),
                    'total': money(sum(i['amount'] for i in installments)),
                },
                tenant=effective_tenant(request),
                request_id=request_id_var.get(),
            )
        return created({'data': {**dict(plan), 'installments': installments}})


class BillingReconciliationHandler(HTTPEndpoint):
    """Shift reconciliation — expected vs counted drawer totals (FR-R09-08)."""

    @requires_permission(Permission.BILLING_READ)
    async def get(self, request):
        date_param = request.query_params.get('date')
        shift_date = date_param or _now().date().isoformat()
        cashier_id = request.query_params.get('cashier_id')
        async with get_conn() as conn:
            expected = await _expected_totals(
                conn, shift_date,
                int(cashier_id) if cashier_id else None,
            )
        return ok({'data': {
            'date': shift_date,
            'expected_totals': expected,
            'total': money(sum(expected.values())),
        }})

    @requires_permission(Permission.BILLING_WRITE)
    async def post(self, request):
        body = await parse_body(ReconciliationCloseRequest, request)
        counted = {
            method: money(body.counted_cash.get(method, 0))
            for method in ('cash', 'card', 'check')
        }
        counted_sum = money(sum(counted.values()))
        async with get_conn() as conn:
            expected = await _expected_totals(conn, body.shift_date.isoformat())
            expected_sum = money(sum(expected.values()))
            variance = money(counted_sum - expected_sum)
            if abs(variance) > _BALANCE_EPSILON and not body.variance_reason:
                return validation_error('Variance reason is required when variance is non-zero')
            row = await conn.fetchrow(
                """INSERT INTO shift_reconciliation
                       (cashier_id, shift_date, expected_totals, counted_cash,
                        variance, variance_reason, closed_at)
                   VALUES ($1, $2, $3::jsonb, $4, $5, $6, now())
                   RETURNING *""",
                request.user.id, body.shift_date, expected,
                counted_sum, variance, body.variance_reason,
            )
            await AuditLog(conn).log_event(
                event_type='billing.reconciliation_closed',
                actor_id=request.user.id,
                resource_type='shift_reconciliation',
                resource_id=row['id'],
                details={'shift_date': body.shift_date.isoformat(), 'variance': variance},
                tenant=effective_tenant(request),
                request_id=request_id_var.get(),
            )
        data = dict(row)
        data['counted_cash'] = money(data['counted_cash'])
        data['variance'] = money(data['variance'])
        return created({'data': data})


async def _expected_totals(conn, shift_date, cashier_id=None):
    """Payments grouped by method for a shift date (optionally one cashier)."""
    expected = {'cash': 0.0, 'card': 0.0, 'check': 0.0}
    if cashier_id:
        rows = await conn.fetch(
            """SELECT method, COALESCE(SUM(amount), 0) AS total
               FROM payment
               WHERE payment_date::date = $1 AND operator_id = $2
               GROUP BY method""",
            shift_date, cashier_id,
        )
    else:
        rows = await conn.fetch(
            """SELECT method, COALESCE(SUM(amount), 0) AS total
               FROM payment
               WHERE payment_date::date = $1
               GROUP BY method""",
            shift_date,
        )
    for row in rows:
        if row['method'] in expected:
            expected[row['method']] = money(row['total'])
    return expected


# =========================================================================
# RIS Billing Capture (Sprint S11 — E-RIS-11)
# Handlers: CPT suggestions, billing queue, charge drop, unbilled aging,
# 837 export stub (claim submit), 835 import stub (denial rework).
# =========================================================================

class RisCptSuggestionsHandler(HTTPEndpoint):
    """S11-06: GET /ris/billing/cpt-suggestions?procedure=CT CHEST"""

    @requires_permission(Permission.BILLING_READ)
    async def get(self, request):
        procedure = request.query_params.get('procedure', '').strip()
        if not procedure:
            return validation_error('procedure parameter is required')
        tenant = effective_tenant(request) or 'default'
        async with get_conn() as conn:
            from db.ris_coding import CodingService
            await CodingService(conn).seed_defaults(tenant)
            suggestion = await CodingService(conn).get_suggestions(procedure, tenant)
        return ok({'data': [suggestion] if suggestion else []})


class RisBillingQueueHandler(HTTPEndpoint):
    """S11-04: GET /ris/billing/queue — signed-but-unbilled charges."""

    @requires_permission(Permission.BILLING_READ)
    async def get(self, request):
        tenant = effective_tenant(request) or 'default'
        try:
            page = max(1, int(request.query_params.get('page', '1')))
            per_page = min(200, max(1, int(request.query_params.get('per_page', '20'))))
        except (TypeError, ValueError):
            return validation_error('Invalid pagination parameters')
        async with get_conn() as conn:
            from db.ris_charges import RisCharges
            charges = await RisCharges(conn).list_pending(tenant, per_page, (page - 1) * per_page)
            total = await RisCharges(conn).count_pending(tenant)
        return ok({'data': charges, 'total': total or 0, 'page': page, 'per_page': per_page})


class RisChargeDropHandler(HTTPEndpoint):
    """S11-05: POST /ris/billing/charges/{id}/drop -> BILLED + audit."""

    @requires_permission(Permission.BILLING_WRITE)
    async def post(self, request):
        charge_id = request.path_params['id']
        tenant = effective_tenant(request) or 'default'
        async with get_conn() as conn:
            from db.ris_charges import RisCharges
            charge = await RisCharges(conn).get(charge_id, tenant)
            if not charge:
                return not_found('Charge not found')
            if charge['status'] != 'PENDING':
                return validation_error('Charge is not PENDING')
            row = await RisCharges(conn).mark_billed(charge_id, tenant)
            from db.audit_log import AuditLog
            await AuditLog(conn).log_event(
                event_type='billing.charge_dropped',
                resource_id=charge_id,
                resource_type='ris_charges',
                actor_id=request.user.id,
                tenant=tenant,
            )
        # S11-14: capture-rate instrumentation — time from sign (created_at)
        # to confirm, plus the unbilled count after this drop.
        from datetime import datetime, timezone
        from api import telemetry
        created = charge.get('created_at')
        if created:
            age = (datetime.now(timezone.utc) - created).total_seconds()
            telemetry.ris_charge_drop_latency_seconds.observe(max(age, 0))
        telemetry.ris_unbilled_count.set(float(await _unbilled_count(tenant)))
        return ok({'id': charge_id, 'status': row['status'] if row else 'BILLED'})


async def _unbilled_count(tenant):
    """Current PENDING charge count for the tenant (feeds ris_unbilled_count)."""
    async with get_conn() as conn:
        from db.ris_charges import RisCharges
        return await RisCharges(conn).count_pending(tenant)


class RisUnbilledHandler(HTTPEndpoint):
    """S11-07: GET /ris/billing/unbilled — aging report.

    R2-02-14: every read also publishes the SLA gauges (5-day / 10-day
    buckets) so Prometheus sees the backlog even without a scraper inside
    the billing flow. R2-02-06: a >10-day backlog fires a throttled
    biller/manager alert — best-effort, never fails the query.
    """

    @requires_permission(Permission.BILLING_READ)
    async def get(self, request):
        tenant = effective_tenant(request) or 'default'
        async with get_conn() as conn:
            from db.ris_charges import RisCharges
            groups, total = await RisCharges(conn).aging_groups(tenant)
        # Tolerate any aging-group shape; buckets are best-effort
        # instrumentation, never a contract of the query.
        bucket = {(g.get('age_bucket') or ''): (g.get('n') or 0)
                  for g in groups}
        over5 = (bucket.get('5-10 days', 0) + bucket.get('>10 days', 0))
        over10 = bucket.get('>10 days', 0)
        try:
            ris_unbilled_over_5d.set(over5)
            ris_unbilled_over_10d.set(over10)
        except Exception:
            pass
        if over10:
            try:
                from services.billing_alerts import escalate_aging
                await escalate_aging(None, tenant, over10=over10)
            except Exception:
                pass
        return ok({
            'groups': [dict(r) for r in groups],
            'total_unbilled': total,
        })


class RisClaimSubmitHandler(HTTPEndpoint):
    """S11-09: POST /ris/billing/claims/{id}/submit — 837 export stub."""

    @requires_permission(Permission.BILLING_WRITE)
    async def post(self, request):
        charge_id = request.path_params['id']
        tenant = effective_tenant(request) or 'default'
        async with get_conn() as conn:
            from db.ris_charges import RisCharges, RisClaims
            charge = await RisCharges(conn).get(charge_id, tenant)
            if not charge:
                return not_found('Charge not found')
            import random
            claim_number = f'CLM-{random.randint(100000, 999999)}'
            result = await RisClaims(conn).submit(
                charge_id, claim_number, tenant_id=tenant)
            from db.audit_log import AuditLog
            await AuditLog(conn).log_event(
                event_type='billing.claim_submitted',
                resource_id=charge_id,
                resource_type='ris_claims',
                actor_id=request.user.id,
                tenant=tenant,
            )
        return ok({'id': result['id'], 'claim_number': claim_number, 'status': result['status']})


class RisDenialQueueHandler(HTTPEndpoint):
    """R2-02-01: GET /ris/billing/denials — the coder's rework queue."""

    @requires_permission(Permission.BILLING_READ)
    async def get(self, request):
        tenant = effective_tenant(request) or 'default'
        async with get_conn() as conn:
            from db.ris_charges import RisClaims
            rows = await RisClaims(conn).list_rework(tenant)
        return ok({'data': [_json_row(r) for r in rows]})


class RisDenialImportHandler(HTTPEndpoint):
    """R2-02-01: POST /ris/billing/denials/import — 835-style intake.

    Parses the payer's reason code instead of stamping a fixed DEN-001,
    and appends a history event so the rework trail starts at intake.
    The legacy /denials/{id}/rework route delegates here.
    """

    @requires_permission(Permission.BILLING_WRITE)
    async def post(self, request):
        try:
            payload = await request.json()
        except Exception:
            payload = {}
        tenant = effective_tenant(request) or 'default'
        claim_id = str(payload.get('claim_id')
                       or request.path_params.get('id') or '')
        if not claim_id:
            return api_error('VALIDATION', 'claim_id required', status=422)
        from db.ris_charges import parse_denial
        parsed = parse_denial(payload)
        async with get_conn() as conn:
            from db.ris_charges import RisClaims
            claim = await RisClaims(conn).get(claim_id, tenant)
            if not claim:
                return not_found('Claim not found')
            result = await RisClaims(conn).record_denial_with_event(
                claim_id, parsed['code'], parsed['reason'], tenant_id=tenant)
            from db.audit_log import AuditLog
            await AuditLog(conn).log_event(
                event_type='billing.denial_recorded',
                resource_id=claim_id,
                resource_type='ris_claims',
                actor_id=getattr(request.user, 'id', ''),
                details={'code': parsed['code']},
                tenant=tenant,
            )
        return ok({'id': claim_id,
                   'status': result['status'] if result else 'DENIED',
                   'code': parsed['code']})


class RisClaimResubmitHandler(HTTPEndpoint):
    """R2-02-03: POST /ris/billing/claims/{id}/resubmit — correction +
    resubmission with an attributable history row."""

    @requires_permission(Permission.BILLING_WRITE)
    async def post(self, request):
        claim_id = request.path_params['id']
        tenant = effective_tenant(request) or 'default'
        try:
            body = await request.json()
        except Exception:
            body = {}
        note = str(body.get('note') or '')
        async with get_conn() as conn:
            from db.ris_charges import RisClaims
            result = await RisClaims(conn).correct_and_resubmit(
                claim_id, note=note,
                actor=str(getattr(request.user, 'id', '')),
                tenant_id=tenant)
            if not result:
                return not_found('Claim not found')
            from db.audit_log import AuditLog
            await AuditLog(conn).log_event(
                event_type='billing.claim_resubmitted',
                resource_id=claim_id,
                resource_type='ris_claims',
                actor_id=getattr(request.user, 'id', ''),
                details={'note': note[:200]},
                tenant=tenant,
            )
        return ok({'id': claim_id, 'status': result['status']})


class RisClaimHistoryHandler(HTTPEndpoint):
    """R2-02-03: GET /ris/billing/claims/{id}/history — full rework trail."""

    @requires_permission(Permission.BILLING_READ)
    async def get(self, request):
        claim_id = request.path_params['id']
        tenant = effective_tenant(request) or 'default'
        async with get_conn() as conn:
            from db.ris_charges import RisClaims
            rows = await RisClaims(conn).get_history(claim_id, tenant)
        return ok({'data': [_json_row(r) for r in rows]})


class RisReconciliationHandler(HTTPEndpoint):
    """S11-13: GET /ris/billing/reconciliation — signed vs charged."""

    @requires_permission(Permission.BILLING_READ)
    async def get(self, request):
        tenant = effective_tenant(request) or 'default'
        async with get_conn() as conn:
            from db.ris_charges import RisCharges
            stats = await RisCharges(conn).reconciliation(tenant)
        signed = stats.get('signed') or 0
        charged = stats.get('charged') or 0
        rate = round(charged / signed * 100, 1) if signed else 100.0
        return ok({
            'signed_reports': signed,
            'charged_reports': charged,
            'capture_rate_pct': rate,
        })
