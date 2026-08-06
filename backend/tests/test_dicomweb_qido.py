from unittest.mock import AsyncMock, patch

import pytest
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.routing import Route
from starlette.testclient import TestClient
from starlette.exceptions import HTTPException

from api.auth import User
from api.validate import validation_exception_handler, _ValidationException


def _http_exception(request, exc):
    from starlette.responses import JSONResponse
    return JSONResponse(
        {'error': exc.detail if hasattr(exc, 'detail') else ''},
        status_code=exc.status_code,
    )


class _FakeAuth(BaseHTTPMiddleware):
    def __init__(self, app, user=None):
        super().__init__(app)
        self._user = user or User({'id': 1, 'permissions': []})

    async def dispatch(self, request, call_next):
        request.scope['user'] = self._user
        request.scope['auth'] = None
        return await call_next(request)


def _make_app(user=None):
    from api.dicomweb import DicomWebStudies
    return Starlette(
        routes=[
            Route('/dicomweb/studies', endpoint=DicomWebStudies),
            Route('/dicomweb/studies/{study_uid}/series', endpoint=DicomWebStudies),
            Route('/dicomweb/studies/{study_uid}/series/{series_uid}/instances', endpoint=DicomWebStudies),
        ],
        middleware=[Middleware(_FakeAuth, user=user)],
        exception_handlers={
            HTTPException: _http_exception,
            _ValidationException: validation_exception_handler,
        },
    )


class _FakeConn:
    async def __aenter__(self):
        return self
    async def __aexit__(self, *args):
        pass


class TestQidoStudies:
    @pytest.mark.asyncio
    async def test_returns_studies_by_patient_id(self):
        user = User({'id': 1, 'permissions': ['DICOMWEB_READ']})
        client = TestClient(_make_app(user))

        conn = _FakeConn()
        conn.fetch = AsyncMock(return_value=[
            {
                'patient_id': 'P001',
                'patient_name': 'Smith^John',
                'patient_birth_date': '19700101',
                'patient_sex': 'M',
                'study_instance_uid': '1.2.3.4.5.6',
                'study_id': 'ST001',
                'accession_number': 'ACC001',
                'description': 'Chest CT',
            },
        ])
        conn.fetchval = AsyncMock(return_value=1)

        with patch('api.dicomweb.get_conn', return_value=conn):
            resp = client.get('/dicomweb/studies?PatientID=P001')

        assert resp.status_code == 200
        assert resp.headers['content-type'] == 'application/dicom+json'

        body = resp.json()
        assert isinstance(body, list)
        assert len(body) == 1

        study = body[0]
        assert study['0020000D']['vr'] == 'UI'
        assert study['0020000D']['Value'] == ['1.2.3.4.5.6']
        assert study['00100010']['vr'] == 'PN'
        assert study['00100010']['Value'] == [{'Alphabetic': 'Smith^John'}]
        assert study['00080050']['vr'] == 'SH'
        assert study['00080050']['Value'] == ['ACC001']


class TestQidoSeries:
    @pytest.mark.asyncio
    async def test_returns_series_by_study_uid(self):
        user = User({'id': 1, 'permissions': ['DICOMWEB_READ']})
        client = TestClient(_make_app(user))

        conn = _FakeConn()
        conn.fetch = AsyncMock(return_value=[
            {
                'series_number': '1',
                'modality': 'CT',
                'series_description': 'Chest',
                'series_instance_uid': '1.2.3.4.5.6.7',
            },
        ])

        with patch('api.dicomweb.get_conn', return_value=conn):
            resp = client.get('/dicomweb/studies/1.2.3.4.5.6/series')

        assert resp.status_code == 200
        assert resp.headers['content-type'] == 'application/dicom+json'

        body = resp.json()
        assert isinstance(body, list)
        assert len(body) == 1

        series = body[0]
        assert series['0020000E']['vr'] == 'UI'
        assert series['0020000E']['Value'] == ['1.2.3.4.5.6.7']
        assert series['00080060']['vr'] == 'CS'
        assert series['00080060']['Value'] == ['CT']
        assert series['00200011']['vr'] == 'IS'
        assert series['00200011']['Value'] == ['1']


class TestQidoInstances:
    @pytest.mark.asyncio
    async def test_returns_instances_by_series_uid(self):
        user = User({'id': 1, 'permissions': ['DICOMWEB_READ']})
        client = TestClient(_make_app(user))

        conn = _FakeConn()
        conn.fetch = AsyncMock(return_value=[
            {
                'sop_instance_uid': '1.2.3.4.5.6.7.8',
                'sop_class_uid': '1.2.840.10008.5.1.4.1.1.2',
                'instance_number': '1',
            },
        ])

        with patch('api.dicomweb.get_conn', return_value=conn):
            resp = client.get('/dicomweb/studies/1.2.3.4.5.6/series/1.2.3.4.5.6.7/instances')

        assert resp.status_code == 200
        assert resp.headers['content-type'] == 'application/dicom+json'

        body = resp.json()
        assert isinstance(body, list)
        assert len(body) == 1

        inst = body[0]
        assert inst['00080018']['vr'] == 'UI'
        assert inst['00080018']['Value'] == ['1.2.3.4.5.6.7.8']
        assert inst['00080016']['vr'] == 'UI'
        assert inst['00080016']['Value'] == ['1.2.840.10008.5.1.4.1.1.2']
        assert inst['00200013']['vr'] == 'IS'
        assert inst['00200013']['Value'] == ['1']


class TestQidoFilters:
    @pytest.mark.asyncio
    async def test_studies_filter_by_patient_name_wildcard(self):
        user = User({'id': 1, 'permissions': ['DICOMWEB_READ']})
        client = TestClient(_make_app(user))

        conn = _FakeConn()
        conn.fetch = AsyncMock(return_value=[])
        conn.fetchval = AsyncMock(return_value=0)

        with patch('api.dicomweb.get_conn', return_value=conn):
            resp = client.get('/dicomweb/studies?PatientName=Smith*')

        assert resp.status_code == 200
        sql = conn.fetch.call_args[0][0]
        args = conn.fetch.call_args[0][1]
        assert 'ILIKE' in sql
        # '*' wildcard is translated to '%' in the bind args (parameterized).
        assert args == 'Smith%'

    @pytest.mark.asyncio
    async def test_studies_filter_by_modality(self):
        user = User({'id': 1, 'permissions': ['DICOMWEB_READ']})
        client = TestClient(_make_app(user))

        conn = _FakeConn()
        conn.fetch = AsyncMock(return_value=[])
        conn.fetchval = AsyncMock(return_value=0)

        with patch('api.dicomweb.get_conn', return_value=conn):
            resp = client.get('/dicomweb/studies?Modality=CT')

        assert resp.status_code == 200
        sql = conn.fetch.call_args[0][0]
        assert 'EXISTS' in sql
        assert 'ser.modality' in sql

    @pytest.mark.asyncio
    async def test_studies_filter_by_study_date_range(self):
        user = User({'id': 1, 'permissions': ['DICOMWEB_READ']})
        client = TestClient(_make_app(user))

        conn = _FakeConn()
        conn.fetch = AsyncMock(return_value=[])
        conn.fetchval = AsyncMock(return_value=0)

        with patch('api.dicomweb.get_conn', return_value=conn):
            resp = client.get('/dicomweb/studies?StudyDate=20260101-20260201')

        assert resp.status_code == 200
        sql = conn.fetch.call_args[0][0]
        assert 's.study_date >=' in sql
        assert 's.study_date <=' in sql

    @pytest.mark.asyncio
    async def test_studies_filter_by_study_description(self):
        user = User({'id': 1, 'permissions': ['DICOMWEB_READ']})
        client = TestClient(_make_app(user))

        conn = _FakeConn()
        conn.fetch = AsyncMock(return_value=[])
        conn.fetchval = AsyncMock(return_value=0)

        with patch('api.dicomweb.get_conn', return_value=conn):
            resp = client.get('/dicomweb/studies?StudyDescription=Chest*')

        assert resp.status_code == 200
        sql = conn.fetch.call_args[0][0]
        assert 's.description ILIKE' in sql

    @pytest.mark.asyncio
    async def test_includefield_filters_returned_tags(self):
        user = User({'id': 1, 'permissions': ['DICOMWEB_READ']})
        client = TestClient(_make_app(user))

        conn = _FakeConn()
        conn.fetch = AsyncMock(return_value=[
            {
                'patient_id': 'P001', 'patient_name': 'A',
                'patient_birth_date': None, 'patient_sex': None,
                'study_instance_uid': '1.2.3', 'study_id': 'S1',
                'accession_number': 'ACC001', 'description': '', 'study_date': None,
            },
        ])
        conn.fetchval = AsyncMock(return_value=1)

        with patch('api.dicomweb.get_conn', return_value=conn):
            resp = client.get('/dicomweb/studies?includefield=0020000D,00080050')

        assert resp.status_code == 200
        body = resp.json()
        assert set(body[0].keys()) == {'0020000D', '00080050'}


class TestQidoInstancesDeleted:
    @pytest.mark.asyncio
    async def test_instance_query_excludes_deleted_files(self):
        user = User({'id': 1, 'permissions': ['DICOMWEB_READ']})
        client = TestClient(_make_app(user))

        conn = _FakeConn()
        conn.fetch = AsyncMock(return_value=[])

        with patch('api.dicomweb.get_conn', return_value=conn):
            resp = client.get('/dicomweb/studies/1.2.3/series/1.2.3.4/instances')

        assert resp.status_code == 200
        sql = conn.fetch.call_args[0][0]
        assert 'f.deleted = false' in sql


class TestQidoAuth:
    @pytest.mark.asyncio
    async def test_requires_dicomweb_read_permission(self):
        user = User({'id': 1, 'permissions': ['FILE_READ']})
        client = TestClient(_make_app(user))

        conn = _FakeConn()
        conn.fetch = AsyncMock(return_value=[])
        conn.fetchval = AsyncMock(return_value=0)

        with patch('api.dicomweb.get_conn', return_value=conn):
            resp = client.get('/dicomweb/studies')

        assert resp.status_code == 403


class TestQidoStudiesExtra:
    @pytest.mark.asyncio
    async def test_returns_studies_by_accession_number(self):
        user = User({'id': 1, 'permissions': ['DICOMWEB_READ']})
        client = TestClient(_make_app(user))

        conn = _FakeConn()
        conn.fetch = AsyncMock(return_value=[
            {
                'patient_id': 'P001', 'patient_name': 'A',
                'patient_birth_date': None, 'patient_sex': None,
                'study_instance_uid': '1.2.3', 'study_id': 'S1',
                'accession_number': 'ACC001', 'description': '',
            },
        ])
        conn.fetchval = AsyncMock(return_value=1)

        with patch('api.dicomweb.get_conn', return_value=conn):
            resp = client.get('/dicomweb/studies?AccessionNumber=ACC001')

        assert resp.status_code == 200
        body = resp.json()
        assert len(body) == 1
        assert body[0]['00080050']['Value'] == ['ACC001']


class TestQidoPagination:
    @pytest.mark.asyncio
    async def test_studies_returns_x_total_count(self):
        user = User({'id': 1, 'permissions': ['DICOMWEB_READ']})
        client = TestClient(_make_app(user))

        conn = _FakeConn()
        conn.fetch = AsyncMock(return_value=[
            {'patient_id': 'P001', 'patient_name': 'A', 'study_instance_uid': f'1.2.3.{i}'}
            for i in range(5)
        ])
        conn.fetchval = AsyncMock(return_value=20)

        with patch('api.dicomweb.get_conn', return_value=conn):
            resp = client.get('/dicomweb/studies?limit=5&offset=0')

        assert resp.status_code == 200
        assert resp.headers['content-type'] == 'application/dicom+json'
        assert resp.headers['x-total-count'] == '20'
        body = resp.json()
        assert len(body) == 5
