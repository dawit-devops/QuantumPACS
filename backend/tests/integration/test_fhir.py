from unittest.mock import AsyncMock, MagicMock, patch

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.routing import Route
from starlette.testclient import TestClient

from api.auth import User
from api.fhir import (
    FhirMetadata,
    FhirPatientRoot, FhirPatientResource,
    FhirImagingStudyRead, FhirImagingStudySearch,
    FhirDocumentReferenceRead, FhirDocumentReferenceSearch,
)


class _FakeAuth(BaseHTTPMiddleware):
    def __init__(self, app, user=None):
        super().__init__(app)
        self._user = user or User({'id': 1, 'permissions': ['PATIENT_READ', 'DICOMWEB_READ', 'FILE_READ']})

    async def dispatch(self, request, call_next):
        request.scope['user'] = self._user
        request.scope['auth'] = None
        return await call_next(request)


def _make_app(user=None, extra_routes=None):
    routes = [
        Route('/fhir/metadata', endpoint=FhirMetadata),
        Route('/fhir/Patient', endpoint=FhirPatientRoot),
        Route('/fhir/Patient/{id}', endpoint=FhirPatientResource),
        Route('/fhir/ImagingStudy', endpoint=FhirImagingStudySearch),
        Route('/fhir/ImagingStudy/{id}', endpoint=FhirImagingStudyRead),
        Route('/fhir/DocumentReference', endpoint=FhirDocumentReferenceSearch),
        Route('/fhir/DocumentReference/{id}', endpoint=FhirDocumentReferenceRead),
    ]
    if extra_routes:
        routes.extend(extra_routes)
    return Starlette(
        routes=routes,
        middleware=[Middleware(_FakeAuth, user=user)],
    )





class TestFhirMetadata:
    def test_capability_statement(self):
        client = TestClient(_make_app())
        resp = client.get('/fhir/metadata')
        assert resp.status_code == 200
        assert resp.headers['content-type'] == 'application/fhir+json'
        body = resp.json()
        assert body['resourceType'] == 'CapabilityStatement'
        assert body['fhirVersion'] == '4.0.1'
        rest = body['rest'][0]
        types = {r['type'] for r in rest['resource']}
        assert types == {'Patient', 'ImagingStudy', 'DocumentReference'}


class TestFhirPatient:
    def test_read_patient_found(self):
        mock_conn = MagicMock()
        mock_conn.fetchval = AsyncMock(return_value=1)
        mock_conn.fetchrow = AsyncMock(return_value={
            'id': 1, 'patient_id': 'PID001', 'name': 'Smith^John',
            'birth_date': '19800101', 'sex': 'M', 'meta': None,
            'updated_at': None,
        })
        mock_conn.fetch = AsyncMock(return_value=[])

        with patch('api.fhir.get_conn') as mock_get:
            mock_get.return_value.__aenter__.return_value = mock_conn
            mock_get.return_value.__aexit__ = AsyncMock(return_value=None)

            client = TestClient(_make_app())
            resp = client.get('/fhir/Patient/PID001')

        assert resp.status_code == 200
        body = resp.json()
        assert body['resourceType'] == 'Patient'
        assert body['id'] == 'PID001'
        assert body['identifier'][0]['value'] == 'PID001'
        assert body['gender'] == 'male'

    def test_read_patient_not_found(self):
        mock_conn = MagicMock()
        mock_conn.fetchval = AsyncMock(return_value=None)
        mock_conn.fetchrow = AsyncMock(return_value=None)

        with patch('api.fhir.get_conn') as mock_get:
            mock_get.return_value.__aenter__.return_value = mock_conn
            mock_get.return_value.__aexit__ = AsyncMock(return_value=None)

            client = TestClient(_make_app())
            resp = client.get('/fhir/Patient/NONEXISTENT')

        assert resp.status_code == 404
        assert resp.json()['resourceType'] == 'OperationOutcome'

    def test_search_patient_by_identifier(self):
        mock_conn = MagicMock()
        mock_conn.fetchval = AsyncMock(return_value=1)
        mock_conn.fetch = AsyncMock(return_value=[{
            'id': 1, 'patient_id': 'PID001', 'name': 'Smith^John',
            'birth_date': '19800101', 'sex': 'M', 'meta': None,
        }])

        with patch('api.fhir.get_conn') as mock_get:
            mock_get.return_value.__aenter__.return_value = mock_conn
            mock_get.return_value.__aexit__ = AsyncMock(return_value=None)

            client = TestClient(_make_app())
            resp = client.get('/fhir/Patient?identifier=PID001')

        assert resp.status_code == 200
        bundle = resp.json()
        assert bundle['resourceType'] == 'Bundle'
        assert bundle['total'] == 1
        assert bundle['entry'][0]['resource']['id'] == 'PID001'

    def test_search_patient_by_name(self):
        mock_conn = MagicMock()
        mock_conn.fetchval = AsyncMock(return_value=1)
        mock_conn.fetch = AsyncMock(return_value=[{
            'id': 2, 'patient_id': 'PID002', 'name': 'Doe^Jane',
            'birth_date': '19900215', 'sex': 'F', 'meta': None,
        }])

        with patch('api.fhir.get_conn') as mock_get:
            mock_get.return_value.__aenter__.return_value = mock_conn
            mock_get.return_value.__aexit__ = AsyncMock(return_value=None)

            client = TestClient(_make_app())
            resp = client.get('/fhir/Patient?name=Doe')

        assert resp.status_code == 200
        bundle = resp.json()
        assert bundle['total'] == 1

    def test_search_patient_empty(self):
        mock_conn = MagicMock()
        mock_conn.fetchval = AsyncMock(return_value=0)
        mock_conn.fetch = AsyncMock(return_value=[])

        with patch('api.fhir.get_conn') as mock_get:
            mock_get.return_value.__aenter__.return_value = mock_conn
            mock_get.return_value.__aexit__ = AsyncMock(return_value=None)

            client = TestClient(_make_app())
            resp = client.get('/fhir/Patient?identifier=UNKNOWN')

        assert resp.status_code == 200
        bundle = resp.json()
        assert bundle['total'] == 0


def _study_row():
    return {
        'id': 1, 'study_id': 'STU001', 'study_instance_uid': '1.2.3.4.5',
        'patient_id': 1, 'description': 'Chest CT', 'accession_number': 'ACC001',
    }


class TestFhirImagingStudyEndpoint:
    async def test_imaging_study_includes_endpoint(self):
        from api.fhir import _imagingstudy_resource
        study = {
            'study_id': 'STU001', 'study_instance_uid': '1.2.3.4.5',
            'patient_id': 1, 'description': 'Chest CT',
            'accession_number': 'ACC001', '_patient_logical_id': 'PID001',
            '_series': [],
        }
        resource = await _imagingstudy_resource(study)
        assert 'endpoint' in resource
        assert len(resource['endpoint']) > 0
        assert 'dicomweb' in resource['endpoint'][0]['reference']

    async def test_series_includes_endpoint_local_mode(self):
        # P4.4: every nested series must carry an endpoint (QP base in local
        # mode, archive WADO-RS base when dicom_proxy=true).
        from api.fhir import _imagingstudy_resource
        study = {
            'study_id': 'STU001', 'study_instance_uid': '1.2.3.4.5',
            'patient_id': 1, 'description': 'Chest CT',
            'accession_number': 'ACC001', '_patient_logical_id': 'PID001',
            '_series': [{
                'series_instance_uid': '1.2.3.4.5.6', 'number': '1',
                'modality': 'CT', 'description': 'Series 1',
            }],
        }
        with patch('api.fhir._get_fhir_base_url', AsyncMock(return_value='http://localhost:8080/api/fhir')):
            with patch('api.dicomweb_proxy.proxy_enabled', return_value=False):
                resource = await _imagingstudy_resource(study)
        assert resource['series'][0]['endpoint'] == [
            {'reference': 'http://localhost:8080/api/dicomweb'}]

    async def test_series_includes_archive_endpoint_proxy_mode(self):
        from api.fhir import _imagingstudy_resource
        study = {
            'study_id': 'STU001', 'study_instance_uid': '1.2.3.4.5',
            'patient_id': 1, 'description': 'Chest CT',
            'accession_number': 'ACC001', '_patient_logical_id': 'PID001',
            '_series': [{
                'series_instance_uid': '1.2.3.4.5.6', 'number': '1',
                'modality': 'CT',
            }],
        }
        with patch('api.fhir._get_fhir_base_url', AsyncMock(return_value='http://localhost:8080/api/fhir')):
            with patch('api.fhir.proxy_enabled', return_value=True):
                resource = await _imagingstudy_resource(study)
        assert resource['series'][0]['endpoint'] == [
            {'reference': 'http://localhost:8082/dcm4chee-arc/aets/DCM4CHEE/rs'}]


class TestFhirImagingStudy:
    def test_read_study_found(self):
        mock_conn = MagicMock()
        mock_conn.fetch = AsyncMock(return_value=[])
        mock_conn.fetchrow = AsyncMock(return_value=_study_row())

        with patch('api.fhir.get_conn') as mock_get:
            mock_get.return_value.__aenter__.return_value = mock_conn
            mock_get.return_value.__aexit__ = AsyncMock(return_value=None)

            with patch('api.fhir._fetch_series_for_study', AsyncMock(return_value=[])):
                with patch('api.fhir._patient_logical_id', AsyncMock(return_value='PID001')):
                    client = TestClient(_make_app())
                    resp = client.get('/fhir/ImagingStudy/1.2.3.4.5')

        assert resp.status_code == 200
        body = resp.json()
        assert body['resourceType'] == 'ImagingStudy'
        assert body['id'] == '1.2.3.4.5'
        assert 'Patient/PID001' in body['subject']['reference']

    def test_read_study_not_found(self):
        mock_conn = MagicMock()
        mock_conn.fetchrow = AsyncMock(return_value=None)

        with patch('api.fhir.get_conn') as mock_get:
            mock_get.return_value.__aenter__.return_value = mock_conn
            mock_get.return_value.__aexit__ = AsyncMock(return_value=None)

            client = TestClient(_make_app())
            resp = client.get('/fhir/ImagingStudy/UNKNOWN')

        assert resp.status_code == 404

    def test_search_study_by_patient(self):
        mock_conn = MagicMock()
        mock_conn.fetchval = AsyncMock(return_value=1)
        mock_conn.fetch = AsyncMock(return_value=[_study_row()])
        mock_conn.fetchrow = AsyncMock(return_value=_study_row())

        with patch('api.fhir.get_conn') as mock_get:
            mock_get.return_value.__aenter__.return_value = mock_conn
            mock_get.return_value.__aexit__ = AsyncMock(return_value=None)

            with patch('api.fhir._fetch_series_for_study', AsyncMock(return_value=[])):
                with patch('api.fhir._patient_logical_id', AsyncMock(return_value='PID001')):
                    client = TestClient(_make_app())
                    resp = client.get('/fhir/ImagingStudy?patient=PID001')

        assert resp.status_code == 200
        bundle = resp.json()
        assert bundle['resourceType'] == 'Bundle'
        assert bundle['total'] >= 1

    def test_search_study_by_accession(self):
        mock_conn = MagicMock()
        mock_conn.fetchval = AsyncMock(return_value=1)
        mock_conn.fetch = AsyncMock(return_value=[_study_row()])
        mock_conn.fetchrow = AsyncMock(return_value=_study_row())

        with patch('api.fhir.get_conn') as mock_get:
            mock_get.return_value.__aenter__.return_value = mock_conn
            mock_get.return_value.__aexit__ = AsyncMock(return_value=None)

            with patch('api.fhir._fetch_series_for_study', AsyncMock(return_value=[])):
                with patch('api.fhir._patient_logical_id', AsyncMock(return_value='PID001')):
                    client = TestClient(_make_app())
                    resp = client.get('/fhir/ImagingStudy?accession=ACC001')

        assert resp.status_code == 200
        bundle = resp.json()
        assert bundle['total'] >= 1


class TestFhirDocumentReference:
    def test_read_doc_found(self):
        mock_conn = MagicMock()
        mock_conn.fetchrow = AsyncMock(return_value={
            'id': 123, '_patient_logical_id': 'PID001',
            'share_url': 'http://example.com/share/abc',
            'created': '2026-07-26T00:00:00',
        })

        with patch('api.fhir.get_conn') as mock_get:
            mock_get.return_value.__aenter__.return_value = mock_conn
            mock_get.return_value.__aexit__ = AsyncMock(return_value=None)

            client = TestClient(_make_app())
            resp = client.get('/fhir/DocumentReference/123')

        assert resp.status_code == 200
        body = resp.json()
        assert body['resourceType'] == 'DocumentReference'
        assert body['id'] == '123'

    def test_read_doc_not_found(self):
        mock_conn = MagicMock()
        mock_conn.fetchrow = AsyncMock(return_value=None)

        with patch('api.fhir.get_conn') as mock_get:
            mock_get.return_value.__aenter__.return_value = mock_conn
            mock_get.return_value.__aexit__ = AsyncMock(return_value=None)

            client = TestClient(_make_app())
            resp = client.get('/fhir/DocumentReference/99999')

        assert resp.status_code == 404

    def test_search_doc_by_patient(self):
        mock_conn = MagicMock()
        mock_conn.fetchval = AsyncMock(return_value=1)
        mock_conn.fetch = AsyncMock(return_value=[{
            'id': 456, '_patient_logical_id': 'PID001',
            'share_url': 'http://example.com/share/xyz',
            'created': '2026-07-26T00:00:00',
        }])

        with patch('api.fhir.get_conn') as mock_get:
            mock_get.return_value.__aenter__.return_value = mock_conn
            mock_get.return_value.__aexit__ = AsyncMock(return_value=None)

            client = TestClient(_make_app())
            resp = client.get('/fhir/DocumentReference?patient=PID001')

        assert resp.status_code == 200
        bundle = resp.json()
        assert bundle['total'] >= 1
        assert bundle['entry'][0]['resource']['id'] == '456'


_WRITE_USER = User({'id': 1, 'permissions': ['PATIENT_READ', 'PATIENT_WRITE', 'DICOMWEB_READ', 'FILE_READ']})


class TestFhirPatientNameParsing:
    def test_patient_resource_splits_name_on_caret(self):
        from api.fhir import _patient_resource
        row = {
            'patient_id': 'PID001', 'name': 'Smith^John^Q^Jr',
            'birth_date': '19800101', 'sex': 'M', 'meta': None,
        }
        resource = _patient_resource(row)
        name = resource['name'][0]
        assert name['family'] == 'Smith'
        assert name['given'] == ['John']

    def test_patient_resource_no_caret_uses_full_as_family(self):
        from api.fhir import _patient_resource
        row = {
            'patient_id': 'PID002', 'name': 'SingleName',
            'birth_date': '19900215', 'sex': 'F', 'meta': None,
        }
        resource = _patient_resource(row)
        name = resource['name'][0]
        assert name['family'] == 'SingleName'
        assert name['given'] == []


class TestFhirPatientWrite:
    def test_create_patient_success(self):
        mock_conn = MagicMock()
        mock_conn.fetchval = AsyncMock(side_effect=[None, 42, 42])
        mock_conn.fetch = AsyncMock(return_value=[])
        mock_conn.fetchrow = AsyncMock(return_value={
            'id': 1, 'patient_id': 'PID-NEW', 'name': 'Smith^John',
            'birth_date': '19800101', 'sex': 'M', 'meta': None,
        })

        with patch('api.fhir.get_conn') as mock_get:
            mock_get.return_value.__aenter__.return_value = mock_conn
            mock_get.return_value.__aexit__ = AsyncMock(return_value=None)

            from api.fhir import FhirPatientRoot
            app = Starlette(
                routes=[Route('/fhir/Patient', endpoint=FhirPatientRoot)],
                middleware=[Middleware(_FakeAuth, user=_WRITE_USER)],
            )
            client = TestClient(app)
            resp = client.post('/fhir/Patient', json={
                'resourceType': 'Patient',
                'identifier': [{'value': 'PID-NEW'}],
                'name': [{'family': 'Smith', 'given': ['John']}],
                'birthDate': '1980-01-01',
                'gender': 'male',
            })

        assert resp.status_code == 201
        assert resp.headers['location'].endswith('/Patient/PID-NEW')
        body = resp.json()
        assert body['resourceType'] == 'Patient'
        assert body['id'] == 'PID-NEW'

    def test_create_patient_duplicate_returns_existing(self):
        mock_conn = MagicMock()
        mock_conn.fetchval = AsyncMock(side_effect=[42, 42])
        mock_conn.fetch = AsyncMock(return_value=[])
        mock_conn.fetchrow = AsyncMock(return_value={
            'id': 1, 'patient_id': 'PID-NEW', 'name': 'Smith^John',
            'birth_date': '19800101', 'sex': 'M', 'meta': None,
        })

        with patch('api.fhir.get_conn') as mock_get:
            mock_get.return_value.__aenter__.return_value = mock_conn
            mock_get.return_value.__aexit__ = AsyncMock(return_value=None)

            from api.fhir import FhirPatientRoot
            app = Starlette(
                routes=[Route('/fhir/Patient', endpoint=FhirPatientRoot)],
                middleware=[Middleware(_FakeAuth, user=_WRITE_USER)],
            )
            client = TestClient(app)
            resp = client.post('/fhir/Patient', json={
                'resourceType': 'Patient',
                'identifier': [{'value': 'PID-NEW'}],
                'name': [{'family': 'Smith', 'given': ['John']}],
                'gender': 'male',
            })

        assert resp.status_code == 200
        assert resp.headers['location'].endswith('/Patient/PID-NEW')

    def test_create_patient_invalid_gender(self):
        from api.fhir import FhirPatientRoot
        app = Starlette(
            routes=[Route('/fhir/Patient', endpoint=FhirPatientRoot)],
            middleware=[Middleware(_FakeAuth, user=_WRITE_USER)],
        )
        client = TestClient(app)
        resp = client.post('/fhir/Patient', json={
            'resourceType': 'Patient',
            'identifier': [{'value': 'PID-X'}],
            'gender': 'banana',
        })
        assert resp.status_code == 422
        assert resp.json()['issue'][0]['code'] == 'value'

    def test_create_patient_missing_identifier(self):
        from api.fhir import FhirPatientRoot
        app = Starlette(
            routes=[Route('/fhir/Patient', endpoint=FhirPatientRoot)],
            middleware=[Middleware(_FakeAuth, user=_WRITE_USER)],
        )
        client = TestClient(app)
        resp = client.post('/fhir/Patient', json={'resourceType': 'Patient'})
        assert resp.status_code == 422

    def test_create_patient_invalid_body(self):
        from api.fhir import FhirPatientRoot
        app = Starlette(
            routes=[Route('/fhir/Patient', endpoint=FhirPatientRoot)],
            middleware=[Middleware(_FakeAuth, user=_WRITE_USER)],
        )
        client = TestClient(app)
        resp = client.post('/fhir/Patient', json={'invalid': 'data'})
        assert resp.status_code == 422

    def test_update_patient_success(self):
        mock_conn = MagicMock()
        mock_conn.execute = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value=1)
        mock_conn.fetchrow = AsyncMock(return_value={
            'id': 1, 'patient_id': 'PID001', 'name': 'Smith^Jane',
            'birth_date': '19800101', 'sex': 'F', 'meta': None,
        })
        mock_conn.fetch = AsyncMock(return_value=[])

        with patch('api.fhir.get_conn') as mock_get:
            mock_get.return_value.__aenter__.return_value = mock_conn
            mock_get.return_value.__aexit__ = AsyncMock(return_value=None)

            from api.fhir import FhirPatientResource
            app = Starlette(
                routes=[Route('/fhir/Patient/{id}', endpoint=FhirPatientResource)],
                middleware=[Middleware(_FakeAuth, user=_WRITE_USER)],
            )
            client = TestClient(app)
            resp = client.put('/fhir/Patient/PID001', json={
                'resourceType': 'Patient',
                'name': [{'family': 'Smith', 'given': ['Jane']}],
                'gender': 'female',
            })

        assert resp.status_code == 200
        body = resp.json()
        assert body['resourceType'] == 'Patient'
        assert body['id'] == 'PID001'

    def test_update_patient_not_found(self):
        mock_conn = MagicMock()
        mock_conn.execute = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value=None)
        mock_conn.fetchrow = AsyncMock(return_value=None)

        with patch('api.fhir.get_conn') as mock_get:
            mock_get.return_value.__aenter__.return_value = mock_conn
            mock_get.return_value.__aexit__ = AsyncMock(return_value=None)

            from api.fhir import FhirPatientResource
            app = Starlette(
                routes=[Route('/fhir/Patient/{id}', endpoint=FhirPatientResource)],
                middleware=[Middleware(_FakeAuth, user=_WRITE_USER)],
            )
            client = TestClient(app)
            resp = client.put('/fhir/Patient/NONEXISTENT', json={
                'resourceType': 'Patient',
                'name': [{'family': 'X', 'given': ['Y']}],
            })

        assert resp.status_code == 404

    def test_delete_patient_success(self):
        mock_conn = MagicMock()
        mock_conn.execute = AsyncMock()
        mock_conn.fetchval = AsyncMock(side_effect=[42, False])

        with patch('api.fhir.get_conn') as mock_get:
            mock_get.return_value.__aenter__.return_value = mock_conn
            mock_get.return_value.__aexit__ = AsyncMock(return_value=None)

            from api.fhir import FhirPatientResource
            app = Starlette(
                routes=[Route('/fhir/Patient/{id}', endpoint=FhirPatientResource)],
                middleware=[Middleware(_FakeAuth, user=_WRITE_USER)],
            )
            client = TestClient(app)
            resp = client.delete('/fhir/Patient/PID001')

        assert resp.status_code == 204

    def test_delete_patient_with_studies_conflict(self):
        mock_conn = MagicMock()
        mock_conn.execute = AsyncMock()
        mock_conn.fetchval = AsyncMock(side_effect=[42, True])

        with patch('api.fhir.get_conn') as mock_get:
            mock_get.return_value.__aenter__.return_value = mock_conn
            mock_get.return_value.__aexit__ = AsyncMock(return_value=None)

            from api.fhir import FhirPatientResource
            app = Starlette(
                routes=[Route('/fhir/Patient/{id}', endpoint=FhirPatientResource)],
                middleware=[Middleware(_FakeAuth, user=_WRITE_USER)],
            )
            client = TestClient(app)
            resp = client.delete('/fhir/Patient/PID001')

        assert resp.status_code == 409
        assert resp.json()['issue'][0]['code'] == 'conflict'

    def test_update_patient_if_match_mismatch(self):
        mock_conn = MagicMock()
        mock_conn.execute = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value=1)
        mock_conn.fetchrow = AsyncMock(return_value={
            'id': 1, 'patient_id': 'PID001', 'name': 'Smith^Jane',
            'birth_date': '19800101', 'sex': 'F', 'meta': None,
            'updated_at': '2026-08-06T00:00:00+00:00',
        })
        mock_conn.fetch = AsyncMock(return_value=[])

        with patch('api.fhir.get_conn') as mock_get:
            mock_get.return_value.__aenter__.return_value = mock_conn
            mock_get.return_value.__aexit__ = AsyncMock(return_value=None)

            from api.fhir import FhirPatientResource
            app = Starlette(
                routes=[Route('/fhir/Patient/{id}', endpoint=FhirPatientResource)],
                middleware=[Middleware(_FakeAuth, user=_WRITE_USER)],
            )
            client = TestClient(app)
            resp = client.put(
                '/fhir/Patient/PID001',
                json={'resourceType': 'Patient', 'name': [{'family': 'X'}]},
                headers={'If-Match': 'W/"99"'},
            )

        assert resp.status_code == 412
        assert resp.json()['issue'][0]['code'] == 'conflict'

    def test_delete_patient_not_found(self):
        mock_conn = MagicMock()
        mock_conn.execute = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value=None)

        with patch('api.fhir.get_conn') as mock_get:
            mock_get.return_value.__aenter__.return_value = mock_conn
            mock_get.return_value.__aexit__ = AsyncMock(return_value=None)

            from api.fhir import FhirPatientResource
            app = Starlette(
                routes=[Route('/fhir/Patient/{id}', endpoint=FhirPatientResource)],
                middleware=[Middleware(_FakeAuth, user=_WRITE_USER)],
            )
            client = TestClient(app)
            resp = client.delete('/fhir/Patient/NONEXISTENT')

        assert resp.status_code == 404
