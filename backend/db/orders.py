"""Orders (coordination) persistence — care_coordinator review P0-2.

The Orders page is a read-only coordination view over visit_orders (front-desk
order intake, see db/frontdesk.py), joined to the imaging lifecycle so a
coordinator sees request → scheduled → performed → reported in one row.

visit_orders carries no FK to worklist_entries/exams (orders are created at the
visit, imaging is scheduled later), so the lifecycle linkage is best-effort:
the most recent worklist entry / exam / report for the patient.
"""


class Orders:
    def __init__(self, conn):
        self.conn = conn

    async def list_for_coordinator(self):
        """Coordination list: each order row plus the patient's latest
        schedule/exam/report state (best-effort patient_id join)."""
        return await self.conn.fetch(
            """
            SELECT o.id, o.visit_id, o.patient_id,
                   p.id AS patient_db_id,
                   p.name AS patient_name,
                   o.requested_procedure, o.indication, o.urgency,
                   o.status AS order_status, o.referring_physician, o.created_at,
                   wl.status AS wl_status, wl.scheduled_date, wl.modality,
                   e.status AS exam_status, e.id AS exam_id,
                   r.status AS report_status, r.id AS report_id
            FROM visit_orders o
            LEFT JOIN patients p ON p.patient_id = o.patient_id
            LEFT JOIN LATERAL (
                SELECT status, scheduled_date, modality
                FROM worklist_entries w
                WHERE w.patient_id = o.patient_id
                ORDER BY w.created_at DESC
                LIMIT 1
            ) wl ON true
            LEFT JOIN LATERAL (
                SELECT status, id
                FROM exams e
                WHERE e.patient_id = o.patient_id
                ORDER BY e.created_at DESC
                LIMIT 1
            ) e ON true
            LEFT JOIN LATERAL (
                SELECT status, id
                FROM reports r
                WHERE r.exam_id = e.id
                ORDER BY r.created_at DESC
                LIMIT 1
            ) r ON true
            ORDER BY o.created_at DESC
            """
        )
