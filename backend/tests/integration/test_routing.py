from unittest.mock import AsyncMock, MagicMock, patch

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.routing import Route
from starlette.testclient import TestClient

from api.auth import User
from api.routing import RoutingHandler
from services.ingestion.routing import evaluate_routing_rules, _match_condition


class _FakeAuth(BaseHTTPMiddleware):
    def __init__(self, app, user=None):
        super().__init__(app)
        self._user = user or User({'id': 1, 'permissions': ['ROUTING_READ', 'ROUTING_WRITE']})

    async def dispatch(self, request, call_next):
        request.scope['user'] = self._user
        request.scope['auth'] = None
        return await call_next(request)


def _make_app(user=None):
    return Starlette(
        routes=[Route('/routing', endpoint=RoutingHandler)],
        middleware=[Middleware(_FakeAuth, user=user)],
    )


class TestMatchCondition:
    def test_exact_match(self):
        assert _match_condition({"modality": "CT"}, {"modality": "CT"})
        assert not _match_condition({"modality": "CT"}, {"modality": "MR"})

    def test_operator_eq(self):
        assert _match_condition({"priority": {"eq": "high"}}, {"priority": "high"})
        assert not _match_condition({"priority": {"eq": "high"}}, {"priority": "low"})

    def test_operator_contains(self):
        assert _match_condition({"accession_number": {"contains": "URGENT"}}, {"accession_number": "URGENT-123"})
        assert not _match_condition({"accession_number": {"contains": "URGENT"}}, {"accession_number": "ROUTINE-456"})

    def test_operator_gt_gte(self):
        assert _match_condition({"priority": {"gt": "5"}}, {"priority": "10"})
        assert _match_condition({"priority": {"gte": "10"}}, {"priority": "10"})
        assert not _match_condition({"priority": {"gt": "10"}}, {"priority": "5"})

    def test_operator_lt_lte(self):
        assert _match_condition({"priority": {"lt": "10"}}, {"priority": "5"})
        assert _match_condition({"priority": {"lte": "5"}}, {"priority": "5"})
        assert not _match_condition({"priority": {"lt": "5"}}, {"priority": "10"})

    def test_or_condition(self):
        cond = {"$or": [{"modality": "CT"}, {"modality": "MR"}]}
        assert _match_condition(cond, {"modality": "CT"})
        assert _match_condition(cond, {"modality": "MR"})
        assert not _match_condition(cond, {"modality": "DX"})

    def test_multiple_fields(self):
        cond = {"modality": "CT", "station_ae_title": "STATION-A"}
        assert _match_condition(cond, {"modality": "CT", "station_ae_title": "STATION-A"})
        assert not _match_condition(cond, {"modality": "CT", "station_ae_title": "STATION-B"})

    def test_empty_conditions(self):
        assert _match_condition({}, {"modality": "CT"})
        assert _match_condition({}, {})

    def test_none_value(self):
        assert _match_condition({"modality": {"eq": None}}, {})
        assert not _match_condition({"modality": {"eq": "CT"}}, {})
        assert not _match_condition({"accession_number": {"contains": "X"}}, {})

    def test_ne_operator(self):
        assert _match_condition({"modality": {"ne": "MR"}}, {"modality": "CT"})
        assert not _match_condition({"modality": {"ne": "MR"}}, {"modality": "MR"})

    def test_numeric_cmp(self):
        assert _match_condition({"priority": {"gt": 5}}, {"priority": 10})
        assert _match_condition({"priority": {"gte": 10}}, {"priority": 10})
        assert not _match_condition({"priority": {"gt": 10}}, {"priority": 5})

    def test_int_vs_str_cmp(self):
        assert _match_condition({"priority": {"gt": "5"}}, {"priority": "10"})
        assert not _match_condition({"priority": {"gt": "10"}}, {"priority": "5"})


class TestRoutingEngine:
    async def test_evaluate_ct_routes(self):
        rules = [
            {'id': 'r1', 'name': 'CT to PACS-A', 'conditions': {"modality": "CT"}, 'destination': 'pacs-a.example.com', 'priority': 10, 'enabled': True},
            {'id': 'r2', 'name': 'MR to PACS-B', 'conditions': {"modality": "MR"}, 'destination': 'pacs-b.example.com', 'priority': 10, 'enabled': True},
        ]
        with (
            patch('services.ingestion.routing.get_conn') as mock_conn,
            patch('services.ingestion.routing.RoutingRule') as MockRule,
        ):
            mock_conn.return_value.__aenter__.return_value = None
            MockRule.return_value.list_all = AsyncMock(return_value=rules)
            destinations = await evaluate_routing_rules({"modality": "CT"})
            assert len(destinations) == 1
            assert destinations[0]['destination'] == 'pacs-a.example.com'

    async def test_evaluate_no_match(self):
        rules = [
            {'id': 'r1', 'name': 'CT only', 'conditions': {"modality": "CT"}, 'destination': 'pacs-a.example.com', 'priority': 10, 'enabled': True},
        ]
        with (
            patch('services.ingestion.routing.get_conn') as mock_conn,
            patch('services.ingestion.routing.RoutingRule') as MockRule,
        ):
            mock_conn.return_value.__aenter__.return_value = None
            MockRule.return_value.list_all = AsyncMock(return_value=rules)
            destinations = await evaluate_routing_rules({"modality": "MR"})
            assert len(destinations) == 0

    async def test_evaluate_operator_condition(self):
        rules = [
            {'id': 'r1', 'name': 'Urgent', 'conditions': {"accession_number": {"contains": "URGENT"}}, 'destination': 'urgent.example.com', 'priority': 1, 'enabled': True},
        ]
        with (
            patch('services.ingestion.routing.get_conn') as mock_conn,
            patch('services.ingestion.routing.RoutingRule') as MockRule,
        ):
            mock_conn.return_value.__aenter__.return_value = None
            MockRule.return_value.list_all = AsyncMock(return_value=rules)
            destinations = await evaluate_routing_rules({"accession_number": "URGENT-789", "modality": "CT"})
            assert len(destinations) == 1
            assert destinations[0]['destination'] == 'urgent.example.com'

    async def test_list_all_with_limit(self):
        with (
            patch('services.ingestion.routing.get_conn') as mock_get,
            patch('services.ingestion.routing.RoutingRule') as MockRule,
        ):
            mock_get.return_value.__aenter__.return_value = None
            MockRule.return_value.list_all = AsyncMock(return_value=[
                {'id': 'r1', 'name': 'Rule 1', 'destination': 'dest-a', 'conditions': {}, 'priority': 1, 'enabled': True},
                {'id': 'r2', 'name': 'Rule 2', 'destination': 'dest-b', 'conditions': {}, 'priority': 2, 'enabled': True},
            ])
            destinations = await evaluate_routing_rules({"modality": "CT"})
            assert len(destinations) == 2

    async def test_evaluate_empty_rules(self):
        with (
            patch('services.ingestion.routing.get_conn') as mock_conn,
            patch('services.ingestion.routing.RoutingRule') as MockRule,
        ):
            mock_conn.return_value.__aenter__.return_value = None
            MockRule.return_value.list_all = AsyncMock(return_value=[])
            destinations = await evaluate_routing_rules({})
            assert destinations == []


class TestRoutingApiPagination:
    def test_get_routing_with_pagination(self):
        mock_conn = MagicMock()
        mock_conn.fetch = AsyncMock(return_value=[
            {'id': 'r1', 'name': 'Rule 1', 'description': '', 'conditions': '{}', 'destination': 'dest-a', 'priority': 1, 'enabled': True, 'created_at': None, 'updated_at': None},
        ])
        mock_conn.fetchval = AsyncMock(return_value=1)

        with patch('api.routing.get_conn') as mock_get:
            mock_get.return_value.__aenter__.return_value = mock_conn
            mock_get.return_value.__aexit__ = AsyncMock(return_value=None)

            client = TestClient(_make_app())
            resp = client.get('/routing?page=1&per_page=10')

        assert resp.status_code == 200
        body = resp.json()
        assert 'data' in body
        assert body['pagination']['page'] == 1
        assert body['pagination']['per_page'] == 10
        assert body['pagination']['total'] == 1

    def test_get_routing_defaults_to_all(self):
        mock_conn = MagicMock()
        mock_conn.fetch = AsyncMock(return_value=[])
        mock_conn.fetchval = AsyncMock(return_value=0)

        with patch('api.routing.get_conn') as mock_get:
            mock_get.return_value.__aenter__.return_value = mock_conn
            mock_get.return_value.__aexit__ = AsyncMock(return_value=None)

            client = TestClient(_make_app())
            resp = client.get('/routing')

        assert resp.status_code == 200
        body = resp.json()
        assert body['pagination']['page'] == 1
        assert body['pagination']['per_page'] == 50
        assert body['pagination']['total'] == 0
