"""P4.2 — live MLLP E2E against the running backend (Phase 4 kickoff).

Sends real ADT/ORM messages over MLLP framing to the dev MLLP server and
asserts rows appear in the real database. Skipped when the server is not
reachable (e.g. CI without a dev backend), mirroring the archive-reachability
gating pattern used by the DICOMweb suite.
"""

import asyncio
import os
import uuid

import asyncpg
import pytest

from config import load_config

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
    """Real-DB connection for asserting handler side effects."""
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


def _adt_a01(pid: str, name: str) -> str:
    return (
        f'MSH|^~\\&|SENDING|SENDING_FACILITY|QUANTUMPACS||202608161030||ADT^A01|'
        f'{uuid.uuid4().hex[:8]}|P|2.5\r'
        f'EVN|A01|202608161030\r'
        f'PID|1||{pid}||{name}||19800101|M|||123 Main St^^Metropolis^NY^10001\r'
    )


def _orm_o01(pid: str, accession: str) -> str:
    return (
        f'MSH|^~\\&|SENDING|SENDING_FACILITY|QUANTUMPACS||202608161100||ORM^O01|'
        f'{uuid.uuid4().hex[:8]}|P|2.5\r'
        f'PID|1||{pid}||Live^Patient||19800101|M\r'
        f'ORC|NW|{accession}|||CM|||||||202608161100\r'
        f'OBR|1|{accession}|{accession}|CT CHEST^Chest CT^L|||202608170800|||||'
        f'||||||CT_SCANNER^CT Room 1||||||CT|||1^CM^30^Q^30^A||||Routine'
        f' screening|Lee^Kim\r'
    )


@pytest.mark.asyncio(loop_scope='module')
class TestLiveMllpE2E:
    async def test_adt_a01_patient_row_appears(self, live_mllp, live_db):
        host, port = live_mllp
        pid = f'LIVE{uuid.uuid4().hex[:8].upper()}'
        resp = await _send(host, port, _mllp(_adt_a01(pid, 'Live^Patient')))
        assert resp.startswith(MLLP_START) and b'ACK' in resp, resp

        row = await live_db.fetchrow(
            'SELECT patient_id, name, birth_date, sex FROM patients '
            'WHERE patient_id = $1',
            pid,
        )
        assert row is not None
        assert row['name'] == 'Live^Patient'
        assert row['birth_date'] == '19800101'

        # P4.2 audit: the message itself must be stored with an ok parse.
        audited = await live_db.fetchval(
            'SELECT count(*) FROM hl7_messages WHERE patient_id = $1 '
            "AND parse_status = 'ok'",
            pid,
        )
        assert audited >= 1

    async def test_orm_o01_worklist_entry_and_cancel(self, live_mllp, live_db):
        host, port = live_mllp
        pid = f'LIVE{uuid.uuid4().hex[:8].upper()}'
        accession = f'ACC{uuid.uuid4().hex[:8].upper()}'

        resp = await _send(host, port, _mllp(_orm_o01(pid, accession)))
        assert b'ACK' in resp, resp

        entry = await live_db.fetchrow(
            'SELECT accession_number, requested_procedure_desc, modality, '
            "status FROM worklist_entries WHERE accession_number = $1",
            accession,
        )
        assert entry is not None
        assert entry['modality'] == 'CT'
        assert entry['status'] == 'scheduled'

        # Negative: cancelled order (ORC-1 CA) must flip the entry to cancelled.
        cancel = _orm_o01(pid, accession).replace('ORC|NW', 'ORC|CA')
        resp = await _send(host, port, _mllp(cancel))
        assert b'ACK' in resp, resp
        entry = await live_db.fetchrow(
            'SELECT status FROM worklist_entries WHERE accession_number = $1',
            accession,
        )
        assert entry['status'] == 'cancelled'

    async def test_malformed_message_nacks_and_audits(self, live_mllp, live_db):
        host, port = live_mllp
        resp = await _send(host, port, _mllp('THIS IS NOT HL7\rLINE2\r'))
        assert b'ERR Unparseable message' in resp, resp

        failed = await live_db.fetchval(
            "SELECT count(*) FROM hl7_messages WHERE parse_status = 'failed'"
        )
        assert failed >= 1