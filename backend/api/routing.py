import json

from starlette.endpoints import HTTPEndpoint

from api.rbac import requires_permission
from api.permissions import Permission
from api.response import not_found, ok, created, no_content
from api.validate import parse_body
from api.schemas.routing import RoutingRuleRequest
from db.audit_log import AuditLog
from db.conn import get_conn
from db.routing_rule import RoutingRule
from log import request_id_var


class RoutingHandler(HTTPEndpoint):
    @requires_permission(Permission.ROUTING_READ)
    async def get(self, request):
        async with get_conn() as conn:
            rules = await RoutingRule(conn).list_all()
        return ok({'data': rules})

    @requires_permission(Permission.ROUTING_WRITE)
    async def post(self, request):
        body = await parse_body(RoutingRuleRequest, request)
        conditions = body.conditions
        if isinstance(conditions, str):
            conditions = json.loads(conditions)
        async with get_conn() as conn:
            rule_data = {
                'name': body.name,
                'description': body.description or '',
                'conditions': json.dumps(conditions),
                'destination': body.destination,
                'priority': body.priority or 0,
                'enabled': body.enabled if body.enabled is not None else True,
            }
            tenant_id = getattr(request.user, 'tenant', None) or request.headers.get('X-Tenant-ID', '')
            if tenant_id:
                rule_data['tenant_id'] = tenant_id
            result = await RoutingRule(conn).create(rule_data)
            await AuditLog(conn).log_event(
                event_type='routing.rule_created',
                actor_id=request.user.id,
                resource_type='routing_rule',
                resource_id=result['id'],
                details={'name': body.name, 'destination': body.destination},
                tenant=request.user.tenant,
                request_id=request_id_var.get(),
            )
        return created({'data': result})


class RoutingRuleHandler(HTTPEndpoint):
    @requires_permission(Permission.ROUTING_READ)
    async def get(self, request):
        rule_id = request.path_params['id']
        async with get_conn() as conn:
            rule = await RoutingRule(conn).get_by_id(rule_id)
        if not rule:
            return not_found('Routing rule not found')
        return ok({'data': rule})

    @requires_permission(Permission.ROUTING_WRITE)
    async def put(self, request):
        rule_id = request.path_params['id']
        body = await parse_body(RoutingRuleRequest, request)
        conditions = body.conditions
        if isinstance(conditions, str):
            conditions = json.loads(conditions)
        async with get_conn() as conn:
            rr = RoutingRule(conn)
            existing = await rr.get_by_id(rule_id)
            if not existing:
                return not_found('Routing rule not found')
            await rr.update(rule_id, {
                'name': body.name,
                'description': body.description or '',
                'conditions': json.dumps(conditions),
                'destination': body.destination,
                'priority': body.priority or 0,
                'enabled': body.enabled if body.enabled is not None else True,
            })
            await AuditLog(conn).log_event(
                event_type='routing.rule_updated',
                actor_id=request.user.id,
                resource_type='routing_rule',
                resource_id=rule_id,
                details={'name': body.name},
                tenant=request.user.tenant,
                request_id=request_id_var.get(),
            )
        return ok({'data': {'id': rule_id}})

    @requires_permission(Permission.ROUTING_WRITE)
    async def delete(self, request):
        rule_id = request.path_params['id']
        async with get_conn() as conn:
            rr = RoutingRule(conn)
            existing = await rr.get_by_id(rule_id)
            if not existing:
                return not_found('Routing rule not found')
            await rr.delete(rule_id)
            await AuditLog(conn).log_event(
                event_type='routing.rule_deleted',
                actor_id=request.user.id,
                resource_type='routing_rule',
                resource_id=rule_id,
                details={'name': existing['name']},
                tenant=request.user.tenant,
                request_id=request_id_var.get(),
            )
        return no_content()
