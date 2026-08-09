"""Index tenant-hot columns for portal, front desk and patient search

Revision ID: 047
Revises: 046
Create Date: 2026-08-09

Why
---
PACS audit remediation (docs/PACS_AUDIT-2026-08-06.md), R5-11: at demo scale
the missing indexes are invisible, but they degrade linearly with per-tenant
volume:

- Portal orders/reports filter `exams WHERE patient_id` (db/portal.py) and
  the waiting queue joins on it — no index → seq-scan.
- `visits(visit_date)` is filtered by the waiting queue and list_visits —
  only patient_id/status were indexed in 037.
- Both patient searches run `name ILIKE '%q%'` on every keystroke (≥2 chars)
  — no trigram index, full scan.

Schema
------
Indexes only, no column changes. pg_trgm is an extension (CREATE EXTENSION
IF NOT EXISTS keeps environments honest when it is already loaded).

Rollback
--------
Drops the extension-owned and plain indexes, leaves pg_trgm installed.
"""

from alembic import op

revision = '047'
down_revision = '046'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("CREATE INDEX IF NOT EXISTS ix_exams_patient ON exams(patient_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_visits_visit_date ON visits(visit_date)")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_patients_name_trgm"
        " ON patients USING gin (name gin_trgm_ops)"
    )


def downgrade():
    op.execute("DROP INDEX IF EXISTS ix_patients_name_trgm")
    op.execute("DROP INDEX IF EXISTS ix_visits_visit_date")
    op.execute("DROP INDEX IF EXISTS ix_exams_patient")