"""RIS interface engine schema — ris_hl7_messages + endpoints + events (E-RIS-02)

Revision ID: 067
Revises: 066
Create Date: 2026-08-18

Why
---
The RIS program's interface engine (docs/RIS-integration/ris-integration-spec.md
§3.2 v5, sprint S3-01/02/03) needs an exception queue: every inbound HL7
message is persisted with a status lifecycle (RECEIVED→PARSED→PROCESSED,
or FAILED with retry_count) so nothing is dropped silently and failed
messages can be replayed. ris_interface_endpoints tracks registered
connections; ris_interface_events feeds the interface health dashboard
and alerting. As with 066 (ris_orders), the spec's facility_id REFERENCES
facilities(id) is replaced by a tenant_id tag column — QuantumPACS has no
facilities table; isolation is per-tenant DB pools (TenantMiddleware +
db/conn.py). The legacy hl7_messages table stays as the audit mirror the
existing admin endpoints read; ris_hl7_messages is the engine's own
lifecycle store.

Rollback
--------
Drops all three tables. Safe: no production data exists yet (feature not
shipped).
"""

import sqlalchemy as sa
from alembic import op

revision = '067'
down_revision = '066'
branch_labels = None
depends_on = None

INTERFACE_TYPES = ('HL7_ADT', 'HL7_ORM', 'HL7_ORU', 'DICOM_MWL', 'DICOM_MPPS', 'FHIR')
PROTOCOLS = ('HL7V2', 'DICOM', 'FHIR')
MESSAGE_STATUSES = ('RECEIVED', 'PARSED', 'PROCESSED', 'FAILED', 'RETRYING',
                    'ACKNOWLEDGED', 'QUEUED')
SEVERITIES = ('INFO', 'WARNING', 'ERROR', 'CRITICAL')


def upgrade():
    op.create_table(
        'ris_interface_endpoints',
        sa.Column('id', sa.Uuid(), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', sa.Text()),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('interface_type', sa.String(20), nullable=False),
        sa.Column('protocol', sa.String(20), nullable=False),
        sa.Column('config', sa.JSON(), server_default=sa.text("'{}'::jsonb")),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true')),
        sa.Column('last_message_at', sa.DateTime(timezone=True)),
        sa.Column('message_count', sa.BigInteger(), server_default=sa.text('0')),
        sa.Column('error_count', sa.BigInteger(), server_default=sa.text('0')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.CheckConstraint(
            "interface_type IN ('HL7_ADT', 'HL7_ORM', 'HL7_ORU', 'DICOM_MWL',"
            " 'DICOM_MPPS', 'FHIR')",
            name='ck_ris_endpoints_interface_type',
        ),
        sa.CheckConstraint(
            "protocol IN ('HL7V2', 'DICOM', 'FHIR')",
            name='ck_ris_endpoints_protocol',
        ),
    )

    op.create_table(
        'ris_hl7_messages',
        sa.Column('id', sa.Uuid(), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', sa.Text()),
        sa.Column('endpoint_id', sa.Uuid(), sa.ForeignKey('ris_interface_endpoints.id')),
        sa.Column('message_type', sa.String(10), nullable=False),
        sa.Column('trigger_event', sa.String(10), nullable=False),
        sa.Column('control_id', sa.String(100), nullable=False),
        sa.Column('raw_message', sa.Text(), nullable=False),
        sa.Column('parsed_segments', sa.JSON()),
        sa.Column('status', sa.String(20), nullable=False, server_default='RECEIVED'),
        sa.Column('error_message', sa.Text()),
        sa.Column('retry_count', sa.Integer(), server_default=sa.text('0')),
        sa.Column('max_retries', sa.Integer(), server_default=sa.text('3')),
        sa.Column('processed_at', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.CheckConstraint(
            "status IN ('RECEIVED', 'PARSED', 'PROCESSED', 'FAILED', 'RETRYING',"
            " 'ACKNOWLEDGED', 'QUEUED')",
            name='ck_ris_hl7_messages_status',
        ),
    )
    op.create_index(
        'ix_ris_hl7_tenant_status', 'ris_hl7_messages', ['tenant_id', 'status', 'created_at'],
    )
    op.create_index('ix_ris_hl7_control', 'ris_hl7_messages', ['control_id'])
    op.create_index(
        'ix_ris_hl7_type', 'ris_hl7_messages', ['message_type', 'trigger_event'],
    )

    op.create_table(
        'ris_interface_events',
        sa.Column('id', sa.Uuid(), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', sa.Text()),
        sa.Column('endpoint_id', sa.Uuid(), sa.ForeignKey('ris_interface_endpoints.id')),
        sa.Column('event_type', sa.String(30), nullable=False),
        sa.Column('severity', sa.String(10), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('metadata', sa.JSON(), server_default=sa.text("'{}'::jsonb")),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.CheckConstraint(
            "severity IN ('INFO', 'WARNING', 'ERROR', 'CRITICAL')",
            name='ck_ris_interface_events_severity',
        ),
    )
    op.create_index(
        'ix_ris_interface_events_tenant', 'ris_interface_events', ['tenant_id', 'created_at'],
    )


def downgrade():
    op.drop_table('ris_interface_events')
    op.drop_table('ris_hl7_messages')
    op.drop_table('ris_interface_endpoints')