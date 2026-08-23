"""Escalation Policy Service for Critical Findings (S10-04).

Queries unacknowledged critical findings older than SLA threshold (default: 15 minutes)
and escalates them to the chief radiologist or ED charge physician.
"""
from db.conn import get_conn
from db.ris_critical_results import RisCriticalResults
from api.notify import notify_role
from config import config
from log import get_logger

log = get_logger(__name__)

DEFAULT_ESCALATION_SLA_MINUTES = 15
BACKUP_ESCALATION_ROLE = 'radiologist'


def _read_sla_minutes():
    """D4: SLA from config, defaulting on absent/invalid values (fail-safe).

    lifecycle.py calls run_escalation_check() with no arguments each tick,
    so the worker picks up operator changes to the SLA without a restart.
    """
    raw = config.get('critical_escalation_sla_minutes',
                     DEFAULT_ESCALATION_SLA_MINUTES)
    try:
        value = int(raw)
    except (TypeError, ValueError):
        log.warning(
            'critical_escalation_sla_minutes=%r invalid; using default %s',
            raw, DEFAULT_ESCALATION_SLA_MINUTES,
        )
        return DEFAULT_ESCALATION_SLA_MINUTES
    if value <= 0:
        log.warning(
            'critical_escalation_sla_minutes=%s must be positive; using default',
            value,
        )
        return DEFAULT_ESCALATION_SLA_MINUTES
    return value


def _read_target_role():
    """D4: escalation target from config, defaulting when empty.

    The recipient-role design (migration 072) defaults the flag recipient
    to ed_physician; the escalation target is separate and configurable.
    """
    role = config.get('critical_escalation_target_role',
                      BACKUP_ESCALATION_ROLE) or ''
    return role if str(role).strip() else BACKUP_ESCALATION_ROLE


class CriticalEscalationEngine:
    async def run_escalation_check(self, sla_minutes=None) -> int:
        """Find overdue critical findings and escalate them. Returns count of escalated items."""
        sla_minutes = sla_minutes or _read_sla_minutes()
        target_role = _read_target_role()
        escalated_count = 0
        async with get_conn() as conn:
            critical_db = RisCriticalResults(conn)
            overdue = await critical_db.get_unacknowledged_over_minutes(sla_minutes)
            for item in overdue:
                escalated = await critical_db.escalate(
                    item['id'], escalated_to=target_role)
                if escalated:
                    escalated_count += 1
                    await notify_role(
                        conn, target_role, 'critical.escalated',
                        f"CRITICAL ESCALATION: Accession {item.get('accession_number')}",
                        f"Critical finding for patient {item.get('patient_name') or item.get('patient_id')} "
                        f"was unacknowledged after {sla_minutes}m: {item.get('finding_description')}",
                        f"/reading/{item.get('exam_id')}",
                    )
                    log.warning(
                        "Critical result %s escalated to %s after %dm SLA breach",
                        item['id'], target_role, sla_minutes,
                    )
        return escalated_count
