# RIS Integration Spec — Full Inbuilt RIS for QuantumPACS v3

**Version:** 1.0 · **Date:** 2026-08-18 · **Status:** Draft  
**Scope:** Consolidated MVP + v1.1 + v2.0 → v3.0 full RIS integration  
**Platform:** QuantumPACS v3-dev (Starlette backend, React/Vite frontend, PostgreSQL)  
**Source:** `docs/reaserch/RIS/` — all 23 documents consolidated

---

## 1. Executive Summary

### 1.1 Purpose

This spec consolidates the RIS implementation plan from `docs/reaserch/RIS/` (PRD, release plans, sprint details, personas, workflows, stories, UI/UX, metrics, acceptance criteria) into a single engineering implementation document mapped directly to the existing QuantumPACS v3-dev codebase. It covers the **full RIS surface** — MVP through v2.0 — as an integrated feature of v3.

### 1.2 Scope

- **Replace + extend** existing simplified worklist/orders/billing with full RIS-grade implementations
- **All 11 human personas** and **6 machine actors** from `01_persona_catalog.md`
- **33 user stories** with testable acceptance criteria
- **12 epics (MVP) + 12 epics (v1.1/v2.0)** from `RELEASE_PLAN.md` and `RELEASE_PLAN_V2.md`
- **Full order lifecycle:** Ordered → Scheduled → Arrived → In Progress → Completed → Read → Signed
- **IDN multi-site scheduling** from the start (reusing existing `cross_tenant_grants` infrastructure)
- **New DICOM MWL SCP + MPPS consumer** services
- **New HL7 interface engine** with exception queue and retry
- **New conflict-free scheduling engine** with EXCLUDE constraints
- **Speech recognition/dictation** integration (no AI-assisted coding for v3)

### 1.3 What Changes vs. Existing Codebase

| Existing Module | What Changes | RIS Replacement |
|:---|:---|:---|
| `worklist_entries` (basic) | Evolves to RIS-grade MWL + scheduling | `orders`, `order_procedures`, `appointments`, `worklist_entries` (upgraded) |
| `exams` (basic) | Merges into order lifecycle + tracking | `exams` (upgraded with MWL fields, MPPS status) |
| `reports` (basic) | Becomes structured report engine | `reports`, `report_versions`, `report_templates` |
| `visit_orders` (read-only) | Replaced by HL7-driven order intake | `orders` (HL7 ORM → order lifecycle) |
| `billing` (invoices/claims) | Extends to radiology billing | `charges`, `claims` (auto charge drop, 837/835) |
| `appointments` (basic) | Replaced by conflict-free scheduling | `appointments` (EXCLUDE constraint, resource model) |
| `api/worklist.py` | Becomes MWL SCP + REST API | New MWL DICOM service + enhanced API |
| `api/hl7.py` (basic receiver) | Replaced by full interface engine | New HL7 interface engine with queues |

### 1.4 What's New (No Existing Equivalent)

- **Scheduling engine** with room/modality/technologist resources and conflict detection
- **MWL SCP** (DICOM C-FIND) for modality integration
- **MPPS consumer** (N-CREATE/N-SET) for live tracking
- **Interface engine** with HL7 v2 message queue, exception handling, retry, ≤5-min alerting
- **Prior-auth engine** with payer integration and booking rules
- **Appointment reminders** (SMS/email/phone) with opt-out
- **Critical results** workflow with tracked acknowledgment and escalation
- **Results distribution** (ORU/FHIR DiagnosticReport to EMR)
- **Denial rework queue** with reason codes and resubmission
- **Chargeback analytics** per site (for IDN)
- **FHIR R4 ServiceRequest/DiagnosticReport** read/write APIs

---

## 2. Architecture

### 2.1 Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    QuantumPACS v3 (Monolith)                 │
│                                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ HL7      │  │ MWL SCP  │  │ MPPS     │  │ Interface│   │
│  │ Receiver │  │ (DICOM)  │  │ Consumer │  │ Engine   │   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘   │
│       │              │              │              │          │
│       ▼              ▼              ▼              ▼          │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              RIS Service Layer                         │   │
│  │  Order Intake │ Scheduling │ Tracking │ Reporting     │   │
│  │  Registration │ Prior Auth │ Billing  │ Distribution  │   │
│  └──────────────────────┬───────────────────────────────┘   │
│                         │                                    │
│  ┌──────────────────────┴───────────────────────────────┐   │
│  │              PostgreSQL (asyncpg + Alembic)            │   │
│  │  orders │ appointments │ worklist │ exams │ reports    │   │
│  │  charges │ claims │ prior_auth │ critical_results      │   │
│  │  interface_messages │ hl7_messages │ audit_log          │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              React/Vite Frontend                       │   │
│  │  Tracking Board │ Scheduling │ Registration           │   │
│  │  Reading Worklist │ Report Editor │ Billing Queue     │   │
│  │  Admin │ Dashboard │ FHIR Admin │ HL7 Admin          │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
         │              │              │              │
         ▼              ▼              ▼              ▼
    ┌─────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
    │ Modalities│  │ HIS/EMR  │  │ PACS     │  │ Billing  │
    │ (DICOM)  │  │ (HL7/FHIR)│ │          │  │ (X12)    │
    └─────────┘  └──────────┘  └──────────┘  └──────────┘
```

### 2.2 New Services

| Service | Type | Purpose | Location |
|:---|:---|:---|:---|
| HL7 Interface Engine | Async background (thread) | Message queue, parse, route, retry, exception handling | `backend/services/hl7_engine/` |
| MWL SCP | DICOM server (pynetdicom) | Serve MWL entries via C-FIND to modalities | `backend/services/mwl_scp/` |
| MPPS Consumer | DICOM server (pynetdicom) | Accept N-CREATE/N-SET from modalities, update tracking | `backend/services/mpps_consumer/` |
| Scheduling Engine | Service layer | Conflict-free booking with EXCLUDE constraints | `backend/services/scheduling/` |
| Order Lifecycle | Service layer | State machine for order status transitions | `backend/services/order_lifecycle/` |
| Prior-Auth Engine | Service layer | Payer integration, booking rules, expiry alerts | `backend/services/prior_auth/` |
| Results Distribution | Service layer | Signed report → ORU/FHIR → EMR | `backend/services/results_distribution/` |

### 2.3 Existing Services Enhanced

| Service | What Changes |
|:---|:---|
| `api/worklist.py` | Add MWL station-AE lookup, MPPS-driven status updates, live tracking filters |
| `api/exams.py` | Add MPPS status linkage, protocol assignment, dose tracking |
| `api/reports.py` | Add structured templates, versioning, sign-off → charge drop hook |
| `api/billing.py` | Add CPT/ICD-10 suggestion, auto charge drop, unbilled aging, 837/835 stub |
| `api/frontdesk.py` | Add MPI dedup, insurance eligibility, one-click check-in |
| `api/hl7.py` | Route to new interface engine instead of inline processing |
| `api/notifications.py` | Add critical results workflow, appointment reminders, opt-out registry |

---

## 3. Data Model

### 3.1 Design Decisions

- **Evolve existing schema**: merge/upgrade `worklist_entries`, `exams`, `reports` tables to be RIS-grade
- **Order status + child statuses**: `orders` table has lifecycle status; `worklist_entries`, `exams`, `reports` have sub-statuses that roll up
- **RLS**: all clinical rows scoped by `facility_id` (existing pattern)
- **EXCLUDE constraints**: `appointments` table uses `EXCLUDE` for conflict-free booking
- **Partial unique indexes**: accession unique per facility

### 3.2 Schema Changes (Alembic Migrations)

#### Migration: RIS Schema v1 — Orders & Registration (MVP)

```sql
-- Orders table: replaces visit_orders with full lifecycle
CREATE TABLE ris_orders (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    facility_id uuid NOT NULL REFERENCES facilities(id),
    accession_number varchar(20) NOT NULL,
    patient_id varchar(64) NOT NULL,
    patient_name varchar(256),
    patient_dob date,
    referring_physician varchar(256),
    clinical_indication text,
    priority varchar(20) NOT NULL DEFAULT 'ROUTINE'
        CHECK (priority IN ('ROUTINE','URGENT','STAT')),
    status varchar(30) NOT NULL DEFAULT 'ORDERED'
        CHECK (status IN ('ORDERED','SCHEDULED','ARRIVED','IN_PROGRESS',
                          'COMPLETED','READ','SIGNED','CANCELLED')),
    prior_auth_status varchar(20) DEFAULT 'NOT_REQUIRED'
        CHECK (prior_auth_status IN ('NOT_REQUIRED','REQUIRED','PENDING',
                                     'APPROVED','DENIED','EXPIRED')),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    created_by uuid REFERENCES users(id),
    CONSTRAINT uq_ris_order_accession UNIQUE (facility_id, accession_number)
);

-- Index for MWL serving and tracking board queries
CREATE INDEX idx_ris_orders_facility_status ON ris_orders (facility_id, status);
CREATE INDEX idx_ris_orders_patient ON ris_orders (patient_id);
CREATE INDEX idx_ris_orders_scheduled ON ris_orders (facility_id, status, created_at)
    WHERE status IN ('ORDERED','SCHEDULED');

-- Order procedures: one order can have multiple procedures
CREATE TABLE ris_order_procedures (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id uuid NOT NULL REFERENCES ris_orders(id) ON DELETE CASCADE,
    facility_id uuid NOT NULL REFERENCES facilities(id),
    procedure_code varchar(20) NOT NULL,
    procedure_name varchar(256) NOT NULL,
    modality varchar(10) NOT NULL,
    body_part varchar(100),
    laterality varchar(10),
    contrast boolean DEFAULT false,
    cpt_code varchar(10),
    icd10_code varchar(10),
    status varchar(30) NOT NULL DEFAULT 'ORDERED'
        CHECK (status IN ('ORDERED','SCHEDULED','IN_PROGRESS','COMPLETED')),
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uq_order_proc_per_order UNIQUE (order_id, procedure_code)
);

-- Appointments: conflict-free scheduling with EXCLUDE constraint
CREATE TABLE ris_appointments (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    facility_id uuid NOT NULL REFERENCES facilities(id),
    order_id uuid NOT NULL REFERENCES ris_orders(id),
    patient_id varchar(64) NOT NULL,
    appointment_date date NOT NULL,
    appointment_time time NOT NULL,
    duration_minutes int NOT NULL DEFAULT 30,
    room_id uuid,
    modality varchar(10) NOT NULL,
    technologist_id uuid,
    status varchar(30) NOT NULL DEFAULT 'SCHEDULED'
        CHECK (status IN ('SCHEDULED','ARRIVED','IN_PROGRESS','COMPLETED',
                          'CANCELLED','NO_SHOW')),
    cancellation_reason text,
    site_id uuid,
    prior_auth_id uuid,
    reminder_sent boolean DEFAULT false,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    created_by uuid REFERENCES users(id)
);

-- EXCLUDE constraint: no double-booking rooms
-- (GiST index required; room_id can be NULL for unassigned)
CREATE INDEX idx_ris_appt_facility_date ON ris_appointments (facility_id, appointment_date);
CREATE INDEX idx_ris_appt_patient ON ris_appointments (patient_id);

-- Scheduled rooms/technologists availability
CREATE TABLE ris_resources (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    facility_id uuid NOT NULL REFERENCES facilities(id),
    resource_type varchar(20) NOT NULL CHECK (resource_type IN ('ROOM','MODALITY','TECHNOLOGIST')),
    name varchar(100) NOT NULL,
    modality varchar(10),
    is_active boolean DEFAULT true,
    metadata jsonb DEFAULT '{}',
    created_at timestamptz NOT NULL DEFAULT now()
);

-- Resource availability schedules (recurring)
CREATE TABLE ris_resource_schedules (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    resource_id uuid NOT NULL REFERENCES ris_resources(id) ON DELETE CASCADE,
    day_of_week smallint NOT NULL CHECK (day_of_week BETWEEN 0 AND 6),
    start_time time NOT NULL,
    end_time time NOT NULL,
    is_available boolean DEFAULT true,
    CONSTRAINT uq_resource_schedule UNIQUE (resource_id, day_of_week, start_time)
);
```

#### Migration: RIS Schema v2 — Worklist, MWL, MPPS (MVP)

```sql
-- Enhanced worklist entries (evolve existing worklist_entries)
-- Add MWL-specific fields
ALTER TABLE worklist_entries ADD COLUMN IF NOT EXISTS
    ris_order_id uuid REFERENCES ris_orders(id);
ALTER TABLE worklist_entries ADD COLUMN IF NOT EXISTS
    scheduled_appointment_id uuid REFERENCES ris_appointments(id);
ALTER TABLE worklist_entries ADD COLUMN IF NOT EXISTS
    station_ae varchar(16);
ALTER TABLE worklist_entries ADD COLUMN IF NOT EXISTS
    requesting_physician varchar(256);
ALTER TABLE worklist_entries ADD COLUMN IF NOT EXISTS
    requested_procedure_code varchar(20);
ALTER TABLE worklist_entries ADD COLUMN IF NOT EXISTS
    body_part varchar(100);
ALTER TABLE worklist_entries ADD COLUMN IF NOT EXISTS
    contrast boolean DEFAULT false;
ALTER TABLE worklist_entries ADD COLUMN IF NOT EXISTS
    priority varchar(20) DEFAULT 'ROUTINE'
        CHECK (priority IN ('ROUTINE','URGENT','STAT'));
ALTER TABLE worklist_entries ADD COLUMN IF NOT EXISTS
    mpps_status varchar(20)
        CHECK (mpps_status IN ('IN_PROGRESS','COMPLETED','DISCONTINUED',NULL));

-- MPPS events: full audit trail of modality progress
CREATE TABLE ris_mpps_events (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    facility_id uuid NOT NULL REFERENCES facilities(id),
    worklist_entry_id uuid REFERENCES worklist_entries(id),
    order_id uuid REFERENCES ris_orders(id),
    event_type varchar(20) NOT NULL CHECK (event_type IN ('N_CREATE','N_SET','N_ACTION')),
    mpps_status varchar(20) NOT NULL,
    performed_procedure_step_id varchar(64),
    start_date timestamptz,
    end_date timestamptz,
    modality varchar(10),
    station_ae varchar(16),
    raw_message jsonb,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_mpps_events_order ON ris_mpps_events (order_id);
CREATE INDEX idx_mpps_events_facility ON ris_mpps_events (facility_id, created_at);
```

#### Migration: RIS Schema v3 — Reports & Critical Results (MVP)

```sql
-- Enhanced reports (evolve existing reports table)
ALTER TABLE reports ADD COLUMN IF NOT EXISTS
    ris_order_id uuid REFERENCES ris_orders(id);
ALTER TABLE reports ADD COLUMN IF NOT EXISTS
    template_id uuid;
ALTER TABLE reports ADD COLUMN IF NOT EXISTS
    signed_at timestamptz;
ALTER TABLE reports ADD COLUMN IF NOT EXISTS
    signed_by uuid REFERENCES users(id);
ALTER TABLE reports ADD COLUMN IF NOT EXISTS
    distributed_at timestamptz;
ALTER TABLE reports ADD COLUMN IF NOT EXISTS
    is_critical boolean DEFAULT false;

-- Report versioning
CREATE TABLE ris_report_versions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    report_id uuid NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
    version_number int NOT NULL DEFAULT 1,
    content jsonb NOT NULL,
    diff_from_previous jsonb,
    author_id uuid NOT NULL REFERENCES users(id),
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uq_report_version UNIQUE (report_id, version_number)
);

-- Report templates
CREATE TABLE ris_report_templates (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    facility_id uuid NOT NULL REFERENCES facilities(id),
    name varchar(100) NOT NULL,
    modality varchar(10),
    body_part varchar(100),
    template_content jsonb NOT NULL,
    version int NOT NULL DEFAULT 1,
    is_active boolean DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

-- Critical results notifications
CREATE TABLE ris_critical_results (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    facility_id uuid NOT NULL REFERENCES facilities(id),
    report_id uuid NOT NULL REFERENCES reports(id),
    order_id uuid REFERENCES ris_orders(id),
    flag_description text NOT NULL,
    notification_channel varchar(20) NOT NULL
        CHECK (notification_channel IN ('EHR_ALERT','MESSAGING','PAGE','PHONE')),
    recipient_id uuid REFERENCES users(id),
    recipient_name varchar(256),
    recipient_contact varchar(256),
    sent_at timestamptz NOT NULL DEFAULT now(),
    acknowledged_at timestamptz,
    acknowledged_by uuid REFERENCES users(id),
    escalation_level int DEFAULT 0,
    escalation_policy jsonb DEFAULT '{}',
    status varchar(20) NOT NULL DEFAULT 'PENDING'
        CHECK (status IN ('PENDING','ACKNOWLEDGED','ESCALATED')),
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_critical_results_facility ON ris_critical_results (facility_id, status);
CREATE INDEX idx_critical_results_report ON ris_critical_results (report_id);
```

#### Migration: RIS Schema v4 — Billing & Revenue (MVP)

```sql
-- Charges: auto-created on report sign-off
CREATE TABLE ris_charges (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    facility_id uuid NOT NULL REFERENCES facilities(id),
    order_id uuid NOT NULL REFERENCES ris_orders(id),
    report_id uuid REFERENCES reports(id),
    patient_id varchar(64) NOT NULL,
    cpt_code varchar(10) NOT NULL,
    cpt_description varchar(256),
    icd10_code varchar(10),
    charge_amount numeric(12,2) NOT NULL,
    status varchar(20) NOT NULL DEFAULT 'PENDING'
        CHECK (status IN ('PENDING','BILLED','PAID','DENIED','VOID')),
    prior_auth_id uuid,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_charges_facility ON ris_charges (facility_id, status);
CREATE INDEX idx_charges_patient ON ris_charges (patient_id);
CREATE INDEX idx_charges_unbilled ON ris_charges (facility_id, created_at)
    WHERE status = 'PENDING';

-- Claims: 837 export tracking
CREATE TABLE ris_claims (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    facility_id uuid NOT NULL REFERENCES facilities(id),
    charge_id uuid NOT NULL REFERENCES ris_charges(id),
    claim_number varchar(50),
    payer_id varchar(50),
    payer_name varchar(256),
    submitted_at timestamptz,
    status varchar(20) NOT NULL DEFAULT 'DRAFT'
        CHECK (status IN ('DRAFT','SUBMITTED','ACKNOWLEDGED','PAID','DENIED')),
    rejection_code varchar(20),
    rejection_reason text,
    paid_amount numeric(12,2),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_claims_facility ON ris_claims (facility_id, status);
CREATE INDEX idx_claims_unbilled ON ris_claims (facility_id, submitted_at)
    WHERE status IN ('DRAFT','DENIED');
```

#### Migration: RIS Schema v5 — Interface Engine & HL7 (MVP)

```sql
-- Interface endpoints: registered connections
CREATE TABLE ris_interface_endpoints (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    facility_id uuid NOT NULL REFERENCES facilities(id),
    name varchar(100) NOT NULL,
    interface_type varchar(20) NOT NULL
        CHECK (interface_type IN ('HL7_ADT','HL7_ORM','HL7_ORU','DICOM_MWL',
                                  'DICOM_MPPS','FHIR')),
    protocol varchar(20) NOT NULL CHECK (protocol IN ('HL7V2','DICOM','FHIR')),
    config jsonb NOT NULL DEFAULT '{}',
    is_active boolean DEFAULT true,
    last_message_at timestamptz,
    message_count bigint DEFAULT 0,
    error_count bigint DEFAULT 0,
    created_at timestamptz NOT NULL DEFAULT now()
);

-- HL7 messages: full audit trail with exception queue
CREATE TABLE ris_hl7_messages (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    facility_id uuid NOT NULL REFERENCES facilities(id),
    endpoint_id uuid REFERENCES ris_interface_endpoints(id),
    message_type varchar(10) NOT NULL,
    trigger_event varchar(10) NOT NULL,
    control_id varchar(100) NOT NULL,
    raw_message text NOT NULL,
    parsed_segments jsonb,
    status varchar(20) NOT NULL DEFAULT 'RECEIVED'
        CHECK (status IN ('RECEIVED','PARSED','PROCESSED','FAILED','RETRYING',
                          'ACKNOWLEDGED','QUEUED')),
    error_message text,
    retry_count int DEFAULT 0,
    max_retries int DEFAULT 3,
    processed_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now()
);

-- Partition by created_at for performance
CREATE INDEX idx_hl7_messages_facility ON ris_hl7_messages (facility_id, status, created_at);
CREATE INDEX idx_hl7_messages_control ON ris_hl7_messages (control_id);

-- Interface events: monitoring and alerting
CREATE TABLE ris_interface_events (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    facility_id uuid NOT NULL REFERENCES facilities(id),
    endpoint_id uuid REFERENCES ris_interface_endpoints(id),
    event_type varchar(30) NOT NULL,
    severity varchar(10) NOT NULL CHECK (severity IN ('INFO','WARNING','ERROR','CRITICAL')),
    message text NOT NULL,
    metadata jsonb DEFAULT '{}',
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_interface_events_facility ON ris_interface_events (facility_id, created_at);
```

#### Migration: RIS Schema v6 — Prior-Auth (v1.1)

```sql
-- Prior authorization requests
CREATE TABLE ris_prior_auth_requests (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    facility_id uuid NOT NULL REFERENCES facilities(id),
    order_id uuid NOT NULL REFERENCES ris_orders(id),
    procedure_code varchar(20) NOT NULL,
    cpt_code varchar(10),
    payer_id varchar(50),
    payer_name varchar(256),
    status varchar(20) NOT NULL DEFAULT 'REQUIRED'
        CHECK (status IN ('NOT_REQUIRED','REQUIRED','PENDING','APPROVED',
                          'DENIED','EXPIRED')),
    auth_number varchar(50),
    approved_units int,
    approved_date date,
    expiry_date date,
    denial_reason text,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_prior_auth_facility ON ris_prior_auth_requests (facility_id, status);
CREATE INDEX idx_prior_auth_order ON ris_prior_auth_requests (order_id);
CREATE INDEX idx_prior_auth_expiry ON ris_prior_auth_requests (expiry_date)
    WHERE status = 'APPROVED';
```

### 3.3 Relationship Diagram

```
facilities (existing)
    │
    ├── ris_orders ──────┬── ris_order_procedures
    │    │                │
    │    ├── ris_appointments ── ris_resources ── ris_resource_schedules
    │    │
    │    ├── worklist_entries (upgraded)
    │    │    └── ris_mpps_events
    │    │
    │    ├── exams (upgraded)
    │    │    └── reports (upgraded)
    │    │         ├── ris_report_versions
    │    │         ├── ris_critical_results
    │    │         └── ris_charges ── ris_claims
    │    │
    │    └── ris_prior_auth_requests
    │
    ├── ris_interface_endpoints
    │    ├── ris_hl7_messages
    │    └── ris_interface_events
    │
    └── ris_report_templates
```

---

## 4. API Contracts

### 4.1 New Endpoints

#### Orders

| Method | Path | Permission | Purpose |
|:---|:---|:---|:---|
| `POST` | `/api/ris/orders` | `ORDER_WRITE` | Create order (HL7 ORM or manual) |
| `GET` | `/api/ris/orders` | `ORDER_READ` | List orders (filtered, paginated) |
| `GET` | `/api/ris/orders/{id}` | `ORDER_READ` | Get order detail |
| `PUT` | `/api/ris/orders/{id}` | `ORDER_WRITE` | Update order |
| `PUT` | `/api/ris/orders/{id}/status` | `ORDER_WRITE` | Transition order status |
| `GET` | `/api/ris/orders/{id}/status-history` | `ORDER_READ` | Status change audit trail |
| `GET` | `/api/ris/orders/{id}/procedures` | `ORDER_READ` | List procedures for order |

#### Scheduling

| Method | Path | Permission | Purpose |
|:---|:---|:---|:---|
| `POST` | `/api/ris/appointments` | `SCHEDULE_WRITE` | Book appointment (conflict check) |
| `GET` | `/api/ris/appointments` | `SCHEDULE_READ` | List appointments |
| `PUT` | `/api/ris/appointments/{id}` | `SCHEDULE_WRITE` | Reschedule/cancel |
| `GET` | `/api/ris/appointments/availability` | `SCHEDULE_READ` | Slot availability search |
| `GET` | `/api/ris/appointments/calendar` | `SCHEDULE_READ` | Calendar view data |
| `POST` | `/api/ris/appointments/{id}/check-in` | `SCHEDULE_WRITE` | One-click check-in |
| `GET` | `/api/ris/resources` | `SCHEDULE_READ` | List resources (rooms/techs) |
| `POST` | `/api/ris/resources` | `SCHEDULE_WRITE` | Create resource |

#### Tracking Board

| Method | Path | Permission | Purpose |
|:---|:---|:---|:---|
| `GET` | `/api/ris/tracking` | `WORKLIST_READ` | Tracking board data (live) |
| `GET` | `/api/ris/tracking/kpi` | `WORKLIST_READ` | KPI strip counts |
| `PUT` | `/api/ris/tracking/{id}/status` | `WORKLIST_WRITE` | Update exam status |
| `GET` | `/api/ris/tracking/{id}/timeline` | `WORKLIST_READ` | Status lifecycle timeline |

#### Registration / Front-Desk

| Method | Path | Permission | Purpose |
|:---|:---|:---|:---|
| `POST` | `/api/ris/patients` | `PATIENT_WRITE` | Register patient (MPI dedup) |
| `GET` | `/api/ris/patients/search` | `PATIENT_READ` | Search patients (MPI) |
| `GET` | `/api/ris/patients/{id}` | `PATIENT_READ` | Patient detail |
| `PUT` | `/api/ris/patients/{id}` | `PATIENT_WRITE` | Update patient |
| `POST` | `/api/ris/patients/{id}/insurance` | `PATIENT_WRITE` | Add/verify insurance |
| `POST` | `/api/ris/patients/{id}/check-in` | `SCHEDULE_WRITE` | Check-in from schedule |

#### Reading Worklist & Reporting

| Method | Path | Permission | Purpose |
|:---|:---|:---|:---|
| `GET` | `/api/ris/reading-list` | `WORKLIST_READ` | Priority-sorted reading list |
| `GET` | `/api/ris/reports/{exam_id}` | `REPORT_READ` | Get report for exam |
| `POST` | `/api/ris/reports/{exam_id}` | `REPORT_WRITE` | Create/update report |
| `POST` | `/api/ris/reports/{exam_id}/sign` | `REPORT_SIGN` | Sign report (→ distribute) |
| `POST` | `/api/ris/reports/{exam_id}/submit` | `REPORT_WRITE` | Submit report (resident) |
| `POST` | `/api/ris/reports/{exam_id}/return` | `REPORT_SIGN` | Return to resident |
| `GET` | `/api/ris/reports/templates` | `REPORT_READ` | List report templates |
| `POST` | `/api/ris/reports/templates` | `REPORT_WRITE` | Create template |

#### Critical Results

| Method | Path | Permission | Purpose |
|:---|:---|:---|:---|
| `POST` | `/api/ris/critical-results` | `CRITICAL_RESULTS_WRITE` | Flag critical finding |
| `GET` | `/api/ris/critical-results` | `CRITICAL_RESULTS_READ` | List critical results |
| `POST` | `/api/ris/critical-results/{id}/acknowledge` | `CRITICAL_RESULTS_READ` | Acknowledge critical result |
| `GET` | `/api/ris/critical-results/{id}/escalation` | `CRITICAL_RESULTS_READ` | Escalation status |

#### Billing

| Method | Path | Permission | Purpose |
|:---|:---|:---|:---|
| `GET` | `/api/ris/billing/queue` | `BILLING_READ` | Billing queue (signed but unbilled) |
| `POST` | `/api/ris/billing/charges/{id}/drop` | `BILLING_WRITE` | Drop charge to billing |
| `GET` | `/api/ris/billing/unbilled` | `BILLING_READ` | Unbilled aging report |
| `POST` | `/api/ris/billing/claims/{id}/submit` | `BILLING_WRITE` | Submit claim (837) |
| `POST` | `/api/ris/billing/denials/{id}/rework` | `BILLING_WRITE` | Rework denied claim |
| `GET` | `/api/ris/billing/cpt-suggestions` | `BILLING_READ` | CPT/ICD-10 suggestions |

#### Prior-Auth (v1.1)

| Method | Path | Permission | Purpose |
|:---|:---|:---|:---|
| `POST` | `/api/ris/prior-auth` | `PRIOR_AUTH_WRITE` | Create prior-auth request |
| `GET` | `/api/ris/prior-auth` | `PRIOR_AUTH_READ` | List prior-auth requests |
| `PUT` | `/api/ris/prior-auth/{id}` | `PRIOR_AUTH_WRITE` | Update prior-auth status |
| `POST` | `/api/ris/prior-auth/{id}/verify` | `PRIOR_AUTH_READ` | Verify eligibility |

#### Interface Engine / Monitoring

| Method | Path | Permission | Purpose |
|:---|:---|:---|:---|
| `GET` | `/api/ris/interfaces` | `INTERFACE_READ` | List interface endpoints |
| `GET` | `/api/ris/interfaces/{id}/messages` | `INTERFACE_READ` | Message history |
| `GET` | `/api/ris/interfaces/{id}/metrics` | `INTERFACE_READ` | Interface health metrics |
| `GET` | `/api/ris/interfaces/exceptions` | `INTERFACE_READ` | Exception queue |
| `POST` | `/api/ris/interfaces/exceptions/{id}/retry` | `INTERFACE_WRITE` | Retry failed message |

#### Reports (reading-list)

| Method | Path | Permission | Purpose |
|:---|:---|:---|:---|
| `GET` | `/api/ris/reports/reading-list` | `WORKLIST_READ` | Priority-sorted reading list |
| `POST` | `/api/ris/reports/{exam_id}/assign` | `WORKLIST_WRITE` | Assign to reader |

### 4.2 Response Format

All responses follow existing `api/response.py` conventions:

```json
{
  "ok": true,
  "data": { ... },
  "meta": {
    "page": 1,
    "per_page": 25,
    "total": 150
  }
}
```

Error responses:

```json
{
  "ok": false,
  "error": "CONFLICT",
  "message": "Appointment conflicts with existing booking in room CT-1 at 10:00"
}
```

### 4.3 Key API Patterns

#### Order Status Transition

```python
# Valid transitions enforced by service layer
VALID_TRANSITIONS = {
    'ORDERED':     ['SCHEDULED', 'CANCELLED'],
    'SCHEDULED':   ['ARRIVED', 'CANCELLED'],
    'ARRIVED':     ['IN_PROGRESS', 'CANCELLED'],
    'IN_PROGRESS': ['COMPLETED', 'CANCELLED'],
    'COMPLETED':   ['READ'],
    'READ':        ['SIGNED'],
    'SIGNED':      [],  # terminal
    'CANCELLED':   ['ORDERED'],  # can re-order
}
```

#### Appointment Conflict Check (EXCLUDE constraint)

```sql
-- GiST EXCLUDE constraint on appointments
ALTER TABLE ris_appointments ADD CONSTRAINT excl_room_double_book
    EXCLUDE USING gist (
        room_id WITH =,
        tsrange(
            appointment_date + appointment_time,
            appointment_date + appointment_time + (duration_minutes || ' minutes')::interval
        ) WITH &&
    ) WHERE (room_id IS NOT NULL AND status != 'CANCELLED');
```

---

## 5. Service Layer

### 5.1 Order Lifecycle Service

```python
# backend/services/order_lifecycle/service.py

class OrderLifecycleService:
    """State machine for order status transitions with guards."""
    
    async def transition(self, order_id: str, new_status: str, 
                         actor_id: str, reason: str = None) -> Order:
        """Transition order to new status with validation."""
        order = await self.repo.get(order_id)
        if new_status not in VALID_TRANSITIONS[order.status]:
            raise InvalidTransitionError(order.status, new_status)
        
        # Audit every transition
        await self.audit.log_transition(order_id, order.status, new_status, actor_id, reason)
        
        # Side effects per transition
        if new_status == 'SCHEDULED':
            await self._serve_mwl(order)
            await self._create_appointment(order)
        elif new_status == 'COMPLETED':
            await self._create_report(order)
            await self._notify_referring(order)
        elif new_status == 'SIGNED':
            await self._drop_charge(order)
            await self._distribute_to_emr(order)
        
        return await self.repo.update_status(order_id, new_status)
```

### 5.2 Scheduling Engine

```python
# backend/services/scheduling/engine.py

class SchedulingEngine:
    """Conflict-free booking with resource matching."""
    
    async def book(self, order_id: str, appointment: AppointmentRequest,
                   actor_id: str) -> Appointment:
        """Book appointment with conflict and contraindication checks."""
        # 1. Resource availability check
        available = await self._check_availability(
            appointment.room_id, appointment.date, 
            appointment.time, appointment.duration
        )
        if not available:
            raise ConflictError("Room/technologist not available")
        
        # 2. EXCLUDE constraint (DB-level enforcement)
        # 3. Contrast/contraindication check
        # 4. Prior-auth check (if required)
        # 5. Create appointment + update order status to SCHEDULED
        # 6. Serve MWL entry
        # 7. Audit
        
        return await self.repo.create(appointment)
```

### 5.3 MWL SCP Service

```python
# backend/services/mwl_scp/service.py

class MwlScpService:
    """DICOM MWL SCP (C-FIND) serving scheduled entries."""
    
    async def handle_c_find(self, dataset):
        """Handle C-FIND query from modality, return matching MWL entries."""
        # Query worklist_entries WHERE status = 'SCHEDULED' OR 'ARRIVED'
        # Filter by station_ae if requested
        # Return matching entries as DICOM datasets
        
        entries = await self.worklist_repo.find_scheduled(
            station_ae=dataset.get('StationAETitle'),
            patient_name=dataset.get('PatientName'),
            accession=dataset.get('AccessionNumber'),
        )
        return [self._to_dicom_mwl(e) for e in entries]
```

### 5.4 MPPS Consumer Service

```python
# backend/services/mpps_consumer/service.py

class MppsConsumerService:
    """DICOM MPPS consumer (N-CREATE/N-SET) for live tracking."""
    
    async def handle_n_create(self, dataset):
        """Handle N-CREATE from modality → IN_PROGRESS on tracking board."""
        worklist_entry = await self._resolve_entry(dataset)
        await self.order_service.transition(
            worklist_entry.order_id, 'IN_PROGRESS',
            actor_id='MPPS', reason='Modality N-CREATE'
        )
        await self._echo_to_pacs(dataset)  # PACS integration
        await self._log_mpps_event(worklist_entry.id, 'N_CREATE', dataset)
    
    async def handle_n_set(self, dataset):
        """Handle N-CREATE from modality → COMPLETED on tracking board."""
        worklist_entry = await self._resolve_entry(dataset)
        await self.order_service.transition(
            worklist_entry.order_id, 'COMPLETED',
            actor_id='MPPS', reason='Modality N-SET'
        )
        await self._echo_to_pacs(dataset)
        await self._log_mpps_event(worklist_entry.id, 'N_SET', dataset)
```

### 5.5 HL7 Interface Engine

```python
# backend/services/hl7_engine/engine.py

class Hl7InterfaceEngine:
    """Full HL7 v2 interface engine with message queue, parse, route, retry."""
    
    async def receive_message(self, raw_hl7: str, endpoint_id: str):
        """Receive HL7 message, parse, validate, route, and process."""
        # 1. Parse HL7 → segments (JSONB)
        parsed = self.parser.parse(raw_hl7)
        
        # 2. Persist message with RECEIVED status
        msg = await self.repo.create_message(
            endpoint_id=endpoint_id,
            raw=raw_hl7,
            parsed=parsed,
            status='RECEIVED'
        )
        
        # 3. Route based on message type
        handler = self._route(parsed['message_type'], parsed['trigger_event'])
        
        # 4. Process (with retry on failure)
        try:
            result = await handler.process(parsed)
            await self.repo.update_status(msg.id, 'PROCESSED')
            await self._send_ack(msg, 'AA')  # Application Accept
        except Exception as e:
            await self.repo.update_status(msg.id, 'FAILED', error=str(e))
            await self._queue_retry(msg)
            await self._alert_if_critical(msg, e)
            await self._send_ack(msg, 'AE')  # Application Error
    
    def _route(self, msg_type: str, trigger: str):
        """Route message to appropriate handler."""
        routes = {
            ('ADT', 'A04'): self.adt_handler.register,    # Register patient
            ('ADT', 'A08'): self.adt_handler.update,      # Update demographics
            ('ADT', 'A40'): self.adt_handler.merge,       # Patient merge
            ('ORM', 'O01'): self.orm_handler.create_order, # New order
            ('ORM', 'O02'): self.orm_handler.cancel_order, # Cancel order
            ('ORU', 'R01'): self.oru_handler.distribute_report, # Report result
        }
        return routes.get((msg_type, trigger))
```

### 5.6 Prior-Auth Engine (v1.1)

```python
# backend/services/prior_auth/engine.py

class PriorAuthEngine:
    """Prior authorization tracking with payer integration."""
    
    async def check_booking_eligibility(self, order_id: str) -> BookingEligibility:
        """Check if order can be booked (auth status, expiry, payer rules)."""
        auth = await self.repo.get_by_order(order_id)
        if not auth:
            return BookingEligibility(eligible=True, reason='No auth required')
        
        if auth.status == 'DENIED':
            return BookingEligibility(
                eligible=False, reason='Prior auth denied',
                override_available=True
            )
        if auth.status == 'EXPIRED':
            return BookingEligibility(
                eligible=False, reason='Prior auth expired',
                override_available=True
            )
        if auth.status == 'APPROVED' and auth.expiry_date:
            days_until_expiry = (auth.expiry_date - date.today()).days
            if days_until_expiry <= 7:
                # Alert scheduler
                await self._send_expiry_alert(auth, days_until_expiry)
        
        return BookingEligibility(eligible=True, reason='Auth approved')
```

---

## 6. Frontend Components

### 6.1 New Components

| Component | Path | Purpose |
|:---|:---|:---|
| `TrackingBoard.tsx` | `frontend/src/worklist/TrackingBoard.tsx` | Live tracking board with status lifecycle |
| `TrackingBoard.css` | `frontend/src/worklist/TrackingBoard.css` | Tracking board styles |
| `KpiStrip.tsx` | `frontend/src/worklist/KpiStrip.tsx` | KPI counts (volume, in-progress, overdue, STAT) |
| `CalendarGrid.tsx` | `frontend/src/schedule/CalendarGrid.tsx` | Calendar grid for scheduling |
| `BookingForm.tsx` | `frontend/src/schedule/BookingForm.tsx` | Appointment booking with conflict check |
| `ResourceManager.tsx` | `frontend/src/schedule/ResourceManager.tsx` | Room/modality/technologist management |
| `OrderIntake.tsx` | `frontend/src/worklist/OrderIntake.tsx` | Order creation/intake form |
| `PriorAuthPanel.tsx` | `frontend/src/worklist/PriorAuthPanel.tsx` | Prior-auth status panel (v1.1) |
| `CriticalResults.tsx` | `frontend/src/radiologist/CriticalResults.tsx` | Critical results flagging workflow |
| `ReportEditor.tsx` | `frontend/src/radiologist/ReportEditor.tsx` | Enhanced report editor with templates |
| `BillingQueue.tsx` | `frontend/src/billing/BillingQueue.tsx` | Billing queue with CPT suggestions |
| `DenialRework.tsx` | `frontend/src/billing/DenialRework.tsx` | Denial rework queue (v1.1) |
| `InterfaceDashboard.tsx` | `frontend/src/admin/InterfaceDashboard.tsx` | HL7/DICOM interface health |
| `ExceptionQueue.tsx` | `frontend/src/admin/ExceptionQueue.tsx` | Failed message exception queue |

### 6.2 Existing Components Enhanced

| Component | What Changes |
|:---|:---|
| `Worklist.tsx` | Upgrade to tracking board with status lifecycle, KPI strip, filters, row actions |
| `ReadingWorklist.tsx` | Add priority sorting, unread toggle, AI flag badges, PACS viewer launch |
| `ReportPanel.tsx` | Add structured templates, versioning, sign-off flow |
| `CreateEntry.tsx` | Replace with `OrderIntake.tsx` (HL7-driven, not manual entry) |
| `CalendarView.tsx` | Upgrade to conflict-free scheduling with resource matching |

### 6.3 Route Structure

```typescript
// frontend/src/routing/ris.tsx (new)
export const risRoutes = [
  { path: '/tracking', component: TrackingBoard },
  { path: '/tracking/kpi', component: KpiStrip },
  { path: '/scheduling', component: CalendarGrid },
  { path: '/scheduling/book', component: BookingForm },
  { path: '/scheduling/resources', component: ResourceManager },
  { path: '/orders', component: OrderIntake },
  { path: '/orders/:id', component: OrderDetail },
  { path: '/reading', component: ReadingWorklist },
  { path: '/reading/:examId', component: ReadingConsole },
  { path: '/reports/:examId/edit', component: ReportEditor },
  { path: '/reports/templates', component: ReportTemplates },
  { path: '/registration', component: PatientRegistration },
  { path: '/check-in', component: CheckIn },
  { path: '/billing/queue', component: BillingQueue },
  { path: '/billing/unbilled', component: UnbilledAging },
  { path: '/billing/denials', component: DenialRework },
  { path: '/critical-results', component: CriticalResults },
  { path: '/interfaces', component: InterfaceDashboard },
  { path: '/interfaces/exceptions', component: ExceptionQueue },
  { path: '/prior-auth', component: PriorAuthPanel },
  { path: '/dashboard', component: RISDashboard },
];
```

---

## 7. RBAC Permissions

### 7.1 New Permissions

```python
# backend/api/permissions.py (extend)

class Permission(Enum):
    # RIS Orders
    ORDER_READ = 'ORDER_READ'
    ORDER_WRITE = 'ORDER_WRITE'
    
    # RIS Scheduling
    SCHEDULE_READ = 'SCHEDULE_READ'
    SCHEDULE_WRITE = 'SCHEDULE_WRITE'
    
    # RIS Worklist/Tracking
    WORKLIST_READ = 'WORKLIST_READ'
    WORKLIST_WRITE = 'WORKLIST_WRITE'
    
    # RIS Reports
    REPORT_READ = 'REPORT_READ'
    REPORT_WRITE = 'REPORT_WRITE'
    REPORT_SIGN = 'REPORT_SIGN'
    
    # RIS Critical Results
    CRITICAL_RESULTS_READ = 'CRITICAL_RESULTS_READ'
    CRITICAL_RESULTS_WRITE = 'CRITICAL_RESULTS_WRITE'
    
    # RIS Billing
    BILLING_READ = 'BILLING_READ'
    BILLING_WRITE = 'BILLING_WRITE'
    
    # RIS Prior Auth
    PRIOR_AUTH_READ = 'PRIOR_AUTH_READ'
    PRIOR_AUTH_WRITE = 'PRIOR_AUTH_WRITE'
    
    # RIS Interface
    INTERFACE_READ = 'INTERFACE_READ'
    INTERFACE_WRITE = 'INTERFACE_WRITE'
    
    # RIS Patient
    PATIENT_READ = 'PATIENT_READ'
    PATIENT_WRITE = 'PATIENT_WRITE'
```

### 7.2 Role-Permission Matrix

| Role | Permissions |
|:---|:---|
| Radiologist | WORKLIST_READ, REPORT_READ/WRITE/SIGN, CRITICAL_RESULTS_READ/WRITE, PATIENT_READ |
| Technologist | WORKLIST_READ/WRITE, SCHEDULE_READ, PATIENT_READ |
| Scheduler | SCHEDULE_READ/WRITE, ORDER_READ, PATIENT_READ/WRITE, PRIOR_AUTH_READ |
| Front Desk | PATIENT_READ/WRITE, SCHEDULE_READ/WRITE, ORDER_READ |
| Billing Coder | BILLING_READ/WRITE, ORDER_READ, REPORT_READ |
| RIS Admin | All RIS permissions |
| Department Manager | ORDER_READ, WORKLIST_READ, BILLING_READ, REPORT_READ |
| Referring MD | ORDER_READ (scoped to their patients) |
| ED Physician | ORDER_READ, WORKLIST_READ, CRITICAL_RESULTS_READ |
| Tenant Admin | All RIS permissions (scoped to facility) |
| Super Admin | All permissions (audited bypass) |

---

## 8. Integration Contracts

### 8.1 HL7 v2 Message Types

| Message | Direction | Handler | Action |
|:---|:---|:---|:---|
| ADT^A04 | HIS → RIS | `adt_handler.register` | Register/update patient demographics |
| ADT^A08 | HIS → RIS | `adt_handler.update` | Update patient demographics |
| ADT^A40 | HIS → RIS | `adt_handler.merge` | Patient merge (MPI) |
| ORM^O01 | HIS → RIS | `orm_handler.create_order` | Create order from referring MD |
| ORM^O01 | HIS → RIS | `orm_handler.cancel_order` | Cancel order |
| ORU^R01 | RIS → HIS | `oru_handler.distribute_report` | Send signed report to EMR |

### 8.2 DICOM Services

| Service | Port | AE Title | Purpose |
|:---|:---|:---|:---|
| MWL SCP | 11113 | `QPACS_MWL` | Serve MWL via C-FIND to modalities |
| MPPS Consumer | 11114 | `QPACS_MPPS` | Accept N-CREATE/N-SET from modalities |
| Existing C-STORE SCP | 11112 | `QPACS` | Image storage (unchanged) |

### 8.3 FHIR R4 Endpoints

| Resource | Path | Methods | Purpose |
|:---|:---|:---|:---|
| ServiceRequest | `/fhir/ServiceRequest` | GET, POST, PUT | Order CRUD |
| DiagnosticReport | `/fhir/DiagnosticReport` | GET, POST | Report CRUD |
| Patient | `/fhir/Patient` | GET, POST, PUT | Patient CRUD (existing) |
| ImagingStudy | `/fhir/ImagingStudy` | GET | Study read (existing) |
| DocumentReference | `/fhir/DocumentReference` | GET | Document read (existing) |

---

## 9. Implementation Phases

### 9.1 Phase 1: MVP (Sprints S1–S12)

| Sprint | Focus | Epics | Key Milestone |
|:---|:---|:---|:---|
| S1–S2 | Platform Foundation | E-RIS-01 | Auth + RBAC + tenant isolation |
| S3 | Interface Engine | E-RIS-02 | HL7 listener accepts real ORM |
| S4 | Registration + Order Intake | E-RIS-03, E-RIS-04 | Order with accession from ORM |
| S5 | Scheduling | E-RIS-05 | Conflict-free booking live |
| S6 | MWL/MPPS | E-RIS-06 | Scanner pulls MWL; MPPS updates board |
| S7 | Tracking Board | E-RIS-07 | Live board in UAT |
| S8–S9 | Reporting | E-RIS-08 | Template report + sign |
| S10 | Critical Results + Distribution | E-RIS-09, E-RIS-10 | Critical loop + ORU to EMR |
| S11 | Billing | E-RIS-11 | Auto charge drop + aging view |
| S12 | Hardening | — | UAT, perf, security, DR drill |

**MVP Exit Gates:**
- G1: MWL ≥ 98% auto-fill
- G2: 0 scheduling conflicts
- G3: MPPS → tracking < 5s
- G4: Charge capture ≥ 98%
- G5: Interface delivery > 99.9%
- G6: Atomic tenant provisioning < 15 min
- G7: No P0/P1 open defects

### 9.2 Phase 2: v1.1 (Sprints R2-S1–R2-S7)

| Sprint | Focus | Epics | Key Milestone |
|:---|:---|:---|:---|
| R2-S1–S2 | Prior-Auth + Reminders | E-RIS2-01, E-RIS2-02 | Prior-auth ≥ 95% pre-scan |
| R2-S3–S4 | Denial Rework + Templates + SR Polish | E-RIS2-03, E-RIS2-04, E-RIS2-06 | Unbilled $0 > 5 days |
| R2-S5–S6 | IDN Grants + Multi-Site Scheduling | E-RIS2-05 | Cross-site search + book |
| R2-S7 | FHIR Read + Phase-1 Gates | E-RIS2-07 | RVG-1…RVG-4 green |

### 9.3 Phase 3: v2.0 (Sprints R2-S8–R2-S12)

| Sprint | Focus | Epics | Key Milestone |
|:---|:---|:---|:---|
| R2-S8–S9 | Full FHIR + Portal Delivery | E-RIS2-08, E-RIS2-09 | Portal results live |
| R2-S10–S12 | AI Coding + Chargeback + Hardening | E-RIS2-10, E-RIS2-11, E-RIS2-12 | V2 go/no-go |

---

## 10. SLAs & SRE Plan

### 10.1 Performance SLAs

| Metric | Target | Measurement |
|:---|:---|:---|
| MWL query response | < 1s p95 | Prometheus histogram `ris_mwl_query_duration_seconds` |
| Booking slot search | < 1.5s p95 | Prometheus histogram `ris_booking_search_duration_seconds` |
| Registration screen transition | < 1s p95 | Prometheus histogram `ris_registration_duration_seconds` |
| Worklist load | < 1s p95 | Prometheus histogram `ris_worklist_load_duration_seconds` |
| Report autosave | < 1s perceived | Async background save |
| Tracking board update | ≤ 30s | WebSocket broadcast or polling |

### 10.2 Workflow SLAs

| Metric | Target | Alert Threshold |
|:---|:---|:---|
| Order intake → scheduling | < 1 min | > 5 min |
| MPPS → tracking update | < 5s | > 10s |
| Interface message delivery | > 99.9% | < 99.5% |
| Signed report → EMR | < 5 min | > 10 min |
| Critical result acknowledgment | 100% | Any unacknowledged > 15 min |

### 10.3 Monitoring Stack

| Component | Tool | Purpose |
|:---|:---|:---|
| Metrics | Prometheus + Grafana | RIS-specific dashboards |
| Logs | Structured JSON (existing) | Order lifecycle, interface events |
| Alerts | Prometheus AlertManager | SLA breach, interface failures |
| Tracing | OpenTelemetry (existing) | Request tracing across services |
| Audit | `audit_log` table (existing) | HIPAA compliance |

### 10.4 Key Prometheus Metrics

```python
# New RIS-specific metrics
ris_order_transitions = Counter('ris_order_transitions_total', 'Order status transitions', ['from_status', 'to_status'])
ris_mwl_query_duration = Histogram('ris_mwl_query_duration_seconds', 'MWL query latency')
ris_mpps_event_duration = Histogram('ris_mpps_event_duration_seconds', 'MPPS event processing latency')
ris_hl7_message_latency = Histogram('ris_hl7_message_latency_seconds', 'HL7 message processing latency')
ris_hl7_messages_total = Counter('ris_hl7_messages_total', 'HL7 messages processed', ['type', 'trigger', 'status'])
ris_booking_conflicts = Counter('ris_booking_conflicts_total', 'Booking conflict attempts')
ris_critical_result_ack = Histogram('ris_critical_result_ack_seconds', 'Critical result acknowledgment time')
ris_charge_drop_latency = Histogram('ris_charge_drop_latency_seconds', 'Time from sign to charge drop')
ris_unbilled_count = Gauge('ris_unbilled_count', 'Number of unbilled charges')
ris_mwl_served_total = Counter('ris_mwl_served_total', 'MWL entries served to modalities')
ris_mpps_received_total = Counter('ris_mpps_received_total', 'MPPS events received')
```

### 10.5 Alert Rules

```yaml
groups:
  - name: ris_sla
    rules:
      - alert: RISMwlLatencyHigh
        expr: histogram_quantile(0.95, ris_mwl_query_duration_seconds_bucket) > 1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "MWL query latency > 1s p95"
      
      - alert: RISHL7FailureRateHigh
        expr: rate(ris_hl7_messages_total{status="FAILED"}[5m]) / rate(ris_hl7_messages_total[5m]) > 0.001
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "HL7 interface delivery < 99.9%"
      
      - alert: RISCriticalResultUnacked
        expr: ris_critical_result_unacknowledged > 0
        for: 15m
        labels:
          severity: critical
        annotations:
          summary: "Critical result unacknowledged > 15 minutes"
      
      - alert: RISUnbilledAging
        expr: ris_unbilled_count > 0
        for: 5d
        labels:
          severity: warning
        annotations:
          summary: "Unbilled charges > 5 business days"
```

---

## 11. Testing Strategy

### 11.1 Backend Tests

| Test Type | Framework | Scope |
|:---|:---|:---|
| Unit tests | pytest | Service layer, state machine, conflict detection |
| Integration tests | pytest + async fixtures | API endpoints, DB migrations, RLS isolation |
| E2E tests | pytest + test harness | Order lifecycle, scheduling, MWL/MPPS, billing |
| Conformance tests | pytest + DICOM test set | MWL C-FIND, MPPS N-CREATE/N-SET |
| RLS tests | pytest | Cross-tenant isolation, grant enforcement |

### 11.2 Frontend Tests

| Test Type | Framework | Scope |
|:---|:---|:---|
| Component tests | Vitest + React Testing Library | Tracking board, booking form, report editor |
| E2E tests | Playwright | Order flow, scheduling, reading, billing |
| Accessibility | Playwright + axe | WCAG 2.1 AA compliance |

### 11.3 Key Test Scenarios

1. **Order lifecycle**: ORM → order → schedule → MWL served → MPPS → tracking update → report → sign → charge drop
2. **Conflict-free booking**: Room/technologist conflict detection, EXCLUDE constraint enforcement
3. **MWL serving**: Modality C-FIND query → correct entries returned → station AE filtering
4. **MPPS processing**: N-CREATE → IN_PROGRESS → N-SET → COMPLETED → PACS echo
5. **Critical results**: Flag → notification → acknowledgment → escalation timeout
6. **Billing**: Auto charge drop on sign-off → unbilled aging → claim submission
7. **RLS isolation**: Cross-facility reads denied, granted reads return correct data
8. **Interface engine**: HL7 message parse → route → process → ACK → retry on failure

---

## 12. Acceptance Criteria Summary

### 12.1 MVP Gates

| Gate | Criterion | Verification |
|:---|:---|:---|
| G1 | MWL ≥ 98% auto-fill | Modality test set, no manual entry |
| G2 | 0 scheduling conflicts | EXCLUDE constraint + E2E test |
| G3 | MPPS → tracking < 5s | Latency measurement |
| G4 | Charge capture ≥ 98% | Daily reconciliation |
| G5 | Interface delivery > 99.9% | Message count + exception queue |
| G6 | Tenant provisioning < 15 min | Automated provisioning test |
| G7 | No P0/P1 open defects | Defect triage |

### 12.2 v1.1 Gates (RVG)

| Gate | Criterion | Verification |
|:---|:---|:---|
| RVG-1 | Prior-auth ≥ 95% pre-scan | Metric instrumentation |
| RVG-2 | Unbilled $0 > 5 days | Daily reconciliation |
| RVG-3 | IDN grants live, 0 cross-tenant writes | RLS + audit regression |
| RVG-4 | FHIR read conformance green | Conformance suite |

### 12.3 v2.0 Gates (RVG)

| Gate | Criterion | Verification |
|:---|:---|:---|
| RVG-5 | Full FHIR + portal delivery | Conformance + consent audit |
| RVG-6 | Charge capture ≥ 98%, unbilled $0 > 5 days | Sustained metric |

---

## 13. Risks & Mitigations

| Risk | Impact | Mitigation |
|:---|:---|:---|
| HL7 interface failures | Orders stuck, MWL empty | Exception queue + ≤5-min alerting + retry |
| Double-booking regressions | Scheduling conflicts | DB EXCLUDE constraint + E2E test on every schema change |
| MWL auto-fill < 98% | Technologist re-entry | Conformance test set + worklist quality dashboard |
| Billing capture leakage | Revenue loss | Auto charge drop + daily unbilled reconciliation |
| Critical result escalation failures | HIPAA violation | Tracked acknowledgment + escalation timers + audit |
| IDN cross-tenant data exposure | PHI incident | Read-only grants + RLS OR-clause + audit |
| RIS scope creep | MVP delay | Strict exit gates; features not meeting gates → backlog |
| Existing codebase refactoring risk | Regression | Incremental migration; parallel old/new during transition |

---

## 14. Migration Strategy

### 14.1 Schema Migration

- **Alembic migrations** in `backend/migrations/versions/`
- Each phase gets its own migration(s)
- Existing tables are **altered** (not replaced) to add RIS fields
- New tables are created alongside existing ones
- `ris_orders` replaces `visit_orders` (view-based compatibility during transition)

### 14.2 API Migration

- New RIS endpoints under `/api/ris/` prefix
- Existing `/api/worklist`, `/api/exams`, `/api/reports` endpoints continue to work
- Gradual deprecation: frontend switches to new RIS endpoints
- Legacy endpoints remain for backward compatibility

### 14.3 Frontend Migration

- New RIS routes added to routing
- Existing views continue to work
- Phase 1: Add tracking board alongside existing worklist
- Phase 2: Upgrade worklist to full tracking board
- Phase 3: Add scheduling, billing, admin views

---

## 15. Document Traceability

| This Spec Section | Source Documents |
|:---|:---|
| §2 Architecture | PRD §4.1, 02_end_to_end_workflows.md |
| §3 Data Model | 00_README.md §4, PRD §4.2 |
| §4 API Contracts | PRD §4.2, 04_uiux_requirements.md |
| §5 Service Layer | RELEASE_PLAN.md epics, sprint details |
| §6 Frontend | 04_uiux_requirements.md |
| §7 RBAC | 01_persona_catalog.md §4 |
| §8 Integration | PRD §4.2, 02_end_to_end_workflows.md |
| §9 Implementation | RELEASE_PLAN.md §4, RELEASE_PLAN_V2.md §4 |
| §10 SLAs | 05_metrics_and_slas.md |
| §11 Testing | 06_acceptance_criteria.md |
| §12 Acceptance | 06_acceptance_criteria.md, RELEASE_PLAN.md §2 |
| §13 Risks | PRD §5.2, RELEASE_PLAN.md §7 |
