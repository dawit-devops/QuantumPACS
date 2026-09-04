"""RIS order intake schema — ris_orders + ris_order_procedures (E-RIS-03)

Revision ID: 066
Revises: 065
Create Date: 2026-08-18

Why
---
The RIS program (docs/RIS-integration/ris-integration-spec.md §3.2) starts
with order intake: ris_orders holds the order lifecycle
(ORDERED→…→SIGNED), ris_order_procedures one-to-many ordered procedures.
The spec models facility_id uuid REFERENCES facilities(id), but QuantumPACS
has no facilities table — isolation is per-tenant DB pools (TenantMiddleware
+ db/conn.py), so tenant scope is a tenant_id tag column like exams/
worklist. Accession uniqueness is enforced per tenant via
UNIQUE (tenant_id, accession_number). Runtime sync_db() in db/ris_orders.py
stays as idempotent self-healing; this migration is the schema chain.

Rollback
--------
Drops both tables. Safe: no production data exists yet (feature not shipped).
"""

import sqlalchemy as sa
from alembic import op

revision = '066'
down_revision = '065'
branch_labels = None
depends_on = None

ORDER_STATUSES = ('ORDERED', 'SCHEDULED', 'ARRIVED', 'IN_PROGRESS',
                  'COMPLETED', 'READ', 'SIGNED', 'CANCELLED')
PRIORITIES = ('ROUTINE', 'URGENT', 'STAT')


def upgrade():
    op.create_table(
        'ris_orders',
        sa.Column('id', sa.Uuid(), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', sa.Text()),
        sa.Column('accession_number', sa.Text(), nullable=False),
        sa.Column('patient_id', sa.Text(), nullable=False),
        sa.Column('patient_name', sa.Text(), server_default=''),
        sa.Column('patient_dob', sa.Date()),
        sa.Column('referring_physician', sa.Text(), server_default=''),
        sa.Column('clinical_indication', sa.Text(), server_default=''),
        sa.Column('priority', sa.Text(), nullable=False, server_default='ROUTINE'),
        sa.Column('status', sa.Text(), nullable=False, server_default='ORDERED'),
        sa.Column('prior_auth_status', sa.Text(), nullable=False, server_default='NOT_REQUIRED'),
        sa.Column('created_by', sa.Text(), server_default=''),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.CheckConstraint(
            "priority IN ('ROUTINE', 'URGENT', 'STAT')",
            name='ck_ris_orders_priority',
        ),
        sa.CheckConstraint(
            "status IN ('ORDERED', 'SCHEDULED', 'ARRIVED', 'IN_PROGRESS',"
            " 'COMPLETED', 'READ', 'SIGNED', 'CANCELLED')",
            name='ck_ris_orders_status',
        ),
        sa.CheckConstraint(
            "prior_auth_status IN ('NOT_REQUIRED', 'REQUIRED', 'PENDING',"
            " 'APPROVED', 'DENIED', 'EXPIRED')",
            name='ck_ris_orders_prior_auth',
        ),
        sa.UniqueConstraint('tenant_id', 'accession_number', name='uq_ris_order_accession'),
    )
    op.create_index('ix_ris_orders_tenant_status', 'ris_orders', ['tenant_id', 'status'])
    op.create_index('ix_ris_orders_patient', 'ris_orders', ['patient_id'])
    op.create_index(
        'ix_ris_orders_scheduled', 'ris_orders', ['tenant_id', 'status', 'created_at'],
        postgresql_where=sa.text("status IN ('ORDERED', 'SCHEDULED')"),
    )

    op.create_table(
        'ris_order_procedures',
        sa.Column('id', sa.Uuid(), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('order_id', sa.Uuid(), sa.ForeignKey('ris_orders.id', ondelete='CASCADE'), nullable=False),
        sa.Column('tenant_id', sa.Text()),
        sa.Column('procedure_code', sa.Text(), nullable=False),
        sa.Column('procedure_name', sa.Text(), nullable=False),
        sa.Column('modality', sa.Text(), nullable=False),
        sa.Column('body_part', sa.Text(), server_default=''),
        sa.Column('laterality', sa.Text(), server_default=''),
        sa.Column('contrast', sa.Boolean(), server_default=sa.text('false')),
        sa.Column('cpt_code', sa.Text(), server_default=''),
        sa.Column('icd10_code', sa.Text(), server_default=''),
        sa.Column('status', sa.Text(), nullable=False, server_default='ORDERED'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.CheckConstraint(
            "status IN ('ORDERED', 'SCHEDULED', 'IN_PROGRESS', 'COMPLETED')",
            name='ck_ris_order_procedures_status',
        ),
        sa.UniqueConstraint('order_id', 'procedure_code', name='uq_order_proc_per_order'),
    )


def downgrade():
    op.drop_table('ris_order_procedures')
    op.drop_table('ris_orders')