"""S6-04 / S6-10 — MWL + MPPS conformance test sets.

The HL7 side has a parse-rate conformance gate (test_hl7_conformance);
the DICOM wire had only behavioral tests until now. These suites assert
the *attribute contract* modalities depend on:

MWL C-FIND responses (PS3.4 UW-RS + PS3.3 CIOD):
  - top-level identifiers (accession, patient name/id, study UID,
    requested procedure ID)
  - SPS sequence content (modality, station AE, start date/time in DICOM
    format, SPS ID, SPS status from the standard vocabulary)
  - file_meta SOP class/instance validity

MPPS events:
  - the standard status vocabulary (IN_PROGRESS / COMPLETED /
    DISCONTINUED) maps onto worklist states without gaps
  - every processed event persists the full audit tuple

Acceptance mirrors HL7's: >= 95% of corpus entries conform.
"""

import re
import uuid

import pytest

from pynetdicom.sop_class import ModalityWorklistInformationFind
from pydicom.dataset import Dataset


MIN_CONFORMANCE_RATE = 0.95

_UID_RE = re.compile(r'^[0-9.]{1,64}$')
_DATE_RE = re.compile(r'^\d{8}$')
_TIME_RE = re.compile(r'^\d{6}$')

# Required top-level attributes on every MWL response item.
_REQUIRED_TOP_LEVEL = [
    'AccessionNumber', 'PatientName', 'PatientID',
    'StudyInstanceUID', 'RequestedProcedureID',
]

# Required attributes inside ScheduledProcedureStepSequence[0].
_REQUIRED_SPS = [
    'Modality', 'ScheduledStationAETitle',
    'ScheduledProcedureStepStartDate', 'ScheduledProcedureStepStartTime',
    'ScheduledProcedureStepID', 'ScheduledProcedureStepStatus',
]

_VALID_SPS_STATUS = {'SCHEDULED', 'ARRIVED', 'STARTED', 'COMPLETED', 'CANCELLED'}


def _entry(**overrides):
    base = {
        'id': uuid.uuid4(),
        'accession_number': 'ACC-CONF-1',
        'patient_name': 'Conf^Test',
        'patient_id': 'PID-CONF-1',
        'patient_birth_date': None,
        'patient_sex': '',
        'referring_physician': '',
        'study_uid': '1.2.840.113619.2.1.1',
        'requested_procedure_id': 'RP-1',
        'requested_procedure_desc': 'CT Chest',
        'requested_procedure_priority': 'ROUTINE',
        'requested_procedure_code': None,
        'requested_procedure_code_scheme': None,
        'requested_procedure_code_meaning': None,
        'modality': 'CT',
        'station_ae_title': 'CT_SCANNER',
        'scheduled_station_name': '',
        'scheduled_date': '2026-08-22',
        'scheduled_time': '09:30:00',
        'scheduled_performing_physician': '',
        'scheduled_procedure_step_id': 'SPS-1',
        'protocol_name': '',
        'reason_for_requested_procedure': '',
        'status': 'scheduled',
    }
    base.update(overrides)
    return base


def _mwl_conformance_errors(ds):
    """Return a list of contract violations for one response dataset."""
    errors = []
    for attr in _REQUIRED_TOP_LEVEL:
        val = getattr(ds, attr, None)
        if val is None or val == '':
            errors.append(f'missing top-level {attr}')
    if getattr(ds, 'StudyInstanceUID', '') and not _UID_RE.match(
            str(ds.StudyInstanceUID)):
        errors.append('StudyInstanceUID is not a valid UID')
    sps_items = getattr(ds, 'ScheduledProcedureStepSequence', [])
    if not sps_items:
        errors.append('missing ScheduledProcedureStepSequence')
        return errors
    sps = sps_items[0]
    for attr in _REQUIRED_SPS:
        val = getattr(sps, attr, None)
        if val is None or val == '':
            errors.append(f'missing SPS {attr}')
    if not _DATE_RE.match(str(getattr(sps, 'ScheduledProcedureStepStartDate', ''))):
        errors.append('SPS start date not YYYYMMDD')
    if not _TIME_RE.match(str(getattr(sps, 'ScheduledProcedureStepStartTime', ''))):
        errors.append('SPS start time not HHMMSS')
    if str(getattr(sps, 'ScheduledProcedureStepStatus', '')) not in _VALID_SPS_STATUS:
        errors.append('SPS status outside standard vocabulary')
    fm = ds.file_meta
    if str(fm.MediaStorageSOPClassUID) != str(ModalityWorklistInformationFind):
        errors.append('file_meta SOP class is not MWL find')
    if not _UID_RE.match(str(fm.MediaStorageSOPInstanceUID)):
        errors.append('file_meta SOP instance UID invalid')
    return errors


class TestMwlConformance:
    """S6-04 — attribute contract of MWL C-FIND responses."""

    @pytest.mark.parametrize('overrides', [
        {},
        {'status': 'arrived'},
        {'status': 'in_progress'},
        {'status': 'performed'},
        {'status': 'cancelled'},
        {'priority_field': None},   # extra keys ignored
        {'patient_sex': 'F'},
        {'requested_procedure_code': '71550', 'requested_procedure_code_scheme': '99SDM',
         'requested_procedure_code_meaning': 'CT chest w/o contrast'},
    ])
    def test_entry_conforms(self, overrides):
        overrides.pop('priority_field', None)
        from dcm.server import _entry_to_dataset
        ds = _entry_to_dataset(_entry(**overrides))
        errors = _mwl_conformance_errors(ds)
        assert not errors, f'conformance violations: {errors}'

    def test_corpus_pass_rate_at_least_95_percent(self):
        from dcm.server import _entry_to_dataset
        corpus = [_entry(accession_number=f'ACC-{i}', patient_id=f'P-{i}')
                  for i in range(20)]
        # One deliberately degraded entry (empty dates) must still keep the
        # corpus above the acceptance floor.
        corpus.append(_entry(scheduled_date='', scheduled_time=''))
        conformant = sum(
            1 for e in corpus if not _mwl_conformance_errors(
                _entry_to_dataset(e)))
        rate = conformant / len(corpus)
        assert rate >= MIN_CONFORMANCE_RATE, (
            f'MWL conformance {rate:.0%} below {MIN_CONFORMANCE_RATE:.0%}')

    def test_empty_dates_are_reported_not_crashed(self):
        from dcm.server import _entry_to_dataset
        ds = _entry_to_dataset(_entry(scheduled_date='', scheduled_time=''))
        errors = _mwl_conformance_errors(ds)
        # The degraded entry violates exactly the two format rules.
        assert any('start date' in e for e in errors)
        assert any('start time' in e for e in errors)


from services.mpps_consumer.service import (
    MPPS_TO_WORKLIST_STATUS,
    _record_event,
)


class TestMppsConformance:
    """S6-10 — status vocabulary coverage + persisted audit tuple."""

    def test_standard_status_vocabulary_covered(self):
        # PS3.7 MPPS statuses must all map to a worklist state.
        assert set(MPPS_TO_WORKLIST_STATUS) == {
            'IN_PROGRESS', 'COMPLETED', 'DISCONTINUED'}

    @pytest.mark.asyncio
    async def test_event_persists_required_tuple(self):
        conn_calls = []

        class _Conn:
            async def execute(self, sql, *args):
                conn_calls.append((sql, args))

        ds = Dataset()
        ds.AccessionNumber = 'ACC-MPPS-1'
        rows = await _record_event(
            _Conn(), 'ACC-MPPS-1', 'N_CREATE', 'IN_PROGRESS',
            '1.2.3.4', 'CT_SCANNER', ds,
        )
        assert rows is None  # fire-and-forget insert
        sql, args = conn_calls[0]
        assert 'INSERT INTO ris_mpps_events' in sql
        assert 'raw_message' in sql
        # accession, event, status, study uid, station ae, raw, tenant, ts
        assert args[0] == 'ACC-MPPS-1'
        assert args[1] == 'N_CREATE'
        assert args[2] == 'IN_PROGRESS'
        assert args[3] == '1.2.3.4'
        assert args[4] == 'CT_SCANNER'

    @pytest.mark.asyncio
    async def test_raw_message_serializes_standard_attrs(self):
        captured = {}

        class _Conn:
            async def execute(self, sql, *args):
                captured['args'] = args

        ds = Dataset()
        ds.AccessionNumber = 'ACC-MPPS-2'
        await _record_event(
            _Conn(), 'ACC-MPPS-2', 'N_SET', 'COMPLETED',
            '1.2.3.5', 'MR_1', ds,
        )
        import json
        raw = json.loads(captured['args'][5])
        assert raw.get('AccessionNumber') == 'ACC-MPPS-2'
