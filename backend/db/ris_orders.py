"""RIS order persistence (E-RIS-03) — ris_orders + ris_order_procedures.

The spec (docs/RIS-integration/ris-integration-spec.md §3.2) models tenant
scope as facility_id uuid REFERENCES facilities(id), but QuantumPACS has no
facilities table: isolation comes from per-tenant DB pools resolved by
TenantMiddleware (db/conn.py get_conn), and rows carry a tenant_id tag
column like exams/worklist. Cross-facility (IDN) reads reuse the existing
user_tenant_grants + X-Tenant-ID path instead of row-level RLS.
"""
from datetime import datetime, timezone

from pypika import Order

from db.conn import get_tenant_slug
from db.table import Table


class RisOrders(Table):
    name = 'ris_orders'

    async def sync_db(self):
        await self.exec("""
        CREATE TABLE IF NOT EXISTS ris_orders (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id TEXT,
            accession_number TEXT NOT NULL,
            patient_id TEXT NOT NULL,
            patient_name TEXT DEFAULT '',
            patient_dob DATE,
            referring_physician TEXT DEFAULT '',
            clinical_indication TEXT DEFAULT '',
            priority TEXT NOT NULL DEFAULT 'ROUTINE'
                CHECK (priority IN ('ROUTINE', 'URGENT', 'STAT')),
            status TEXT NOT NULL DEFAULT 'ORDERED'
                CHECK (status IN ('ORDERED', 'SCHEDULED', 'ARRIVED', 'IN_PROGRESS',
                                  'COMPLETED', 'READ', 'SIGNED', 'CANCELLED')),
            prior_auth_status TEXT DEFAULT 'NOT_REQUIRED'
                CHECK (prior_auth_status IN ('NOT_REQUIRED', 'REQUIRED', 'PENDING',
                                             'APPROVED', 'DENIED', 'EXPIRED')),
            created_by TEXT DEFAULT '',
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now(),
            CONSTRAINT uq_ris_order_accession UNIQUE (tenant_id, accession_number)
        )
        """)
        await self.exec("""
        CREATE INDEX IF NOT EXISTS ix_ris_orders_tenant_status
            ON ris_orders (tenant_id, status)
        """)
        await self.exec("""
        CREATE INDEX IF NOT EXISTS ix_ris_orders_patient ON ris_orders (patient_id)
        """)
        await self.exec("""
        CREATE INDEX IF NOT EXISTS ix_ris_orders_scheduled
            ON ris_orders (tenant_id, status, created_at)
            WHERE status IN ('ORDERED', 'SCHEDULED')
        """)

    async def create(self, data):
        now = datetime.now(timezone.utc)
        q = self.insert().columns(
            'tenant_id', 'accession_number', 'patient_id', 'patient_name',
            'patient_dob', 'referring_physician', 'clinical_indication',
            'priority', 'status', 'created_by', 'created_at', 'updated_at',
        ).insert((
            get_tenant_slug() or 'default',
            data['accession_number'],
            data['patient_id'],
            data.get('patient_name', ''),
            data.get('patient_dob') or None,
            data.get('referring_physician', ''),
            data.get('clinical_indication', ''),
            data.get('priority', 'ROUTINE'),
            'ORDERED',
            data.get('created_by', ''),
            now, now,
        )).returning('id')
        row = await self.fetchone(q)
        if not row:
            raise RuntimeError('Failed to create order')
        return await self.get(row['id'])

    async def get(self, order_id):
        q = self.select('*').where(self.table.id == order_id)
        return await self.fetchone(q)

    async def get_by_accession(self, accession_number):
        """Idempotency hook: ORM re-sends of a known accession must not
        duplicate the order (services/hl7_engine/service.py)."""
        q = self.select('*').where(self.table.accession_number == accession_number)
        return await self.fetchone(q)

    async def list(self, limit=25, offset=0, status=None, patient_id=None):
        q = self.select('*')
        if status:
            q = q.where(self.table.status == status)
        if patient_id:
            q = q.where(self.table.patient_id == patient_id)
        q = q.orderby(self.table.created_at, order=Order.desc).limit(limit).offset(offset)
        return await self.fetch(q)

    async def update_status(self, order_id, status):
        q = self.update().set(
            self.table.status, status,
        ).set(
            self.table.updated_at, datetime.now(timezone.utc),
        ).where(self.table.id == order_id).returning('id')
        row = await self.fetchone(q)
        if not row:
            return None
        return await self.get(order_id)


class RisOrderProcedures(Table):
    name = 'ris_order_procedures'

    async def sync_db(self):
        await self.exec("""
        CREATE TABLE IF NOT EXISTS ris_order_procedures (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            order_id UUID NOT NULL REFERENCES ris_orders(id) ON DELETE CASCADE,
            tenant_id TEXT,
            procedure_code TEXT NOT NULL,
            procedure_name TEXT NOT NULL,
            modality TEXT NOT NULL,
            body_part TEXT DEFAULT '',
            laterality TEXT DEFAULT '',
            contrast BOOLEAN DEFAULT false,
            cpt_code TEXT DEFAULT '',
            icd10_code TEXT DEFAULT '',
            status TEXT NOT NULL DEFAULT 'ORDERED'
                CHECK (status IN ('ORDERED', 'SCHEDULED', 'IN_PROGRESS', 'COMPLETED')),
            created_at TIMESTAMPTZ DEFAULT now(),
            CONSTRAINT uq_order_proc_per_order UNIQUE (order_id, procedure_code)
        )
        """)

    async def create(self, order_id, data):
        q = self.insert().columns(
            'order_id', 'tenant_id', 'procedure_code', 'procedure_name',
            'modality', 'body_part', 'laterality', 'contrast',
            'cpt_code', 'icd10_code', 'status',
        ).insert((
            order_id,
            get_tenant_slug() or 'default',
            data['procedure_code'],
            data['procedure_name'],
            data['modality'],
            data.get('body_part', ''),
            data.get('laterality', ''),
            data.get('contrast', False),
            data.get('cpt_code', ''),
            data.get('icd10_code', ''),
            'ORDERED',
        )).returning('id')
        row = await self.fetchone(q)
        if not row:
            raise RuntimeError('Failed to create order procedure')
        return await self.get(row['id'])

    async def get(self, procedure_id):
        q = self.select('*').where(self.table.id == procedure_id)
        return await self.fetchone(q)

    async def list_for_order(self, order_id):
        q = self.select('*').where(self.table.order_id == order_id)
        return await self.fetch(q)