"""S3-18 — HL7 E2E over the live wire (RIS-SL-20: order < 1 min).

Real MLLP connection to the running backend, real database. Asserts the
engine path end-to-end: ORM -> ACK + ris_orders + ris_hl7_messages
(PROCESSED) + auto-registered endpoint; malformed -> ERR + exception
queue (FAILED); manual retry replays the queue entry (retry_count
increments on a deterministic re-failure). Skipped when the MLLP server
is unreachable (CI without a dev backend), mirroring test_mllp_live.
"""

import asyncio
import os
import uuid

import asyncpg
import pytest

from config import load_config
from services.hl7_engine.service import Hl7InterfaceEngine

MLLP_START = b'\x0b'
MLLP_END = b'\x1c\x0d'


def _mllp(msg: str) -> bytes:
    return MLLP_START + msg.encode('utf-8') + MLLP_END


async def _send(host: str, port: int, msg: bytes, timeout: float = 10.0) -> bytes:
    reader, writer = await asyncio.open_connection(host, port)
    try:
        writer.write(msg)
        await writer.drain()
        data = await asyncio.wait_for(reader.readuntil(MLLP_END), timeout)
    finally:
        writer.close()
        await writer.wait_closed()
    return data


@pytest.fixture(scope='module')
def live_mllp():
    """Resolve MLLP endpoint; skip module when unreachable."""
    cfg = load_config()
    host = os.environ.get('MLLP_HOST', '127.0.0.1')
    port = int(os.environ.get('MLLP_PORT', cfg.get('hl7_mllp_port', '12579')))

    async def _probe():
        try:
            r, w = await asyncio.open_connection(host, port)
            w.close()
            await w.wait_closed()
            return True
        except (OSError, ConnectionError):
            return False

    if not asyncio.run(_probe()):
        pytest.skip(f'MLLP server not reachable at {host}:{port} (live test)')
    return host, port


@pytest.fixture(scope='module')
async def live_db():
    """Real-DB connection for asserting engine side effects."""
    cfg = load_config()
    conn = await asyncpg.connect(
        user=cfg['db_user'],
        password=cfg['db_password'],
        database=cfg['db_database'],
        host=cfg['db_host'],
        port=int(cfg['db_port']),
    )
    try:
        yield conn
    finally:
        await conn.close()


@pytest.fixture(scope='module')
async def live_engine(live_db):
    """Engine wired to the real DB pool, so retries hit the same store."""
    import db.conn
    created = db.conn.database._pool is None
    if created:
        await db.conn.setup(pool_size=4)
    try:
        yield Hl7InterfaceEngine()
    finally:
        if created:
            await db.conn.database.close()


def _orm_o01(control_id: str, accession: str) -> str:
    return (
        f'MSH|^~\\&|SENDING|SENDING_FACILITY|QUANTUMPACS||202608181030||ORM^O01|'
        f'{control_id}|P|2.5\r'
        f'PID|1||E2E{control_id}||E2E^Patient||19800101|M\r'
        f'ORC|NW|{accession}|||CM|||||||202608181030\r'
        f'OBR|1|{accession}|{accession}|CT CHEST^Chest CT^L|||202608190800|||||'
        f'||||||CT_SCANNER^CT Room 1||||||CT|||1^CM^30^Q^30^A||||Routine'
        f' screening|Lee^Kim\r'
    )


@pytest.mark.asyncio(loop_scope='module')
class TestRisHl7WireE2E:
    async def test_orm_creates_order_message_and_endpoint(self, live_mllp, live_db):
        host, port = live_mllp
        control_id = uuid.uuid4().hex[:8].upper()
        accession = f'E2E{uuid.uuid4().hex[:8].upper()}'

        started = asyncio.get_event_loop().time()
        resp = await _send(host, port, _mllp(_orm_o01(control_id, accession)))
        elapsed = asyncio.get_event_loop().time() - started
        assert b'ACK' in resp, resp
        # RIS-SL-20: order intake must complete in under a minute on the wire.
        assert elapsed < 60

        msg = await live_db.fetchrow(
            'SELECT control_id, message_type, status FROM ris_hl7_messages '
            'WHERE control_id = $1',
            control_id,
        )
        assert msg is not None
        assert msg['message_type'] == 'ORM'
        assert msg['status'] == 'PROCESSED'

        order = await live_db.fetchrow(
            'SELECT accession_number, status FROM ris_orders '
            'WHERE accession_number = $1',
            accession,
        )
        assert order is not None
        assert order['status'] == 'ORDERED'

        endpoint = await live_db.fetchrow(
            'SELECT name, message_count FROM ris_interface_endpoints '
            "WHERE name = 'SENDING_FACILITY'"
        )
        assert endpoint is not None
        assert endpoint['message_count'] >= 1

    async def test_malformed_message_lands_in_exception_queue(self, live_mllp, live_db):
        host, port = live_mllp
        resp = await _send(host, port, _mllp('THIS IS NOT HL7\rLINE2\r'))
        assert b'ERR Unparseable message' in resp, resp

        failed = await live_db.fetchval(
            "SELECT count(*) FROM ris_hl7_messages WHERE status = 'FAILED' "
            "AND error_message = 'Unparseable message'"
        )
        assert failed >= 1

    async def test_manual_retry_replays_exception_queue_entry(self, live_mllp, live_engine, live_db):
        host, port = live_mllp
        await _send(host, port, _mllp('STILL NOT HL7\rLINE2\r'))

        row = await live_db.fetchrow(
            "SELECT id, status, retry_count FROM ris_hl7_messages "
            "WHERE status = 'FAILED' AND error_message = 'Unparseable message' "
            'ORDER BY created_at DESC LIMIT 1'
        )
        assert row is not None and row['retry_count'] == 0

        ok = await live_engine.retry_message(row['id'])
        # Deterministic replay: the payload is still unparseable, so the
        # retry must fail again and consume retry budget — not silently pass.
        assert ok is False

        after = await live_db.fetchrow(
            'SELECT status, retry_count FROM ris_hl7_messages WHERE id = $1',
            row['id'],
        )
        assert after['status'] == 'FAILED'
        assert after['retry_count'] == 1

def _adt_a04(control_id: str, patient_id: str, name: str = 'E2E^Register') -> str:
    return (
        f'MSH|^~\\&|HIS|HIS_FACILITY|QUANTUMPACS||202608210900||ADT^A04|'
        f'{control_id}|P|2.5\r'
        f'PID|1||{patient_id}||{name}||19850412|M\r'
    )


def _adt_a40(control_id: str, surviving_id: str, merged_id: str) -> str:
    return (
        f'MSH|^~\\&|HIS|HIS_FACILITY|QUANTUMPACS||202608210930||ADT^A40|'
        f'{control_id}|P|2.5\r'
        f'PID|1||{surviving_id}||E2E^Surviving||19850412|M\r'
        f'MRG|{merged_id}\r'
    )


@pytest.mark.asyncio(loop_scope='module')
class TestAdtRegistrationE2E:
    """S3-19 — registration flow over the wire: A04 creates/updates the
    patient, A40 merge propagates to MPI state (merged_into + inactive),
    and both land as PROCESSED interface messages."""

    async def test_a04_registers_patient(self, live_mllp, live_db):
        host, port = live_mllp
        control_id = uuid.uuid4().hex[:8].upper()
        patient_id = f'E2EA04{uuid.uuid4().hex[:8].upper()}'

        resp = await _send(host, port, _mllp(_adt_a04(control_id, patient_id)))
        assert b'ACK' in resp, resp

        msg = await live_db.fetchrow(
            'SELECT message_type, status FROM ris_hl7_messages '
            'WHERE control_id = $1',
            control_id,
        )
        assert msg is not None
        assert msg['message_type'] == 'ADT'
        assert msg['status'] == 'PROCESSED'

        patient = await live_db.fetchrow(
            'SELECT patient_id FROM patients WHERE patient_id = $1',
            patient_id,
        )
        assert patient is not None, 'A04 must register the patient'

    async def test_a40_merge_propagates_to_mpi(self, live_mllp, live_db):
        host, port = live_mllp
        control_id = uuid.uuid4().hex[:8].upper()
        suffix = uuid.uuid4().hex[:8].upper()
        surviving_id = f'E2EA40S{suffix}'
        merged_id = f'E2EA40M{suffix}'

        # Both legs must exist before the merge: register the loser first.
        await _send(host, port, _mllp(_adt_a04(f'{control_id}A', merged_id)))
        await _send(host, port, _mllp(_adt_a04(f'{control_id}B', surviving_id)))
        resp = await _send(host, port, _mllp(_adt_a40(control_id, surviving_id,
                                                      merged_id)))
        assert b'ACK' in resp, resp

        msg = await live_db.fetchrow(
            'SELECT status FROM ris_hl7_messages WHERE control_id = $1',
            control_id,
        )
        assert msg is not None and msg['status'] == 'PROCESSED'

        survivor = await live_db.fetchrow(
            "SELECT meta->>'active' AS active FROM patients "
            'WHERE patient_id = $1',
            surviving_id,
        )
        assert survivor is not None

        loser = await live_db.fetchrow(
            "SELECT meta->>'merged_into' AS merged_into, "
            "meta->>'active' AS active FROM patients "
            'WHERE patient_id = $1',
            merged_id,
        )
        assert loser is not None, 'merge target must exist'
        assert loser['merged_into'] == surviving_id
        assert loser['active'] == 'false', 'merged leg must be deactivated'
