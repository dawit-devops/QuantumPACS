"""S3-10 — RIS patient CRUD API tests.

Spec §4.1 contract: POST /api/ris/patients (PATIENT_WRITE), GET search/
detail (PATIENT_READ), PUT update (PATIENT_WRITE), POST insurance
(PATIENT_WRITE), POST check-in (SCHEDULE_WRITE). The legacy /patients
endpoints (REGISTRATION_*) are untouched. FrontDesk repo is mocked.
"""

from unittest.mock import AsyncMock, patch

import pytest
from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.middleware import Middleware
from starlette.routing import Route
from starlette.testclient import TestClient

from api.auth import User
from api.validate import validation_exception_handler, _ValidationException
from tests.test_ris_orders import _FakeAuth, _http_exception


def _conn_ctx():
    conn = AsyncMock()
    conn.__aenter__ = AsyncMock(return_value=conn)
    conn.__aexit__ = AsyncMock(return_value=False)
    return conn


def _patient_row(patient_id='MRN-001'):
    return {
        'id': 1, 'patient_id': patient_id, 'name': 'Jane Doe',
        'birth_date': '1980-01-01', 'sex': 'F', 'meta': None, 'tenant_id': 'default',
    }


def _visit_row(visit_id=10, status='registered'):
    return {
        'id': visit_id, 'patient_id': 'MRN-001', 'visit_date': '2026-08-18',
        'destination_room': '', 'status': status, 'hl7_sync_status': 'pending',
    }


def _make_app(user=None):
    from api.frontdesk import (
        RisPatientsHandler, RisPatientsSearchHandler, RisPatientHandler,
        RisPatientInsuranceHandler, RisPatientCheckInHandler,
    )
    return Starlette(
        routes=[
            Route('/ris/patients', endpoint=RisPatientsHandler),
            Route('/ris/patients/search', endpoint=RisPatientsSearchHandler),
            Route('/ris/patients/{id}', endpoint=RisPatientHandler),
            Route('/ris/patients/{id}/insurance', endpoint=RisPatientInsuranceHandler),
            Route('/ris/patients/{id}/check-in', endpoint=RisPatientCheckInHandler),
        ],
        middleware=[Middleware(_FakeAuth, user=user)],
        exception_handlers={
            HTTPException: _http_exception,
            _ValidationException: validation_exception_handler,
        },
    )


@pytest.fixture
def frontdesk_patches():
    class AuditLogStub:
        instances = []

        def __init__(self, conn):
            self.log_event = AsyncMock()
            AuditLogStub.instances.append(self)

    patchers = [
        patch('api.frontdesk.get_conn'),
        patch('api.frontdesk.FrontDesk'),
        patch('api.frontdesk.AuditLog', new=AuditLogStub),
    ]
    started = [p.start() for p in patchers]
    yield {
        'get_conn': started[0],
        'FrontDesk': started[1],
        'audit': AuditLogStub,
    }
    for p in patchers:
        p.stop()


def _fd(frontdesk_patches):
    fd = AsyncMock()
    frontdesk_patches['FrontDesk'].return_value = fd
    return fd


class TestRisPatientRegistration:
    def test_post_creates_patient_with_dedup(self, frontdesk_patches):
        fd = _fd(frontdesk_patches)
        fd.find_patient_duplicate.return_value = None
        fd.create_patient.return_value = _patient_row()

        client = TestClient(_make_app(User({'id': 1, 'permissions': ['PATIENT_WRITE']})))
        resp = client.post('/ris/patients', json={
            'name': 'Jane Doe', 'birth_date': '1980-01-01', 'sex': 'F',
        })

        assert resp.status_code == 201
        assert resp.json()['data']['patient_id'] == 'MRN-001'
        fd.find_patient_duplicate.assert_awaited_once_with('Jane Doe', '1980-01-01')
        fd.create_patient.assert_awaited_once()
        frontdesk_patches['audit'].instances[0].log_event.assert_awaited_once()

    def test_post_captures_phone_and_email(self, frontdesk_patches):
        # S8 (P-01): registration must pass the patient's contact fields
        # through to persistence for the portal profile.
        fd = _fd(frontdesk_patches)
        fd.find_patient_duplicate.return_value = None
        fd.create_patient.return_value = _patient_row()

        client = TestClient(_make_app(User({'id': 1, 'permissions': ['PATIENT_WRITE']})))
        resp = client.post('/ris/patients', json={
            'name': 'Jane Doe', 'birth_date': '1980-01-01', 'sex': 'F',
            'phone': '(555) 123-4567', 'email': 'jane@example.com',
        })

        assert resp.status_code == 201, resp.text
        kwargs = fd.create_patient.call_args.args[0]
        assert kwargs['phone'] == '(555) 123-4567'
        assert kwargs['email'] == 'jane@example.com'

    def test_post_returns_409_on_duplicate(self, frontdesk_patches):
        fd = _fd(frontdesk_patches)
        fd.find_patient_duplicate.return_value = _patient_row()

        client = TestClient(_make_app(User({'id': 1, 'permissions': ['PATIENT_WRITE']})))
        resp = client.post('/ris/patients', json={'name': 'Jane Doe', 'birth_date': '1980-01-01'})

        assert resp.status_code == 409
        assert resp.json()['error']['code'] == 'PATIENT_EXISTS'
        fd.create_patient.assert_not_awaited()

    def test_post_requires_patient_write(self, frontdesk_patches):
        client = TestClient(_make_app(User({'id': 1, 'permissions': []})))
        resp = client.post('/ris/patients', json={'name': 'Jane Doe'})
        assert resp.status_code == 403


class TestRisPatientSearch:
    def test_search_returns_matches(self, frontdesk_patches):
        fd = _fd(frontdesk_patches)
        fd.search_patients.return_value = [_patient_row()]

        client = TestClient(_make_app(User({'id': 1, 'permissions': ['PATIENT_READ']})))
        resp = client.get('/ris/patients/search?q=jane')

        assert resp.status_code == 200
        assert resp.json()['data'][0]['name'] == 'Jane Doe'
        fd.search_patients.assert_awaited_once_with('jane', dob='', phone='')

    def test_search_short_query_returns_empty(self, frontdesk_patches):
        fd = _fd(frontdesk_patches)
        client = TestClient(_make_app(User({'id': 1, 'permissions': ['PATIENT_READ']})))
        resp = client.get('/ris/patients/search?q=j')
        assert resp.status_code == 200
        assert resp.json()['data'] == []
        fd.search_patients.assert_not_awaited()

    def test_search_by_dob(self, frontdesk_patches):
        # FD-07: quick search supports DOB (full or partial, e.g. '1980').
        fd = _fd(frontdesk_patches)
        fd.search_patients.return_value = [_patient_row()]

        client = TestClient(_make_app(User({'id': 1, 'permissions': ['PATIENT_READ']})))
        resp = client.get('/ris/patients/search?dob=1980')

        assert resp.status_code == 200
        fd.search_patients.assert_awaited_once_with('', dob='1980', phone='')

    def test_search_by_phone(self, frontdesk_patches):
        # FD-07: quick search supports phone.
        fd = _fd(frontdesk_patches)
        fd.search_patients.return_value = [_patient_row()]

        client = TestClient(_make_app(User({'id': 1, 'permissions': ['PATIENT_READ']})))
        resp = client.get('/ris/patients/search?phone=555')

        assert resp.status_code == 200
        fd.search_patients.assert_awaited_once_with('', dob='', phone='555')


class TestRisPatientDetail:
    def test_get_patient(self, frontdesk_patches):
        fd = _fd(frontdesk_patches)
        fd.get_patient.return_value = _patient_row()

        client = TestClient(_make_app(User({'id': 1, 'permissions': ['PATIENT_READ']})))
        resp = client.get('/ris/patients/MRN-001')

        assert resp.status_code == 200
        assert resp.json()['data']['name'] == 'Jane Doe'
        fd.get_patient.assert_awaited_once_with('MRN-001')

    def test_get_unknown_patient_404(self, frontdesk_patches):
        fd = _fd(frontdesk_patches)
        fd.get_patient.return_value = None

        client = TestClient(_make_app(User({'id': 1, 'permissions': ['PATIENT_READ']})))
        resp = client.get('/ris/patients/NOPE')
        assert resp.status_code == 404

    def test_get_requires_patient_read(self, frontdesk_patches):
        client = TestClient(_make_app(User({'id': 1, 'permissions': []})))
        resp = client.get('/ris/patients/MRN-001')
        assert resp.status_code == 403


class TestRisPatientUpdate:
    def test_put_updates_patient(self, frontdesk_patches):
        fd = _fd(frontdesk_patches)
        fd.get_patient.return_value = _patient_row()
        updated = _patient_row()
        updated['name'] = 'Jane Q Doe'
        fd.get_patient.side_effect = [_patient_row(), updated]

        client = TestClient(_make_app(User({'id': 1, 'permissions': ['PATIENT_WRITE']})))
        resp = client.put('/ris/patients/MRN-001', json={'name': 'Jane Q Doe'})

        assert resp.status_code == 200
        assert resp.json()['data']['name'] == 'Jane Q Doe'
        fd.update_patient.assert_awaited_once_with('MRN-001', {'name': 'Jane Q Doe'})
        frontdesk_patches['audit'].instances[0].log_event.assert_awaited_once()

    def test_put_unknown_patient_404(self, frontdesk_patches):
        fd = _fd(frontdesk_patches)
        fd.get_patient.return_value = None

        client = TestClient(_make_app(User({'id': 1, 'permissions': ['PATIENT_WRITE']})))
        resp = client.put('/ris/patients/NOPE', json={'name': 'X'})
        assert resp.status_code == 404
        fd.update_patient.assert_not_awaited()

    def test_put_requires_patient_write(self, frontdesk_patches):
        client = TestClient(_make_app(User({'id': 1, 'permissions': ['PATIENT_READ']})))
        resp = client.put('/ris/patients/MRN-001', json={'name': 'X'})
        assert resp.status_code == 403


class TestRisPatientInsurance:
    def test_post_insurance(self, frontdesk_patches):
        fd = _fd(frontdesk_patches)
        fd.get_patient.return_value = _patient_row()
        fd.create_insurance.return_value = {
            'id': 5, 'patient_id': 'MRN-001', 'policy_number': 'POL-1',
            'guarantor_name': '', 'authorization_status': 'none',
            'authorization_number': '', 'notes': '', 'created_by': '1',
        }

        client = TestClient(_make_app(User({'id': 1, 'permissions': ['PATIENT_WRITE']})))
        resp = client.post('/ris/patients/MRN-001/insurance', json={'policy_number': 'POL-1'})

        assert resp.status_code == 201
        assert resp.json()['data']['policy_number'] == 'POL-1'
        fd.create_insurance.assert_awaited_once()

    def test_post_insurance_captures_coverage_fields(self, frontdesk_patches):
        # FD-02: the POST schema accepts provider/member_id/copay/deductible
        # so the eligibility endpoint can return real coverage data.
        fd = _fd(frontdesk_patches)
        fd.get_patient.return_value = _patient_row()
        fd.create_insurance.return_value = {
            'id': 5, 'patient_id': 'MRN-001', 'policy_number': 'POL-1',
            'provider': 'Aetna', 'member_id': 'M-123',
            'copay_amount': 25.0, 'deductible_total': 500.0,
            'deductible_remaining': 500.0,
            'guarantor_name': '', 'authorization_status': 'none',
            'authorization_number': '', 'notes': '', 'created_by': '1',
        }

        client = TestClient(_make_app(User({'id': 1, 'permissions': ['PATIENT_WRITE']})))
        resp = client.post('/ris/patients/MRN-001/insurance', json={
            'policy_number': 'POL-1',
            'provider': 'Aetna',
            'member_id': 'M-123',
            'copay_amount': 25.0,
            'deductible_total': 500.0,
        })

        assert resp.status_code == 201
        data = resp.json()['data']
        assert data['provider'] == 'Aetna'
        assert data['member_id'] == 'M-123'
        assert data['copay_amount'] == 25.0
        assert data['deductible_total'] == 500.0
        fd.create_insurance.assert_awaited_once()


class TestRisPatientCheckIn:
    def test_check_in_moves_open_visit(self, frontdesk_patches):
        fd = _fd(frontdesk_patches)
        fd.get_patient.return_value = _patient_row()
        fd.find_open_visit.return_value = _visit_row()

        client = TestClient(_make_app(User({'id': 1, 'permissions': ['SCHEDULE_WRITE']})))
        resp = client.post('/ris/patients/MRN-001/check-in')

        assert resp.status_code == 200
        assert resp.json()['data']['status'] == 'checked_in'
        fd.update_visit.assert_awaited_once_with(10, {'status': 'checked_in'})
        frontdesk_patches['audit'].instances[0].log_event.assert_awaited_once()

    def test_check_in_no_open_visit_409(self, frontdesk_patches):
        fd = _fd(frontdesk_patches)
        fd.get_patient.return_value = _patient_row()
        fd.find_open_visit.return_value = None

        client = TestClient(_make_app(User({'id': 1, 'permissions': ['SCHEDULE_WRITE']})))
        resp = client.post('/ris/patients/MRN-001/check-in')

        assert resp.status_code == 409
        assert resp.json()['error']['code'] == 'NO_OPEN_VISIT'
        fd.update_visit.assert_not_awaited()

    def test_check_in_unknown_patient_404(self, frontdesk_patches):
        fd = _fd(frontdesk_patches)
        fd.get_patient.return_value = None

        client = TestClient(_make_app(User({'id': 1, 'permissions': ['SCHEDULE_WRITE']})))
        resp = client.post('/ris/patients/NOPE/check-in')
        assert resp.status_code == 404

    def test_check_in_requires_schedule_write(self, frontdesk_patches):
        client = TestClient(_make_app(User({'id': 1, 'permissions': ['PATIENT_WRITE']})))
        resp = client.post('/ris/patients/MRN-001/check-in')
        assert resp.status_code == 403


if __name__ == '__main__':
    pytest.main([__file__, '-v'])