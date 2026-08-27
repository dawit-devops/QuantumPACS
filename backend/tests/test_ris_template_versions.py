"""R2-02-07/09 — report-template versioning: publish + rollback.

Templates are clinical artifacts; edits must be versioned and reversible.
publish_version snapshots the new body as the active version; rollback
re-activates any prior version without data loss (append-only history).
"""

import pytest

from unittest.mock import AsyncMock, patch


class _Conn:
    def __init__(self):
        self.calls = []
        self._fetch = []
        self._fetchrow = None

    def set_fetch(self, rows):
        self._fetch = rows

    def set_fetchrow(self, row):
        self._fetchrow = row

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def execute(self, sql, *args):
        self.calls.append(('execute', sql, args))

    async def fetch(self, sql, *args):
        self.calls.append(('fetch', sql, args))
        return self._fetch

    async def fetchrow(self, sql, *args):
        self.calls.append(('fetchrow', sql, args))
        if getattr(self, '_fetchrow_seq', None):
            return self._fetchrow_seq.pop(0)
        return self._fetchrow


class TestTemplateVersioningDb:
    @pytest.mark.asyncio
    async def test_publish_snapshots_and_activates(self):
        from db.ris_templates import RisReportTemplates

        conn = _Conn()
        # fetchrow sequence: MAX(version) probe, then INSERT .. RETURNING.
        conn._fetchrow_seq = [{'v': 2}, {'id': 'tpl-1', 'version_number': 3}]
        tpl = RisReportTemplates(conn)
        row = await tpl.publish_version(
            'tpl-1', findings='New findings body',
            impression='New impression', published_by='admin-1')
        assert row['version_number'] == 3
        inserts = [c for c in conn.calls if 'INSERT INTO ris_report_template_versions' in c[1]]
        assert inserts, 'publish must snapshot a version row'
        updates = [c for c in conn.calls if 'UPDATE ris_report_templates' in c[1]]
        assert updates, 'publish must activate on the template row'

    @pytest.mark.asyncio
    async def test_rollback_reactivates_prior_version(self):
        from db.ris_templates import RisReportTemplates

        conn = _Conn()
        target = {'id': 'tpl-1', 'version_number': 2,
                  'findings_template': 'Old', 'impression_template': 'Old imp'}
        conn._fetchrow_seq = [target]
        tpl = RisReportTemplates(conn)
        with patch.object(RisReportTemplates, 'apply_version',
                          AsyncMock(return_value=target)) as apply_v:
            row = await tpl.rollback_to_version('tpl-1', 2, actor='admin-1')
        apply_v.assert_awaited_once()
        assert row['version_number'] == 2
        events = [c for c in conn.calls if 'INSERT INTO ris_claim_events' in c[1]]
        assert not events  # billing ledger untouched — separate concern

    @pytest.mark.asyncio
    async def test_list_versions_ordered(self):
        from db.ris_templates import RisReportTemplates

        conn = _Conn()
        versions = [{'id': 'v2', 'version_number': 2},
                    {'id': 'v1', 'version_number': 1}]
        conn.set_fetch(versions)
        rows = await RisReportTemplates(conn).list_versions('tpl-1')
        assert [r['version_number'] for r in rows] == [2, 1]
        sql = conn.calls[0][1]
        assert 'ris_report_template_versions' in sql
        assert 'DESC' in sql


class TestTemplateVersionApi:
    def _app(self):
        from starlette.applications import Starlette
        from starlette.middleware import Middleware
        from starlette.middleware.base import BaseHTTPMiddleware
        from starlette.routing import Route

        from api.auth import User
        from api.reports import (
            TemplateVersionsHandler,
            TemplatePublishHandler,
            TemplateRollbackHandler,
        )

        class _FakeAuth(BaseHTTPMiddleware):
            def __init__(self, app, user=None):
                super().__init__(app)
                self._user = user or User({'id': 1, 'permissions': []})

            async def dispatch(self, request, call_next):
                request.scope['user'] = self._user
                request.scope['auth'] = None
                return await call_next(request)

        return Starlette(
            routes=[
                Route('/ris/report-templates/{id}/versions',
                      endpoint=TemplateVersionsHandler),
                Route('/ris/report-templates/{id}/publish',
                      endpoint=TemplatePublishHandler, methods=['POST']),
                Route('/ris/report-templates/{id}/rollback',
                      endpoint=TemplateRollbackHandler, methods=['POST']),
            ],
            middleware=[Middleware(_FakeAuth,
                                   user=User({'id': 7, 'tenant': 'default',
                                              'permissions': ['REPORT_TEMPLATE_ADMIN']}))],
        )

    def test_publish_endpoint(self):
        from starlette.testclient import TestClient
        client = TestClient(self._app())
        with patch('api.reports.get_conn', return_value=_Conn()), \
             patch('db.ris_templates.RisReportTemplates.publish_version',
                   AsyncMock(return_value={'id': 'tpl-1', 'version_number': 4})):
            resp = client.post('/ris/report-templates/tpl-1/publish', json={
                'findings': 'F', 'impression': 'I'})
        assert resp.status_code == 200, resp.text
        assert resp.json()['data']['version_number'] == 4

    def test_rollback_endpoint_unknown_version_404(self):
        from starlette.testclient import TestClient
        client = TestClient(self._app())
        with patch('api.reports.get_conn', return_value=_Conn()), \
             patch('db.ris_templates.RisReportTemplates.rollback_to_version',
                   AsyncMock(return_value=None)):
            resp = client.post('/ris/report-templates/tpl-1/rollback',
                               json={'version': 99})
        assert resp.status_code == 404
