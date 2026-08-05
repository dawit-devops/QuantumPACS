"""R10 Biomedical Engineer endpoints — equipment registry, PM/QC schedules,
downtime events, work orders, vendor contracts, and parts inventory."""
from datetime import date, datetime, timedelta, timezone

from starlette.endpoints import HTTPEndpoint

from api.rbac import requires_permission
from api.permissions import Permission
from api.response import not_found, ok, created, validation_error
from api.validate import parse_body
from api.schemas.equipment import (
    CreateContractRequest,
    CreateDowntimeRequest,
    CreateEquipmentRequest,
    CreatePartRequest,
    CreateQcRecordRequest,
    CreateScheduleRequest,
    CreateWorkOrderRequest,
    ScheduleActionRequest,
    UpdateContractRequest,
    UpdateDowntimeRequest,
    UpdateEquipmentRequest,
    UpdatePartRequest,
    UpdateWorkOrderRequest,
)
from api.notify import notify_role
from db.audit_log import AuditLog
from db.conn import get_conn
from db.equipment import (
    DowntimeEvents,
    Equipment,
    EquipmentReports,
    MaintenanceSchedules,
    PartsInventory,
    QCRecords,
    VendorContracts,
    WorkOrders,
)
from log import request_id_var

# Documented work order lifecycle: open → in_progress → on_hold → resolved.
_WORK_ORDER_TRANSITIONS = {
    'open': {'in_progress', 'on_hold'},
    'in_progress': {'on_hold', 'resolved'},
    'on_hold': {'resolved'},
    'resolved': set(),
}


def _compliance_note(row):
    last = row.get('last_completed_at')
    if not last:
        return 'never completed'
    next_due = row.get('next_due_date')
    if next_due and last.date() <= next_due:
        return 'on-time'
    return 'late'


def _pm_on_time(row):
    last = row.get('last_completed_at')
    if last is None:
        return True
    next_due = row.get('next_due_date')
    return bool(next_due) and last.date() <= next_due


class EquipmentHandler(HTTPEndpoint):
    @requires_permission(Permission.EQUIPMENT_READ)
    async def get(self, request):
        status = request.query_params.get('status')
        modality = request.query_params.get('modality')
        search = request.query_params.get('search')
        async with get_conn() as conn:
            rows = await Equipment(conn).list(
                status=status, modality=modality, search=search,
            )
        return ok({'data': rows})

    @requires_permission(Permission.EQUIPMENT_WRITE)
    async def post(self, request):
        body = await parse_body(CreateEquipmentRequest, request)
        async with get_conn() as conn:
            existing = await Equipment(conn).by_identifier(body.identifier)
            if existing:
                return validation_error(
                    f'Equipment identifier {body.identifier} already exists',
                )
            equipment = await Equipment(conn).create({
                'identifier': body.identifier,
                'modality': body.modality,
                'manufacturer': body.manufacturer,
                'model': body.model,
                'serial_number': body.serial_number,
                'location': body.location,
                'acquisition_date': body.acquisition_date,
                'operational_status': body.operational_status,
                'warranty_end_date': body.warranty_end_date,
                'created_by': str(request.user.id),
            })
            await AuditLog(conn).log_event(
                event_type='equipment.created',
                actor_id=request.user.id,
                resource_type='equipment',
                resource_id=equipment['id'],
                details={
                    'identifier': body.identifier,
                    'modality': body.modality,
                },
                tenant=request.user.tenant,
                request_id=request_id_var.get(),
            )
        return created({'data': equipment})


class EquipmentItemHandler(HTTPEndpoint):
    @requires_permission(Permission.EQUIPMENT_READ)
    async def get(self, request):
        equipment_id = request.path_params['id']
        async with get_conn() as conn:
            row = await Equipment(conn).get(equipment_id)
        if not row:
            return not_found('Equipment not found')
        return ok({'data': row})

    @requires_permission(Permission.EQUIPMENT_WRITE)
    async def put(self, request):
        equipment_id = request.path_params['id']
        body = await parse_body(UpdateEquipmentRequest, request)
        updates = body.model_dump(exclude_none=True)
        if not updates:
            return ok({})
        async with get_conn() as conn:
            existing = await Equipment(conn).get(equipment_id)
            if not existing:
                return not_found('Equipment not found')
            await Equipment(conn).update(equipment_id, updates)
            details = dict(updates)
            if 'operational_status' in updates:
                details['old_operational_status'] = existing.get('operational_status')
            await AuditLog(conn).log_event(
                event_type='equipment.updated',
                actor_id=request.user.id,
                resource_type='equipment',
                resource_id=equipment_id,
                details=details,
                tenant=request.user.tenant,
                request_id=request_id_var.get(),
            )
        return ok({})


class MaintenanceSchedulesHandler(HTTPEndpoint):
    @requires_permission(Permission.EQUIPMENT_READ)
    async def get(self, request):
        scope = request.query_params.get('scope', 'all')
        equipment_id = request.query_params.get('equipment_id')
        today = date.today()
        async with get_conn() as conn:
            rows = await MaintenanceSchedules(conn).list_pm(equipment_id=equipment_id)
        items = []
        due_count = 0
        overdue_count = 0
        for row in rows:
            next_due = row.get('next_due_date')
            if next_due is None:
                status = 'upcoming'
            elif next_due < today:
                status = 'overdue'
            elif next_due <= today + timedelta(days=7):
                status = 'due'
            else:
                status = 'upcoming'
            if status == 'due':
                due_count += 1
            elif status == 'overdue':
                overdue_count += 1
            items.append({
                'id': row['id'],
                'equipment_id': row['equipment_id'],
                'identifier': row.get('identifier', ''),
                'modality': row.get('modality', ''),
                'title': row.get('title', ''),
                'frequency_days': row.get('frequency_days'),
                'last_completed_at': row.get('last_completed_at'),
                'next_due_date': row.get('next_due_date'),
                'status': status,
                'compliance_note': _compliance_note(row),
            })
        if scope != 'all':
            items = [item for item in items if item['status'] == scope]
        active_count = sum(1 for r in rows if r.get('status') == 'active')
        on_time_count = sum(
            1 for r in rows if r.get('status') == 'active' and _pm_on_time(r)
        )
        compliance_pct = round(on_time_count / active_count * 100, 2) if active_count else 0.0
        summary = {
            'due_count': due_count,
            'overdue_count': overdue_count,
            'compliance_pct': compliance_pct,
        }
        return ok({'data': items, 'summary': summary})

    @requires_permission(Permission.EQUIPMENT_WRITE)
    async def post(self, request):
        equipment_id = request.path_params['id']
        body = await parse_body(CreateScheduleRequest, request)
        next_due = body.next_due_date or (date.today() + timedelta(days=body.frequency_days))
        async with get_conn() as conn:
            equipment = await Equipment(conn).get(equipment_id)
            if not equipment:
                return not_found('Equipment not found')
            schedule = await MaintenanceSchedules(conn).create({
                'equipment_id': equipment_id,
                'schedule_type': body.schedule_type,
                'title': body.title,
                'frequency_days': body.frequency_days,
                'next_due_date': next_due,
            })
            await AuditLog(conn).log_event(
                event_type='equipment.schedule_created',
                actor_id=request.user.id,
                resource_type='maintenance_schedule',
                resource_id=schedule['id'],
                details={
                    'equipment_id': equipment_id,
                    'schedule_type': body.schedule_type,
                },
                tenant=request.user.tenant,
                request_id=request_id_var.get(),
            )
        return created({'data': schedule})


class MaintenanceScheduleItemHandler(HTTPEndpoint):
    @requires_permission(Permission.EQUIPMENT_WRITE)
    async def put(self, request):
        schedule_id = request.path_params['id']
        body = await parse_body(ScheduleActionRequest, request)
        if body.action != 'complete':
            return validation_error('Unsupported schedule action')
        async with get_conn() as conn:
            existing = await MaintenanceSchedules(conn).get(schedule_id)
            if not existing:
                return not_found('Maintenance schedule not found')
            schedule = await MaintenanceSchedules(conn).complete(
                schedule_id, str(request.user.id),
            )
            await AuditLog(conn).log_event(
                event_type='equipment.pm_completed',
                actor_id=request.user.id,
                resource_type='maintenance_schedule',
                resource_id=schedule_id,
                details={
                    'equipment_id': existing.get('equipment_id'),
                    'title': existing.get('title'),
                },
                tenant=request.user.tenant,
                request_id=request_id_var.get(),
            )
        return ok({'data': schedule})


class QCRecordsHandler(HTTPEndpoint):
    @requires_permission(Permission.EQUIPMENT_READ)
    async def get(self, request):
        equipment_id = request.path_params['id']
        try:
            limit = int(request.query_params.get('limit', '50'))
        except (TypeError, ValueError):
            limit = 50
        limit = max(1, min(limit, 500))
        async with get_conn() as conn:
            rows = await QCRecords(conn).list(equipment_id, limit)
        return ok({'data': rows})

    @requires_permission(Permission.EQUIPMENT_WRITE)
    async def post(self, request):
        equipment_id = request.path_params['id']
        body = await parse_body(CreateQcRecordRequest, request)
        async with get_conn() as conn:
            equipment = await Equipment(conn).get(equipment_id)
            if not equipment:
                return not_found('Equipment not found')
            record = await QCRecords(conn).create({
                'equipment_id': equipment_id,
                'schedule_id': body.schedule_id,
                'test_type': body.test_type,
                'pass_fail': body.pass_fail,
                'measured_values': body.measured_values,
                'tested_by': str(request.user.id),
            })
            if body.pass_fail == 'fail':
                await Equipment(conn).set_status_where(
                    equipment_id, 'maintenance', 'operational',
                )
                await AuditLog(conn).log_event(
                    event_type='equipment.qc_failed',
                    actor_id=request.user.id,
                    resource_type='qc_record',
                    resource_id=record['id'],
                    details={
                        'equipment_id': equipment_id,
                        'test_type': body.test_type,
                    },
                    tenant=request.user.tenant,
                    request_id=request_id_var.get(),
                )
                identifier = equipment.get('identifier') or equipment_id
                await notify_role(
                    conn, 'biomedical_engineer', 'equipment.qc_failure',
                    f'QC failed: {identifier}',
                    f'QC test {body.test_type} failed for {identifier} — action required',
                    f'/equipment/{equipment_id}',
                )
            else:
                await AuditLog(conn).log_event(
                    event_type='equipment.qc_created',
                    actor_id=request.user.id,
                    resource_type='qc_record',
                    resource_id=record['id'],
                    details={
                        'equipment_id': equipment_id,
                        'test_type': body.test_type,
                        'pass_fail': body.pass_fail,
                    },
                    tenant=request.user.tenant,
                    request_id=request_id_var.get(),
                )
        return created({'data': record})


class DowntimeEventsHandler(HTTPEndpoint):
    @requires_permission(Permission.EQUIPMENT_READ)
    async def get(self, request):
        equipment_id = request.path_params['id']
        async with get_conn() as conn:
            rows = await DowntimeEvents(conn).list(equipment_id)
        return ok({'data': rows})

    @requires_permission(Permission.EQUIPMENT_WRITE)
    async def post(self, request):
        equipment_id = request.path_params['id']
        body = await parse_body(CreateDowntimeRequest, request)
        async with get_conn() as conn:
            equipment = await Equipment(conn).get(equipment_id)
            if not equipment:
                return not_found('Equipment not found')
            open_event = await DowntimeEvents(conn).get_open(equipment_id)
            if open_event:
                return validation_error('Equipment already has an open downtime event')
            event = await DowntimeEvents(conn).create({
                'equipment_id': equipment_id,
                'cause_category': body.cause_category,
                'impact': body.impact,
                'start_at': body.start_at or datetime.now(timezone.utc),
                'created_by': str(request.user.id),
            })
            if equipment.get('operational_status') != 'retired':
                await Equipment(conn).set_status(equipment_id, 'down')
            await AuditLog(conn).log_event(
                event_type='equipment.downtime_started',
                actor_id=request.user.id,
                resource_type='downtime_event',
                resource_id=event['id'],
                details={
                    'equipment_id': equipment_id,
                    'cause_category': body.cause_category,
                },
                tenant=request.user.tenant,
                request_id=request_id_var.get(),
            )
        return created({'data': event})


class DowntimeEventHandler(HTTPEndpoint):
    @requires_permission(Permission.EQUIPMENT_READ)
    async def get(self, request):
        equipment_id = request.path_params['id']
        downtime_id = request.path_params['downtime_id']
        async with get_conn() as conn:
            event = await DowntimeEvents(conn).get_for_equipment(downtime_id, equipment_id)
        if not event:
            return not_found('Downtime event not found')
        return ok({'data': event})

    @requires_permission(Permission.EQUIPMENT_WRITE)
    async def put(self, request):
        equipment_id = request.path_params['id']
        downtime_id = request.path_params['downtime_id']
        body = await parse_body(UpdateDowntimeRequest, request)
        async with get_conn() as conn:
            existing = await DowntimeEvents(conn).get_for_equipment(downtime_id, equipment_id)
            if not existing:
                return not_found('Downtime event not found')
            updates = {
                'end_at': body.end_at or datetime.now(timezone.utc),
                'status': 'closed',
                'resolution': body.resolution,
            }
            if body.cause_category is not None:
                updates['cause_category'] = body.cause_category
            if body.impact is not None:
                updates['impact'] = body.impact
            event = await DowntimeEvents(conn).update(downtime_id, updates)
            duration_minutes = None
            if event.get('start_at') and event.get('end_at'):
                duration_minutes = round(
                    (event['end_at'] - event['start_at']).total_seconds() / 60,
                )
            open_count = await conn.fetchval(
                """SELECT COUNT(1) FROM downtime_events
                   WHERE equipment_id = $1 AND status = 'open'""",
                equipment_id,
            )
            if not open_count:
                await Equipment(conn).set_status_where(
                    equipment_id, 'operational', 'down',
                )
            await AuditLog(conn).log_event(
                event_type='equipment.downtime_ended',
                actor_id=request.user.id,
                resource_type='downtime_event',
                resource_id=downtime_id,
                details={
                    'equipment_id': equipment_id,
                    'duration_minutes': duration_minutes,
                },
                tenant=request.user.tenant,
                request_id=request_id_var.get(),
            )
        return ok({'data': event})


class EquipmentOpenDowntimeHandler(HTTPEndpoint):
    @requires_permission(Permission.EQUIPMENT_READ)
    async def get(self, request):
        async with get_conn() as conn:
            rows = await DowntimeEvents(conn).list_open()
        return ok({'data': rows})


class WorkOrdersHandler(HTTPEndpoint):
    @requires_permission(Permission.EQUIPMENT_READ)
    async def get(self, request):
        status = request.query_params.get('status')
        equipment_id = request.query_params.get('equipment_id')
        async with get_conn() as conn:
            rows = await WorkOrders(conn).list(status=status, equipment_id=equipment_id)
        return ok({'data': rows})

    @requires_permission(Permission.EQUIPMENT_WRITE)
    async def post(self, request):
        body = await parse_body(CreateWorkOrderRequest, request)
        async with get_conn() as conn:
            equipment = await Equipment(conn).get(body.equipment_id)
            if not equipment:
                return not_found('Equipment not found')
            work_order = await WorkOrders(conn).create({
                'equipment_id': body.equipment_id,
                'description': body.description,
                'created_by': str(request.user.id),
            })
            await AuditLog(conn).log_event(
                event_type='equipment.work_order_created',
                actor_id=request.user.id,
                resource_type='work_order',
                resource_id=work_order['id'],
                details={
                    'equipment_id': body.equipment_id,
                    'description': body.description,
                },
                tenant=request.user.tenant,
                request_id=request_id_var.get(),
            )
            identifier = equipment.get('identifier') or body.equipment_id
            await notify_role(
                conn, 'biomedical_engineer', 'equipment.work_order',
                f'New work order: {identifier}',
                body.description,
                f'/work-orders/{work_order["id"]}',
            )
        return created({'data': work_order})


class WorkOrderHandler(HTTPEndpoint):
    @requires_permission(Permission.EQUIPMENT_READ)
    async def get(self, request):
        work_order_id = request.path_params['id']
        async with get_conn() as conn:
            row = await WorkOrders(conn).get(work_order_id)
        if not row:
            return not_found('Work order not found')
        return ok({'data': row})

    @requires_permission(Permission.EQUIPMENT_WRITE)
    async def put(self, request):
        work_order_id = request.path_params['id']
        body = await parse_body(UpdateWorkOrderRequest, request)
        updates = body.model_dump(exclude_none=True)
        if not updates:
            return ok({})
        async with get_conn() as conn:
            existing = await WorkOrders(conn).get(work_order_id)
            if not existing:
                return not_found('Work order not found')
            old_status = existing.get('status')
            new_status = updates.get('status')
            if new_status and new_status != old_status:
                allowed = _WORK_ORDER_TRANSITIONS.get(old_status, set())
                if new_status not in allowed:
                    return validation_error(
                        f'Invalid work order status transition: {old_status} → {new_status}',
                    )
            if new_status == 'resolved':
                updates['resolved_at'] = datetime.now(timezone.utc)
            work_order = await WorkOrders(conn).update(work_order_id, updates)
            if new_status:
                details = {'status_from': old_status, 'status_to': new_status}
            else:
                details = dict(updates)
            await AuditLog(conn).log_event(
                event_type='equipment.work_order_updated',
                actor_id=request.user.id,
                resource_type='work_order',
                resource_id=work_order_id,
                details=details,
                tenant=request.user.tenant,
                request_id=request_id_var.get(),
            )
        return ok({'data': work_order})


class VendorContractsHandler(HTTPEndpoint):
    @requires_permission(Permission.EQUIPMENT_READ)
    async def get(self, request):
        equipment_id = request.path_params['id']
        today = date.today()
        async with get_conn() as conn:
            rows = await VendorContracts(conn).list(equipment_id)
        items = []
        for row in rows:
            days_to_end = None
            warranty_warning = False
            if row.get('warranty_end_date'):
                days_to_end = (row['warranty_end_date'] - today).days
                warranty_warning = days_to_end <= 90
            items.append({
                **row,
                'days_to_warranty_end': days_to_end,
                'warranty_warning': warranty_warning,
            })
        return ok({'data': items})

    @requires_permission(Permission.EQUIPMENT_WRITE)
    async def post(self, request):
        equipment_id = request.path_params['id']
        body = await parse_body(CreateContractRequest, request)
        async with get_conn() as conn:
            equipment = await Equipment(conn).get(equipment_id)
            if not equipment:
                return not_found('Equipment not found')
            contract = await VendorContracts(conn).create({
                'equipment_id': equipment_id,
                'vendor_name': body.vendor_name,
                'coverage_terms': body.coverage_terms,
                'warranty_end_date': body.warranty_end_date,
                'response_sla_p1_minutes': body.response_sla_p1_minutes,
                'response_sla_p2_minutes': body.response_sla_p2_minutes,
            })
            await AuditLog(conn).log_event(
                event_type='equipment.contract_created',
                actor_id=request.user.id,
                resource_type='vendor_contract',
                resource_id=contract['id'],
                details={
                    'equipment_id': equipment_id,
                    'vendor_name': body.vendor_name,
                },
                tenant=request.user.tenant,
                request_id=request_id_var.get(),
            )
        return created({'data': contract})


class VendorContractHandler(HTTPEndpoint):
    @requires_permission(Permission.EQUIPMENT_WRITE)
    async def put(self, request):
        contract_id = request.path_params['id']
        body = await parse_body(UpdateContractRequest, request)
        updates = body.model_dump(exclude_none=True)
        if not updates:
            return ok({})
        async with get_conn() as conn:
            existing = await VendorContracts(conn).get(contract_id)
            if not existing:
                return not_found('Vendor contract not found')
            contract = await VendorContracts(conn).update(contract_id, updates)
            await AuditLog(conn).log_event(
                event_type='equipment.contract_updated',
                actor_id=request.user.id,
                resource_type='vendor_contract',
                resource_id=contract_id,
                details=updates,
                tenant=request.user.tenant,
                request_id=request_id_var.get(),
            )
        return ok({'data': contract})


class PartsInventoryHandler(HTTPEndpoint):
    @requires_permission(Permission.EQUIPMENT_READ)
    async def get(self, request):
        async with get_conn() as conn:
            rows = await PartsInventory(conn).list()
        items = [{
            **row,
            'low_stock': (row.get('stock_level') or 0) < (row.get('low_stock_threshold') or 0),
        } for row in rows]
        return ok({'data': items})

    @requires_permission(Permission.EQUIPMENT_WRITE)
    async def post(self, request):
        body = await parse_body(CreatePartRequest, request)
        async with get_conn() as conn:
            part = await PartsInventory(conn).create({
                'part_name': body.part_name,
                'stock_level': body.stock_level,
                'low_stock_threshold': body.low_stock_threshold,
                'unit': body.unit,
            })
            await AuditLog(conn).log_event(
                event_type='equipment.part_created',
                actor_id=request.user.id,
                resource_type='part',
                resource_id=part['id'],
                details={
                    'part_name': body.part_name,
                    'stock_level': body.stock_level,
                },
                tenant=request.user.tenant,
                request_id=request_id_var.get(),
            )
        return created({'data': part})

    @requires_permission(Permission.EQUIPMENT_WRITE)
    async def put(self, request):
        part_id = request.path_params['id']
        body = await parse_body(UpdatePartRequest, request)
        updates = body.model_dump(exclude_none=True)
        if not updates:
            return ok({})
        async with get_conn() as conn:
            existing = await PartsInventory(conn).get(part_id)
            if not existing:
                return not_found('Part not found')
            part = await PartsInventory(conn).update(part_id, updates)
            stock_level = part.get('stock_level') or 0
            threshold = part.get('low_stock_threshold') or 0
            await AuditLog(conn).log_event(
                event_type='equipment.part_updated',
                actor_id=request.user.id,
                resource_type='part',
                resource_id=part_id,
                details=updates,
                tenant=request.user.tenant,
                request_id=request_id_var.get(),
            )
            if stock_level < threshold:
                part_name = existing.get('part_name') or part_id
                await AuditLog(conn).log_event(
                    event_type='equipment.low_stock',
                    actor_id=request.user.id,
                    resource_type='part',
                    resource_id=part_id,
                    details={
                        'part_name': part_name,
                        'stock_level': stock_level,
                        'low_stock_threshold': threshold,
                    },
                    tenant=request.user.tenant,
                    request_id=request_id_var.get(),
                )
                await notify_role(
                    conn, 'biomedical_engineer', 'equipment.low_stock',
                    f'Low stock: {part_name}',
                    f'Stock level {stock_level} is below threshold {threshold}',
                    '/parts',
                )
        return ok({'data': part})


class EquipmentReportsHandler(HTTPEndpoint):
    @requires_permission(Permission.EQUIPMENT_READ)
    async def get(self, request):
        path = request.url.path
        if path.endswith('/uptime'):
            return await self._uptime_report(request)
        if path.endswith('/compliance'):
            return await self._compliance_report(request)
        return await self._downtime_causes_report(request)

    def _date_range(self, request):
        today = date.today()
        from_str = request.query_params.get('from')
        to_str = request.query_params.get('to')
        try:
            from_date = date.fromisoformat(from_str) if from_str else today - timedelta(days=30)
        except ValueError:
            from_date = today - timedelta(days=30)
        try:
            to_date = date.fromisoformat(to_str) if to_str else today
        except ValueError:
            to_date = today
        return from_date, to_date

    async def _uptime_report(self, request):
        from_date, to_date = self._date_range(request)
        async with get_conn() as conn:
            rows = await EquipmentReports(conn).uptime(from_date, to_date)
        total_seconds = max((to_date - from_date).total_seconds(), 1)
        items = []
        for r in rows:
            down_seconds = float(r['down_seconds'] or 0)
            uptime_pct = round(100 * (1 - down_seconds / total_seconds), 2)
            items.append({
                'identifier': r['identifier'],
                'modality': r.get('modality', ''),
                'uptime_pct': uptime_pct,
                'downtime_hours': round(down_seconds / 3600, 2),
            })
        return ok({
            'data': items,
            'from': from_date.isoformat(),
            'to': to_date.isoformat(),
        })

    async def _compliance_report(self, request):
        from_date, to_date = self._date_range(request)
        async with get_conn() as conn:
            rows = await EquipmentReports(conn).compliance(from_date, to_date)
        items = []
        for r in rows:
            pm_scheduled = r['pm_scheduled'] or 0
            qc_total = r['qc_total'] or 0
            pm_compliance_pct = (
                round((r['pm_completed'] or 0) / pm_scheduled * 100, 2)
                if pm_scheduled else 0.0
            )
            qc_failure_pct = (
                round((r['qc_failures'] or 0) / qc_total * 100, 2)
                if qc_total else 0.0
            )
            items.append({
                'identifier': r['identifier'],
                'modality': r.get('modality', ''),
                'pm_completed': r['pm_completed'] or 0,
                'pm_scheduled': pm_scheduled,
                'pm_compliance_pct': pm_compliance_pct,
                'qc_total': qc_total,
                'qc_failures': r['qc_failures'] or 0,
                'qc_failure_pct': qc_failure_pct,
            })
        return ok({
            'data': items,
            'from': from_date.isoformat(),
            'to': to_date.isoformat(),
        })

    async def _downtime_causes_report(self, request):
        from_date, to_date = self._date_range(request)
        async with get_conn() as conn:
            rows = await EquipmentReports(conn).downtime_causes(from_date, to_date)
        items = [{
            'cause_category': r['cause_category'],
            'event_count': r['event_count'],
            'total_duration_minutes': round(float(r['total_minutes'] or 0), 1),
        } for r in rows]
        return ok({
            'data': items,
            'from': from_date.isoformat(),
            'to': to_date.isoformat(),
        })
