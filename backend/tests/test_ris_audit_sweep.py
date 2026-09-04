"""S1-21 — RIS audit-completeness sweep.

The platform audit standard: every state-mutating handler emits an
AuditLog.log_event. TenantMiddleware already meters HTTP traffic, and the
domain suites assert behavior — this module is the *completeness net*: it
fails when a RIS write surface loses its audit emission during refactor,
or when a new write surface lands without one.

Two layers:
1. Source contract (AST): every registered RIS write module contains a
   log_event call, and its required event-type strings are present.
   Dynamic templates (prior_auth.{...}d) are matched by prefix.
2. Functional: the dynamic prior-auth decision template resolves to
   prior_auth.approved / prior_auth.denied.
"""

import ast
import pathlib

import pytest

from unittest.mock import patch

BACKEND = pathlib.Path(__file__).resolve().parents[1]

# Every RIS surface that mutates state must audit. Modules here without a
# single log_event call fail the sweep.
RIS_WRITE_MODULES = [
    'api/frontdesk.py',
    'api/reports.py',
    'api/prior_auth.py',
    'api/reminders.py',
    'api/billing.py',
    'services/order_lifecycle/service.py',
    'services/scheduling/engine.py',
    'services/mpps_consumer/service.py',
]

# Required event types per module. A plain string must appear verbatim; a
# string ending in '.' is treated as a *prefix* for dynamically-built event
# names (f-strings), so refactors can't silently drop them.
REQUIRED_EVENTS = {
    'api/frontdesk.py': [
        'frontdesk.patient_registered',
        'frontdesk.checkin',
        'frontdesk.appointment_created',
    ],
    'api/reports.py': [
        'report.saved',
        'report.signed',
    ],
    'api/prior_auth.py': [
        'prior_auth.submitted',
        'prior_auth.',  # template → approved / denied
    ],
    'api/reminders.py': [
        'reminder.config_updated',
    ],
    'api/billing.py': [
        'billing.charge_dropped',
    ],
    'services/order_lifecycle/service.py': [
        'ORDER_STATUS_TRANSITION',
    ],
}


def _module_tree(rel):
    return ast.parse((BACKEND / rel).read_text())


def _string_constants(tree):
    """All string literals in the module, including f-string literal parts."""
    out = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            out.add(node.value)
    return out


def _has_log_event_call(tree):
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            fn = node.func
            name = fn.attr if isinstance(fn, ast.Attribute) else getattr(fn, 'id', '')
            if name == 'log_event':
                return True
    return False


class TestAuditSourceContract:
    @pytest.mark.parametrize('rel', RIS_WRITE_MODULES)
    def test_write_module_emits_audit(self, rel):
        tree = _module_tree(rel)
        assert _has_log_event_call(tree), (
            f'{rel} mutates state but contains no AuditLog.log_event call'
        )

    @pytest.mark.parametrize('rel,events',
                             sorted(REQUIRED_EVENTS.items()))
    def test_required_event_types_present(self, rel, events):
        strings = _string_constants(_module_tree(rel))
        for ev in events:
            if ev.endswith('.'):
                assert any(s.startswith(ev) for s in strings), (
                    f'{rel}: no dynamic event with prefix {ev!r}'
                )
            else:
                assert ev in strings, f'{rel}: missing audit event {ev!r}'


class TestPriorAuthDecisionAudit:
    """The decision endpoint builds its event type from the outcome —
    verify both resolutions actually reach the audit log."""

    @staticmethod
    def _post_decision(action):
        import json as _json

        from starlette.applications import Starlette
        from starlette.middleware import Middleware
        from starlette.middleware.base import BaseHTTPMiddleware
        from starlette.routing import Route
        from starlette.testclient import TestClient

        from api.auth import User
        from api.prior_auth import PriorAuthDecisionHandler

        class _FakeAuth(BaseHTTPMiddleware):
            def __init__(self, app, user=None):
                super().__init__(app)
                self._user = user or User({'id': 1, 'permissions': []})

            async def dispatch(self, request, call_next):
                request.scope['user'] = self._user
                request.scope['auth'] = None
                return await call_next(request)

        class _Conn:
            def __init__(self):
                self.inserts = []

            async def __aenter__(self):
                return self

            async def __aexit__(self, *exc):
                return False

            async def execute(self, sql, *args):
                if 'INSERT INTO logs' in sql:
                    self.inserts.append(args[0])

            async def fetchval(self, sql, *args):
                return None

            async def fetch(self, sql, *args):
                return []

            async def fetchrow(self, sql, *args):
                return {'id': 'pa-1', 'order_id': 'ord-1', 'status': 'PENDING'}

        conn = _Conn()
        app = Starlette(
            routes=[Route('/ris/prior-auth/{id}/decision',
                          PriorAuthDecisionHandler, methods=['POST'])],
            middleware=[Middleware(_FakeAuth,
                                   user=User({'id': 7, 'tenant': 'default',
                                              'permissions': ['PRIOR_AUTH_WRITE']}))],
        )
        body = {'action': action}
        if action == 'approve':
            body.update({'auth_number': 'AUTH-1', 'expiry_date': '2026-09-21'})
        with patch('api.prior_auth.get_conn', return_value=conn):
            client = TestClient(app)
            resp = client.post('/ris/prior-auth/pa-1/decision', json=body)
        assert resp.status_code == 200, resp.text
        events = [_json.loads(row)['event'] for row in conn.inserts]
        return events

    @pytest.mark.asyncio
    @pytest.mark.parametrize('action,event', [
        ('approve', 'prior_auth.approved'),
        ('deny', 'prior_auth.denied'),
    ])
    async def test_decision_audits_outcome(self, action, event):
        events = self._post_decision(action)
        assert event in events, \
            f'decision {action} must audit as {event}'
