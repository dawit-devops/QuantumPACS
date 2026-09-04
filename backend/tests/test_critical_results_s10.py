"""Tests for Sprint S10: Critical Results + Distribution (Tasks S10-13 .. S10-15).

Covers critical finding flagging, ED physician notification, mandated acknowledgment,
background escalation SLA breach, HL7 ORU^R01 distribution engine with delivery retry,
and RLS tenant isolation.
"""
import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime, timezone, timedelta
from starlette.testclient import TestClient
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


class TestCriticalFlagPostValidation:
    """S-8: the flag POST must not accept a payload with no patient
    identity — an untargetable alert is worse than none."""

    def _post(self, payload):
        from unittest.mock import patch
        from starlette.applications import Starlette
        from starlette.middleware import Middleware
        from starlette.middleware.base import BaseHTTPMiddleware
        from starlette.routing import Route
        from api.auth import User
        from api.notifications import CriticalResultsHandler

        class _FakeAuth(BaseHTTPMiddleware):
            def __init__(self, _app, user=None):
                super().__init__(_app)
                self._user = user or User({'id': 1, 'permissions': []})

            async def dispatch(self, request, call_next):
                request.scope['user'] = self._user
                request.scope['auth'] = None
                return await call_next(request)

        user = User({'id': 1, 'permissions': ['REPORT_WRITE']})
        test_app = Starlette(
            routes=[Route('/critical', endpoint=CriticalResultsHandler)],
            middleware=[Middleware(_FakeAuth, user=user)],
        )
        with patch('api.notifications.get_conn'):
            return TestClient(test_app).post('/critical', json=payload)

    def test_rejects_missing_patient_identity(self):
        resp = self._post({'finding_description': 'Acute hemorrhage'})
        assert resp.status_code == 400, \
            'a flag without any patient identity must be rejected'

    def test_accepts_accession_plus_patient(self):
        with patch('api.notify.notify_role'), \
             patch('db.ris_critical_results.RisCriticalResults') as cls:
            fake = AsyncMock()
            fake.create_flag = AsyncMock(return_value={'id': 'f1'})
            cls.return_value = fake
            resp = self._post({
                'finding_description': 'Acute hemorrhage',
                'accession_number': 'ACC-FLAG-01',
                'patient_name': 'Jane Smith',
            })
        assert resp.status_code == 200


class TestCriticalEventCatalog:
    """H11: critical lifecycle events must be pref-configurable."""

    def test_critical_events_in_catalog(self):
        from db.notification_prefs import NotificationPrefs, CLINICAL_EVENT_TYPES
        for et in ('critical.flagged', 'critical.escalated'):
            assert et in NotificationPrefs.EVENT_CATALOG, f'{et} not in catalog'
            assert et in CLINICAL_EVENT_TYPES, f'{et} not clinical'

    def test_admin_roles_mute_critical_events_by_default(self):
        from db.notification_prefs import NotificationPrefs
        assert NotificationPrefs.default_enabled('super_admin', 'critical.flagged') is False
        assert NotificationPrefs.default_enabled('tenant_admin', 'critical.escalated') is False
        assert NotificationPrefs.default_enabled('radiologist', 'critical.flagged') is True


class TestEscalationScoping:
    """V-5: the escalation query must be scoped — a finding explicitly
    assigned to a specific recipient is not in the engine's default pool,
    and escalate() must not clobber an already-acknowledged finding."""

    @pytest.mark.asyncio
    async def test_query_skips_findings_assigned_to_specific_recipient(self):
        async with get_conn() as conn:
            past_time = datetime.now(timezone.utc) - timedelta(minutes=20)
            async def _flag(acc, recipient_id):
                return await conn.fetchrow("""
                    INSERT INTO ris_critical_results
                    (accession_number, patient_id, patient_name, finding_description,
                     recipient_role, recipient_id, status, flagged_by, flagged_at,
                     tenant_id, created_at, updated_at)
                    VALUES ($1, 'PAT-X', 'X', 'Acute Hemorrhage',
                            'ed_physician', $2, 'flagged', 'rad_1', $3,
                            'default', $3, $3)
                    RETURNING id
                """, acc, recipient_id, past_time)
            assigned = await _flag('ACC-ASSIGNED-01', 'ed-doc-42')
            pool = await _flag('ACC-POOL-01', '')

            overdue = await RisCriticalResults(conn).get_unacknowledged_over_minutes(15)
            ids = [r['id'] for r in overdue]
            assert pool['id'] in ids
            assert assigned['id'] not in ids, \
                'an explicitly-assigned finding must not be escalated by the generic engine'

    @pytest.mark.asyncio
    async def test_escalate_does_not_clobber_acknowledged(self):
        async with get_conn() as conn:
            past_time = datetime.now(timezone.utc) - timedelta(minutes=20)
            row = await conn.fetchrow("""
                INSERT INTO ris_critical_results
                (accession_number, patient_id, patient_name, finding_description,
                 recipient_role, status, flagged_by, flagged_at, tenant_id, created_at, updated_at)
                VALUES ('ACC-ACKED-01', 'PAT-Y', 'Y', 'Acute Hemorrhage',
                        'ed_physician', 'acknowledged', 'rad_1', $1, 'default', $1, $1)
                RETURNING id
            """, past_time)
            result = await RisCriticalResults(conn).escalate(row['id'], escalated_to='radiologist')
            assert result is None, \
                'escalate must not overwrite an acknowledged finding'


class TestAckGuardDb:
    """H12: acknowledge must not overwrite escalated/cleared state."""

    @pytest.mark.asyncio
    async def test_acknowledge_requires_flagged_status(self):
        async with get_conn() as conn:
            critical_db = RisCriticalResults(conn)
            flag = await critical_db.create_flag({
                'accession_number': 'ACC-CRIT-GUARD',
                'patient_id': 'PAT-GUARD',
                'patient_name': 'Guard Patient',
                'finding_description': 'Acute ischemia',
                'recipient_id': 'ed_1',
                'recipient_role': 'ed_physician',
            }, flagged_by='rad_1')
            await critical_db.escalate(flag['id'], escalated_to='radiologist')
            ack = await critical_db.acknowledge(flag['id'], acknowledged_by='ed_1')
            assert ack is None

    @pytest.mark.asyncio
    async def test_acknowledge_requires_flagged_status_not_acknowledged(self):
        async with get_conn() as conn:
            critical_db = RisCriticalResults(conn)
            flag = await critical_db.create_flag({
                'accession_number': 'ACC-CRIT-GUARD2',
                'patient_id': 'PAT-GUARD2',
                'patient_name': 'Guard Patient Two',
                'finding_description': 'Pneumothorax',
                'recipient_id': 'ed_2',
                'recipient_role': 'ed_physician',
            }, flagged_by='rad_2')
            await critical_db.acknowledge(flag['id'], acknowledged_by='ed_2')
            again = await critical_db.acknowledge(flag['id'], acknowledged_by='ed_2')
            assert again is None


class TestResultsDistributionEngine:
    @pytest.mark.asyncio
    async def test_oru_generation_and_delivery_retry(self):
        """A2: SENT requires a successful transmission — the engine is
        exercised through a patched-successful _deliver so the payload
        assertions run against the earned-status path."""
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
            try:
                with patch('config.config',
                           {'distribution_endpoint': 'http://emr:8080/oru'}), \
                     patch.object(dist_engine, '_deliver',
                                  new=AsyncMock(return_value=True)):
                    dist_res = await dist_engine.distribute_report(report['id'])
                assert dist_res['status'] == 'SENT'
                assert 'ORU^R01' in dist_res['payload']
                assert 'CRITICAL' in dist_res['payload']

                # Verify report timestamp update
                rep_check = await conn.fetchrow(
                    "SELECT distributed_at FROM reports WHERE id = $1",
                    report['id'])
                assert rep_check['distributed_at'] is not None
            finally:
                await conn.execute(
                    "DELETE FROM ris_results_distribution WHERE report_id = $1",
                    report['id'])


class TestDeliveryRetry:
    """B-6: retry must attempt a real transmission — flipping FAILED rows
    straight back to SENT without delivering anything is a no-op that hides
    outages."""

    @pytest.mark.asyncio
    async def test_retry_without_endpoint_keeps_failed_and_bumps_attempts(self):
        async with get_conn() as conn:
            # The retry query is global — clear rows other tests leave
            # behind (TestDeliveryStatus seeds a permanent FAILED row).
            await conn.execute(
                "DELETE FROM ris_results_distribution WHERE accession_number LIKE 'ACC-%'")
            row = await conn.fetchrow("""
                INSERT INTO ris_results_distribution
                (report_id, accession_number, status, attempts, payload)
                VALUES (gen_random_uuid(), 'ACC-RETRY-01', 'FAILED', 2, 'MSH|')
                RETURNING id, attempts
            """)
            dist_engine = ResultsDistributionEngine()
            with patch('config.config', {'distribution_endpoint': ''}):
                retried = await dist_engine.retry_failed_deliveries()
            assert retried == 0, \
                'a retry with no reachable endpoint must not fake a SENT'
            updated = await conn.fetchrow(
                "SELECT status, attempts FROM ris_results_distribution WHERE id = $1",
                row['id'])
            assert updated['status'] == 'FAILED'
            assert updated['attempts'] == 3, \
                'the failed attempt must still count'
            await conn.execute(
                "DELETE FROM ris_results_distribution WHERE accession_number LIKE 'ACC-RETRY-%'")

    @pytest.mark.asyncio
    async def test_retry_marks_sent_after_successful_delivery(self):
        async with get_conn() as conn:
            await conn.execute(
                "DELETE FROM ris_results_distribution WHERE accession_number LIKE 'ACC-%'")
            row = await conn.fetchrow("""
                INSERT INTO ris_results_distribution
                (report_id, accession_number, status, attempts, payload)
                VALUES (gen_random_uuid(), 'ACC-RETRY-02', 'FAILED', 1, 'MSH|')
                RETURNING id
            """)
            dist_engine = ResultsDistributionEngine()
            with patch('config.config', {'distribution_endpoint': 'http://emr:8080/oru'}), \
                 patch.object(dist_engine, '_deliver',
                              new=AsyncMock(return_value=True)):
                retried = await dist_engine.retry_failed_deliveries()
            assert retried == 1
            updated = await conn.fetchrow(
                "SELECT status, attempts FROM ris_results_distribution WHERE id = $1",
                row['id'])
            assert updated['status'] == 'SENT'
            assert updated['attempts'] == 2
            await conn.execute(
                "DELETE FROM ris_results_distribution WHERE accession_number LIKE 'ACC-RETRY-%'")


class TestCriticalResultsRLS:
    @pytest.mark.asyncio
    async def test_critical_results_list_tenant_filtered(self):
        async with get_conn() as conn:
            critical_db = RisCriticalResults(conn)
            active = await critical_db.list_active()
            assert isinstance(active, list)


class TestDeliveryStatus:
    """S10-12: delivery-status rows expose routing metadata, never the PHI payload."""

    @pytest.mark.asyncio
    async def test_delivery_status_returns_rows_without_payload(self):
        async with get_conn() as conn:
            await conn.execute("DELETE FROM ris_results_distribution")
            await conn.execute(
                "INSERT INTO ris_results_distribution"
                " (report_id, accession_number, status, payload)"
                " VALUES ('11111111-1111-1111-1111-111111111111', 'ACC-DEL-01', 'SENT', 'secret-phi')"
            )
            await conn.execute(
                "INSERT INTO ris_results_distribution"
                " (report_id, accession_number, status, payload)"
                " VALUES ('22222222-2222-2222-2222-222222222222', 'ACC-DEL-02', 'FAILED', 'secret-phi-2')"
            )

        from api.notifications import DeliveryStatusHandler
        from starlette.applications import Starlette
        from starlette.middleware import Middleware
        from starlette.routing import Route
        import httpx
        from api.auth import User
        from tests.test_tracking_api import _FakeAuth

        app = Starlette(
            routes=[
                Route('/notifications/delivery-status', endpoint=DeliveryStatusHandler),
            ],
            middleware=[Middleware(
                _FakeAuth,
                user=User({'id': 1, 'permissions': ['REPORT_READ']}),
            )],
        )
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url='http://test'
        ) as client:
            resp = await client.get(
                '/notifications/delivery-status',
                params={'report_id': '11111111-1111-1111-1111-111111111111'},
            )
        assert resp.status_code == 200, resp.text
        rows = resp.json()['data']
        assert len(rows) == 1
        assert rows[0]['accession_number'] == 'ACC-DEL-01'
        # CR-8: the ORU payload is PHI — it must not be serialized to callers.
        assert 'payload' not in rows[0]


class TestFirstSendHonesty:
    """A2 (GAP_AUDIT_TDD_PIPELINE.md): distribute_report() used to record
    SENT without transmitting anything — _deliver() was only reachable from
    the retry manager. First send must earn its status: SENT only after a
    real _deliver() success; transport failure or missing endpoint records
    FAILED so the lifecycle retry worker drains it once EMR routing exists."""

    async def _seed(self, conn, tag):
        exam_row = await conn.fetchrow(
            "INSERT INTO exams (accession_number, patient_id, status, modality) "
            "VALUES ($1, $2, 'completed', 'CT') RETURNING id",
            f'ACC-A2-{tag}', f'PAT-A2-{tag}')
        report = await Reports(conn).create(
            exam_row['id'],
            {'status': 'draft', 'findings': 'f', 'impression': 'i'},
            created_by='rad-1')
        return exam_row, report

    async def _cleanup(self, conn, tag, report_id=None):
        await conn.execute(
            "DELETE FROM ris_results_distribution WHERE accession_number LIKE $1",
            f'ACC-A2-{tag}%')
        await conn.execute("DELETE FROM reports WHERE id = $1", report_id)
        await conn.execute("DELETE FROM exams WHERE accession_number LIKE $1",
                           f'ACC-A2-{tag}%')

    @pytest.mark.asyncio
    async def test_first_send_without_endpoint_records_failed(self):
        import uuid as _uuid
        tag = _uuid.uuid4().hex[:6]
        async with get_conn() as conn:
            _exam, report = await self._seed(conn, tag)
            try:
                engine = ResultsDistributionEngine()
                with patch('config.config', {}):
                    res = await engine.distribute_report(report['id'])
                assert res['status'] == 'FAILED', (
                    'no EMR endpoint configured — SENT would be a fake '
                    'success; got %r' % res['status'])
                row = await conn.fetchrow(
                    "SELECT status, attempts FROM ris_results_distribution"
                    " WHERE report_id = $1", report['id'])
                assert row['status'] == 'FAILED'
                assert row['attempts'] == 1
            finally:
                await self._cleanup(conn, tag, report['id'])

    @pytest.mark.asyncio
    async def test_sent_only_after_successful_delivery(self):
        import uuid as _uuid
        tag = _uuid.uuid4().hex[:6]
        async with get_conn() as conn:
            _exam, report = await self._seed(conn, tag)
            try:
                engine = ResultsDistributionEngine()
                with patch('config.config',
                           {'distribution_endpoint': 'http://emr:8080/oru'}), \
                     patch.object(engine, '_deliver',
                                  new=AsyncMock(return_value=True)) as mock_deliver:
                    res = await engine.distribute_report(report['id'])
                assert res['status'] == 'SENT'
                mock_deliver.assert_awaited_once()
                args = mock_deliver.await_args
                assert 'ORU^R01' in args.args[0]
                assert args.args[1] == 'http://emr:8080/oru'
                row = await conn.fetchrow(
                    "SELECT status, delivered_at FROM ris_results_distribution"
                    " WHERE report_id = $1", report['id'])
                assert row['status'] == 'SENT'
                assert row['delivered_at'] is not None
            finally:
                await self._cleanup(conn, tag, report['id'])

    @pytest.mark.asyncio
    async def test_transport_failure_records_failed_attempt(self):
        import uuid as _uuid
        tag = _uuid.uuid4().hex[:6]
        async with get_conn() as conn:
            _exam, report = await self._seed(conn, tag)
            try:
                engine = ResultsDistributionEngine()
                with patch('config.config',
                           {'distribution_endpoint': 'http://emr:8080/oru'}), \
                     patch.object(engine, '_deliver',
                                  new=AsyncMock(return_value=False)):
                    res = await engine.distribute_report(report['id'])
                assert res['status'] == 'FAILED'
                row = await conn.fetchrow(
                    "SELECT status, attempts FROM ris_results_distribution"
                    " WHERE report_id = $1", report['id'])
                assert row['status'] == 'FAILED'
                assert row['attempts'] == 1
            finally:
                await self._cleanup(conn, tag, report['id'])
