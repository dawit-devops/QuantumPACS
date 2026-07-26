import asyncio
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


SAMPLE_ADT_A01 = (
    'MSH|^~\\&|SENDING|SENDING_FACILITY|QUANTUMPACS||202607251030||ADT^A01|MSG001|P|2.5\r'
    'EVN|A01|202607251030\r'
    'PID|1||PID001||Smith^John||19800101|M|||123 Main St^^Metropolis^NY^10001||(555)123-4567\r'
)


SAMPLE_ADT_A08 = (
    'MSH|^~\\&|SENDING|SENDING_FACILITY|QUANTUMPACS||202607251030||ADT^A08|MSG002|P|2.5\r'
    'EVN|A08|202607251030\r'
    'PID|1||PID001||Smith^Jane||19800101|F\r'
)


SAMPLE_ADT_A03 = (
    'MSH|^~\\&|SENDING|SENDING_FACILITY|QUANTUMPACS||202607251030||ADT^A03|MSG003|P|2.5\r'
    'EVN|A03|202607251030\r'
    'PID|1||PID001||Smith^John||19800101|M\r'
)


SAMPLE_ADT_A04 = (
    'MSH|^~\\&|SENDING|SENDING_FACILITY|QUANTUMPACS||202607251030||ADT^A04|MSG004|P|2.5\r'
    'EVN|A04|202607251030\r'
    'PID|1||PID002||Doe^Jane||19900215|F|||456 Oak Rd^^Gotham^NY^10002\r'
)

SAMPLE_ADT_A05 = (
    'MSH|^~\\&|SENDING|SENDING_FACILITY|QUANTUMPACS||202607251030||ADT^A05|MSG005|P|2.5\r'
    'EVN|A05|202607251030\r'
    'PID|1||PID003||Brown^Bob||19750320|M\r'
)

SAMPLE_ORM_O01 = (
    'MSH|^~\\&|SENDING|SENDING_FACILITY|QUANTUMPACS||202607251030||ORM^O01|MSG004|P|2.5\r'
    'PID|1||PID001||Smith^John||19800101|M\r'
    'ORC|NW|ORD001|||CM|||||||202607251030\r'
    'OBR|1|ORD001|RP001|CT CHEST^Chest CT^L|||202607260800|||||||||||CT_SCANNER||||||CT\r'
)


MLLP_START = b'\x0b'
MLLP_END = b'\x1c\x0d'


def _mllp_encode(msg: str) -> bytes:
    return MLLP_START + msg.encode('utf-8') + MLLP_END


class TestMllpServer:
    @pytest.mark.asyncio
    async def test_receives_and_parses_adt_a01(self):
        handler = AsyncMock(return_value=b'ACK')
        from services.ingestion.hl7_server import MllpServer
        server = MllpServer(host='127.0.0.1', port=0, handler=handler)
        try:
            await server.start()
            port = server._server.sockets[0].getsockname()[1]

            reader, writer = await asyncio.open_connection('127.0.0.1', port)
            writer.write(_mllp_encode(SAMPLE_ADT_A01))
            await writer.drain()
            await asyncio.sleep(0.1)
            writer.close()
            await writer.wait_closed()

            handler.assert_awaited_once()
            msg_bytes = handler.call_args[0][0]
            assert isinstance(msg_bytes, bytes)
            assert b'ADT^A01' in msg_bytes
            assert b'PID001' in msg_bytes
            assert b'Smith^John' in msg_bytes
        finally:
            await server.stop()

    @pytest.mark.asyncio
    async def test_sends_mllp_ack_on_success(self):
        handler = AsyncMock(return_value=b'ACK')
        from services.ingestion.hl7_server import MllpServer
        server = MllpServer(host='127.0.0.1', port=0, handler=handler)
        try:
            await server.start()
            port = server._server.sockets[0].getsockname()[1]

            reader, writer = await asyncio.open_connection('127.0.0.1', port)
            writer.write(_mllp_encode(SAMPLE_ADT_A01))
            await writer.drain()
            response = await asyncio.wait_for(reader.readexactly(2), timeout=2.0)
            assert response == b'\x0bA'
            rest = await reader.readuntil(b'\x1c\x0d')
            assert rest == b'CK\x1c\x0d'
            writer.close()
            await writer.wait_closed()
        finally:
            await server.stop()

    @pytest.mark.asyncio
    async def test_rejects_malformed_message(self):
        handler = AsyncMock()
        from services.ingestion.hl7_server import MllpServer
        server = MllpServer(host='127.0.0.1', port=0, handler=handler)
        try:
            await server.start()
            port = server._server.sockets[0].getsockname()[1]

            reader, writer = await asyncio.open_connection('127.0.0.1', port)
            writer.write(MLLP_START + b'NOT VALID HL7' + MLLP_END)
            await writer.drain()
            response = await asyncio.wait_for(reader.readuntil(b'\x1c\x0d'), timeout=2.0)
            assert response.startswith(b'\x0b')
            assert b'NACK' in response or b'ERR' in response
            writer.close()
            await writer.wait_closed()
        finally:
            await server.stop()

    @pytest.mark.asyncio
    async def test_tls_connection(self):
        import datetime
        import tempfile
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        import ssl

        now = datetime.datetime.now(datetime.UTC)
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        subject = issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'localhost')])
        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(key.public_key())
            .serial_number(1)
            .not_valid_before(now)
            .not_valid_after(now + datetime.timedelta(hours=1))
            .add_extension(x509.SubjectAlternativeName([x509.DNSName('localhost')]), critical=False)
            .sign(key, hashes.SHA256())
        )

        enc = serialization.Encoding.PEM
        with tempfile.NamedTemporaryFile(suffix='.pem', delete=False) as cert_f:
            cert_f.write(cert.public_bytes(encoding=enc))
            cert_path = cert_f.name
        with tempfile.NamedTemporaryFile(suffix='.pem', delete=False) as key_f:
            key_f.write(key.private_bytes(
                encoding=enc,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption(),
            ))
            key_path = key_f.name

        ssl_ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ssl_ctx.load_cert_chain(cert_path, key_path)

        handler = AsyncMock(return_value=b'ACK')
        from services.ingestion.hl7_server import MllpServer
        server = MllpServer(host='127.0.0.1', port=0, handler=handler, ssl_context=ssl_ctx)
        try:
            await server.start()
            port = server._server.sockets[0].getsockname()[1]

            client_ctx = ssl.create_default_context(cafile=cert_path)
            client_ctx.check_hostname = False
            client_ctx.verify_mode = ssl.CERT_NONE

            reader, writer = await asyncio.open_connection('127.0.0.1', port, ssl=client_ctx)
            writer.write(_mllp_encode(SAMPLE_ADT_A01))
            await writer.drain()
            await asyncio.sleep(0.1)
            writer.close()
            await writer.wait_closed()

            handler.assert_awaited_once()
            msg_bytes = handler.call_args[0][0]
            assert b'ADT^A01' in msg_bytes
        finally:
            await server.stop()
            os.unlink(cert_path)
            os.unlink(key_path)


class TestHl7MessageParsing:
    def test_parse_adt_a01_extracts_patient_fields(self):
        from services.ingestion.hl7_server import parse_hl7_message
        result = parse_hl7_message(SAMPLE_ADT_A01)
        assert result['message_type'] == 'ADT'
        assert result['event_type'] == 'A01'
        assert result['patient_id'] == 'PID001'
        assert result['patient_name'] == 'Smith^John'
        assert result['birth_date'] == '19800101'
        assert result['sex'] == 'M'
        assert 'address' in result
        assert result['address'] is not None
        assert result['sending_facility'] == 'SENDING_FACILITY'

    def test_parse_adt_a04_extracts_fields(self):
        from services.ingestion.hl7_server import parse_hl7_message
        result = parse_hl7_message(SAMPLE_ADT_A04)
        assert result['message_type'] == 'ADT'
        assert result['event_type'] == 'A04'
        assert result['patient_id'] == 'PID002'
        assert result['patient_name'] == 'Doe^Jane'
        assert result['birth_date'] == '19900215'
        assert result['sex'] == 'F'
        assert result['address'] is not None

    def test_parse_adt_a05_extracts_fields(self):
        from services.ingestion.hl7_server import parse_hl7_message
        result = parse_hl7_message(SAMPLE_ADT_A05)
        assert result['message_type'] == 'ADT'
        assert result['event_type'] == 'A05'
        assert result['patient_id'] == 'PID003'
        assert result['patient_name'] == 'Brown^Bob'
        assert result['birth_date'] == '19750320'
        assert result['sex'] == 'M'

    def test_parse_adt_a08_updates_name(self):
        from services.ingestion.hl7_server import parse_hl7_message
        result = parse_hl7_message(SAMPLE_ADT_A08)
        assert result['event_type'] == 'A08'
        assert result['patient_name'] == 'Smith^Jane'
        assert result['sex'] == 'F'

    def test_parse_orm_o01_extracts_order_fields(self):
        from services.ingestion.hl7_server import parse_hl7_message
        result = parse_hl7_message(SAMPLE_ORM_O01)
        assert result['message_type'] == 'ORM'
        assert result['event_type'] == 'O01'
        assert result['patient_id'] == 'PID001'
        assert result['accession_number'] == 'ORD001'
        assert result['requested_procedure_id'] == 'RP001'
        assert result['requested_procedure_desc'] == 'CT CHEST^Chest CT^L'
        assert result['scheduled_date'] == '20260726'
        assert result['scheduled_time'] == '0800'
        assert result['modality'] == 'CT'
        assert result['station_ae_title'] == 'CT_SCANNER'

    def test_parse_invalid_hl7_raises(self):
        from services.ingestion.hl7_server import parse_hl7_message
        result = parse_hl7_message(b'not even close')
        assert result is None


def _mock_conn():
    c = MagicMock()
    c.fetchval = AsyncMock(return_value=42)
    c.execute = AsyncMock()
    return c


class TestHl7PatientHandler:
    @pytest.mark.asyncio
    async def test_adt_a01_creates_patient(self):
        mock_conn = _mock_conn()

        with patch('services.ingestion.hl7_server.get_conn') as mock_get:
            mock_get.return_value.__aenter__.return_value = mock_conn
            mock_get.return_value.__aexit__ = AsyncMock(return_value=None)

            from services.ingestion.hl7_server import handle_adt_message
            result = await handle_adt_message({
                'message_type': 'ADT',
                'event_type': 'A01',
                'patient_id': 'PID001',
                'patient_name': 'Smith^John',
                'birth_date': '19800101',
                'sex': 'M',
            })

        assert result is True
        assert mock_conn.fetchval.called

    @pytest.mark.asyncio
    async def test_adt_a04_creates_patient(self):
        mock_conn = _mock_conn()

        with patch('services.ingestion.hl7_server.get_conn') as mock_get:
            mock_get.return_value.__aenter__.return_value = mock_conn
            mock_get.return_value.__aexit__ = AsyncMock(return_value=None)

            from services.ingestion.hl7_server import handle_adt_message
            result = await handle_adt_message({
                'message_type': 'ADT',
                'event_type': 'A04',
                'patient_id': 'PID002',
                'patient_name': 'Doe^Jane',
                'birth_date': '19900215',
                'sex': 'F',
            })

        assert result is True

    @pytest.mark.asyncio
    async def test_adt_a05_creates_patient(self):
        mock_conn = MagicMock(); mock_conn.execute = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value=43)

        with patch('services.ingestion.hl7_server.get_conn') as mock_get:
            mock_get.return_value.__aenter__.return_value = mock_conn
            mock_get.return_value.__aexit__ = AsyncMock(return_value=None)

            from services.ingestion.hl7_server import handle_adt_message
            result = await handle_adt_message({
                'message_type': 'ADT',
                'event_type': 'A05',
                'patient_id': 'PID003',
                'patient_name': 'Brown^Bob',
                'birth_date': '19750320',
                'sex': 'M',
            })

        assert result is True

    @pytest.mark.asyncio
    async def test_adt_a08_updates_patient_demographics(self):
        mock_conn = MagicMock(); mock_conn.execute = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value=42)

        with patch('services.ingestion.hl7_server.get_conn') as mock_get:
            mock_get.return_value.__aenter__.return_value = mock_conn
            mock_get.return_value.__aexit__ = AsyncMock(return_value=None)

            from services.ingestion.hl7_server import handle_adt_message
            result = await handle_adt_message({
                'message_type': 'ADT',
                'event_type': 'A08',
                'patient_id': 'PID001',
                'patient_name': 'Smith^Jane',
                'birth_date': '19800101',
                'sex': 'F',
            })

        assert result is True

    @pytest.mark.asyncio
    async def test_adt_a03_marks_patient_inactive(self):
        mock_conn = MagicMock(); mock_conn.execute = AsyncMock()
        mock_conn.execute = AsyncMock()

        with patch('services.ingestion.hl7_server.get_conn') as mock_get:
            mock_get.return_value.__aenter__.return_value = mock_conn
            mock_get.return_value.__aexit__ = AsyncMock(return_value=None)

            from services.ingestion.hl7_server import handle_adt_message
            result = await handle_adt_message({
                'message_type': 'ADT',
                'event_type': 'A03',
                'patient_id': 'PID001',
            })

        assert result is True

    @pytest.mark.asyncio
    async def test_adt_missing_patient_id_returns_false(self):
        from services.ingestion.hl7_server import handle_adt_message
        result = await handle_adt_message({
            'message_type': 'ADT',
            'event_type': 'A01',
            'patient_id': '',
        })
        assert result is False

    @pytest.mark.asyncio
    async def test_adt_unknown_event_returns_false(self):
        from services.ingestion.hl7_server import handle_adt_message
        result = await handle_adt_message({
            'message_type': 'ADT',
            'event_type': 'A99',
            'patient_id': 'PID001',
        })
        assert result is False


class TestHl7OrmHandler:
    @pytest.mark.asyncio
    async def test_orm_o01_creates_worklist_entry(self):
        mock_conn = MagicMock(); mock_conn.execute = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value="uuid-123")
        mock_conn.fetchrow = AsyncMock(return_value=None)

        with patch('services.ingestion.hl7_server.get_conn') as mock_get:
            mock_get.return_value.__aenter__.return_value = mock_conn
            mock_get.return_value.__aexit__ = AsyncMock(return_value=None)

            from services.ingestion.hl7_server import handle_orm_message
            result = await handle_orm_message({
                'message_type': 'ORM',
                'event_type': 'O01',
                'patient_id': 'PID001',
                'patient_name': 'Smith^John',
                'birth_date': '19800101',
                'sex': 'M',
                'accession_number': 'ORD001',
                'requested_procedure_id': 'RP001',
                'requested_procedure_desc': 'CT CHEST^Chest CT^L',
                'modality': 'CT',
                'station_ae_title': 'CT_SCANNER',
                'scheduled_date': '20260726',
                'scheduled_time': '0800',
            })

        assert result is True
        assert mock_conn.fetchval.called

    @pytest.mark.asyncio
    async def test_orm_missing_fields_returns_false(self):
        from services.ingestion.hl7_server import handle_orm_message
        result = await handle_orm_message({
            'message_type': 'ORM',
            'event_type': 'O01',
            'patient_id': '',
            'accession_number': '',
        })
        assert result is False

    @pytest.mark.asyncio
    async def test_orm_already_exists_succeeds(self):
        mock_conn = MagicMock(); mock_conn.execute = AsyncMock()
        mock_conn.fetchval = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value={"id": "uuid-123"})

        with patch('services.ingestion.hl7_server.get_conn') as mock_get:
            mock_get.return_value.__aenter__.return_value = mock_conn
            mock_get.return_value.__aexit__ = AsyncMock(return_value=None)

            from services.ingestion.hl7_server import handle_orm_message
            result = await handle_orm_message({
                'message_type': 'ORM',
                'event_type': 'O01',
                'patient_id': 'PID001',
                'patient_name': 'Smith^John',
                'birth_date': '19800101',
                'sex': 'M',
                'accession_number': 'ORD001',
                'requested_procedure_id': 'RP001',
                'requested_procedure_desc': 'CT CHEST^Chest CT^L',
                'modality': 'CT',
                'scheduled_date': '20260726',
            })

        assert result is True
        assert mock_conn.fetchval.called
        assert mock_conn.fetchval.call_count == 1

class TestHl7Audit:
    @pytest.mark.asyncio
    async def test_store_hl7_message_creates_record(self):
        mock_conn = MagicMock(); mock_conn.execute = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value="uuid-456")

        with patch('services.ingestion.hl7_server.get_conn') as mock_get:
            mock_get.return_value.__aenter__.return_value = mock_conn
            mock_get.return_value.__aexit__ = AsyncMock(return_value=None)

            from services.ingestion.hl7_server import _store_hl7_message
            await _store_hl7_message(
                SAMPLE_ADT_A01.encode('utf-8'),
                {'message_type': 'ADT', 'event_type': 'A01', 'patient_id': 'PID001'},
                'ok',
            )

        assert mock_conn.fetchval.called

    @pytest.mark.asyncio
    async def test_default_handler_stores_adt_message(self):
        mock_conn = MagicMock(); mock_conn.execute = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value="uuid-789")

        with patch('services.ingestion.hl7_server.get_conn') as mock_get:
            mock_get.return_value.__aenter__.return_value = mock_conn
            mock_get.return_value.__aexit__ = AsyncMock(return_value=None)

            mock_patient = MagicMock()
            mock_patient.fetchval = AsyncMock(return_value=42)
            mock_patient.insert_or_select = AsyncMock(return_value={'id': 42})

            with patch('services.ingestion.hl7_server.Patient') as mock_pat_cls:
                mock_pat_cls.return_value = mock_patient

                from services.ingestion.hl7_server import default_handler
                result = await default_handler(SAMPLE_ADT_A01.encode('utf-8'))

        assert result == b'ACK'

    @pytest.mark.asyncio
    async def test_default_handler_stores_failed_message(self):
        mock_conn = MagicMock(); mock_conn.execute = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value="uuid-000")

        with patch('services.ingestion.hl7_server.get_conn') as mock_get:
            mock_get.return_value.__aenter__.return_value = mock_conn
            mock_get.return_value.__aexit__ = AsyncMock(return_value=None)

            from services.ingestion.hl7_server import default_handler
            result = await default_handler(b'NOT VALID HL7')

        assert b'ERR' in result
        assert mock_conn.fetchval.called

    @pytest.mark.asyncio
    async def test_upsert_patient_tags_sync_source(self):
        mock_conn = MagicMock(); mock_conn.execute = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value=42)
        mock_conn.execute = AsyncMock()

        with patch('services.ingestion.hl7_server.get_conn') as mock_get:
            mock_get.return_value.__aenter__.return_value = mock_conn
            mock_get.return_value.__aexit__ = AsyncMock(return_value=None)

            mock_patient = MagicMock()
            mock_patient.fetchval = AsyncMock(return_value=42)
            mock_patient.insert_or_select = AsyncMock(return_value={'id': 42})

            with patch('services.ingestion.hl7_server.Patient') as mock_pat_cls:
                mock_pat_cls.return_value = mock_patient

                from services.ingestion.hl7_server import _upsert_patient
                result = await _upsert_patient({
                    'patient_id': 'PID001',
                    'patient_name': 'Smith^John',
                    'patient_birth_date': '19800101',
                    'patient_sex': 'M',
                })

        assert result is True
        execute_calls = [c for c in mock_conn.execute.call_args_list]
        assert any('sync_source' in str(c) for c in execute_calls)
