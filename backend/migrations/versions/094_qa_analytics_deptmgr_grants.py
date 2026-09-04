"""Add QA_ANALYTICS_READ permission + dept_manager grant updates

Revision ID: 094
Revises: 093
Create Date: 2026-08-24

Why
---
Adds the QA_ANALYTICS_READ permission for the QA Analytics Dashboard
(QA-02 through QA-07 in the UI/UX redesign spec). Also adds EQUIPMENT_READ
and SCHEDULE_WRITE to the dept_manager role for DM-04 (Equipment Utilization)
and DM-07 (Staff Schedule Management).

Schema
------
No table changes. Permission enum update + built-in role grant update.

References
----------
- docs/ui-ux-redesign-spec.md §2.8 (QA Manager), §2.9 (Department Manager)
- docs/audit-qa-deptmanager-gap-analysis.md
"""

from alembic import op
from sqlalchemy import text

revision = '094'
down_revision = '093'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    # Add QA_ANALYTICS_READ to any role that holds QA_READ. The built-in
    # qa_team was removed in 052, but custom QA roles may exist.
    conn.execute(text("""
        UPDATE roles
        SET permissions = permissions || '["QA_ANALYTICS_READ"]'::jsonb,
            updated_at = now()
        WHERE permissions ? 'QA_READ'
          AND NOT (permissions ? 'QA_ANALYTICS_READ')
    """))

    # Add EQUIPMENT_READ and SCHEDULE_WRITE to dept_manager built-in role.
    conn.execute(text("""
        UPDATE roles
        SET permissions = permissions ||
              '["EQUIPMENT_READ", "SCHEDULE_WRITE"]'::jsonb,
            updated_at = now()
        WHERE slug = 'dept_manager'
          AND built_in = TRUE
          AND NOT (permissions ? 'EQUIPMENT_READ')
    """))


def downgrade():
    conn = op.get_bind()
    # Remove QA_ANALYTICS_READ from roles that have it
    conn.execute(text("""
        UPDATE roles
        SET permissions = (
            SELECT COALESCE(jsonb_agg(val), '[]'::jsonb)
            FROM jsonb_array_elements_text(permissions) AS val
            WHERE val != 'QA_ANALYTICS_READ'
        )
        WHERE permissions ? 'QA_ANALYTICS_READ'
    """))

    # Remove EQUIPMENT_READ and SCHEDULE_WRITE from dept_manager
    conn.execute(text("""
        UPDATE roles
        SET permissions = (
            SELECT COALESCE(jsonb_agg(val), '[]'::jsonb)
            FROM jsonb_array_elements_text(permissions) AS val
            WHERE val NOT IN ('EQUIPMENT_READ', 'SCHEDULE_WRITE')
        )
        WHERE slug = 'dept_manager'
    """))
