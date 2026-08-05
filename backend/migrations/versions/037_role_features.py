"""Create role-feature tables: front desk, billing, equipment, nursing,
service director analytics, and hospital staff portal

Revision ID: 037
Revises: 036
Create Date: 2026-08-04

Why
---
Implements the v3 role packages verified 2026-08-04:
- R08 Front Desk (FR-R08-02..09): visits, order intake, appointments with
  conflict detection, consent capture, insurance/guarantor, waiting queue.
- R09 Cashier (FR-R09-01..08): invoices, payments (idempotent, tokenized),
  receipts, claims, refunds w/ approval, quotes, payment plans, shift
  reconciliation, procedure pricing catalog.
- R10 Biomedical Engineer (FR-R10-01..09): equipment registry, PM/QC
  schedules, downtime events, work orders, vendor contracts, parts inventory.
- R11 Nursing (FR-R11-01..10): prep checklists, vitals, safety confirmations
  (contrast gate), contrast records, reaction escalations, sedation,
  recovery/discharge, MAR, handoff notes.
- R03 Service Director (FR-R03-01..05, 10, 12, 14, 15): modality capacity,
  SLA breaches, dashboard audit, analytics report templates + deliveries.
- R19 Hospital Staff (FR-R19-01..10): patient-staff scope (minimum necessary),
  follow-up requests.

Money is NUMERIC(12,2) — never FLOAT (per docs/review-database.md).

Tables
------
39 new tables across the six domains (see above); two are seeded:
procedure_pricing_catalog (R09) and analytics_report_templates (R03).

Rollback
--------
Drops all new tables and indexes.

References
----------
- docs/requirements/front-desk/ (R08)
- docs/requirements/cashier/ (R09)
- docs/requirements/biomedical-engineer/ (R10)
- docs/requirements/nursing/ (R11)
- docs/requirements/service-director/ (R03)
- docs/requirements/hospital-staff/ (R19)
"""

from alembic import op

revision = "037"
down_revision = "036"
branch_labels = None
depends_on = None

NEW_TABLES = [
    # ---- R08 Front Desk ----
    ("""
    CREATE TABLE IF NOT EXISTS visits (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        patient_id TEXT NOT NULL,
        visit_date DATE DEFAULT CURRENT_DATE,
        status TEXT NOT NULL DEFAULT 'registered'
            CHECK (status IN ('registered', 'checked_in', 'in_progress', 'complete')),
        destination_room TEXT DEFAULT '',
        hl7_sync_status TEXT NOT NULL DEFAULT 'pending'
            CHECK (hl7_sync_status IN ('pending', 'synced', 'failed')),
        created_by TEXT DEFAULT '',
        created_at TIMESTAMPTZ DEFAULT now(),
        updated_at TIMESTAMPTZ DEFAULT now()
    )
    """),
    ("""
    CREATE TABLE IF NOT EXISTS visit_orders (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        visit_id UUID NOT NULL REFERENCES visits(id) ON DELETE CASCADE,
        patient_id TEXT NOT NULL,
        requested_procedure TEXT NOT NULL,
        indication TEXT DEFAULT '',
        urgency TEXT NOT NULL DEFAULT 'routine'
            CHECK (urgency IN ('routine', 'urgent', 'stat')),
        referring_physician TEXT DEFAULT '',
        status TEXT NOT NULL DEFAULT 'open'
            CHECK (status IN ('open', 'cancelled')),
        created_by TEXT DEFAULT '',
        created_at TIMESTAMPTZ DEFAULT now()
    )
    """),
    ("""
    CREATE TABLE IF NOT EXISTS appointments (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        patient_id TEXT NOT NULL,
        visit_id UUID REFERENCES visits(id) ON DELETE SET NULL,
        worklist_entry_id UUID,
        modality TEXT DEFAULT '',
        room TEXT DEFAULT '',
        technologist TEXT DEFAULT '',
        scheduled_date DATE,
        scheduled_time TIME,
        status TEXT NOT NULL DEFAULT 'scheduled'
            CHECK (status IN ('scheduled', 'checked_in', 'completed', 'cancelled')),
        created_by TEXT DEFAULT '',
        created_at TIMESTAMPTZ DEFAULT now(),
        updated_at TIMESTAMPTZ DEFAULT now()
    )
    """),
    ("""
    CREATE TABLE IF NOT EXISTS consent_documents (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        visit_id UUID NOT NULL REFERENCES visits(id) ON DELETE CASCADE,
        consent_type TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'required'
            CHECK (status IN ('required', 'attached', 'missing')),
        file_name TEXT DEFAULT '',
        attached_by TEXT DEFAULT '',
        attached_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ DEFAULT now()
    )
    """),
    ("""
    CREATE TABLE IF NOT EXISTS insurance_records (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        patient_id TEXT NOT NULL,
        visit_id UUID REFERENCES visits(id) ON DELETE SET NULL,
        policy_number TEXT DEFAULT '',
        guarantor_name TEXT DEFAULT '',
        authorization_status TEXT NOT NULL DEFAULT 'none'
            CHECK (authorization_status IN ('none', 'pending', 'approved', 'denied')),
        authorization_number TEXT DEFAULT '',
        notes TEXT DEFAULT '',
        created_by TEXT DEFAULT '',
        created_at TIMESTAMPTZ DEFAULT now(),
        updated_at TIMESTAMPTZ DEFAULT now()
    )
    """),
    # ---- R09 Cashier ----
    ("""
    CREATE TABLE IF NOT EXISTS procedure_pricing_catalog (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        procedure_code TEXT NOT NULL UNIQUE,
        description TEXT DEFAULT '',
        list_price NUMERIC(12, 2) NOT NULL DEFAULT 0,
        active BOOLEAN NOT NULL DEFAULT TRUE,
        created_at TIMESTAMPTZ DEFAULT now()
    )
    """),
    ("""
    CREATE TABLE IF NOT EXISTS invoice (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        patient_id TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'open'
            CHECK (status IN ('open', 'partially_paid', 'paid', 'written_off')),
        total_amount NUMERIC(12, 2) NOT NULL DEFAULT 0,
        paid_amount NUMERIC(12, 2) NOT NULL DEFAULT 0,
        balance NUMERIC(12, 2) NOT NULL DEFAULT 0,
        created_by TEXT DEFAULT '',
        created_at TIMESTAMPTZ DEFAULT now(),
        updated_at TIMESTAMPTZ DEFAULT now()
    )
    """),
    ("""
    CREATE TABLE IF NOT EXISTS invoice_line (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        invoice_id UUID NOT NULL REFERENCES invoice(id) ON DELETE CASCADE,
        procedure_code TEXT DEFAULT '',
        description TEXT DEFAULT '',
        quantity INTEGER NOT NULL DEFAULT 1,
        unit_price NUMERIC(12, 2) NOT NULL DEFAULT 0,
        discount_amount NUMERIC(12, 2) NOT NULL DEFAULT 0,
        line_total NUMERIC(12, 2) NOT NULL DEFAULT 0,
        created_at TIMESTAMPTZ DEFAULT now()
    )
    """),
    ("""
    CREATE TABLE IF NOT EXISTS payment (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        invoice_id UUID NOT NULL REFERENCES invoice(id) ON DELETE CASCADE,
        method TEXT NOT NULL CHECK (method IN ('cash', 'card', 'check')),
        amount NUMERIC(12, 2) NOT NULL,
        payment_date TIMESTAMPTZ DEFAULT now(),
        operator_id INTEGER,
        processor_token TEXT DEFAULT '',
        idempotency_key TEXT UNIQUE,
        split_group_id TEXT DEFAULT '',
        created_at TIMESTAMPTZ DEFAULT now()
    )
    """),
    ("""
    CREATE TABLE IF NOT EXISTS receipt (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        payment_id UUID NOT NULL UNIQUE REFERENCES payment(id) ON DELETE CASCADE,
        receipt_number TEXT NOT NULL UNIQUE,
        generated_at TIMESTAMPTZ DEFAULT now(),
        emailed_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ DEFAULT now()
    )
    """),
    ("""
    CREATE TABLE IF NOT EXISTS claim (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        invoice_id UUID NOT NULL REFERENCES invoice(id) ON DELETE CASCADE,
        status TEXT NOT NULL DEFAULT 'submitted'
            CHECK (status IN ('submitted', 'acknowledged', 'denied', 'appeal')),
        action_required BOOLEAN NOT NULL DEFAULT FALSE,
        source TEXT NOT NULL DEFAULT 'manual'
            CHECK (source IN ('external_feed', 'manual')),
        external_claim_id TEXT DEFAULT '',
        submitted_at TIMESTAMPTZ DEFAULT now(),
        created_at TIMESTAMPTZ DEFAULT now(),
        updated_at TIMESTAMPTZ DEFAULT now()
    )
    """),
    ("""
    CREATE TABLE IF NOT EXISTS refund (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        invoice_id UUID NOT NULL REFERENCES invoice(id) ON DELETE CASCADE,
        payment_id UUID,
        amount NUMERIC(12, 2) NOT NULL,
        reason TEXT DEFAULT '',
        status TEXT NOT NULL DEFAULT 'pending_approval'
            CHECK (status IN ('pending_approval', 'approved', 'applied', 'rejected')),
        threshold_exceeded BOOLEAN NOT NULL DEFAULT FALSE,
        approved_by TEXT DEFAULT '',
        approved_at TIMESTAMPTZ,
        created_by TEXT DEFAULT '',
        created_at TIMESTAMPTZ DEFAULT now(),
        updated_at TIMESTAMPTZ DEFAULT now()
    )
    """),
    ("""
    CREATE TABLE IF NOT EXISTS quote (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        patient_id TEXT NOT NULL,
        invoice_id UUID,
        procedure_code TEXT DEFAULT '',
        total NUMERIC(12, 2) NOT NULL DEFAULT 0,
        estimated_patient_responsibility NUMERIC(12, 2) NOT NULL DEFAULT 0,
        quoted_by TEXT DEFAULT '',
        quoted_at TIMESTAMPTZ DEFAULT now(),
        created_at TIMESTAMPTZ DEFAULT now()
    )
    """),
    ("""
    CREATE TABLE IF NOT EXISTS payment_plan (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        invoice_id UUID NOT NULL REFERENCES invoice(id) ON DELETE CASCADE,
        status TEXT NOT NULL DEFAULT 'active'
            CHECK (status IN ('active', 'completed', 'cancelled')),
        created_by TEXT DEFAULT '',
        created_at TIMESTAMPTZ DEFAULT now(),
        updated_at TIMESTAMPTZ DEFAULT now()
    )
    """),
    ("""
    CREATE TABLE IF NOT EXISTS payment_plan_installment (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        plan_id UUID NOT NULL REFERENCES payment_plan(id) ON DELETE CASCADE,
        installment_no INTEGER NOT NULL,
        amount NUMERIC(12, 2) NOT NULL,
        due_date DATE NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending'
            CHECK (status IN ('pending', 'paid', 'overdue')),
        paid_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ DEFAULT now()
    )
    """),
    ("""
    CREATE TABLE IF NOT EXISTS shift_reconciliation (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        cashier_id INTEGER,
        shift_date DATE NOT NULL DEFAULT CURRENT_DATE,
        expected_totals JSONB DEFAULT '{}'::jsonb,
        counted_cash NUMERIC(12, 2) NOT NULL DEFAULT 0,
        variance NUMERIC(12, 2) NOT NULL DEFAULT 0,
        variance_reason TEXT DEFAULT '',
        closed_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ DEFAULT now()
    )
    """),
    # ---- R10 Biomedical Engineer ----
    ("""
    CREATE TABLE IF NOT EXISTS equipment (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        identifier TEXT NOT NULL UNIQUE,
        modality TEXT DEFAULT '',
        manufacturer TEXT DEFAULT '',
        model TEXT DEFAULT '',
        serial_number TEXT DEFAULT '',
        location TEXT DEFAULT '',
        acquisition_date DATE,
        operational_status TEXT NOT NULL DEFAULT 'operational'
            CHECK (operational_status IN ('operational', 'maintenance', 'down', 'retired')),
        warranty_end_date DATE,
        created_by TEXT DEFAULT '',
        created_at TIMESTAMPTZ DEFAULT now(),
        updated_at TIMESTAMPTZ DEFAULT now()
    )
    """),
    ("""
    CREATE TABLE IF NOT EXISTS maintenance_schedules (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        equipment_id UUID NOT NULL REFERENCES equipment(id) ON DELETE CASCADE,
        schedule_type TEXT NOT NULL DEFAULT 'pm'
            CHECK (schedule_type IN ('pm', 'qc')),
        title TEXT DEFAULT '',
        frequency_days INTEGER NOT NULL DEFAULT 90,
        last_completed_at TIMESTAMPTZ,
        next_due_date DATE,
        status TEXT NOT NULL DEFAULT 'active'
            CHECK (status IN ('active', 'completed')),
        completed_by TEXT DEFAULT '',
        created_at TIMESTAMPTZ DEFAULT now(),
        updated_at TIMESTAMPTZ DEFAULT now()
    )
    """),
    ("""
    CREATE TABLE IF NOT EXISTS qc_records (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        equipment_id UUID NOT NULL REFERENCES equipment(id) ON DELETE CASCADE,
        schedule_id UUID,
        test_type TEXT DEFAULT '',
        pass_fail TEXT NOT NULL CHECK (pass_fail IN ('pass', 'fail')),
        measured_values JSONB DEFAULT '{}'::jsonb,
        tested_by TEXT DEFAULT '',
        tested_at TIMESTAMPTZ DEFAULT now(),
        created_at TIMESTAMPTZ DEFAULT now()
    )
    """),
    ("""
    CREATE TABLE IF NOT EXISTS downtime_events (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        equipment_id UUID NOT NULL REFERENCES equipment(id) ON DELETE CASCADE,
        start_at TIMESTAMPTZ DEFAULT now(),
        end_at TIMESTAMPTZ,
        cause_category TEXT DEFAULT '',
        impact TEXT DEFAULT '',
        resolution TEXT DEFAULT '',
        status TEXT NOT NULL DEFAULT 'open'
            CHECK (status IN ('open', 'closed')),
        created_by TEXT DEFAULT '',
        created_at TIMESTAMPTZ DEFAULT now(),
        updated_at TIMESTAMPTZ DEFAULT now()
    )
    """),
    ("""
    CREATE TABLE IF NOT EXISTS work_orders (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        equipment_id UUID NOT NULL REFERENCES equipment(id) ON DELETE CASCADE,
        description TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'open'
            CHECK (status IN ('open', 'in_progress', 'on_hold', 'resolved')),
        assigned_to TEXT DEFAULT '',
        notes TEXT DEFAULT '',
        resolved_at TIMESTAMPTZ,
        created_by TEXT DEFAULT '',
        created_at TIMESTAMPTZ DEFAULT now(),
        updated_at TIMESTAMPTZ DEFAULT now()
    )
    """),
    ("""
    CREATE TABLE IF NOT EXISTS vendor_contracts (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        equipment_id UUID NOT NULL REFERENCES equipment(id) ON DELETE CASCADE,
        vendor_name TEXT DEFAULT '',
        coverage_terms TEXT DEFAULT '',
        warranty_end_date DATE,
        response_sla_p1_minutes INTEGER DEFAULT 15,
        response_sla_p2_minutes INTEGER DEFAULT 240,
        created_at TIMESTAMPTZ DEFAULT now(),
        updated_at TIMESTAMPTZ DEFAULT now()
    )
    """),
    ("""
    CREATE TABLE IF NOT EXISTS parts_inventory (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        part_name TEXT NOT NULL,
        stock_level INTEGER NOT NULL DEFAULT 0,
        low_stock_threshold INTEGER NOT NULL DEFAULT 5,
        unit TEXT DEFAULT 'unit',
        created_at TIMESTAMPTZ DEFAULT now(),
        updated_at TIMESTAMPTZ DEFAULT now()
    )
    """),
    # ---- R11 Nursing ----
    ("""
    CREATE TABLE IF NOT EXISTS prep_checklists (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        visit_id UUID,
        exam_id UUID,
        patient_id TEXT NOT NULL,
        procedure_type TEXT DEFAULT '',
        items JSONB DEFAULT '[]'::jsonb,
        status TEXT NOT NULL DEFAULT 'in_progress'
            CHECK (status IN ('in_progress', 'complete')),
        confirmed_by TEXT DEFAULT '',
        confirmed_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ DEFAULT now(),
        updated_at TIMESTAMPTZ DEFAULT now()
    )
    """),
    ("""
    CREATE TABLE IF NOT EXISTS vitals (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        visit_id UUID,
        exam_id UUID,
        patient_id TEXT NOT NULL,
        bp_systolic INTEGER,
        bp_diastolic INTEGER,
        hr INTEGER,
        spo2 INTEGER,
        temperature NUMERIC(4, 1),
        respiration INTEGER,
        recorded_at TIMESTAMPTZ DEFAULT now(),
        operator_id TEXT DEFAULT '',
        created_at TIMESTAMPTZ DEFAULT now()
    )
    """),
    ("""
    CREATE TABLE IF NOT EXISTS safety_confirmations (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        visit_id UUID,
        exam_id UUID,
        patient_id TEXT NOT NULL,
        allergy_flag BOOLEAN NOT NULL DEFAULT FALSE,
        pregnancy_flag BOOLEAN NOT NULL DEFAULT FALSE,
        renal_flag BOOLEAN NOT NULL DEFAULT FALSE,
        confirmed BOOLEAN NOT NULL DEFAULT FALSE,
        confirmed_by TEXT DEFAULT '',
        confirmed_at TIMESTAMPTZ,
        override_required BOOLEAN NOT NULL DEFAULT FALSE,
        override_justification TEXT DEFAULT '',
        override_by TEXT DEFAULT '',
        created_at TIMESTAMPTZ DEFAULT now()
    )
    """),
    ("""
    CREATE TABLE IF NOT EXISTS contrast_records (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        exam_id UUID,
        visit_id UUID,
        patient_id TEXT NOT NULL,
        agent TEXT NOT NULL,
        dose TEXT DEFAULT '',
        route TEXT DEFAULT '',
        rate TEXT DEFAULT '',
        administered_at TIMESTAMPTZ DEFAULT now(),
        nurse_id TEXT DEFAULT '',
        created_at TIMESTAMPTZ DEFAULT now()
    )
    """),
    ("""
    CREATE TABLE IF NOT EXISTS reaction_escalations (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        visit_id UUID,
        exam_id UUID,
        patient_id TEXT NOT NULL,
        reaction_type TEXT DEFAULT '',
        severity TEXT NOT NULL DEFAULT 'moderate'
            CHECK (severity IN ('mild', 'moderate', 'severe')),
        onset TEXT DEFAULT '',
        actions TEXT DEFAULT '',
        status TEXT NOT NULL DEFAULT 'sent'
            CHECK (status IN ('sent', 'acknowledged')),
        escalated_to TEXT DEFAULT '',
        ack_by TEXT DEFAULT '',
        ack_at TIMESTAMPTZ,
        logged_by TEXT DEFAULT '',
        created_at TIMESTAMPTZ DEFAULT now()
    )
    """),
    ("""
    CREATE TABLE IF NOT EXISTS sedation_records (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        exam_id UUID,
        visit_id UUID,
        patient_id TEXT NOT NULL,
        sedative TEXT DEFAULT '',
        dose TEXT DEFAULT '',
        route TEXT DEFAULT '',
        administered_at TIMESTAMPTZ DEFAULT now(),
        monitoring_interval_minutes INTEGER DEFAULT 5,
        sedation_score TEXT DEFAULT '',
        recorded_by TEXT DEFAULT '',
        created_at TIMESTAMPTZ DEFAULT now()
    )
    """),
    ("""
    CREATE TABLE IF NOT EXISTS recovery_records (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        visit_id UUID,
        exam_id UUID,
        patient_id TEXT NOT NULL,
        observations TEXT DEFAULT '',
        discharge_criteria JSONB DEFAULT '{}'::jsonb,
        criteria_met BOOLEAN NOT NULL DEFAULT FALSE,
        discharged_at TIMESTAMPTZ,
        discharge_by TEXT DEFAULT '',
        created_at TIMESTAMPTZ DEFAULT now()
    )
    """),
    ("""
    CREATE TABLE IF NOT EXISTS mar_records (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        visit_id UUID,
        patient_id TEXT NOT NULL,
        medication TEXT NOT NULL,
        dose TEXT DEFAULT '',
        route TEXT DEFAULT '',
        administered_at TIMESTAMPTZ DEFAULT now(),
        indication TEXT DEFAULT '',
        administered_by TEXT DEFAULT '',
        created_at TIMESTAMPTZ DEFAULT now()
    )
    """),
    ("""
    CREATE TABLE IF NOT EXISTS handoff_notes (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        visit_id UUID,
        patient_id TEXT NOT NULL,
        from_user TEXT DEFAULT '',
        to_role TEXT DEFAULT '',
        note TEXT DEFAULT '',
        created_at TIMESTAMPTZ DEFAULT now()
    )
    """),
    # ---- R03 Service Director ----
    ("""
    CREATE TABLE IF NOT EXISTS modality_capacity (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        modality TEXT NOT NULL,
        day_of_week INTEGER NOT NULL CHECK (day_of_week BETWEEN 0 AND 6),
        start_time TIME NOT NULL,
        end_time TIME NOT NULL,
        capacity INTEGER NOT NULL DEFAULT 1,
        created_at TIMESTAMPTZ DEFAULT now(),
        updated_at TIMESTAMPTZ DEFAULT now(),
        UNIQUE (modality, day_of_week, start_time)
    )
    """),
    ("""
    CREATE TABLE IF NOT EXISTS sla_breaches (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        exam_id UUID NOT NULL,
        breach_type TEXT NOT NULL CHECK (breach_type IN ('STAT', 'Routine')),
        minutes_overdue INTEGER NOT NULL DEFAULT 0,
        detected_at TIMESTAMPTZ DEFAULT now(),
        status TEXT NOT NULL DEFAULT 'pending'
            CHECK (status IN ('pending', 'escalated', 'resolved')),
        notified_users JSONB DEFAULT '[]'::jsonb,
        resolved_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ DEFAULT now()
    )
    """),
    ("""
    CREATE TABLE IF NOT EXISTS dashboard_audit (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id INTEGER,
        tenant TEXT DEFAULT '',
        action TEXT NOT NULL,
        widget TEXT DEFAULT '',
        format TEXT DEFAULT '',
        record_count INTEGER DEFAULT 0,
        source_kpi TEXT DEFAULT '',
        target_url TEXT DEFAULT '',
        study_uid TEXT DEFAULT '',
        justification TEXT DEFAULT '',
        recipients JSONB DEFAULT '[]'::jsonb,
        ip_address TEXT DEFAULT '',
        created_at TIMESTAMPTZ DEFAULT now()
    )
    """),
    ("""
    CREATE TABLE IF NOT EXISTS analytics_report_templates (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT DEFAULT '',
        default_format TEXT NOT NULL DEFAULT 'csv',
        created_at TIMESTAMPTZ DEFAULT now()
    )
    """),
    ("""
    CREATE TABLE IF NOT EXISTS report_deliveries (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        template_id TEXT REFERENCES analytics_report_templates(id) ON DELETE SET NULL,
        params JSONB DEFAULT '{}'::jsonb,
        format TEXT NOT NULL DEFAULT 'csv',
        status TEXT NOT NULL DEFAULT 'pending'
            CHECK (status IN ('pending', 'generating', 'complete', 'failed')),
        error TEXT DEFAULT '',
        generated_by TEXT DEFAULT '',
        generated_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ DEFAULT now()
    )
    """),
    # ---- R19 Hospital Staff ----
    ("""
    CREATE TABLE IF NOT EXISTS follow_up_requests (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        report_id UUID,
        exam_id UUID,
        patient_id TEXT NOT NULL,
        requester_id INTEGER,
        reason TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'submitted'
            CHECK (status IN ('submitted', 'acknowledged', 'completed', 'cancelled')),
        priority TEXT NOT NULL DEFAULT 'routine'
            CHECK (priority IN ('routine', 'stat')),
        assigned_to TEXT DEFAULT '',
        created_at TIMESTAMPTZ DEFAULT now(),
        updated_at TIMESTAMPTZ DEFAULT now()
    )
    """),
    ("""
    CREATE TABLE IF NOT EXISTS patient_staff_scope (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        patient_id TEXT NOT NULL,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        scope_type TEXT NOT NULL DEFAULT 'ward'
            CHECK (scope_type IN ('ward', 'care_team', 'assigned')),
        assigned_by INTEGER,
        created_at TIMESTAMPTZ DEFAULT now(),
        UNIQUE (patient_id, user_id)
    )
    """),
]

INDEXES = [
    "CREATE INDEX IF NOT EXISTS ix_visits_patient ON visits(patient_id)",
    "CREATE INDEX IF NOT EXISTS ix_visits_status ON visits(status)",
    "CREATE INDEX IF NOT EXISTS ix_visit_orders_visit ON visit_orders(visit_id)",
    "CREATE INDEX IF NOT EXISTS ix_appointments_slot ON appointments(modality, scheduled_date, scheduled_time)",
    "CREATE INDEX IF NOT EXISTS ix_appointments_patient ON appointments(patient_id)",
    "CREATE INDEX IF NOT EXISTS ix_consent_documents_visit ON consent_documents(visit_id)",
    "CREATE INDEX IF NOT EXISTS ix_insurance_patient ON insurance_records(patient_id)",
    "CREATE INDEX IF NOT EXISTS ix_invoice_patient ON invoice(patient_id)",
    "CREATE INDEX IF NOT EXISTS ix_invoice_status ON invoice(status)",
    "CREATE INDEX IF NOT EXISTS ix_invoice_line_invoice ON invoice_line(invoice_id)",
    "CREATE INDEX IF NOT EXISTS ix_payment_invoice ON payment(invoice_id)",
    "CREATE INDEX IF NOT EXISTS ix_payment_operator ON payment(operator_id)",
    "CREATE INDEX IF NOT EXISTS ix_claim_invoice ON claim(invoice_id)",
    "CREATE INDEX IF NOT EXISTS ix_claim_status ON claim(status)",
    "CREATE INDEX IF NOT EXISTS ix_refund_invoice ON refund(invoice_id)",
    "CREATE INDEX IF NOT EXISTS ix_refund_status ON refund(status)",
    "CREATE INDEX IF NOT EXISTS ix_quote_patient ON quote(patient_id)",
    "CREATE INDEX IF NOT EXISTS ix_payment_plan_invoice ON payment_plan(invoice_id)",
    "CREATE INDEX IF NOT EXISTS ix_installment_plan ON payment_plan_installment(plan_id)",
    "CREATE INDEX IF NOT EXISTS ix_shift_recon_cashier ON shift_reconciliation(cashier_id, shift_date)",
    "CREATE INDEX IF NOT EXISTS ix_equipment_modality ON equipment(modality)",
    "CREATE INDEX IF NOT EXISTS ix_maintenance_equipment ON maintenance_schedules(equipment_id)",
    "CREATE INDEX IF NOT EXISTS ix_maintenance_due ON maintenance_schedules(next_due_date)",
    "CREATE INDEX IF NOT EXISTS ix_qc_records_equipment ON qc_records(equipment_id)",
    "CREATE INDEX IF NOT EXISTS ix_qc_records_tested ON qc_records(tested_at)",
    "CREATE INDEX IF NOT EXISTS ix_downtime_equipment ON downtime_events(equipment_id)",
    "CREATE INDEX IF NOT EXISTS ix_downtime_status ON downtime_events(status)",
    "CREATE INDEX IF NOT EXISTS ix_work_orders_equipment ON work_orders(equipment_id)",
    "CREATE INDEX IF NOT EXISTS ix_work_orders_status ON work_orders(status)",
    "CREATE INDEX IF NOT EXISTS ix_vendor_contracts_equipment ON vendor_contracts(equipment_id)",
    "CREATE INDEX IF NOT EXISTS ix_parts_inventory_name ON parts_inventory(part_name)",
    "CREATE INDEX IF NOT EXISTS ix_prep_checklists_patient ON prep_checklists(patient_id)",
    "CREATE INDEX IF NOT EXISTS ix_vitals_patient ON vitals(patient_id)",
    "CREATE INDEX IF NOT EXISTS ix_safety_patient ON safety_confirmations(patient_id)",
    "CREATE INDEX IF NOT EXISTS ix_contrast_exam ON contrast_records(exam_id)",
    "CREATE INDEX IF NOT EXISTS ix_reactions_patient ON reaction_escalations(patient_id)",
    "CREATE INDEX IF NOT EXISTS ix_sedation_exam ON sedation_records(exam_id)",
    "CREATE INDEX IF NOT EXISTS ix_recovery_patient ON recovery_records(patient_id)",
    "CREATE INDEX IF NOT EXISTS ix_mar_patient ON mar_records(patient_id)",
    "CREATE INDEX IF NOT EXISTS ix_handoff_patient ON handoff_notes(patient_id)",
    "CREATE INDEX IF NOT EXISTS ix_modality_capacity_mod ON modality_capacity(modality)",
    "CREATE INDEX IF NOT EXISTS ix_sla_breaches_status ON sla_breaches(status, detected_at)",
    "CREATE INDEX IF NOT EXISTS ix_sla_breaches_exam ON sla_breaches(exam_id)",
    "CREATE INDEX IF NOT EXISTS ix_dashboard_audit_user ON dashboard_audit(user_id, created_at)",
    "CREATE INDEX IF NOT EXISTS ix_report_deliveries_template ON report_deliveries(template_id)",
    "CREATE INDEX IF NOT EXISTS ix_follow_up_status ON follow_up_requests(status)",
    "CREATE INDEX IF NOT EXISTS ix_follow_up_patient ON follow_up_requests(patient_id)",
    "CREATE INDEX IF NOT EXISTS ix_patient_scope_user ON patient_staff_scope(user_id)",
    "CREATE INDEX IF NOT EXISTS ix_patient_scope_patient ON patient_staff_scope(patient_id)",
]

SEEDS = [
    ("""
    INSERT INTO procedure_pricing_catalog (procedure_code, description, list_price) VALUES
        ('CTABDPEL', 'CT Abdomen and Pelvis with contrast', 850.00),
        ('CTHEAD', 'CT Head without contrast', 450.00),
        ('CTCHEST', 'CT Chest with contrast', 700.00),
        ('MRBRAIN', 'MRI Brain without contrast', 1100.00),
        ('MRLUMBAR', 'MRI Lumbar Spine without contrast', 1050.00),
        ('USABDOMEN', 'Ultrasound Abdomen complete', 350.00),
        ('USPELVIS', 'Ultrasound Pelvis complete', 320.00),
        ('DXCHEST', 'X-ray Chest 2 views', 120.00),
        ('DXEXTREM', 'X-ray Extremity 2 views', 110.00),
        ('MGSCR', 'Mammography Screening bilateral', 260.00),
        ('FLKUB', 'Fluoroscopy KUB', 280.00)
    ON CONFLICT (procedure_code) DO NOTHING
    """),
    ("""
    INSERT INTO analytics_report_templates (id, name, description, default_format) VALUES
        ('tpl-01', 'Monthly Volume', 'Study volume by day, modality and series/size totals', 'csv'),
        ('tpl-02', 'Turnaround by Modality', 'Report turnaround p50/p95 by modality and priority', 'csv'),
        ('tpl-03', 'Protocol Compliance', 'Per-protocol compliance % vs ACR benchmarks', 'csv'),
        ('tpl-04', 'Capacity Utilization', 'Scheduled vs capacity by modality, date and timeslot', 'csv'),
        ('tpl-05', 'SLA Breach Detail', 'STAT and routine SLA breaches with minutes overdue', 'csv')
    ON CONFLICT (id) DO NOTHING
    """),
]


def upgrade():
    for table_sql in NEW_TABLES:
        op.execute(table_sql)
    for index_sql in INDEXES:
        op.execute(index_sql)
    for seed_sql in SEEDS:
        op.execute(seed_sql)


def downgrade():
    # Drop in dependency order: children first, parents last.
    drop_order = [
        'payment_plan_installment', 'payment_plan', 'quote', 'refund', 'claim',
        'receipt', 'payment', 'invoice_line', 'invoice', 'procedure_pricing_catalog',
        'shift_reconciliation',
        'parts_inventory', 'vendor_contracts', 'work_orders', 'downtime_events',
        'qc_records', 'maintenance_schedules', 'equipment',
        'handoff_notes', 'mar_records', 'recovery_records', 'sedation_records',
        'reaction_escalations', 'contrast_records', 'safety_confirmations', 'vitals',
        'prep_checklists',
        'report_deliveries', 'analytics_report_templates', 'dashboard_audit',
        'sla_breaches', 'modality_capacity',
        'follow_up_requests', 'patient_staff_scope',
        'consent_documents', 'insurance_records', 'appointments', 'visit_orders', 'visits',
    ]
    for table in drop_order:
        op.execute(f"DROP TABLE IF EXISTS {table}")
