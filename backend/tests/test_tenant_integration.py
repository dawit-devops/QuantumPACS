"""Integration test: clinical inserts persist tenant_id on a live database.

Complements the mocked unit tests in test_tenant_discriminators.py (G-2).
Here we exercise the *real* model insert paths against the actual schema
(migration 057) and assert that tenant_id is really written to disk — not
just emitted in a SQL string.

All inserts run inside one explicit transaction that is rolled back, so the
dev database is never polluted (the pooled connection's auto-reset cannot be
relied on to discard the implicit transaction).
"""
import asyncio
import uuid

import pytest

from db.conn import (get_conn, reset_tenant_slug, set_tenant_slug, setup,
                     teardown)
from db.exams import (Acquisitions, Exams, Incidents, ProtocolOverrides,
                      SafetyChecks)
from db.patient import Patient
from db.series import Series
from db.study import Study
from db.worklist import Worklist

SLUG = 'itest-tenant'


def _u():
    return uuid.uuid4().hex[:10]


def test_clinical_inserts_persist_tenant_id():
    async def run():
        try:
            await setup()
        except Exception as e:  # pragma: no cover - environmental
            pytest.skip(f'dev database unavailable: {e}')

        try:
            async with get_conn() as conn:
                # One explicit transaction, rolled back at the end, guarantees
                # the dev DB is left untouched regardless of pool reset.
                tx = conn.transaction()
                await tx.start()
                try:
                    tag = _u()
                    checks = []

                    set_tenant_slug(SLUG)

                    pid = (await Patient(conn).insert_or_select({
                        'patient_id': f'ITEST-P-{tag}', 'patient_name': 'IT',
                        'patient_birth_date': '', 'patient_sex': 'O',
                    }))['id']
                    checks.append(('patients', pid))

                    sid = (await Study(conn).insert_or_select({
                        'patient_db_id': pid, 'study_id': f'ITEST-S-{tag}',
                        'study_description': '',
                        'study_instance_uid': f'1.2.3.{tag}.s',
                        'accession_number': f'A-{tag}-s', 'study_date': '',
                        'referring_physician': '', 'performing_physician': '',
                    }))['id']
                    checks.append(('studies', sid))

                    serid = (await Series(conn).insert_or_select({
                        'study_db_id': sid, 'series_number': '1',
                        'modality': 'CT', 'series_description': '',
                        'series_instance_uid': f'1.2.3.{tag}.se',
                    }))['id']
                    checks.append(('series', serid))

                    wl_id = (await Worklist(conn).create({
                        'patient_id': f'ITEST-P-{tag}', 'patient_name': 'IT',
                        'patient_birth_date': '', 'patient_sex': 'O',
                        'accession_number': f'A-{tag}-wl', 'modality': 'CT',
                        'scheduled_date': None, 'scheduled_time': None,
                        'station_ae_title': '', 'created_by': '',
                    }))['id']
                    checks.append(('worklist_entries', wl_id))

                    exam_id = (await Exams(conn).create({
                        'patient_id': f'ITEST-P-{tag}', 'patient_name': 'IT',
                        'patient_birth_date': '', 'patient_sex': 'O',
                        'accession_number': f'A-{tag}-ex', 'modality': 'CT',
                        'station_ae_title': '', 'protocol_name': '',
                        'assigned_technologist': '', 'assigned_radiologist': '',
                        'referring_physician': '', 'created_by': '',
                    }))['id']
                    checks.append(('exams', exam_id))

                    acq_id = (await Acquisitions(conn).create({
                        'exam_id': exam_id, 'series_number': 1,
                        'instance_uid': f'1.2.3.{tag}.ac', 'description': '',
                        'kvp': 0, 'mas': 0, 'dlp': 0, 'ctdivol': 0,
                        'exposure_time': 0, 'status': 'pending',
                    }))['id']
                    checks.append(('acquisitions', acq_id))

                    sc_id = (await SafetyChecks(conn).create({
                        'exam_id': exam_id, 'check_item': f'it-{tag}',
                        'answer': 'y', 'notes': '', 'checked_by': '',
                    }))['id']
                    checks.append(('safety_checks', sc_id))

                    inc_id = (await Incidents(conn).create({
                        'exam_id': exam_id, 'incident_type': 't',
                        'severity': 'low', 'description': 'd',
                        'reported_by': '',
                    }))['id']
                    checks.append(('incidents', inc_id))

                    po_id = (await ProtocolOverrides(conn).create({
                        'exam_id': exam_id, 'justification': 'j',
                        'original_params': {}, 'overridden_params': {},
                        'overridden_by': '',
                    }))['id']
                    checks.append(('protocol_overrides', po_id))

                    # Behavior-level assertion: tenant_id is actually persisted.
                    for table, rid in checks:
                        got = await conn.fetchval(
                            f'SELECT tenant_id FROM {table} WHERE id=$1', rid)
                        assert got == SLUG, (
                            f'{table}#{rid} persisted tenant_id={got!r}, '
                            f'expected {SLUG!r}')

                    # Un-scoped (default platform) path tags the 'default'
                    # tenant.
                    reset_tenant_slug()
                    pid2 = (await Patient(conn).insert_or_select({
                        'patient_id': f'ITEST-D-{tag}', 'patient_name': 'IT',
                        'patient_birth_date': '', 'patient_sex': 'O',
                    }))['id']
                    got = await conn.fetchval(
                        'SELECT tenant_id FROM patients WHERE id=$1', pid2)
                    assert got == 'default', (
                        f'default-path persisted tenant_id={got!r}, '
                        f"expected 'default'")
                finally:
                    await tx.rollback()
        finally:
            await teardown()
            reset_tenant_slug()

    asyncio.run(run())
