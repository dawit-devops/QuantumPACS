"""Escalation Policy Service for Critical Findings (S10-04).

Queries unacknowledged critical findings older than SLA threshold (default: 15 minutes)
and escalates them to the chief radiologist or ED charge physician.
"""
from db.conn import get_conn
from db.ris_critical_results import RisCriticalResults
from api.notify import notify_role
from log import get_logger

log = get_logger(__name__)

DEFAULT_ESCALATION_SLA_MINUTES = 15
BACKUP_ESCALATION_ROLE = 'radiologist'


class CriticalEscalationEngine:
    async def run_escalation_check(self, sla_minutes=DEFAULT_ESCALATION_SLA_MINUTES) -> int:
        """Find overdue critical findings and escalate them. Returns count of escalated items."""
        escalated_count = 0
        async with get_conn() as conn:
            critical_db = RisCriticalResults(conn)
            overdue = await critical_db.get_unacknowledged_over_minutes(sla_minutes)
            for item in overdue:
                escalated = await critical_db.escalate(item['id'], escalated_to=BACKUP_ESCALATION_ROLE)
                if escalated:
                    escalated_count += 1
                    await notify_role(
                        conn, BACKUP_ESCALATION_ROLE, 'critical.escalated',
                        f"CRITICAL ESCALATION: Accession {item.get('accession_number')}",
                        f"Critical finding for patient {item.get('patient_name') or item.get('patient_id')} "
                        f"was unacknowledged after {sla_minutes}m: {item.get('finding_description')}",
                        f"/reading/{item.get('exam_id')}",
                    )
                    log.warning(
                        "Critical result %s escalated after %dm SLA breach",
                        item['id'], sla_minutes,
                    )
        return escalated_count
