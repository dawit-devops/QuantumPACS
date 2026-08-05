"""R09 Cashier/Billing data layer — table constants and money conversion.

The billing endpoints execute raw asyncpg SQL with $1 parameters directly
on the connection (see api/billing.py); this module centralizes the billing
table names and the conversion every NUMERIC(12,2) column requires.

Why: asyncpg returns NUMERIC columns as Decimal, and the JSON encoder used
by api.response (allow_nan=False, no Decimal default) cannot serialize
them. money() converts to float so responses never fail to serialize.
Table DDL is owned by migration 037 — no sync_db here, by design.
"""
from decimal import Decimal

BILLING_TABLES = [
    'procedure_pricing_catalog',
    'invoice',
    'invoice_line',
    'payment',
    'receipt',
    'claim',
    'refund',
    'quote',
    'payment_plan',
    'payment_plan_installment',
    'shift_reconciliation',
]

PAYMENT_METHODS = ('cash', 'card', 'check')


def money(value):
    """Convert a NUMERIC(12,2) value (Decimal or int/float) to a rounded float.

    None-safe so aggregate results (e.g. COALESCE(SUM(...), 0)) and
    unset columns can pass through without a type guard at every call site.
    """
    if value is None:
        return 0.0
    if isinstance(value, Decimal):
        value = float(value)
    return round(float(value), 2)
