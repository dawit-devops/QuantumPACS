"""DICOM audit remediation: extended MWL fields (ME-03)

Revision ID: 043
Revises: 042
Create Date: 2026-08-07

Why
---
PACS audit (docs/PACS_AUDIT-2026-08-06.md) ME-03: MWL C-FIND responses
omitted RequestedProcedureCodeSequence, RequestedProcedurePriority,
ReasonForRequestedProcedure, ScheduledProcedureStepStatus,
ScheduledStationName, ScheduledPerformingPhysicianName and
ReferringPhysicianName. These are additive columns populated from the HL7
ORM segments; existing rows keep their empty defaults.

Rollback
--------
Drops the eight columns.
"""

from alembic import op

revision = '043'
down_revision = '042'
branch_labels = None
depends_on = None

_COLUMNS = (
    'requested_procedure_priority',
    'reason_for_requested_procedure',
    'requested_procedure_code',
    'requested_procedure_code_meaning',
    'requested_procedure_code_scheme',
    'scheduled_station_name',
    'scheduled_performing_physician',
    'referring_physician',
)


def upgrade():
    for col in _COLUMNS:
        op.execute(
            f"ALTER TABLE worklist_entries ADD COLUMN IF NOT EXISTS {col} TEXT DEFAULT ''"
        )


def downgrade():
    for col in _COLUMNS:
        op.execute(f"ALTER TABLE worklist_entries DROP COLUMN IF EXISTS {col}")
