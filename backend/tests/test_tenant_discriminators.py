"""G-2 regression tests: clinical-table writes must carry tenant_id.

Without a per-row tenant discriminator only `files` was tenant-scoped; the
clinical tables (patients/studies/series/exams/worklist_entries/...) had no
tenant tag. These tests assert every insert path emits a `tenant_id` column
so the tenant slug is persisted on every new row.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from db.patient import Patient
from db.study import Study
from db.series import Series
from db.worklist import Worklist
from db.exams import (
    Exams, Acquisitions, SafetyChecks, Incidents, ProtocolOverrides,
)
from db.frontdesk import FrontDesk
from db.table import Table


def _capturing_conn():
    conn = MagicMock()
    conn.fetchrow = AsyncMock(return_value=None)
    conn.fetch = AsyncMock(return_value=[])
    return conn


def _run_insert(cls, method, *args):
    captured = {}

    async def fake_fetch(self, q, *a, **k):
        captured['sql'] = q.get_sql()
        return MagicMock()

    with patch.object(Table, 'fetchval', fake_fetch), \
         patch.object(Table, 'fetchone', fake_fetch):
        inst = cls(_capturing_conn())
        asyncio.run(getattr(inst, method)(*args))
    return captured.get('sql', '')


PATIENT = {'patient_id': 'P1', 'patient_name': 'N', 'patient_birth_date': '',
           'patient_sex': ''}
STUDY = {'patient_db_id': 1, 'study_id': 'S1', 'study_description': '',
         'study_instance_uid': '', 'accession_number': '', 'study_date': '',
         'referring_physician': '', 'performing_physician': ''}
SERIES = {'study_db_id': 1, 'series_number': '1', 'modality': 'CT',
          'series_description': '', 'series_instance_uid': ''}
WORKLIST = {'patient_id': 'P1', 'patient_name': 'N', 'patient_birth_date': '',
            'patient_sex': '', 'accession_number': '', 'requested_procedure_id': '',
            'requested_procedure_desc': '', 'requested_procedure_priority': '',
            'reason_for_requested_procedure': '', 'requested_procedure_code': '',
            'requested_procedure_code_meaning': '', 'requested_procedure_code_scheme': '',
            'scheduled_procedure_step_id': '', 'protocol_name': '',
            'requesting_physician': '', 'referring_physician': '',
            'scheduled_station_name': '', 'scheduled_performing_physician': '',
            'scheduled_date': None, 'scheduled_time': None, 'modality': 'CT',
            'station_ae_title': '', 'created_by': ''}
EXAM = {'patient_id': 'P1', 'patient_name': 'N', 'patient_birth_date': '',
        'patient_sex': '', 'accession_number': '', 'requested_procedure_desc': '',
        'modality': 'CT', 'station_ae_title': '', 'protocol_name': '',
        'assigned_technologist': '', 'assigned_radiologist': '',
        'referring_physician': '', 'created_by': ''}


class TestClinicalInsertsTagTenant:
    def test_patient_insert_tags_tenant(self):
        assert 'tenant_id' in _run_insert(Patient, 'insert_or_select', PATIENT)

    def test_study_insert_tags_tenant(self):
        assert 'tenant_id' in _run_insert(Study, 'insert_or_select', STUDY)

    def test_series_insert_tags_tenant(self):
        assert 'tenant_id' in _run_insert(Series, 'insert_or_select', SERIES)

    def test_worklist_insert_tags_tenant(self):
        assert 'tenant_id' in _run_insert(Worklist, 'create', WORKLIST)

    def test_exams_insert_tags_tenant(self):
        assert 'tenant_id' in _run_insert(Exams, 'create', EXAM)

    def test_acquisitions_insert_tags_tenant(self):
        data = {'exam_id': 'e1', 'series_number': 1, 'instance_uid': '',
                'description': '', 'kvp': 0, 'mas': 0, 'dlp': 0, 'ctdivol': 0,
                'exposure_time': 0, 'status': 'pending'}
        assert 'tenant_id' in _run_insert(Acquisitions, 'create', data)

    def test_safety_checks_insert_tags_tenant(self):
        data = {'exam_id': 'e1', 'check_item': 'x', 'answer': 'y',
                'notes': '', 'checked_by': ''}
        assert 'tenant_id' in _run_insert(SafetyChecks, 'create', data)

    def test_incidents_insert_tags_tenant(self):
        data = {'exam_id': 'e1', 'incident_type': 't', 'severity': 'low',
                'description': 'd', 'reported_by': ''}
        assert 'tenant_id' in _run_insert(Incidents, 'create', data)

    def test_protocol_overrides_insert_tags_tenant(self):
        data = {'exam_id': 'e1', 'justification': 'j', 'original_params': {},
                'overridden_params': {}, 'overridden_by': ''}
        assert 'tenant_id' in _run_insert(ProtocolOverrides, 'create', data)

    def test_frontdesk_create_patient_tags_tenant(self):
        data = {'patient_id': 'P1', 'name': 'N', 'birth_date': '', 'sex': '',
                'meta': None}
        captured = {}

        async def fake_fetchrow(q, *a, **k):
            captured['sql'] = q
            return None

        fd = FrontDesk(_capturing_conn())
        fd.conn.fetchrow = fake_fetchrow
        with patch('db.frontdesk.get_tenant_slug', return_value='default'):
            asyncio.run(fd.create_patient(data))
        assert 'tenant_id' in captured['sql']

    def test_frontdesk_create_worklist_tags_tenant(self):
        data = {'patient_id': 'P1', 'patient_name': 'N', 'patient_birth_date': '',
                'patient_sex': '', 'scheduled_date': '2026-01-01',
                'scheduled_time': '10:00', 'modality': 'CT',
                'station_ae_title': '', 'created_by': ''}
        captured = {}

        async def fake_fetchval(q, *a, **k):
            captured['sql'] = q
            return None

        fd = FrontDesk(_capturing_conn())
        fd.conn.fetchval = fake_fetchval
        with patch('db.frontdesk.get_tenant_slug', return_value='default'):
            asyncio.run(fd.create_worklist_entry(data))
        assert 'tenant_id' in captured['sql']
