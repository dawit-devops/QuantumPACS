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

SAMPLE_ADT_A02 = (
    'MSH|^~\\&|SENDING|SENDING_FACILITY|QUANTUMPACS||202607251030||ADT^A02|MSG006|P|2.5\r'
    'EVN|A02|202607251030\r'
    'PID|1||PID001||Smith^John||19800101|M\r'
    'PV1|1|I|WARD-A^ROOM-101^^^FACILITY|||||||||||||||||IN|||SUR|||||||||||||||||||||||||202607251030\r'
)

SAMPLE_ADT_A06 = (
    'MSH|^~\\&|SENDING|SENDING_FACILITY|QUANTUMPACS||202607251030||ADT^A06|MSG007|P|2.5\r'
    'EVN|A06|202607251030\r'
    'PID|1||PID002||Doe^Jane||19900215|F\r'
    'MRG|PID001^^^SENDING_FACILITY^MR\r'
)

SAMPLE_ADT_A07 = (
    'MSH|^~\\&|SENDING|SENDING_FACILITY|QUANTUMPACS||202607251030||ADT^A07|MSG008|P|2.5\r'
    'EVN|A07|202607251030\r'
    'PID|1||PID001||Smith^John||19800101|M\r'
    'MRG|PID002^^^SENDING_FACILITY^MR\r'
)

SAMPLE_ADT_A40 = (
    'MSH|^~\\&|SENDING|SENDING_FACILITY|QUANTUMPACS||202607251030||ADT^A40|MSG009|P|2.5\r'
    'EVN|A40|202607251030\r'
    'PID|1||PID003||Brown^Bob||19750320|M\r'
    'MRG|PID001^^^SENDING_FACILITY^MR\r'
)

SAMPLE_ORM_O01 = (
    'MSH|^~\\&|SENDING|SENDING_FACILITY|QUANTUMPACS||202607251030||ORM^O01|MSG004|P|2.5\r'
    'PID|1||PID001||Smith^John||19800101|M\r'
    'ORC|NW|ORD001|||CM|||||||202607251030\r'
    'OBR|1|ORD001|RP001|CT CHEST^Chest CT^L|||202607260800|||||||||||CT_SCANNER^CT Room 1||||||CT|||1^CM^30^Q^30^A||||Routine screening|Lee^Kim\r'
)

SAMPLE_ORU_R01 = (
    'MSH|^~\\&|SENDING|SENDING_FACILITY|QUANTUMPACS||202607261200||ORU^R01|MSG010|P|2.5\r'
    'PID|1||PID001||Smith^John||19800101|M\r'
    'OBR|1|ORD001|ORD001|CT CHEST^Chest CT^L|||202607260800|||||||||||CT_SCANNER||||||CT|F\r'
    'OBX|1|ST|1234^FINDINGS^L||Normal study|Normal|||F\r'
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

    @pytest.mark.asyncio
    async def test_ip_whitelist_rejects_unlisted(self):
        handler = AsyncMock()
        from services.ingestion.hl7_server import MllpServer
        server = MllpServer(host='127.0.0.1', port=0, handler=handler, allowed_ips=['10.0.0.1'])
        try:
            await server.start()
            port = server._server.sockets[0].getsockname()[1]

            reader, writer = await asyncio.open_connection('127.0.0.1', port)
            writer.write(_mllp_encode(SAMPLE_ADT_A01))
            await writer.drain()
            await asyncio.sleep(0.1)
            writer.close()
            try:
                await writer.wait_closed()
            except (ConnectionResetError, ConnectionError):
                pass

            handler.assert_not_awaited()
        finally:
            await server.stop()


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

    def test_parse_orm_o01_extracts_mwl_extended_fields(self):
        from services.ingestion.hl7_server import parse_hl7_message
        result = parse_hl7_message(SAMPLE_ORM_O01)
        # OBR-4 components → RequestedProcedureCodeSequence (ME-03).
        assert result['requested_procedure_code'] == 'CT CHEST'
        assert result['requested_procedure_code_meaning'] == 'Chest CT'
        assert result['requested_procedure_code_scheme'] == 'L'
        # OBR-18.1 station name, OBR-32 performing physician.
        assert result['scheduled_station_name'] == 'CT Room 1'
        assert result['scheduled_performing_physician'] == 'Lee^Kim'
        # OBR-27 component 7 priority, OBR-31 reason for study.
        assert result['requested_procedure_priority'] == 'A'
        assert result['reason_for_requested_procedure'] == 'Routine screening'
        # OBR-16 ordering provider (empty in the sample) → referring.
        assert result['referring_physician'] == ''

    def test_parse_oru_r01_extracts_accession_from_obr(self):
        from services.ingestion.hl7_server import parse_hl7_message
        result = parse_hl7_message(SAMPLE_ORU_R01)
        assert result['message_type'] == 'ORU'
        assert result['event_type'] == 'R01'
        assert result['patient_id'] == 'PID001'
        assert result['accession_number'] == 'ORD001'
        assert result['result_status'] == 'F'

    def test_parse_adt_a02_extracts_patient_fields(self):
        from services.ingestion.hl7_server import parse_hl7_message
        result = parse_hl7_message(SAMPLE_ADT_A02)
        assert result['message_type'] == 'ADT'
        assert result['event_type'] == 'A02'
        assert result['patient_id'] == 'PID001'
        assert result['patient_name'] == 'Smith^John'

    def test_parse_adt_a06_extracts_merge_fields(self):
        from services.ingestion.hl7_server import parse_hl7_message
        result = parse_hl7_message(SAMPLE_ADT_A06)
        assert result['message_type'] == 'ADT'
        assert result['event_type'] == 'A06'
        assert result['patient_id'] == 'PID002'
        assert result['surviving_patient_id'] == 'PID002'
        assert result['merged_patient_id'] == 'PID001'

    def test_parse_adt_a07_extracts_undo_merge_fields(self):
        from services.ingestion.hl7_server import parse_hl7_message
        result = parse_hl7_message(SAMPLE_ADT_A07)
        assert result['message_type'] == 'ADT'
        assert result['event_type'] == 'A07'
        assert result['patient_id'] == 'PID001'
        assert result['surviving_patient_id'] == 'PID001'
        assert result['merged_patient_id'] == 'PID002'

    def test_parse_adt_a40_extracts_merge_list_fields(self):
        from services.ingestion.hl7_server import parse_hl7_message
        result = parse_hl7_message(SAMPLE_ADT_A40)
        assert result['message_type'] == 'ADT'
        assert result['event_type'] == 'A40'
        assert result['patient_id'] == 'PID003'
        assert result['surviving_patient_id'] == 'PID003'
        assert result['merged_patient_id'] == 'PID001'

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

    @pytest.mark.asyncio
    async def test_adt_a02_transfer_updates_patient(self):
        mock_conn = MagicMock(); mock_conn.execute = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value=42)

        with patch('services.ingestion.hl7_server.get_conn') as mock_get:
            mock_get.return_value.__aenter__.return_value = mock_conn
            mock_get.return_value.__aexit__ = AsyncMock(return_value=None)

            from services.ingestion.hl7_server import handle_adt_message
            result = await handle_adt_message({
                'message_type': 'ADT',
                'event_type': 'A02',
                'patient_id': 'PID001',
                'patient_name': 'Smith^John',
                'birth_date': '19800101',
                'sex': 'M',
            })

        assert result is True

    @pytest.mark.asyncio
    async def test_adt_a06_merge_patients(self):
        mock_conn = MagicMock(); mock_conn.execute = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value=42)
        mock_conn.fetch = AsyncMock(return_value=[
            {'id': 10, 'patient_id': 'PID002', 'study_instance_uid': '1.2.3'},
        ])

        with patch('services.ingestion.hl7_server.get_conn') as mock_get:
            mock_get.return_value.__aenter__.return_value = mock_conn
            mock_get.return_value.__aexit__ = AsyncMock(return_value=None)

            from services.ingestion.hl7_server import handle_adt_message
            result = await handle_adt_message({
                'message_type': 'ADT',
                'event_type': 'A06',
                'patient_id': 'PID002',
                'patient_name': 'Doe^Jane',
                'merged_patient_id': 'PID001',
                'surviving_patient_id': 'PID002',
            })

        assert result is True

    @pytest.mark.asyncio
    async def test_adt_a07_undo_merge(self):
        mock_conn = MagicMock(); mock_conn.execute = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value=42)

        with patch('services.ingestion.hl7_server.get_conn') as mock_get:
            mock_get.return_value.__aenter__.return_value = mock_conn
            mock_get.return_value.__aexit__ = AsyncMock(return_value=None)

            from services.ingestion.hl7_server import handle_adt_message
            result = await handle_adt_message({
                'message_type': 'ADT',
                'event_type': 'A07',
                'patient_id': 'PID001',
                'patient_name': 'Smith^John',
                'merged_patient_id': 'PID002',
                'surviving_patient_id': 'PID001',
            })

        assert result is True

    @pytest.mark.asyncio
    async def test_adt_a40_merge_patient_list(self):
        mock_conn = MagicMock(); mock_conn.execute = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value=42)
        mock_conn.fetch = AsyncMock(return_value=[])

        with patch('services.ingestion.hl7_server.get_conn') as mock_get:
            mock_get.return_value.__aenter__.return_value = mock_conn
            mock_get.return_value.__aexit__ = AsyncMock(return_value=None)

            from services.ingestion.hl7_server import handle_adt_message
            result = await handle_adt_message({
                'message_type': 'ADT',
                'event_type': 'A40',
                'patient_id': 'PID003',
                'patient_name': 'Brown^Bob',
                'merged_patient_id': 'PID001',
                'surviving_patient_id': 'PID003',
            })

        assert result is True

    @pytest.mark.asyncio
    async def test_adt_a06_missing_merge_id_returns_false(self):
        from services.ingestion.hl7_server import handle_adt_message
        result = await handle_adt_message({
            'message_type': 'ADT',
            'event_type': 'A06',
            'patient_id': 'PID002',
            'merged_patient_id': '',
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


class TestHl7OruHandler:
    @pytest.mark.asyncio
    async def test_oru_marks_worklist_entry_performed(self):
        mock_conn = MagicMock(); mock_conn.execute = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value="uuid-123")

        with patch('services.ingestion.hl7_server.get_conn') as mock_get:
            mock_get.return_value.__aenter__.return_value = mock_conn
            mock_get.return_value.__aexit__ = AsyncMock(return_value=None)

            mock_wl = MagicMock()
            mock_wl.get_by_accession = AsyncMock(return_value={
                'id': 'uuid-1', 'accession_number': 'ORD001', 'status': 'in_progress',
            })
            mock_wl.mark_performed = AsyncMock()
            with patch('services.ingestion.hl7_server.Worklist') as mock_wl_cls:
                mock_wl_cls.return_value = mock_wl

                from services.ingestion.hl7_server import handle_oru_message
                result = await handle_oru_message({
                    'message_type': 'ORU',
                    'event_type': 'R01',
                    'patient_id': 'PID001',
                    'patient_name': 'Smith^John',
                    'birth_date': '19800101',
                    'sex': 'M',
                    'accession_number': 'ORD001',
                    'result_status': 'F',
                })

        assert result is True
        mock_wl.mark_performed.assert_awaited_once_with('ORD001')

    @pytest.mark.asyncio
    async def test_oru_skips_performed_entry(self):
        mock_conn = MagicMock(); mock_conn.execute = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value="uuid-123")

        with patch('services.ingestion.hl7_server.get_conn') as mock_get:
            mock_get.return_value.__aenter__.return_value = mock_conn
            mock_get.return_value.__aexit__ = AsyncMock(return_value=None)

            mock_wl = MagicMock()
            mock_wl.get_by_accession = AsyncMock(return_value={
                'id': 'uuid-1', 'accession_number': 'ORD001', 'status': 'performed',
            })
            mock_wl.mark_performed = AsyncMock()
            with patch('services.ingestion.hl7_server.Worklist') as mock_wl_cls:
                mock_wl_cls.return_value = mock_wl

                from services.ingestion.hl7_server import handle_oru_message
                result = await handle_oru_message({
                    'message_type': 'ORU',
                    'event_type': 'R01',
                    'patient_id': 'PID001',
                    'accession_number': 'ORD001',
                    'result_status': 'F',
                })

        assert result is True
        mock_wl.mark_performed.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_oru_missing_accession_returns_false(self):
        from services.ingestion.hl7_server import handle_oru_message
        result = await handle_oru_message({
            'message_type': 'ORU',
            'event_type': 'R01',
            'patient_id': 'PID001',
        })
        assert result is False

    @pytest.mark.asyncio
    async def test_default_handler_processes_oru(self):
        mock_conn = MagicMock(); mock_conn.execute = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value="uuid-123")

        with patch('services.ingestion.hl7_server.get_conn') as mock_get:
            mock_get.return_value.__aenter__.return_value = mock_conn
            mock_get.return_value.__aexit__ = AsyncMock(return_value=None)

            mock_patient = MagicMock()
            mock_patient.insert_or_select = AsyncMock(return_value={'id': 42})
            with patch('services.ingestion.hl7_server.Patient') as mock_pat_cls:
                mock_pat_cls.return_value = mock_patient

                mock_wl = MagicMock()
                mock_wl.get_by_accession = AsyncMock(return_value=None)
                with patch('services.ingestion.hl7_server.Worklist') as mock_wl_cls:
                    mock_wl_cls.return_value = mock_wl

                    from services.ingestion.hl7_server import default_handler
                    resp = await default_handler(SAMPLE_ORU_R01.encode('utf-8'))

        assert resp == b'ACK'

class TestHl7HttpEndpoint:
    def test_post_hl7_message_returns_ack(self):
        mock_conn = MagicMock(); mock_conn.execute = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value="uuid-abc")

        with patch('services.ingestion.hl7_server.get_conn') as mock_get:
            mock_get.return_value.__aenter__.return_value = mock_conn
            mock_get.return_value.__aexit__ = AsyncMock(return_value=None)

            mock_patient = MagicMock()
            mock_patient.fetchval = AsyncMock(return_value=42)
            mock_patient.insert_or_select = AsyncMock(return_value={'id': 42})

            with patch('services.ingestion.hl7_server.Patient') as mock_pat_cls:
                mock_pat_cls.return_value = mock_patient

                from api.hl7 import Hl7Receiver
                from starlette.applications import Starlette
                from starlette.routing import Route
                from starlette.testclient import TestClient

                app = Starlette(
                    routes=[Route('/api/hl7', endpoint=Hl7Receiver, methods=['POST'])],
                )
                client = TestClient(app)
                resp = client.post('/api/hl7', content=SAMPLE_ADT_A01)

        assert resp.status_code == 200
        assert resp.text == 'ACK'

    def test_post_hl7_invalid_message_returns_err(self):
        from api.hl7 import Hl7Receiver
        from starlette.applications import Starlette
        from starlette.routing import Route
        from starlette.testclient import TestClient

        app = Starlette(
            routes=[Route('/api/hl7', endpoint=Hl7Receiver, methods=['POST'])],
        )
        client = TestClient(app)
        resp = client.post('/api/hl7', content='NOT VALID HL7')
        assert resp.status_code == 200
        assert 'ERR' in resp.text or 'NACK' in resp.text

    def test_get_returns_method_not_allowed(self):
        from api.hl7 import Hl7Receiver
        from starlette.applications import Starlette
        from starlette.routing import Route
        from starlette.testclient import TestClient

        app = Starlette(
            routes=[Route('/api/hl7', endpoint=Hl7Receiver, methods=['POST'])],
        )
        client = TestClient(app)
        resp = client.get('/api/hl7')
        assert resp.status_code == 405


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
    async def test_adt_a01_with_sending_facility_tags_tenant(self):
        mock_conn = MagicMock(); mock_conn.execute = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value=42)

        with patch('services.ingestion.hl7_server.get_conn') as mock_get:
            mock_get.return_value.__aenter__.return_value = mock_conn
            mock_get.return_value.__aexit__ = AsyncMock(return_value=None)

            from services.ingestion.hl7_server import default_handler
            result = await default_handler(SAMPLE_ADT_A01.encode('utf-8'))

        assert result == b'ACK'
        execute_calls = [c for c in mock_conn.execute.call_args_list]
        tenant_calls = [c for c in execute_calls if 'tenant_id' in str(c) or 'SENDING_FACILITY' in str(c)]
        assert len(tenant_calls) > 0

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


@pytest.mark.asyncio
class TestHl7StructuredLogging:
    async def test_unknown_adt_event_logs_warning(self, caplog):
        from services.ingestion.hl7_server import handle_adt_message
        import logging
        caplog.set_level(logging.WARNING)
        result = await handle_adt_message({
            'message_type': 'ADT',
            'event_type': 'A99',
            'patient_id': 'PID001',
        })
        assert result is False
        assert any('Unknown ADT event' in msg for msg in caplog.messages)
        assert any('A99' in msg for msg in caplog.messages)

    async def test_unknown_message_type_logs_structured(self, caplog):
        with patch('services.ingestion.hl7_server._store_hl7_message', new=AsyncMock()):
            from services.ingestion.hl7_server import default_handler
            import logging
            caplog.set_level(logging.WARNING)
            msg = (
                b'MSH|^~\\&|SENDING|FACILITY|RECV|APP|20250101000000||SIU^S12|MSG001|P|2.5\r'
                b'SCH|12345||BOOKED|Surgery^\r'
            )
            result = await default_handler(msg)
            assert b'ACK' in result
            assert any('SIU' in msg for msg in caplog.messages)
            assert any('S12' in msg for msg in caplog.messages)
            assert any('MSG001' in msg for msg in caplog.messages)
