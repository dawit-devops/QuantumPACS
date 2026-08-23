"""D4 (GAP_AUDIT_TDD_PIPELINE.md): escalation policy must be configurable.

The SLA (15 min) and target role ('radiologist') were hardcoded module
constants contradicting the recipient-role design (migration 072 defaults
the escalation recipient to ed_physician). Config keys drive both, the
worker reads them each tick, and invalid config fails safe to defaults.
"""
import pytest
from unittest.mock import patch
from datetime import datetime, timezone, timedelta

from db.conn import get_conn, database
from services.notification.escalation import CriticalEscalationEngine


@pytest.fixture(autouse=True)
async def setup_db():
    await database.setup()
    yield
    await database.close()


async def _seed_overdue_flag(conn, minutes=20):
    past_time = datetime.now(timezone.utc) - timedelta(minutes=minutes)
    return await conn.fetchrow("""
        INSERT INTO ris_critical_results
        (accession_number, patient_id, patient_name, finding_description,
         recipient_role, status, flagged_by, flagged_at, tenant_id, created_at, updated_at)
        VALUES ('ACC-D4-01', 'PAT-D4', 'D4 Patient', 'Acute Hemorrhage',
                'ed_physician', 'flagged', 'rad_1', $1, 'default', $1, $1)
        RETURNING id, status
        """, past_time)


class TestEscalationPolicyConfig:
    @pytest.mark.asyncio
    async def test_defaults_apply_when_config_absent(self):
        async with get_conn() as conn:
            flag = await _seed_overdue_flag(conn)
            try:
                engine = CriticalEscalationEngine()
                count = await engine.run_escalation_check()
                assert count >= 1
                updated = await conn.fetchrow(
                    "SELECT status, escalated_to FROM ris_critical_results"
                    " WHERE id = $1", flag['id'])
                assert updated['status'] == 'escalated'
                assert updated['escalated_to'] == 'radiologist'
            finally:
                await conn.execute(
                    "DELETE FROM ris_critical_results WHERE tenant_id = 'default'"
                    " AND accession_number = 'ACC-D4-01'")

    @pytest.mark.asyncio
    async def test_config_overrides_change_worker_behavior(self):
        async with get_conn() as conn:
            flag = await _seed_overdue_flag(conn, minutes=5)
            try:
                with patch.dict('services.notification.escalation.config', {
                    'critical_escalation_sla_minutes': '3',
                    'critical_escalation_target_role': 'ed_physician',
                }, clear=False):
                    engine = CriticalEscalationEngine()
                    count = await engine.run_escalation_check()
                assert count >= 1, '5-minute-old flag must breach a 3-minute SLA'
                updated = await conn.fetchrow(
                    "SELECT status, escalated_to FROM ris_critical_results"
                    " WHERE id = $1", flag['id'])
                assert updated['status'] == 'escalated'
                assert updated['escalated_to'] == 'ed_physician'
            finally:
                await conn.execute(
                    "DELETE FROM ris_critical_results WHERE tenant_id = 'default'"
                    " AND accession_number = 'ACC-D4-01'")

    @pytest.mark.asyncio
    async def test_invalid_config_fails_safe_to_defaults(self):
        async with get_conn() as conn:
            flag = await _seed_overdue_flag(conn, minutes=5)
            try:
                with patch.dict('services.notification.escalation.config', {
                    'critical_escalation_sla_minutes': 'not-a-number',
                    'critical_escalation_target_role': '',
                }, clear=False):
                    engine = CriticalEscalationEngine()
                    count = await engine.run_escalation_check()
                # Invalid SLA falls back to the 15-minute default, so a
                # 5-minute-old flag is NOT yet overdue — fail-safe.
                assert count == 0
                updated = await conn.fetchrow(
                    "SELECT status FROM ris_critical_results WHERE id = $1",
                    flag['id'])
                assert updated['status'] == 'flagged'
            finally:
                await conn.execute(
                    "DELETE FROM ris_critical_results WHERE tenant_id = 'default'"
                    " AND accession_number = 'ACC-D4-01'")
