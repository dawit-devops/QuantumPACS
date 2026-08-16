"""P4.1 — ADR-028 R5: MWL C-FIND parity test vs the dcm4chee archive.

Asserts that worklist entries mirrored from QuantumPACS (ORM-O01 via MLLP,
mwl_sync mirror) are served by the dcm4chee-arc MWL SCP over DIMSE, and that
cancelled (order control `CA`) entries do not appear. dcm4chee-arc serves
Worklist C-FIND via DIMSE only — there is no HTTP `/mwl` endpoint.

Skipped when the archive is unreachable (e.g. dev envs without the archive
container), mirroring the reachability-gating pattern of the MLLP/DICOMweb
live suites.
"""

import asyncio
import os
import socket

import pytest

from config import load_config

ARCHIVE_HOST = os.environ.get('ARCHIVE_HOST', '127.0.0.1')
ARCHIVE_PORT = int(os.environ.get('ARCHIVE_PORT', '11112'))
# The archive serves the Modality Worklist SCP on its WORKLIST AE title
# (dcm4chee LDAP: cn=Modality Worklist Information Model - FIND SCP,
# dicomAETitle=WORKLIST, device dcm4chee-arc) — DCM4CHEE is storage-only.
ARCHIVE_AE = os.environ.get('ARCHIVE_AE', 'WORKLIST')


def _archive_reachable() -> bool:
    try:
        with socket.create_connection((ARCHIVE_HOST, ARCHIVE_PORT), timeout=2):
            return True
    except OSError:
        return False


@pytest.fixture(scope='module')
def live_archive():
    """Resolve archive MWL SCP; skip module when unreachable."""
    if not _archive_reachable():
        pytest.skip(
            f'dcm4chee archive MWL SCP not reachable at '
            f'{ARCHIVE_HOST}:{ARCHIVE_PORT} (live test)')
    return ARCHIVE_HOST, ARCHIVE_PORT


@pytest.fixture(scope='module')
async def mirrored_entry(live_archive):
    """Insert a fresh worklist entry in the real DB so the mirror has
    something to carry; the entry mirrors to dcm4chee via mwl_sync when
    proxy mode is on (or was exported by the phase-3 mirror)."""
    import asyncpg
    cfg = load_config()
    conn = await asyncpg.connect(
        user=cfg['db_user'],
        password=cfg['db_password'],
        database=cfg['db_database'],
        host=cfg['db_host'],
        port=int(cfg['db_port']),
    )
    accession = f'PARITY-{os.getpid()}'
    try:
        await conn.execute(
            """
            INSERT INTO worklist_entries
                (accession_number, requested_procedure_desc, modality,
                 status, patient_id)
            VALUES ($1, $2, $3, $4, $5)
            """,
            accession, 'PARITY TEST CT', 'CT', 'scheduled', 'PARITY-PAT-001',
        )
        yield accession
    finally:
        await conn.execute(
            'DELETE FROM worklist_entries WHERE accession_number = $1',
            accession,
        )
        await conn.close()


def _cfind(host, port, accession, modality='CT', max_attempts=1):
    from pynetdicom import AE
    from pynetdicom.sop_class import ModalityWorklistInformationFind
    from pydicom.dataset import Dataset

    def _one_pass():
        ae = AE(ae_title='QPPARITY')
        ae.add_requested_context(ModalityWorklistInformationFind)
        ae.acse_timeout = 5
        ae.network_timeout = 8
        results = []
        assoc = ae.associate(host, port, ae_title=ARCHIVE_AE)
        if not assoc.is_established:
            pytest.fail(f'C-FIND association to {ARCHIVE_AE}@{host}:{port} failed')

        query = Dataset()
        query.QueryRetrieveLevel = 'STATUS'
        query.PatientID = 'PARITY-PAT-001'
        query.AccessionNumber = accession
        query.Modality = modality
        query.ScheduledProcedureStepSequence = [Dataset()]
        for (status, ds) in assoc.send_c_find(
                query, ModalityWorklistInformationFind):
            if status and status.Status in (0xFF00, 0xFF01):
                results.append(ds)
            elif status and status.Status != 0xFF00:
                break
        assoc.release()
        return results

    # The mwl_sync worker replays dirty QP rows to the archive MWL-RS on a
    # fixed interval (default 10s); poll until the mirror lands or give up.
    import time
    for attempt in range(max_attempts):
        results = _one_pass()
        if results or attempt == max_attempts - 1:
            return results
        time.sleep(3)
    return results


def test_cfind_returns_mirrored_entry(live_archive, mirrored_entry):
    """The ORM-mirrored entry (accession + requested procedure) is returned
    by the archive MWL SCP with correct values."""
    host, port = live_archive
    # mwl_sync worker interval is 10s; poll up to ~40s for the mirror.
    results = _cfind(host, port, mirrored_entry, max_attempts=13)
    assert results, 'C-FIND returned no entries for the mirrored accession'
    assert results[0].AccessionNumber == mirrored_entry
    steps = results[0].ScheduledProcedureStepSequence
    assert steps and steps[0].Modality == 'CT'
    assert steps[0].ScheduledProcedureStepDescription == 'PARITY TEST CT'


def test_cfind_does_not_return_cancelled(live_archive):
    """Negative: a cancelled ORM entry (order control `CA`) must not appear
    in the C-FIND result — QP flips status to cancelled, the mirror removes
    it from the archive worklist."""
    import asyncpg
    from config import load_config
    cfg = load_config()

    async def _seed_cancelled():
        conn = await asyncpg.connect(
            user=cfg['db_user'],
            password=cfg['db_password'],
            database=cfg['db_database'],
            host=cfg['db_host'],
            port=int(cfg['db_port']),
        )
        accession = f'PARITY-CA-{os.getpid()}'
        try:
            await conn.execute(
                """
                INSERT INTO worklist_entries
                    (accession_number, requested_procedure_desc, modality,
                     status, patient_id)
                VALUES ($1, $2, $3, $4, $5)
                """,
                accession, 'CANCELLED CT', 'CT', 'cancelled', 'PARITY-PAT-001',
            )
        finally:
            await conn.close()
        return accession

    accession = asyncio.run(_seed_cancelled())
    try:
        results = _cfind(live_archive[0], live_archive[1], accession)
    finally:
        import asyncpg
        async def _cleanup():
            conn = await asyncpg.connect(
                user=cfg['db_user'],
                password=cfg['db_password'],
                database=cfg['db_database'],
                host=cfg['db_host'],
                port=int(cfg['db_port']),
            )
            await conn.execute(
                'DELETE FROM worklist_entries WHERE accession_number = $1',
                accession,
            )
            await conn.close()
        asyncio.run(_cleanup())
    assert not results, (
        'cancelled worklist entry leaked into archive C-FIND result')