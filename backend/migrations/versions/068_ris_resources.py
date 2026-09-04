"""RIS scheduling capacity — ris_resources + ris_resource_schedules (S4-06)

Revision ID: 068
Revises: 067
Create Date: 2026-08-19

Why
---
Sprint S4 (docs/RIS-integration/CONSOLIDATED_SPRINT_PLAN.md S4-06) introduces
schedulable capacity for the booking engine: rooms, modalities and
technologists, each with weekly availability windows. The scheduling engine
(S4-10) resolves slot conflicts against ris_appointments (migration 069)
and these schedules; resources seed the calendar grid UI (S4-08/S4-14).
As with 066/067, the spec's facility_id REFERENCES facilities(id) is
replaced by a tenant_id tag column — QuantumPACS has no facilities table;
isolation is per-tenant DB pools (TenantMiddleware + db/conn.py). A resource
name is unique per tenant.

Rollback
--------
Drops both tables. Safe: no production data exists yet (feature not shipped).
"""

import sqlalchemy as sa
from alembic import op

revision = '068'
down_revision = '067'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'ris_resources',
        sa.Column('id', sa.UUID(), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', sa.Text(), nullable=True),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('resource_type', sa.Text(), nullable=False),
        sa.Column('modality', sa.Text(), nullable=False, server_default=''),
        sa.Column('location', sa.Text(), nullable=False, server_default=''),
        sa.Column('status', sa.Text(), nullable=False, server_default='ACTIVE'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("resource_type IN ('ROOM', 'MODALITY', 'TECH')",
                           name='ck_ris_resources_type'),
        sa.CheckConstraint("status IN ('ACTIVE', 'INACTIVE')",
                           name='ck_ris_resources_status'),
        sa.UniqueConstraint('tenant_id', 'name', name='uq_ris_resource_name'),
    )
    op.create_index('ix_ris_resources_tenant_type', 'ris_resources',
                    ['tenant_id', 'resource_type'])
    op.create_index('ix_ris_resources_modality', 'ris_resources', ['modality'])

    op.create_table(
        'ris_resource_schedules',
        sa.Column('id', sa.UUID(), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', sa.Text(), nullable=True),
        sa.Column('resource_id', sa.UUID(), sa.ForeignKey('ris_resources.id', ondelete='CASCADE'),
                  nullable=False),
        sa.Column('day_of_week', sa.Integer(), nullable=False),
        sa.Column('start_time', sa.Time(), nullable=False),
        sa.Column('end_time', sa.Time(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint('day_of_week BETWEEN 0 AND 6', name='ck_ris_schedules_dow'),
        sa.CheckConstraint('end_time > start_time', name='chk_ris_schedule_end_after_start'),
    )
    op.create_index('ix_ris_schedules_resource', 'ris_resource_schedules', ['resource_id'])
    op.create_index('ix_ris_schedules_tenant_day', 'ris_resource_schedules',
                    ['tenant_id', 'day_of_week'])


def downgrade():
    op.drop_table('ris_resource_schedules')
    op.drop_table('ris_resources')