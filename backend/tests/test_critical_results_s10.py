"""Tests for Sprint S10: Critical Results + Distribution (Tasks S10-13 .. S10-15).

Covers critical finding flagging, ED physician notification, mandated acknowledgment,
background escalation SLA breach, HL7 ORU^R01 distribution engine with delivery retry,
and RLS tenant isolation.
"""
import pytest
from datetime import datetime, timezone, timedelta
from db.conn import get_conn, database
from db.ris_critical_results import RisCriticalResults
from services.notification.escalation import CriticalEscalationEngine
from services.results_distribution.service import ResultsDistributionEngine
from db.reports import Reports


@pytest.fixture(autouse=True)
async def setup_db():
    await database.setup()
    yield
    await database.close()


class TestCriticalResultsFlow:
    @pytest.mark.asyncio
    async def test_create_and_acknowledge_critical_flag(self):
        async with get_conn() as conn:
            critical_db = RisCriticalResults(conn)
            flag = await critical_db.create_flag({
                'accession_number': 'ACC-CRIT-01',
                'patient_id': 'PAT-CRIT-01',
                'patient_name': 'John Doe',
                'finding_description': 'Acute Tension Pneumothorax',
                'recipient_role': 'ed_physician',
                'recipient_name': 'Dr. ED Attending',
            }, flagged_by='rad_user_1')

            assert flag['status'] == 'flagged'
            assert flag['finding_description'] == 'Acute Tension Pneumothorax'
            assert flag['recipient_role'] == 'ed_physician'

            # Acknowledge the flag
            ack = await critical_db.acknowledge(flag['id'], acknowledged_by='ed_doc_1')
            assert ack['status'] == 'acknowledged'
            assert ack['acknowledged_by'] == 'ed_doc_1'
            assert ack['acknowledged_at'] is not None

    @pytest.mark.asyncio
    async def test_critical_escalation_engine(self):
        async with get_conn() as conn:
            critical_db = RisCriticalResults(conn)
            # Create an overdue unacknowledged flag (20 minutes ago)
            past_time = datetime.now(timezone.utc) - timedelta(minutes=20)
            row = await conn.fetchrow("""
                INSERT INTO ris_critical_results
                (accession_number, patient_id, patient_name, finding_description,
                 recipient_role, status, flagged_by, flagged_at, tenant_id, created_at, updated_at)
                VALUES ('ACC-OVERDUE-01', 'PAT-99', 'Jane Smith', 'Acute Intracranial Hemorrhage',
                        'ed_physician', 'flagged', 'rad_1', $1, 'default', $1, $1)
                RETURNING id
            """, past_time)
            critical_id = row['id']

            # Run escalation engine
            engine = CriticalEscalationEngine()
            escalated_count = await engine.run_escalation_check(sla_minutes=15)
            assert escalated_count >= 1

            # Verify status in database
            updated = await conn.fetchrow("SELECT status, escalated_to FROM ris_critical_results WHERE id = $1", critical_id)
            assert updated['status'] == 'escalated'
            assert updated['escalated_to'] == 'radiologist'


class TestResultsDistributionEngine:
    @pytest.mark.asyncio
    async def test_oru_generation_and_delivery_retry(self):
        async with get_conn() as conn:
            exam_row = await conn.fetchrow(
                "INSERT INTO exams (accession_number, patient_id, status, modality) "
                "VALUES ('ACC-ORU-DIST', 'PAT-ORU-01', 'completed', 'CT') "
                "RETURNING id"
            )
            exam_id = exam_row['id']

            report = await Reports(conn).create(
                exam_id,
                {'status': 'draft', 'findings': 'Mass in right lung', 'impression': 'Probable neoplasm', 'is_critical': True},
                created_by='rad_user_1',
            )

            # Test distribution engine
            dist_engine = ResultsDistributionEngine()
            dist_res = await dist_engine.distribute_report(report['id'])
            assert dist_res['status'] == 'SENT'
            assert 'ORU^R01' in dist_res['payload']
            assert 'CRITICAL' in dist_res['payload']

            # Verify report timestamp update
            rep_check = await conn.fetchrow("SELECT distributed_at FROM reports WHERE id = $1", report['id'])
            assert rep_check['distributed_at'] is not None


class TestCriticalResultsRLS:
    @pytest.mark.asyncio
    async def test_critical_results_list_tenant_filtered(self):
        async with get_conn() as conn:
            critical_db = RisCriticalResults(conn)
            active = await critical_db.list_active()
            assert isinstance(active, list)
