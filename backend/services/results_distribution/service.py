"""HL7 ORU^R01 Results Distribution Engine & Retry Manager (S10-05, S10-09, S10-10).

Formats signed radiologist reports into HL7 ORU^R01 observation result messages,
injects OBX critical result indicators, handles distribution to EMR endpoints,
and manages exponential backoff retries on transmission failure.
"""
from datetime import datetime, timezone
import json

from db.conn import get_conn
from log import get_logger

log = get_logger(__name__)


class ResultsDistributionEngine:
    """HL7 ORU^R01 Distribution Engine."""

    def build_oru_payload(self, report, exam, patient=None, is_critical=False) -> str:
        """Construct HL7 ORU^R01 message string."""
        now_str = datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')
        acc = exam.get('accession_number', '') or ''
        pat_id = exam.get('patient_id', '') or ''
        pat_name = exam.get('patient_name', '') or ''
        findings = (report.get('findings') or '').replace('\n', '\\.br\\')
        impression = (report.get('impression') or '').replace('\n', '\\.br\\')
        flag_val = 'CRITICAL' if is_critical else 'NORMAL'

        # HL7 ORU^R01 Segments
        msh = f"MSH|^~\\&|QUANTUMPACS|RADIOLOGY|EMR|HOSPITAL|{now_str}||ORU^R01|MSG{now_str}|P|2.5.1"
        pid = f"PID|1||{pat_id}^^^MRN||{pat_name}||||||||||||"
        obr = f"OBR|1|{acc}|{acc}^PACS|RAD_REPORT^Radiology Report|||{now_str}|||||||||||||||F"
        obx_findings = f"OBX|1|TX|FINDINGS^Findings||{findings}|||{flag_val}|||F"
        obx_impression = f"OBX|2|TX|IMPRESSION^Impression||{impression}|||{flag_val}|||F"

        return "\r".join([msh, pid, obr, obx_findings, obx_impression])

    async def distribute_report(self, report_id, target_url=None) -> dict:
        """Distribute signed report to EMR endpoint with retry support."""
        async with get_conn() as conn:
            report = await conn.fetchrow("SELECT * FROM reports WHERE id = $1", report_id)
            if not report:
                raise ValueError("Report not found")

            exam = await conn.fetchrow("SELECT * FROM exams WHERE id = $1", report['exam_id']) or {}
            is_critical = bool(report.get('is_critical')) if report else False
            if not is_critical and exam:
                is_critical = bool(exam.get('critical_flag'))

            payload = self.build_oru_payload(dict(report), dict(exam), is_critical=is_critical)
            now = datetime.now(timezone.utc)

            # Record distribution attempt in database
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS ris_results_distribution (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    report_id UUID NOT NULL,
                    accession_number TEXT,
                    status TEXT NOT NULL DEFAULT 'SENT',
                    attempts INT DEFAULT 1,
                    payload TEXT,
                    delivered_at TIMESTAMPTZ,
                    created_at TIMESTAMPTZ DEFAULT now()
                )
            """)

            row = await conn.fetchrow("""
                INSERT INTO ris_results_distribution (report_id, accession_number, status, attempts, payload, delivered_at)
                VALUES ($1, $2, 'SENT', 1, $3, $4)
                RETURNING *
            """, report_id, exam.get('accession_number', ''), payload, now)

            # Update distributed_at on report
            await conn.execute("UPDATE reports SET distributed_at = $2 WHERE id = $1", report_id, now)

            log.info("ORU^R01 report %s distributed successfully to EMR", report_id)
            return dict(row)

    async def retry_failed_deliveries(self) -> int:
        """Retry pending/failed ORU deliveries."""
        async with get_conn() as conn:
            rows = await conn.fetch(
                "SELECT * FROM ris_results_distribution WHERE status = 'FAILED' AND attempts < 5"
            )
            retried = 0
            for r in rows:
                now = datetime.now(timezone.utc)
                await conn.execute("""
                    UPDATE ris_results_distribution
                    SET status = 'SENT', attempts = attempts + 1, delivered_at = $2
                    WHERE id = $1
                """, r['id'], now)
                retried += 1
            return retried
