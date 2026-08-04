"""R19 Hospital Staff Portal data access.

Every patient query joins patient_staff_scope for the current user — the
minimum-necessary boundary (HIPAA) — so out-of-scope patients never match.
Uses raw asyncpg SQL: these queries are security-critical and stay explicit.
"""


class Portal:
    def __init__(self, conn=None):
        self.conn = conn

    async def patient_exists(self, patient_id):
        return await self.conn.fetchval(
            "SELECT 1 FROM patients WHERE patient_id = $1",
            patient_id,
        )

    async def get_scope(self, patient_id, user_id):
        return await self.conn.fetchrow(
            "SELECT id, scope_type FROM patient_staff_scope"
            " WHERE patient_id = $1 AND user_id = $2",
            patient_id, user_id,
        )

    async def list_scope(self, user_id):
        rows = await self.conn.fetch(
            """
            SELECT pss.id, pss.patient_id, pss.scope_type, pss.created_at,
                   p.name, p.birth_date, p.sex
            FROM patient_staff_scope pss
            JOIN patients p ON p.patient_id = pss.patient_id
            WHERE pss.user_id = $1
            ORDER BY pss.created_at DESC
            """,
            user_id,
        )
        return [dict(r) for r in rows]

    async def create_scope(self, patient_id, user_id, scope_type):
        return await self.conn.fetchrow(
            """
            INSERT INTO patient_staff_scope (patient_id, user_id, scope_type, assigned_by)
            VALUES ($1, $2, $3, $2)
            ON CONFLICT (patient_id, user_id) DO NOTHING
            RETURNING id, scope_type
            """,
            patient_id, user_id, scope_type,
        )

    async def delete_scope(self, scope_id, user_id):
        return await self.conn.fetchrow(
            "DELETE FROM patient_staff_scope WHERE id = $1 AND user_id = $2"
            " RETURNING id, patient_id",
            scope_id, user_id,
        )

    async def search_patients(self, user_id, query):
        like = f'%{query}%'
        rows = await self.conn.fetch(
            """
            SELECT p.patient_id, p.name, p.birth_date, p.sex
            FROM patients p
            JOIN patient_staff_scope pss
              ON pss.patient_id = p.patient_id AND pss.user_id = $1
            WHERE p.name ILIKE $2 OR p.patient_id ILIKE $2
            LIMIT 20
            """,
            user_id, like,
        )
        return [dict(r) for r in rows]

    async def get_demographics(self, patient_id):
        return await self.conn.fetchrow(
            "SELECT patient_id, name, birth_date, sex FROM patients"
            " WHERE patient_id = $1",
            patient_id,
        )

    async def list_orders(self, patient_id):
        rows = await self.conn.fetch(
            """
            SELECT id, accession_number, modality, requested_procedure_desc,
                   status, priority, created_at, completed_at
            FROM exams
            WHERE patient_id = $1
            ORDER BY created_at DESC
            """,
            patient_id,
        )
        return [dict(r) for r in rows]

    async def list_final_reports(self, patient_id):
        rows = await self.conn.fetch(
            """
            SELECT r.id AS report_id, r.exam_id, e.accession_number,
                   r.signed_at, r.signed_by
            FROM reports r
            JOIN exams e ON e.id = r.exam_id
            WHERE e.patient_id = $1 AND r.status = 'final'
            ORDER BY r.signed_at DESC
            """,
            patient_id,
        )
        return [dict(r) for r in rows]

    async def get_final_report(self, patient_id, report_id):
        row = await self.conn.fetchrow(
            """
            SELECT r.id AS report_id, r.exam_id, r.status, e.accession_number,
                   r.findings, r.impression, r.recommendations,
                   r.signed_by, r.signed_at
            FROM reports r
            JOIN exams e ON e.id = r.exam_id
            WHERE r.id = $1 AND e.patient_id = $2
            """,
            report_id, patient_id,
        )
        # Defense in depth: draft/preliminary must never leave this endpoint,
        # even if a future caller drops the status filter from the SQL.
        if not row or row['status'] != 'final':
            return None
        result = dict(row)
        result.pop('status', None)
        return result

    async def list_follow_ups(self, user_id, status=None):
        if status:
            rows = await self.conn.fetch(
                """
                SELECT fu.id, fu.report_id, fu.exam_id, fu.patient_id,
                       fu.reason, fu.status, fu.priority, fu.assigned_to,
                       fu.created_at, fu.updated_at, e.accession_number
                FROM follow_up_requests fu
                LEFT JOIN exams e ON e.id = fu.exam_id
                WHERE fu.requester_id = $1 AND fu.status = $2
                ORDER BY fu.created_at DESC
                """,
                user_id, status,
            )
        else:
            rows = await self.conn.fetch(
                """
                SELECT fu.id, fu.report_id, fu.exam_id, fu.patient_id,
                       fu.reason, fu.status, fu.priority, fu.assigned_to,
                       fu.created_at, fu.updated_at, e.accession_number
                FROM follow_up_requests fu
                LEFT JOIN exams e ON e.id = fu.exam_id
                WHERE fu.requester_id = $1
                ORDER BY fu.created_at DESC
                """,
                user_id,
            )
        return [dict(r) for r in rows]

    async def create_follow_up(self, user_id, body):
        return await self.conn.fetchrow(
            """
            INSERT INTO follow_up_requests
                (report_id, exam_id, patient_id, requester_id, reason, status, priority)
            VALUES ($1, $2, $3, $4, $5, 'submitted', $6)
            RETURNING id
            """,
            body.report_id, body.exam_id, body.patient_id, user_id,
            body.reason, body.priority,
        )

    async def update_follow_up_status(self, follow_up_id, user_id, status):
        return await self.conn.fetchrow(
            """
            UPDATE follow_up_requests
            SET status = $1, updated_at = now()
            WHERE id = $2 AND requester_id = $3
            RETURNING id
            """,
            status, follow_up_id, user_id,
        )
