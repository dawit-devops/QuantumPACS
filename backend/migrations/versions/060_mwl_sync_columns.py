"""MWL-RS mirror sync columns for worklist_entries

Revision ID: 060
Revises: 059
Create Date: 2026-08-15

Why
---
ADR-028 Phase 3: when the DICOMweb proxy is enabled (dicom_proxy=true),
modalities are served by the dcm4chee archive, so QuantumPACS mirrors its
worklist_entries into the archive via MWL-RS. The background sync worker
needs per-row bookkeeping:

- mwl_synced_at: last successful mirror; rows are dirty when NULL or older
  than updated_at.
- mwl_sync_error: last failure message; a non-empty value keeps the row
  dirty so the worker retries every cycle.

The archive-side key needs no column: MWL-RS POST /mwlitems honors a
top-level StudyInstanceUID in the payload (verified live 2026-08-15) and
is an upsert on it, so the worker derives a deterministic UID from the row
(tenant|patient|accession|SPS id) instead of storing the echoed one.

Schema
------
Two columns on worklist_entries. No data migration.

Rollback
--------
Drops the two columns.
"""

import sqlalchemy as sa
from alembic import op

revision = '060'
down_revision = '059'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('worklist_entries', sa.Column('mwl_synced_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('worklist_entries', sa.Column('mwl_sync_error', sa.Text(), nullable=False, server_default=''))


def downgrade():
    op.drop_column('worklist_entries', 'mwl_sync_error')
    op.drop_column('worklist_entries', 'mwl_synced_at')