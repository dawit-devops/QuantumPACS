from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

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
    from api.equipment import (
        EquipmentHandler, EquipmentItemHandler, MaintenanceSchedulesHandler,
        MaintenanceScheduleItemHandler, QCRecordsHandler, DowntimeEventsHandler,
        DowntimeEventHandler, EquipmentOpenDowntimeHandler, WorkOrdersHandler,
        WorkOrderHandler, VendorContractsHandler, VendorContractHandler,
        PartsInventoryHandler, EquipmentReportsHandler,
    )
    return Starlette(
        routes=[
            # Static sub-routes must precede /equipment/{id} so they are not
            # shadowed by the dynamic id segment.
            Route('/equipment', endpoint=EquipmentHandler),
            Route('/equipment/pm', endpoint=MaintenanceSchedulesHandler),
            Route('/equipment/downtime/open', endpoint=EquipmentOpenDowntimeHandler),
            Route('/equipment/reports/uptime', endpoint=EquipmentReportsHandler),
            Route('/equipment/reports/compliance', endpoint=EquipmentReportsHandler),
            Route('/equipment/reports/downtime-causes', endpoint=EquipmentReportsHandler),
            Route('/equipment/{id}', endpoint=EquipmentItemHandler),
            Route('/equipment/{id}/schedules', endpoint=MaintenanceSchedulesHandler),
            Route('/equipment/schedules/{id}', endpoint=MaintenanceScheduleItemHandler),
            Route('/equipment/{id}/qc', endpoint=QCRecordsHandler),
            Route('/equipment/{id}/downtime', endpoint=DowntimeEventsHandler),
            Route('/equipment/{id}/downtime/{downtime_id}', endpoint=DowntimeEventHandler),
            Route('/equipment/{id}/contracts', endpoint=VendorContractsHandler),
            Route('/vendor-contracts/{id}', endpoint=VendorContractHandler),
            Route('/work-orders', endpoint=WorkOrdersHandler),
            Route('/work-orders/{id}', endpoint=WorkOrderHandler),
            Route('/parts', endpoint=PartsInventoryHandler),
            Route('/parts/{id}', endpoint=PartsInventoryHandler, methods=['PUT']),
        ],
        middleware=[Middleware(_FakeAuth, user=user)],
        exception_handlers={
            HTTPException: _http_exception,
            _ValidationException: validation_exception_handler,
        },
    )


def _equipment_row(**over):
    row = {
        'id': 'eq-1', 'identifier': 'EQ-001', 'modality': 'CT',
        'manufacturer': 'Acme', 'model': 'Model X', 'serial_number': 'SN1',
        'location': 'Room 1', 'acquisition_date': None,
        'operational_status': 'operational', 'warranty_end_date': None,
        'created_by': '1', 'created_at': None, 'updated_at': None,
    }
    row.update(over)
    return row


class TestEquipmentCreate:
    def test_create_requires_equipment_write(self):
        user = User({'id': 1, 'permissions': []})
        client = TestClient(_make_app(user))
        resp = client.post('/equipment', json={'identifier': 'EQ-001'})
        assert resp.status_code == 403

    def test_create_success(self):
        user = User({'id': 1, 'permissions': ['EQUIPMENT_WRITE']})
        client = TestClient(_make_app(user))
        with patch('api.equipment.get_conn') as gc:
            conn = gc.return_value.__aenter__.return_value
            conn.fetchrow = AsyncMock(side_effect=[None, _equipment_row()])
            resp = client.post('/equipment', json={
                'identifier': 'EQ-001', 'modality': 'CT', 'manufacturer': 'Acme',
            })
        assert resp.status_code == 201
        assert resp.json()['data']['identifier'] == 'EQ-001'

    def test_create_duplicate_identifier_rejected(self):
        user = User({'id': 1, 'permissions': ['EQUIPMENT_WRITE']})
        client = TestClient(_make_app(user))
        with patch('api.equipment.get_conn') as gc:
            conn = gc.return_value.__aenter__.return_value
            conn.fetchrow = AsyncMock(return_value={'id': 'existing'})
            resp = client.post('/equipment', json={'identifier': 'EQ-001'})
        assert resp.status_code == 400
        assert 'already exists' in resp.json()['error']['message']


class TestDowntime:
    def test_downtime_create_rejects_when_open_event_exists(self):
        user = User({'id': 1, 'permissions': ['EQUIPMENT_WRITE']})
        client = TestClient(_make_app(user))
        with patch('api.equipment.get_conn') as gc:
            conn = gc.return_value.__aenter__.return_value
            conn.fetchrow = AsyncMock(side_effect=[
                _equipment_row(),
                {'id': 'dt-open', 'equipment_id': 'eq-1', 'status': 'open'},
            ])
            resp = client.post('/equipment/eq-1/downtime', json={
                'cause_category': 'power',
            })
        assert resp.status_code == 400
        assert 'open downtime event' in resp.json()['error']['message']

    def test_downtime_create_success_sets_equipment_down(self):
        user = User({'id': 1, 'permissions': ['EQUIPMENT_WRITE']})
        client = TestClient(_make_app(user))
        with patch('api.equipment.get_conn') as gc:
            conn = gc.return_value.__aenter__.return_value
            conn.fetchrow = AsyncMock(side_effect=[
                _equipment_row(),
                None,
                {'id': 'dt-1', 'equipment_id': 'eq-1', 'cause_category': 'power',
                 'impact': '', 'status': 'open', 'start_at': None, 'end_at': None},
            ])
            conn.execute = AsyncMock()
            resp = client.post('/equipment/eq-1/downtime', json={
                'cause_category': 'power',
            })
        assert resp.status_code == 201
        assert resp.json()['data']['status'] == 'open'
        status_calls = [
            c for c in conn.execute.call_args_list
            if 'operational_status =' in str(c.args[0])
        ]
        assert status_calls
        assert status_calls[0].args[2] == 'down'

    def test_downtime_close_restores_operational(self):
        user = User({'id': 1, 'permissions': ['EQUIPMENT_WRITE']})
        client = TestClient(_make_app(user))
        start = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
        end = datetime(2026, 1, 1, 12, 30, tzinfo=timezone.utc)
        with patch('api.equipment.get_conn') as gc:
            conn = gc.return_value.__aenter__.return_value
            conn.fetchrow = AsyncMock(side_effect=[
                {'id': 'dt-1', 'equipment_id': 'eq-1', 'status': 'open',
                 'start_at': start, 'end_at': None, 'cause_category': 'power'},
                {'id': 'dt-1', 'equipment_id': 'eq-1', 'status': 'closed',
                 'start_at': start, 'end_at': end, 'cause_category': 'power',
                 'resolution': 'fixed'},
            ])
            conn.fetchval = AsyncMock(return_value=0)
            conn.execute = AsyncMock()
            resp = client.put('/equipment/eq-1/downtime/dt-1', json={
                'resolution': 'fixed',
            })
        assert resp.status_code == 200
        assert resp.json()['data']['status'] == 'closed'
        restore_calls = [
            c for c in conn.execute.call_args_list
            if 'operational_status =' in str(c.args[0])
        ]
        assert restore_calls
        assert 'operational' in str(restore_calls[0].args[0])


class TestQcRecords:
    def test_qc_fail_triggers_notify_and_maintenance_status(self):
        user = User({'id': 1, 'permissions': ['EQUIPMENT_WRITE']})
        client = TestClient(_make_app(user))
        with patch('api.equipment.get_conn') as gc:
            conn = gc.return_value.__aenter__.return_value
            conn.fetchrow = AsyncMock(side_effect=[
                _equipment_row(),
                {'id': 'qc-1', 'equipment_id': 'eq-1', 'test_type': 'kV accuracy',
                 'pass_fail': 'fail', 'measured_values': {},
                 'tested_at': None, 'schedule_id': None},
            ])
            conn.execute = AsyncMock()
            with patch('api.equipment.notify_role', new=AsyncMock()) as mock_notify:
                resp = client.post('/equipment/eq-1/qc', json={
                    'test_type': 'kV accuracy', 'pass_fail': 'fail',
                })
        assert resp.status_code == 201
        assert resp.json()['data']['pass_fail'] == 'fail'
        mock_notify.assert_awaited_once()
        maintenance_calls = [
            c for c in conn.execute.call_args_list if len(c.args) > 2 and c.args[2] == 'maintenance'
        ]
        assert maintenance_calls


class TestMaintenanceSchedules:
    def test_pm_list_returns_due_overdue_summary(self):
        user = User({'id': 1, 'permissions': ['EQUIPMENT_READ']})
        client = TestClient(_make_app(user))
        today = date.today()
        rows = [
            {'id': 's1', 'equipment_id': 'eq-1', 'identifier': 'EQ-001', 'modality': 'CT',
             'title': 'PM-1', 'frequency_days': 90, 'last_completed_at': None,
             'next_due_date': today - timedelta(days=1), 'status': 'active'},
            {'id': 's2', 'equipment_id': 'eq-1', 'identifier': 'EQ-001', 'modality': 'CT',
             'title': 'PM-2', 'frequency_days': 90,
             'last_completed_at': datetime.now(timezone.utc),
             'next_due_date': today + timedelta(days=2), 'status': 'active'},
            {'id': 's3', 'equipment_id': 'eq-1', 'identifier': 'EQ-001', 'modality': 'CT',
             'title': 'PM-3', 'frequency_days': 180, 'last_completed_at': None,
             'next_due_date': today + timedelta(days=30), 'status': 'active'},
        ]
        with patch('api.equipment.get_conn') as gc:
            conn = gc.return_value.__aenter__.return_value
            conn.fetch = AsyncMock(return_value=rows)
            resp = client.get('/equipment/pm')
        assert resp.status_code == 200
        body = resp.json()
        assert body['summary']['due_count'] == 1
        assert body['summary']['overdue_count'] == 1
        assert body['summary']['compliance_pct'] == 100.0
        assert [r['status'] for r in body['data']] == ['overdue', 'due', 'upcoming']


class TestEquipmentReports:
    def test_uptime_report_returns_float_pct(self):
        user = User({'id': 1, 'permissions': ['EQUIPMENT_READ']})
        client = TestClient(_make_app(user))
        with patch('api.equipment.get_conn') as gc:
            conn = gc.return_value.__aenter__.return_value
            conn.fetch = AsyncMock(return_value=[
                {'identifier': 'EQ-001', 'modality': 'CT', 'down_seconds': 3600},
            ])
            resp = client.get('/equipment/reports/uptime?from=2026-01-01&to=2026-01-31')
        assert resp.status_code == 200
        row = resp.json()['data'][0]
        assert isinstance(row['uptime_pct'], float)
        assert isinstance(row['downtime_hours'], float)
        assert row['uptime_pct'] > 99.0
