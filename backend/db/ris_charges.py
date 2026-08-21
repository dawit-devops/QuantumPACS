"""RIS Billing DB Layer (S11) — ris_charges + ris_claims.

Sprint S11 replaces the S8-14 runtime charge stub with a full charge
lifecycle: PENDING (auto-created on report sign-off) -> BILLED (coder
confirms) -> claim export (837 stub). Unbilled aging surfaces PENDING
charges older than the aging threshold. All queries scope by tenant_id
(S11-15 — per-tenant pool isolation, same convention as ris_orders).
"""

from db.table import Table

CHARGE_STATUS_PENDING = 'PENDING'
CHARGE_STATUS_BILLED = 'BILLED'
CHARGE_STATUS_PAID = 'PAID'
CHARGE_STATUS_DENIED = 'DENIED'
CHARGE_STATUS_VOID = 'VOID'

CLAIM_STATUS_DRAFT = 'DRAFT'
CLAIM_STATUS_SUBMITTED = 'SUBMITTED'
CLAIM_STATUS_ACKNOWLEDGED = 'ACKNOWLEDGED'
CLAIM_STATUS_PAID = 'PAID'
CLAIM_STATUS_DENIED = 'DENIED'

# Default unit price when a procedure has no pricing catalog entry.
DEFAULT_CHARGE_AMOUNT = 0.00


class RisCharges(Table):
    name = 'ris_charges'

    async def sync_db(self):
        await self.conn.execute("""
        CREATE TABLE IF NOT EXISTS ris_charges (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id TEXT DEFAULT 'default',
            order_id UUID,
            report_id UUID,
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

    async def create(self, *, report_id, exam_id=None, accession_number='',
                     patient_id='', patient_name='', cpt_code='',
                     cpt_description='', icd10_code='', charge_amount=0.0,
                     created_by='', tenant_id='default'):
        """Insert a PENDING charge idempotently per report (V-3 guard).

        A report signed twice (or co-signed) must not produce a second
        charge row — the NOT EXISTS guard makes this a no-op instead of a
        duplicate, preserving the S8 V-3 fix in the full implementation.
        """
        await self.conn.execute("""
        INSERT INTO ris_charges
            (tenant_id, report_id, exam_id, accession_number, patient_id,
             patient_name, cpt_code, cpt_description, icd10_code,
             charge_amount, status, created_by)
        SELECT $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, 'PENDING', $11
        WHERE NOT EXISTS (
            SELECT 1 FROM ris_charges WHERE report_id = $2
        )
        """, tenant_id, report_id, exam_id, accession_number, patient_id,
             patient_name, cpt_code, cpt_description, icd10_code,
             charge_amount, created_by)

    async def get(self, charge_id, tenant_id='default'):
        return await self.conn.fetchrow(
            "SELECT * FROM ris_charges WHERE id = $1 AND tenant_id = $2",
            charge_id, tenant_id,
        )

    async def mark_billed(self, charge_id, tenant_id='default'):
        """Coder confirms a charge -> BILLED. Only PENDING may transition."""
        return await self.conn.fetchrow("""
        UPDATE ris_charges
        SET status = 'BILLED', updated_at = now()
        WHERE id = $1 AND tenant_id = $2 AND status = 'PENDING'
        RETURNING id, status
        """, charge_id, tenant_id)

    async def list_pending(self, tenant_id='default', limit=200, offset=0):
        """Signed-but-unbilled queue (S11-04) with coding attached."""
        from db.billing import money
        rows = await self.conn.fetch(
            "SELECT id, patient_id, patient_name, accession_number,"
            " cpt_code, cpt_description, icd10_code, charge_amount, status,"
            " created_at"
            " FROM ris_charges"
            " WHERE tenant_id = $1 AND status = 'PENDING'"
            " ORDER BY created_at"
            " LIMIT $2 OFFSET $3",
            tenant_id, limit, offset,
        )
        out = []
        for r in rows:
            d = dict(r)
            d['charge_amount'] = money(d.get('charge_amount'))
            out.append(d)
        return out

    async def count_pending(self, tenant_id='default'):
        return await self.conn.fetchval(
            "SELECT count(*) FROM ris_charges"
            " WHERE tenant_id = $1 AND status = 'PENDING'",
            tenant_id,
        )

    async def aging_groups(self, tenant_id='default', min_age_days=5):
        """Unbilled aging grouped by sign date (S11-07).

        A PENDING charge becomes actionable once its report has been
        signed for more than min_age_days. Returns per-date groups with
        count, total amount and the oldest charge's age in days.
        """
        rows = await self.conn.fetch("""
        SELECT c.created_at::date AS date,
               count(*) AS count,
               sum(c.charge_amount) AS total_amount,
               max(date_part('day', now() - c.created_at))::int AS oldest_charge_days
        FROM ris_charges c
        WHERE c.tenant_id = $1 AND c.status = 'PENDING'
          AND c.created_at < now() - make_interval(days => $2)
        GROUP BY c.created_at::date
        ORDER BY c.created_at::date
        """, tenant_id, min_age_days)
        total = await self.conn.fetchval(
            "SELECT count(*) FROM ris_charges"
            " WHERE tenant_id = $1 AND status = 'PENDING'"
            " AND created_at < now() - make_interval(days => $2)",
            tenant_id, min_age_days,
        )
        from db.billing import money
        out = []
        for r in rows:
            d = dict(r)
            d['total_amount'] = money(d.get('total_amount'))
            out.append(d)
        return out, total or 0

    async def reconciliation(self, tenant_id='default'):
        """S11-13: signed reports vs charges — capture-rate inputs."""
        signed = await self.conn.fetchval(
            "SELECT count(*) FROM reports"
            " WHERE tenant_id = $1 AND status = 'final'",
            tenant_id,
        )
        charged = await self.conn.fetchval(
            "SELECT count(DISTINCT report_id) FROM ris_charges"
            " WHERE tenant_id = $1",
            tenant_id,
        )
        return {'signed': signed or 0, 'charged': charged or 0}


class RisClaims(Table):
    name = 'ris_claims'

    async def sync_db(self):
        await self.conn.execute("""
        CREATE TABLE IF NOT EXISTS ris_claims (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id TEXT DEFAULT 'default',
            charge_id UUID NOT NULL,
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

    async def submit(self, charge_id, claim_number, payer_id='', payer_name='',
                     tenant_id='default'):
        """837 export stub (S11-09): create a SUBMITTED claim for a charge."""
        return await self.conn.fetchrow("""
        INSERT INTO ris_claims
            (tenant_id, charge_id, claim_number, payer_id, payer_name,
             status, submitted_at)
        VALUES ($1, $2, $3, $4, $5, 'SUBMITTED', now())
        RETURNING id, status
        """, tenant_id, charge_id, claim_number, payer_id, payer_name)

    async def record_denial(self, claim_id, rejection_code='', rejection_reason='',
                            tenant_id='default'):
        """835 import stub (S11-10): mark a claim DENIED."""
        return await self.conn.fetchrow("""
        UPDATE ris_claims
        SET status = 'DENIED', rejection_code = $3, rejection_reason = $4,
            updated_at = now()
        WHERE id = $1 AND tenant_id = $2
        RETURNING id, status
        """, claim_id, tenant_id, rejection_code, rejection_reason)

    async def get(self, claim_id, tenant_id='default'):
        return await self.conn.fetchrow(
            "SELECT * FROM ris_claims WHERE id = $1 AND tenant_id = $2",
            claim_id, tenant_id,
        )


async def drop_charge(conn, *, report_id, exam_id, accession_number,
                      patient_id='', patient_name='', procedure_desc='',
                      indication='', radiologist_id='', charge_amount=0.0,
                      tenant_id='default'):
    """S11-03: real auto charge drop on report sign-off.

    Resolves the CPT/ICD-10 suggestion from CodingService, then inserts the
    full PENDING charge row (idempotent per report). Keeps the drop_charge
    signature close to the S8-14 stub so api/reports.py wiring stays simple.
    """
    from db.ris_coding import CodingService

    coding = CodingService(conn)
    suggestion = await coding.get_suggestions(procedure_desc, tenant_id)
    await RisCharges(conn).create(
        report_id=report_id,
        exam_id=exam_id,
        accession_number=accession_number,
        patient_id=patient_id,
        patient_name=patient_name,
        cpt_code=suggestion.get('cpt_code', ''),
        cpt_description=suggestion.get('cpt_description', ''),
        icd10_code=suggestion.get('icd10_code', ''),
        charge_amount=charge_amount,
        created_by=radiologist_id,
        tenant_id=tenant_id,
    )
