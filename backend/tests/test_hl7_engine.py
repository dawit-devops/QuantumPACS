"""S3 Interface Engine — HL7 engine lifecycle tests.

Hl7InterfaceEngine: parse → persist (ris_hl7_messages + legacy audit
mirror) → route → ACK/ERR; failures land in the exception queue (FAILED,
retry_count) and replay via retry_failed(); ORM^O01 also creates
ris_orders + procedures (S3-08). DB is mocked; the real wire parser runs.
"""

from datetime import date
from unittest.mock import AsyncMock, patch

import pytest

SAMPLE_ORM_O01 = (
    'MSH|^~\\&|SENDING|SENDING_FACILITY|QUANTUMPACS||202607251030||ORM^O01|MSG004|P|2.5\r'
    'PID|1||PID001||Smith^John||19800101|M\r'
    'ORC|NW|ORD001|||CM|||||||202607251030\r'
    'OBR|1|ORD001|RP001|CT CHEST^Chest CT^L|||202607260800|||||||||||CT_SCANNER^CT Room 1||||||CT|||1^CM^30^Q^30^A||||Routine screening|Lee^Kim\r'
)

SAMPLE_ADT_A01 = (
    'MSH|^~\\&|SENDING|SENDING_FACILITY|QUANTUMPACS||202607251030||ADT^A01|MSG001|P|2.5\r'
    'EVN|A01|202607251030\r'
    'PID|1||PID001||Smith^John||19800101|M|||123 Main St^^Metropolis^NY^10001||(555)123-4567\r'
)

SAMPLE_ORU_R01 = (
    'MSH|^~\\&|SENDING|SENDING_FACILITY|QUANTUMPACS||202607261200||ORU^R01|MSG010|P|2.5\r'
    'PID|1||PID001||Smith^John||19800101|M\r'
    'OBR|1|ORD001|ORD001|CT CHEST^Chest CT^L|||202607260800|||||||||||CT_SCANNER||||||CT|F\r'
    'OBX|1|ST|1234^FINDINGS^L||Normal study|Normal|||F\r'
)

SAMPLE_ORM_NO_PID = (
    'MSH|^~\\&|SENDING|SENDING_FACILITY|QUANTUMPACS||202607251030||ORM^O01|MSG005|P|2.5\r'
    'ORC|NW|ORD002|||CM|||||||202607251030\r'
    'OBR|1|ORD002|RP002|CT CHEST^Chest CT^L|||202607260800|||||||||||CT_SCANNER||||||CT\r'
)

SAMPLE_UNKNOWN_TYPE = (
    'MSH|^~\\&|SENDING|SENDING_FACILITY|QUANTUMPACS||202607251030||ORR^O02|MSG006|P|2.5\r'
    'PID|1||PID001||Smith^John||19800101|M\r'
    'ORC|OK|ORD001\r'
)


def _conn_ctx():
    conn = AsyncMock()
    conn.__aenter__ = AsyncMock(return_value=conn)
    conn.__aexit__ = AsyncMock(return_value=False)
    return conn


@pytest.fixture
def engine_patches():
    """Patch every DB/route boundary; return the mocks for assertions."""
    patchers = [
        patch('services.hl7_engine.service.get_conn'),
        patch('services.hl7_engine.service.handle_adt_message', new=AsyncMock()),
        patch('services.hl7_engine.service.handle_orm_message', new=AsyncMock()),
        patch('services.hl7_engine.service.handle_oru_message', new=AsyncMock()),
        patch('services.hl7_engine.service._store_hl7_message', new=AsyncMock()),
        patch('services.hl7_engine.service.RisHl7Messages'),
        patch('services.hl7_engine.service.RisInterfaceEndpoints'),
        patch('services.hl7_engine.service.RisInterfaceEvents'),
        patch('services.hl7_engine.service.RisOrders'),
        patch('services.hl7_engine.service.RisOrderProcedures'),
    ]
    mocks = {}
    for p in patchers:
        mocks[p.attribute] = p.start()
    yield mocks
    for p in patchers:
        p.stop()


class TestEngineLifecycle:
    @pytest.mark.asyncio
    async def test_orm_o01_acks_and_creates_order_and_procedure(self, engine_patches):
        from services.hl7_engine.service import Hl7InterfaceEngine

        conn = _conn_ctx()
        engine_patches['get_conn'].return_value = conn
        messages = AsyncMock()
        messages.create.return_value = 'msg-uuid'
        engine_patches['RisHl7Messages'].return_value = messages
        orders = AsyncMock()
        orders.create.return_value = {'id': 'order-uuid'}
        orders.get_by_accession.return_value = None
        engine_patches['RisOrders'].return_value = orders
        procedures = AsyncMock()
        procedures.create.return_value = {'id': 'proc-uuid'}
        engine_patches['RisOrderProcedures'].return_value = procedures
        engine_patches['handle_orm_message'].return_value = True

        result = await Hl7InterfaceEngine().receive_message(SAMPLE_ORM_O01.encode())

        assert result == b'ACK'
        engine_patches['handle_orm_message'].assert_awaited_once()
        created = orders.create.call_args[0][0]
        assert created['accession_number'] == 'ORD001'
        assert created['patient_id'] == 'PID001'
        assert created['patient_name'] == 'Smith^John'
        assert created['patient_dob'] == date(1980, 1, 1)
        assert created['priority'] == 'URGENT'
        assert created['clinical_indication'] == 'Routine screening'
        proc = procedures.create.call_args[0][1]
        assert procedures.create.call_args[0][0] == 'order-uuid'
        assert proc['procedure_code'] == 'RP001'
        assert proc['procedure_name'] == 'Chest CT'
        assert proc['modality'] == 'CT'

    @pytest.mark.asyncio
    async def test_message_persisted_processed_and_audit_mirrored(self, engine_patches):
        from services.hl7_engine.service import Hl7InterfaceEngine

        conn = _conn_ctx()
        engine_patches['get_conn'].return_value = conn
        messages = AsyncMock()
        messages.create.return_value = 'msg-uuid'
        engine_patches['RisHl7Messages'].return_value = messages
        engine_patches['handle_adt_message'].return_value = True

        result = await Hl7InterfaceEngine().receive_message(SAMPLE_ADT_A01.encode())

        assert result == b'ACK'
        created = messages.create.call_args[0][0]
        assert created['message_type'] == 'ADT'
        assert created['trigger_event'] == 'A01'
        assert created['control_id'] == 'MSG001'
        assert created['status'] == 'RECEIVED'
        assert created['max_retries'] == 3
        assert created['raw_message'] == SAMPLE_ADT_A01
        messages.update_status.assert_any_await('msg-uuid', 'PARSED', error='')
        messages.update_status.assert_any_await('msg-uuid', 'PROCESSED', error='')
        engine_patches['_store_hl7_message'].assert_awaited_once()
        stored = engine_patches['_store_hl7_message'].call_args[0]
        assert stored[0] == SAMPLE_ADT_A01.encode()
        assert stored[2] == 'ok'

    @pytest.mark.asyncio
    async def test_malformed_message_fails_into_exception_queue(self, engine_patches):
        from services.hl7_engine.service import Hl7InterfaceEngine

        conn = _conn_ctx()
        engine_patches['get_conn'].return_value = conn
        messages = AsyncMock()
        messages.create.return_value = 'msg-uuid'
        engine_patches['RisHl7Messages'].return_value = messages

        result = await Hl7InterfaceEngine().receive_message(b'not an hl7 message\r')

        assert result == b'ERR Unparseable message'
        created = messages.create.call_args[0][0]
        assert created['status'] == 'FAILED'
        assert created['error_message'] == 'Unparseable message'
        engine_patches['_store_hl7_message'].assert_awaited_once()

    @pytest.mark.asyncio
    async def test_missing_required_field_fails(self, engine_patches):
        from services.hl7_engine.service import Hl7InterfaceEngine

        conn = _conn_ctx()
        engine_patches['get_conn'].return_value = conn
        messages = AsyncMock()
        messages.create.return_value = 'msg-uuid'
        engine_patches['RisHl7Messages'].return_value = messages

        result = await Hl7InterfaceEngine().receive_message(SAMPLE_ORM_NO_PID.encode())

        assert result == b'ERR Missing required field patient_id for ORM'
        created = messages.create.call_args[0][0]
        assert created['status'] == 'FAILED'
        assert 'patient_id' in created['error_message']

    @pytest.mark.asyncio
    async def test_unknown_message_type_acked_and_persisted(self, engine_patches):
        from services.hl7_engine.service import Hl7InterfaceEngine

        conn = _conn_ctx()
        engine_patches['get_conn'].return_value = conn
        messages = AsyncMock()
        messages.create.return_value = 'msg-uuid'
        engine_patches['RisHl7Messages'].return_value = messages

        result = await Hl7InterfaceEngine().receive_message(SAMPLE_UNKNOWN_TYPE.encode())

        assert result == b'ACK'
        messages.update_status.assert_any_await('msg-uuid', 'PROCESSED', error='')

    @pytest.mark.asyncio
    async def test_route_failure_marks_failed_and_returns_err(self, engine_patches):
        from services.hl7_engine.service import Hl7InterfaceEngine

        conn = _conn_ctx()
        engine_patches['get_conn'].return_value = conn
        messages = AsyncMock()
        messages.create.return_value = 'msg-uuid'
        engine_patches['RisHl7Messages'].return_value = messages
        engine_patches['handle_adt_message'].return_value = False

        result = await Hl7InterfaceEngine().receive_message(SAMPLE_ADT_A01.encode())

        assert result == b'ERR ADT processing failed'
        messages.update_status.assert_any_await('msg-uuid', 'FAILED', error='ADT handler returned False')

    @pytest.mark.asyncio
    async def test_processing_exception_marks_failed_with_reason(self, engine_patches):
        from services.hl7_engine.service import Hl7InterfaceEngine

        conn = _conn_ctx()
        engine_patches['get_conn'].return_value = conn
        messages = AsyncMock()
        messages.create.return_value = 'msg-uuid'
        engine_patches['RisHl7Messages'].return_value = messages
        orders = AsyncMock()
        orders.create.side_effect = RuntimeError('boom')
        orders.get_by_accession.return_value = None
        engine_patches['RisOrders'].return_value = orders
        engine_patches['handle_orm_message'].return_value = True

        result = await Hl7InterfaceEngine().receive_message(SAMPLE_ORM_O01.encode())

        assert result == b'ERR ORM processing failed'
        messages.update_status.assert_any_await('msg-uuid', 'FAILED', error='boom')


class TestRetryQueue:
    @pytest.mark.asyncio
    async def test_retry_failed_replays_and_marks_processed(self, engine_patches):
        from services.hl7_engine.service import Hl7InterfaceEngine

        conn = _conn_ctx()
        engine_patches['get_conn'].return_value = conn
        messages = AsyncMock()
        messages.list_failed.return_value = [
            {'id': 'msg-uuid', 'retry_count': 0, 'raw_message': SAMPLE_ORM_O01},
        ]
        engine_patches['RisHl7Messages'].return_value = messages
        orders = AsyncMock()
        orders.create.return_value = {'id': 'order-uuid'}
        orders.get_by_accession.return_value = None
        engine_patches['RisOrders'].return_value = orders
        engine_patches['RisOrderProcedures'].return_value = AsyncMock()
        engine_patches['handle_orm_message'].return_value = True

        replayed = await Hl7InterfaceEngine().retry_failed()

        assert replayed == 1
        messages.update_status.assert_any_await('msg-uuid', 'RETRYING')
        messages.update_status.assert_any_await('msg-uuid', 'PROCESSED')
        orders.create.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_retry_failure_increments_retry_count(self, engine_patches):
        from services.hl7_engine.service import Hl7InterfaceEngine

        conn = _conn_ctx()
        engine_patches['get_conn'].return_value = conn
        messages = AsyncMock()
        messages.list_failed.return_value = [
            {'id': 'msg-uuid', 'retry_count': 1, 'raw_message': SAMPLE_ORM_O01},
        ]
        engine_patches['RisHl7Messages'].return_value = messages
        orders = AsyncMock()
        orders.create.side_effect = RuntimeError('still broken')
        orders.get_by_accession.return_value = None
        engine_patches['RisOrders'].return_value = orders
        engine_patches['RisOrderProcedures'].return_value = AsyncMock()
        engine_patches['handle_orm_message'].return_value = True

        replayed = await Hl7InterfaceEngine().retry_failed()

        assert replayed == 1
        messages.update_status.assert_any_await('msg-uuid', 'RETRYING')
        messages.update_status.assert_any_await(
            'msg-uuid', 'FAILED', error='still broken (retry 2/3)', retry_count=2,
        )

    @pytest.mark.asyncio
    async def test_retry_unparseable_raw_increments_retry_count(self, engine_patches):
        from services.hl7_engine.service import Hl7InterfaceEngine

        conn = _conn_ctx()
        engine_patches['get_conn'].return_value = conn
        messages = AsyncMock()
        messages.list_failed.return_value = [
            {'id': 'msg-uuid', 'retry_count': 2, 'raw_message': 'garbage'},
        ]
        engine_patches['RisHl7Messages'].return_value = messages

        replayed = await Hl7InterfaceEngine().retry_failed()

        assert replayed == 1
        messages.update_status.assert_any_await(
            'msg-uuid', 'FAILED', error='Unparseable message (retry 3/3)', retry_count=3,
        )

    @pytest.mark.asyncio
    async def test_retry_message_replays_single_failed(self, engine_patches):
        from services.hl7_engine.service import Hl7InterfaceEngine

        conn = _conn_ctx()
        engine_patches['get_conn'].return_value = conn
        messages = AsyncMock()
        messages.get.return_value = {
            'id': 'msg-uuid', 'status': 'FAILED', 'retry_count': 1, 'raw_message': SAMPLE_ORM_O01,
        }
        engine_patches['RisHl7Messages'].return_value = messages
        orders = AsyncMock()
        orders.get_by_accession.return_value = None
        orders.create.return_value = {'id': 'order-uuid'}
        engine_patches['RisOrders'].return_value = orders
        engine_patches['RisOrderProcedures'].return_value = AsyncMock()
        engine_patches['handle_orm_message'].return_value = True

        ok = await Hl7InterfaceEngine().retry_message('msg-uuid')

        assert ok is True
        messages.update_status.assert_any_await('msg-uuid', 'RETRYING')
        messages.update_status.assert_any_await('msg-uuid', 'PROCESSED')
        orders.create.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_retry_message_refuses_unknown_or_not_failed(self, engine_patches):
        from services.hl7_engine.service import Hl7InterfaceEngine

        conn = _conn_ctx()
        engine_patches['get_conn'].return_value = conn
        messages = AsyncMock()
        engine_patches['RisHl7Messages'].return_value = messages

        engine = Hl7InterfaceEngine()

        messages.get.return_value = None
        assert await engine.retry_message('missing') is False

        messages.get.return_value = {'id': 'x', 'status': 'PROCESSED', 'retry_count': 0}
        assert await engine.retry_message('x') is False

        messages.get.return_value = {'id': 'x', 'status': 'FAILED', 'retry_count': 3}
        assert await engine.retry_message('x') is False

        messages.update_status.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_retry_message_failure_increments_retry_count(self, engine_patches):
        from services.hl7_engine.service import Hl7InterfaceEngine

        conn = _conn_ctx()
        engine_patches['get_conn'].return_value = conn
        messages = AsyncMock()
        messages.get.return_value = {
            'id': 'msg-uuid', 'status': 'FAILED', 'retry_count': 1, 'raw_message': SAMPLE_ORM_O01,
        }
        engine_patches['RisHl7Messages'].return_value = messages
        orders = AsyncMock()
        orders.create.side_effect = RuntimeError('still broken')
        orders.get_by_accession.return_value = None
        engine_patches['RisOrders'].return_value = orders
        engine_patches['RisOrderProcedures'].return_value = AsyncMock()
        engine_patches['handle_orm_message'].return_value = True

        ok = await Hl7InterfaceEngine().retry_message('msg-uuid')

        assert ok is False
        messages.update_status.assert_any_await(
            'msg-uuid', 'FAILED', error='still broken (retry 2/3)', retry_count=2,
        )

    @pytest.mark.asyncio
    async def test_duplicate_accession_is_idempotent(self, engine_patches):
        from services.hl7_engine.service import Hl7InterfaceEngine

        conn = _conn_ctx()
        engine_patches['get_conn'].return_value = conn
        messages = AsyncMock()
        messages.create.return_value = 'msg-uuid'
        engine_patches['RisHl7Messages'].return_value = messages
        engine_patches['RisOrderProcedures'].return_value = AsyncMock()
        orders = AsyncMock()
        orders.get_by_accession.return_value = {'id': 'existing-order'}
        engine_patches['RisOrders'].return_value = orders
        engine_patches['handle_orm_message'].return_value = True

        result = await Hl7InterfaceEngine().receive_message(SAMPLE_ORM_O01.encode())

        assert result == b'ACK'
        orders.get_by_accession.assert_awaited_once_with('ORD001')
        orders.create.assert_not_awaited()


class TestParserNormalization:
    @pytest.mark.asyncio
    async def test_priority_mapping(self):
        from services.hl7_engine.parser import normalize_priority

        assert normalize_priority('R') == 'ROUTINE'
        assert normalize_priority('A') == 'URGENT'
        assert normalize_priority('S') == 'STAT'
        assert normalize_priority('') == 'ROUTINE'
        assert normalize_priority('X') == 'ROUTINE'

    @pytest.mark.asyncio
    async def test_to_date(self):
        from services.hl7_engine.parser import to_date

        assert to_date('19800101') == date(1980, 1, 1)
        assert to_date('202607260800') == date(2026, 7, 26)
        assert to_date('') is None
        assert to_date('notadate') is None

    @pytest.mark.asyncio
    async def test_validate_required_fields(self):
        from services.hl7_engine.parser import validate

        validate({'message_type': 'ADT', 'patient_id': 'P1'})
        validate({'message_type': 'ORM', 'patient_id': 'P1', 'accession_number': 'A1'})
        with pytest.raises(Exception):
            validate({'message_type': 'ORM', 'patient_id': 'P1'})
        with pytest.raises(Exception):
            validate({'message_type': 'ORU', 'accession_number': ''})


class TestEndpointResolution:
    @pytest.mark.asyncio
    async def test_first_message_registers_endpoint(self, engine_patches):
        from services.hl7_engine.service import Hl7InterfaceEngine

        conn = _conn_ctx()
        engine_patches['get_conn'].return_value = conn
        endpoints = AsyncMock()
        endpoints.get_by_name.return_value = None
        endpoints.create.return_value = 'ep-uuid'
        engine_patches['RisInterfaceEndpoints'].return_value = endpoints
        messages = AsyncMock()
        messages.create.return_value = 'msg-uuid'
        engine_patches['RisHl7Messages'].return_value = messages
        orders = AsyncMock()
        orders.get_by_accession.return_value = None
        orders.create.return_value = {'id': 'order-uuid'}
        engine_patches['RisOrders'].return_value = orders
        engine_patches['RisOrderProcedures'].return_value = AsyncMock()
        engine_patches['handle_orm_message'].return_value = True

        result = await Hl7InterfaceEngine().receive_message(SAMPLE_ORM_O01.encode())

        assert result == b'ACK'
        endpoints.get_by_name.assert_awaited_once_with('SENDING_FACILITY')
        endpoints.create.assert_awaited_once_with({
            'name': 'SENDING_FACILITY',
            'interface_type': 'HL7_ORM',
            'protocol': 'HL7V2',
            'config': {},
        })
        messages.create.assert_awaited_once()
        # _persist attached the message to the resolved endpoint and touched it
        assert messages.create.call_args.args[0]['endpoint_id'] == 'ep-uuid'
        endpoints.touch.assert_awaited()

    @pytest.mark.asyncio
    async def test_existing_endpoint_is_reused(self, engine_patches):
        from services.hl7_engine.service import Hl7InterfaceEngine

        conn = _conn_ctx()
        engine_patches['get_conn'].return_value = conn
        endpoints = AsyncMock()
        endpoints.get_by_name.return_value = {'id': 'existing-ep'}
        engine_patches['RisInterfaceEndpoints'].return_value = endpoints
        messages = AsyncMock()
        messages.create.return_value = 'msg-uuid'
        engine_patches['RisHl7Messages'].return_value = messages
        engine_patches['handle_orm_message'].return_value = True
        engine_patches['RisOrders'].return_value = AsyncMock()
        engine_patches['RisOrderProcedures'].return_value = AsyncMock()

        result = await Hl7InterfaceEngine().receive_message(SAMPLE_ORM_O01.encode())

        assert result == b'ACK'
        endpoints.create.assert_not_awaited()
        assert messages.create.call_args.args[0]['endpoint_id'] == 'existing-ep'

    @pytest.mark.asyncio
    async def test_unknown_type_skips_endpoint(self, engine_patches):
        from services.hl7_engine.service import Hl7InterfaceEngine

        conn = _conn_ctx()
        engine_patches['get_conn'].return_value = conn
        engine_patches['RisInterfaceEndpoints'].return_value = AsyncMock()
        messages = AsyncMock()
        messages.create.return_value = 'msg-uuid'
        engine_patches['RisHl7Messages'].return_value = messages
        engine_patches['handle_orm_message'].return_value = True

        await Hl7InterfaceEngine().receive_message(SAMPLE_UNKNOWN_TYPE.encode())

        # ORR^O02 has no endpoint mapping — the message persists unattached
        assert messages.create.call_args.args[0]['endpoint_id'] is None
        engine_patches['RisInterfaceEndpoints'].return_value.create.assert_not_awaited()


class TestFailureAlerting:
    """S3-17 — every FAILED status path triggers notify_interface_failure;
    success paths stay silent."""

    def _patched_engine(self, engine_patches):
        from services.hl7_engine.service import Hl7InterfaceEngine

        engine_patches['get_conn'].return_value = _conn_ctx()
        engine_patches['RisHl7Messages'].return_value = AsyncMock()
        engine_patches['RisInterfaceEvents'].return_value = AsyncMock()
        engine_patches['RisOrders'].return_value = AsyncMock()
        engine_patches['RisOrderProcedures'].return_value = AsyncMock()
        engine_patches['RisInterfaceEndpoints'].return_value = AsyncMock()
        return Hl7InterfaceEngine()

    @pytest.mark.asyncio
    async def test_unparseable_message_alerts(self, engine_patches):
        engine = self._patched_engine(engine_patches)
        with patch('services.hl7_engine.service.notify_interface_failure', new=AsyncMock()) as alert:
            result = await engine.receive_message(b'not hl7 at all')

        assert result == b'ERR Unparseable message'
        alert.assert_awaited_once()
        assert alert.await_args.kwargs['error'] == 'Unparseable message'

    @pytest.mark.asyncio
    async def test_handler_false_alerts(self, engine_patches):
        engine = self._patched_engine(engine_patches)
        engine_patches['handle_orm_message'].return_value = False
        with patch('services.hl7_engine.service.notify_interface_failure', new=AsyncMock()) as alert:
            result = await engine.receive_message(SAMPLE_ORM_O01.encode())

        assert result == b'ERR ORM processing failed'
        alert.assert_awaited_once()
        assert alert.await_args.kwargs['error'] == 'ORM handler returned False'

    @pytest.mark.asyncio
    async def test_success_does_not_alert(self, engine_patches):
        engine = self._patched_engine(engine_patches)
        orders = AsyncMock()
        orders.create.return_value = {'id': 'order-uuid'}
        orders.get_by_accession.return_value = None
        engine_patches['RisOrders'].return_value = orders
        engine_patches['handle_orm_message'].return_value = True
        with patch('services.hl7_engine.service.notify_interface_failure', new=AsyncMock()) as alert:
            result = await engine.receive_message(SAMPLE_ORM_O01.encode())

        assert result == b'ACK'
        alert.assert_not_awaited()


class TestMetrics:
    """S3-04 — interface health metrics recorded by the engine."""

    @staticmethod
    def _counter(name, labels):
        from prometheus_client.registry import REGISTRY
        value = REGISTRY.get_sample_value(name, labels)
        return value or 0.0

    @pytest.mark.asyncio
    async def test_processed_message_increments_counter(self, engine_patches):
        from services.hl7_engine.service import Hl7InterfaceEngine

        conn = _conn_ctx()
        engine_patches['get_conn'].return_value = conn
        messages = AsyncMock()
        messages.create.return_value = 'msg-uuid'
        engine_patches['RisHl7Messages'].return_value = messages
        engine_patches['RisOrderProcedures'].return_value = AsyncMock()
        orders = AsyncMock()
        orders.create.return_value = {'id': 'order-uuid'}
        orders.get_by_accession.return_value = None
        engine_patches['RisOrders'].return_value = orders
        engine_patches['handle_orm_message'].return_value = True

        received_before = self._counter(
            'ris_hl7_messages_total', {'type': 'ORM', 'trigger': 'O01', 'status': 'RECEIVED'},
        )
        processed_before = self._counter(
            'ris_hl7_messages_total', {'type': 'ORM', 'trigger': 'O01', 'status': 'PROCESSED'},
        )

        await Hl7InterfaceEngine().receive_message(SAMPLE_ORM_O01.encode())

        assert self._counter(
            'ris_hl7_messages_total', {'type': 'ORM', 'trigger': 'O01', 'status': 'RECEIVED'},
        ) == received_before + 1
        assert self._counter(
            'ris_hl7_messages_total', {'type': 'ORM', 'trigger': 'O01', 'status': 'PROCESSED'},
        ) == processed_before + 1

    @pytest.mark.asyncio
    async def test_failed_message_increments_failed_counter(self, engine_patches):
        from services.hl7_engine.service import Hl7InterfaceEngine

        conn = _conn_ctx()
        engine_patches['get_conn'].return_value = conn
        messages = AsyncMock()
        messages.create.return_value = 'msg-uuid'
        engine_patches['RisHl7Messages'].return_value = messages

        failed_before = self._counter(
            'ris_hl7_messages_total', {'type': '', 'trigger': '', 'status': 'FAILED'},
        )

        await Hl7InterfaceEngine().receive_message(b'not an hl7 message\r')

        assert self._counter(
            'ris_hl7_messages_total', {'type': '', 'trigger': '', 'status': 'FAILED'},
        ) == failed_before + 1

    @pytest.mark.asyncio
    async def test_latency_histogram_recorded(self, engine_patches):
        from services.hl7_engine.service import Hl7InterfaceEngine

        conn = _conn_ctx()
        engine_patches['get_conn'].return_value = conn
        messages = AsyncMock()
        messages.create.return_value = 'msg-uuid'
        engine_patches['RisHl7Messages'].return_value = messages
        engine_patches['handle_adt_message'].return_value = True

        count_before = self._counter('ris_hl7_message_latency_seconds_count', {})

        await Hl7InterfaceEngine().receive_message(SAMPLE_ADT_A01.encode())

        assert self._counter('ris_hl7_message_latency_seconds_count', {}) == count_before + 1


class TestHl7ApiRoute:
    @pytest.mark.asyncio
    async def test_post_hl7_delegates_to_engine(self, engine_patches):
        from starlette.applications import Starlette
        from starlette.exceptions import HTTPException
        from starlette.middleware import Middleware
        from starlette.routing import Route
        from starlette.testclient import TestClient

        from api.auth import User
        from api.hl7 import Hl7Receiver
        from api.validate import _ValidationException, validation_exception_handler
        from tests.test_ris_orders import _FakeAuth, _http_exception

        conn = _conn_ctx()
        engine_patches['get_conn'].return_value = conn
        messages = AsyncMock()
        messages.create.return_value = 'msg-uuid'
        engine_patches['RisHl7Messages'].return_value = messages
        engine_patches['RisOrderProcedures'].return_value = AsyncMock()
        engine_patches['handle_orm_message'].return_value = True
        orders = AsyncMock()
        orders.create.return_value = {'id': 'order-uuid'}
        orders.get_by_accession.return_value = None
        engine_patches['RisOrders'].return_value = orders

        app = Starlette(
            routes=[Route('/hl7', endpoint=Hl7Receiver)],
            middleware=[Middleware(_FakeAuth, user=User({'id': 1, 'permissions': ['HL7_WRITE']}))],
            exception_handlers={
                HTTPException: _http_exception,
                _ValidationException: validation_exception_handler,
            },
        )
        with patch('api.hl7._allowed_networks', return_value=[]):
            client = TestClient(app)
            resp = client.post('/hl7', content=SAMPLE_ORM_O01.encode())

        assert resp.status_code == 200
        assert resp.text == 'ACK'
        orders.create.assert_awaited_once()

MULTI_OBR_ORM = (
    'MSH|^~\\&|SENDING|SENDING_FACILITY|QUANTUMPACS||202608221000||ORM^O01|MSG901|P|2.5\r'
    'PID|1||PID900||Doe^Jane||19900102|F\r'
    'ORC|NW|ORD900|||CM|||||||202608221000\r'
    'OBR|1|ORD900|RP-A|CT CHEST^Chest CT^L|||202608230800|||||||||||CT_SCANNER^CT Room 1||||||CT|||1^CM^30^Q^30^A||||Chest pain workup|Lee^Kim\r'
    'OBR|2|ORD900|RP-B|MRI BRAIN^Brain MRI^L|||202608230900|||||||||||MR_SCANNER^MR Suite||||||MR|||1^CM^30^Q^30^A||||Headache|Lee^Kim\r'
    'OBR|3|ORD900|RP-C|US ABDOMEN^Abdominal US^L|||202608231000|||||||||||US_ROOM^US Lab||||||US|||1^CM^30^Q^30^A||||RUQ pain|Lee^Kim\r'
)


class TestMultiObrParsing:
    """B1 (GAP_AUDIT_TDD_PIPELINE.md): the segment map was last-wins, so a
    multi-procedure ORM kept only its final OBR — procedures 2..N were lost
    at the wire (plan S3-07/S3-08 acceptance: multi-procedure per order).
    The parser must expose every OBR as an ordered procedure entry while
    keeping the single-OBR scalar fields back-compatible."""

    @pytest.mark.asyncio
    async def test_multi_obr_orm_parses_all_procedures(self):
        from services.ingestion.hl7_server import parse_hl7_message

        parsed = parse_hl7_message(MULTI_OBR_ORM)
        assert parsed is not None
        procs = parsed.get('procedures')
        assert isinstance(procs, list) and len(procs) == 3, (
            'all three OBR segments must survive parsing, got %r' % (procs,)
        )
        codes = [p['procedure_code'] for p in procs]
        assert codes == ['RP-A', 'RP-B', 'RP-C']
        descs = [p['procedure_desc'] for p in procs]
        assert descs == ['CT CHEST^Chest CT^L', 'MRI BRAIN^Brain MRI^L',
                         'US ABDOMEN^Abdominal US^L']
        modalities = [p['modality'] for p in procs]
        assert modalities == ['CT', 'MR', 'US']

    @pytest.mark.asyncio
    async def test_scalar_fields_remain_first_obr_back_compat(self):
        from services.ingestion.hl7_server import parse_hl7_message

        parsed = parse_hl7_message(MULTI_OBR_ORM)
        assert parsed['accession_number'] == 'ORD900'
        assert parsed['requested_procedure_id'] == 'RP-A'
        assert parsed['requested_procedure_desc'] == 'CT CHEST^Chest CT^L'
        assert parsed['modality'] == 'CT'

    @pytest.mark.asyncio
    async def test_single_obr_message_has_one_procedure(self):
        from services.ingestion.hl7_server import parse_hl7_message

        parsed = parse_hl7_message(SAMPLE_ORM_O01)
        procs = parsed.get('procedures')
        assert isinstance(procs, list) and len(procs) == 1
        assert procs[0]['procedure_code'] == 'RP001'


class TestMultiProcedureOrmOrder:
    @pytest.mark.asyncio
    async def test_orm_creates_one_procedure_per_obr(self, engine_patches):
        from services.hl7_engine.service import Hl7InterfaceEngine

        conn = _conn_ctx()
        engine_patches['get_conn'].return_value = conn
        messages = AsyncMock()
        messages.create.return_value = 'msg-uuid'
        engine_patches['RisHl7Messages'].return_value = messages
        orders = AsyncMock()
        orders.create.return_value = {'id': 'order-uuid'}
        orders.get_by_accession.return_value = None
        engine_patches['RisOrders'].return_value = orders
        procedures = AsyncMock()
        engine_patches['RisOrderProcedures'].return_value = procedures
        engine_patches['handle_orm_message'].return_value = True

        result = await Hl7InterfaceEngine().receive_message(
            MULTI_OBR_ORM.encode())

        assert result == b'ACK'
        calls = procedures.create.call_args_list
        assert len(calls) == 3, (
            'one procedure row per OBR segment expected, got %d'
            % len(calls))
        created_codes = [c.args[1]['procedure_code'] for c in calls]
        assert created_codes == ['RP-A', 'RP-B', 'RP-C']
        created_names = [c.args[1]['procedure_name'] for c in calls]
        assert created_names == ['Chest CT', 'Brain MRI', 'Abdominal US']
        modalities = [c.args[1]['modality'] for c in calls]
        assert modalities == ['CT', 'MR', 'US']


ADT_A04_PV1_DG1 = (
    'MSH|^~\\&|SENDING|SENDING_FACILITY|QUANTUMPACS||202608220900||ADT^A04|MSG910|P|2.5\r'
    'PID|1||PID910||Row^Mary||19850615|F\r'
    'PV1|1|O|||||Atten^Alan^^Dr||||||||||||V910001\r'
    'DG1|1||S52.5^Fracture lower end radius^I10||20260822\r'
    'DG1|2||R51^Headache^I10\r'
)

ORM_NO_REASON_WITH_DG1 = (
    'MSH|^~\\&|SENDING|SENDING_FACILITY|QUANTUMPACS||202607251030||ORM^O01|MSG004|P|2.5\r'
    'PID|1||PID001||Smith^John||19800101|M\r'
    'ORC|NW|ORD001|||CM|||||||202607251030\r'
    'OBR|1|ORD001|RP001|CT CHEST^Chest CT^L|||202607260800|||||||||||CT_SCANNER^CT Room 1||||||CT|||1^CM^30^Q^30^A|||||Lee^Kim\r'
    'DG1|1||S52.5^Fracture lower end radius^I10||20260725\r'
)


class TestPv1Dg1Parsing:
    """B2 (GAP_AUDIT_TDD_PIPELINE.md): parse_hl7_message extracted
    MSH/PID/MRG/ORC/OBR only — PV1 and DG1 were dropped despite being in
    the S3-02 conformance set (parser.py's own docstring overstates
    coverage). Encounter context rides PV1; diagnoses ride DG1; both are
    persisted verbatim inside ris_hl7.parsed_segments."""

    @pytest.mark.asyncio
    async def test_pv1_encounter_fields_parsed(self):
        from services.ingestion.hl7_server import parse_hl7_message

        parsed = parse_hl7_message(ADT_A04_PV1_DG1)
        assert parsed.get('patient_class') == 'O'
        assert parsed.get('attending_doctor') == 'Atten^Alan^^Dr'
        assert parsed.get('visit_number') == 'V910001'

    @pytest.mark.asyncio
    async def test_dg1_diagnoses_parsed_in_order(self):
        from services.ingestion.hl7_server import parse_hl7_message

        parsed = parse_hl7_message(ADT_A04_PV1_DG1)
        diagnoses = parsed.get('diagnoses')
        assert isinstance(diagnoses, list) and len(diagnoses) == 2
        assert diagnoses[0]['code'] == 'S52.5'
        assert diagnoses[0]['description'] == 'Fracture lower end radius'
        assert diagnoses[0]['coding_system'] == 'I10'
        assert diagnoses[1]['code'] == 'R51'

    @pytest.mark.asyncio
    async def test_message_without_pv1_dg1_stays_clean(self):
        from services.ingestion.hl7_server import parse_hl7_message

        parsed = parse_hl7_message(SAMPLE_ADT_A01)
        assert 'diagnoses' not in parsed
        assert 'patient_class' not in parsed


class TestOrmDiagnosisIndication:
    @pytest.mark.asyncio
    async def test_order_indication_falls_back_to_dg1(self, engine_patches):
        """When OBR-31 (reason for study) is empty, the first DG1
        descriptions become the order's clinical indication — coders and
        schedulers see *why* without opening the raw HL7."""
        from services.hl7_engine.service import Hl7InterfaceEngine

        conn = _conn_ctx()
        engine_patches['get_conn'].return_value = conn
        messages = AsyncMock()
        messages.create.return_value = 'msg-uuid'
        engine_patches['RisHl7Messages'].return_value = messages
        orders = AsyncMock()
        orders.create.return_value = {'id': 'order-uuid'}
        orders.get_by_accession.return_value = None
        engine_patches['RisOrders'].return_value = orders
        procedures = AsyncMock()
        engine_patches['RisOrderProcedures'].return_value = procedures
        engine_patches['handle_orm_message'].return_value = True

        result = await Hl7InterfaceEngine().receive_message(
            ORM_NO_REASON_WITH_DG1.encode())

        assert result == b'ACK'
        created = orders.create.call_args[0][0]
        assert created['clinical_indication'] == 'Fracture lower end radius'
