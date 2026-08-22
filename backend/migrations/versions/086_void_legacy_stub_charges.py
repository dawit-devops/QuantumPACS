"""Void legacy coding-less stub charges (A1b, GAP_AUDIT_TDD_PIPELINE.md)

Revision ID: 086
Revises: 085
Create Date: 2026-08-22

Migration 077 preserved the S8-14 runtime stub rows (bare INSERT: no CPT,
$0 amount) as PENDING charges. While drop_charge_stub was still wired into
Reports.sign() those rows kept regenerating; A1 removed that writer, and
the surviving rows are dead weight in the billing queue — they poison the
unbilled-aging gauges and the capture-rate reconciliation (every one counts
as a signed-but-unbilled report). This migration flips exactly the legacy
signature — status PENDING, no CPT code, $0 amount — to VOID. Rows a coder
or biller has touched (BILLED/PAID/DENIED) and enriched rows are untouched.

Downgrade restores the flipped rows to PENDING by the same predicate.
"""

from alembic import op

revision = '086'
down_revision = '085'
branch_labels = None
depends_on = None

# Exported for tests: tests/test_migrations.py executes these exact
# statements against a seeded dev DB.
VOID_SQL = """
UPDATE ris_charges
SET status = 'VOID', updated_at = now()
WHERE status = 'PENDING'
  AND (cpt_code IS NULL OR cpt_code = '')
  AND charge_amount = 0
"""

RESTORE_SQL = """
UPDATE ris_charges
SET status = 'PENDING', updated_at = now()
WHERE status = 'VOID'
  AND (cpt_code IS NULL OR cpt_code = '')
  AND charge_amount = 0
"""


def upgrade():
    op.execute(VOID_SQL)


def downgrade():
    op.execute(RESTORE_SQL)
