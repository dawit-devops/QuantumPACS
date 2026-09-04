"""RIS Billing & Revenue — ris_charges, ris_claims, ris_coding_map (S11)

Revision ID: 077
Revises: 076
Create Date: 2026-08-21

Why
---
Sprint S11 replaces the runtime ris_charges stub created by
api/billing.drop_charge_stub() (S8-14) with the spec schema
(ris-integration-spec.md §3.8 migration v4). The stub table diverged:
it had report_id/exam_id/accession_number/status/amount/created_by but
no patient/coding/order/tenant columns. The migration renames the stub
to ris_charges_v0, creates the full table, copies the existing rows
(amount -> charge_amount, 'pending' -> 'PENDING'), and drops the stub.
ris_claims tracks 837 export/835 denial state; ris_coding_map is the
seedable CPT/ICD-10 suggestion source (S11-02).

The codebase has no facilities table — isolation is per-tenant DB pools
(TenantMiddleware + db/conn.py), so tenant scope is a tenant_id tag
column exactly like ris_orders/ris_critical_results. S11-15 "RLS on
charges" is satisfied by tenant_id scoping in every query.

Rollback
--------
Drops ris_claims, ris_coding_map and ris_charges; restores the stub
table shape from ris_charges_v0 (kept until downgrade for safety).
"""

from alembic import op

revision = '077'
down_revision = '076'
branch_labels = None
depends_on = None

CHARGES_STATUSES = ('PENDING', 'BILLED', 'PAID', 'DENIED', 'VOID')
CLAIMS_STATUSES = ('DRAFT', 'SUBMITTED', 'ACKNOWLEDGED', 'PAID', 'DENIED')


def upgrade():
    # 1. Preserve the runtime stub (created by S8-14 drop_charge_stub) so the
    #    17 dev rows survive, then build the real table.
    op.execute('''
    DO $$
    BEGIN
        IF to_regclass('public.ris_charges') IS NOT NULL THEN
            EXECUTE 'ALTER TABLE ris_charges RENAME TO ris_charges_v0';
        END IF;
    END
    $$;
    ''')

    op.execute("""
    CREATE TABLE ris_charges (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        tenant_id TEXT DEFAULT 'default',
        order_id UUID REFERENCES ris_orders(id),
        report_id UUID REFERENCES reports(id),
        exam_id UUID,
        accession_number TEXT NOT NULL DEFAULT '',
        patient_id TEXT NOT NULL DEFAULT '',
        patient_name TEXT DEFAULT '',
        cpt_code TEXT DEFAULT '',
        cpt_description TEXT DEFAULT '',
        icd10_code TEXT DEFAULT '',
        charge_amount NUMERIC(12,2) NOT NULL DEFAULT 0,
        status TEXT NOT NULL DEFAULT 'PENDING'
            CHECK (status IN ('PENDING', 'BILLED', 'PAID', 'DENIED', 'VOID')),
        prior_auth_id UUID,
        created_by TEXT DEFAULT '',
        created_at TIMESTAMPTZ DEFAULT now(),
        updated_at TIMESTAMPTZ DEFAULT now()
    )
    """)
    op.execute(
        'CREATE INDEX IF NOT EXISTS ix_ris_charges_tenant_status '
        'ON ris_charges(tenant_id, status)')
    op.execute(
        'CREATE INDEX IF NOT EXISTS ix_ris_charges_patient '
        'ON ris_charges(patient_id)')
    op.execute(
        'CREATE INDEX IF NOT EXISTS ix_ris_charges_report '
        'ON ris_charges(report_id)')
    op.execute(
        'CREATE INDEX IF NOT EXISTS ix_ris_charges_unbilled '
        'ON ris_charges(tenant_id, created_at) WHERE status = \'PENDING\'')

    # 2. Copy the stub rows (amount -> charge_amount, 'pending' -> 'PENDING').
    op.execute('''
    DO $$
    BEGIN
        IF to_regclass('public.ris_charges_v0') IS NOT NULL THEN
            EXECUTE $q$
                INSERT INTO ris_charges
                    (id, report_id, exam_id, accession_number, charge_amount,
                     status, created_by, created_at)
                SELECT id, report_id, exam_id, accession_number,
                       COALESCE(amount, 0), 'PENDING', created_by, created_at
                FROM ris_charges_v0
            $q$;
            EXECUTE 'DROP TABLE ris_charges_v0';
        END IF;
    END
    $$;
    ''')

    # 3. ris_claims — 837 export / 835 denial tracking.
    op.execute("""
    CREATE TABLE ris_claims (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        tenant_id TEXT DEFAULT 'default',
        charge_id UUID NOT NULL REFERENCES ris_charges(id),
        claim_number TEXT,
        payer_id TEXT,
        payer_name TEXT,
        submitted_at TIMESTAMPTZ,
        status TEXT NOT NULL DEFAULT 'DRAFT'
            CHECK (status IN ('DRAFT', 'SUBMITTED', 'ACKNOWLEDGED', 'PAID', 'DENIED')),
        rejection_code TEXT,
        rejection_reason TEXT,
        paid_amount NUMERIC(12,2),
        created_at TIMESTAMPTZ DEFAULT now(),
        updated_at TIMESTAMPTZ DEFAULT now()
    )
    """)
    op.execute(
        'CREATE INDEX IF NOT EXISTS ix_ris_claims_tenant_status '
        'ON ris_claims(tenant_id, status)')
    op.execute(
        'CREATE INDEX IF NOT EXISTS ix_ris_claims_charge '
        'ON ris_claims(charge_id)')
    op.execute(
        'CREATE INDEX IF NOT EXISTS ix_ris_claims_unbilled '
        'ON ris_claims(tenant_id, submitted_at) '
        'WHERE status IN (\'DRAFT\', \'DENIED\')')

    # 4. ris_coding_map — seedable CPT/ICD-10 suggestion source (S11-02).
    op.execute("""
    CREATE TABLE ris_coding_map (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        tenant_id TEXT DEFAULT 'default',
        procedure_code TEXT NOT NULL,
        procedure_desc TEXT DEFAULT '',
        cpt_code TEXT DEFAULT '',
        cpt_description TEXT DEFAULT '',
        icd10_code TEXT DEFAULT '',
        icd10_description TEXT DEFAULT '',
        active BOOLEAN NOT NULL DEFAULT true,
        created_at TIMESTAMPTZ DEFAULT now(),
        updated_at TIMESTAMPTZ DEFAULT now(),
        UNIQUE (tenant_id, procedure_code)
    )
    """)


def downgrade():
    op.drop_table('ris_coding_map')
    op.drop_table('ris_claims')
    op.drop_table('ris_charges')
    # Restore the stub table shape (S8-14) so downgrade is safe.
    op.execute("""
    CREATE TABLE IF NOT EXISTS ris_charges_v0 (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        report_id UUID,
        exam_id UUID,
        accession_number TEXT,
        status TEXT DEFAULT 'pending',
        amount NUMERIC(12,2) DEFAULT 0,
        created_by TEXT,
        created_at TIMESTAMPTZ DEFAULT now()
    )
    """)
    op.execute("""
    CREATE TABLE ris_charges (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        report_id UUID,
        exam_id UUID,
        accession_number TEXT,
        status TEXT DEFAULT 'pending',
        amount NUMERIC(12,2) DEFAULT 0,
        created_by TEXT,
        created_at TIMESTAMPTZ DEFAULT now()
    )
    """)
    op.execute("""
    INSERT INTO ris_charges
        (id, report_id, exam_id, accession_number, status, amount, created_by, created_at)
    SELECT id, report_id, exam_id, accession_number, 'pending', charge_amount,
           created_by, created_at
    FROM ris_charges_v0
    """)
    op.execute('DROP TABLE ris_charges_v0')
