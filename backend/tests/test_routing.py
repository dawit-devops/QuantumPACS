from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.ingestion.routing import _match_condition, _cmp, evaluate_routing_rules


class TestCompare:
    def test_both_none(self):
        assert _cmp(None, None) == 0

    def test_a_none(self):
        assert _cmp(None, 5) == -1

    def test_b_none(self):
        assert _cmp(5, None) == 1

    def test_numeric_gt(self):
        assert _cmp(10, 5) == 1

    def test_numeric_lt(self):
        assert _cmp(3, 7) == -1

    def test_numeric_eq(self):
        assert _cmp(5, 5) == 0

    def test_string_gt(self):
        assert _cmp('z', 'a') == 1

    def test_string_lt(self):
        assert _cmp('a', 'z') == -1

    def test_string_vs_numeric(self):
        assert _cmp('5', 10) == -1

    def test_float_comparison(self):
        assert _cmp(5.5, 5.0) == 1
        assert _cmp(5.0, 5.5) == -1
        assert _cmp(5.0, 5.0) == 0


class TestMatchCondition:
    def test_exact_match(self):
        assert _match_condition({'modality': 'CT'}, {'modality': 'CT'})
        assert not _match_condition({'modality': 'CT'}, {'modality': 'MR'})

    def test_operator_eq(self):
        assert _match_condition({'priority': {'eq': 'high'}}, {'priority': 'high'})
        assert not _match_condition({'priority': {'eq': 'high'}}, {'priority': 'low'})

    def test_operator_ne(self):
        assert _match_condition({'modality': {'ne': 'MR'}}, {'modality': 'CT'})
        assert not _match_condition({'modality': {'ne': 'MR'}}, {'modality': 'MR'})

    def test_operator_contains(self):
        assert _match_condition({'accession': {'contains': 'URGENT'}}, {'accession': 'URGENT-123'})
        assert not _match_condition({'accession': {'contains': 'URGENT'}}, {'accession': 'ROUTINE-456'})
        assert not _match_condition({'accession': {'contains': 'URGENT'}}, {})

    def test_operator_gt(self):
        assert _match_condition({'priority': {'gt': '5'}}, {'priority': '10'})
        assert not _match_condition({'priority': {'gt': '10'}}, {'priority': '5'})

    def test_operator_gte(self):
        assert _match_condition({'priority': {'gte': '10'}}, {'priority': '10'})
        assert _match_condition({'priority': {'gte': '5'}}, {'priority': '10'})
        assert not _match_condition({'priority': {'gte': '10'}}, {'priority': '5'})

    def test_operator_lt(self):
        assert _match_condition({'priority': {'lt': '10'}}, {'priority': '5'})
        assert not _match_condition({'priority': {'lt': '5'}}, {'priority': '10'})

    def test_operator_lte(self):
        assert _match_condition({'priority': {'lte': '5'}}, {'priority': '5'})
        assert not _match_condition({'priority': {'lte': '5'}}, {'priority': '10'})

    def test_or_condition(self):
        cond = {'$or': [{'modality': 'CT'}, {'modality': 'MR'}]}
        assert _match_condition(cond, {'modality': 'CT'})
        assert _match_condition(cond, {'modality': 'MR'})
        assert not _match_condition(cond, {'modality': 'DX'})

    def test_or_with_single_match(self):
        cond = {'$or': [{'modality': 'CT'}, {'modality': 'MR', 'station': 'A'}]}
        assert _match_condition(cond, {'modality': 'CT'})
        assert _match_condition(cond, {'modality': 'MR', 'station': 'A'})
        assert not _match_condition(cond, {'modality': 'MR', 'station': 'B'})

    def test_or_not_a_list(self):
        cond = {'$or': 'not a list'}
        assert not _match_condition(cond, {'modality': 'CT'})

    def test_or_empty_list(self):
        assert not _match_condition({'$or': []}, {'modality': 'CT'})

    def test_multiple_fields_and(self):
        cond = {'modality': 'CT', 'station_ae_title': 'STATION-A'}
        assert _match_condition(cond, {'modality': 'CT', 'station_ae_title': 'STATION-A'})
        assert not _match_condition(cond, {'modality': 'CT', 'station_ae_title': 'STATION-B'})

    def test_empty_conditions_match_anything(self):
        assert _match_condition({}, {'modality': 'CT'})
        assert _match_condition({}, {})

    def test_missing_field_in_metadata(self):
        assert not _match_condition({'modality': 'CT'}, {})

    def test_none_field_value(self):
        assert not _match_condition({'modality': 'CT'}, {'modality': None})

    def test_operator_with_none(self):
        assert _match_condition({'modality': {'eq': None}}, {})
        assert not _match_condition({'modality': {'eq': 'CT'}}, {})

    def test_numeric_values_work(self):
        assert _match_condition({'priority': {'gt': 5}}, {'priority': 10})
        assert _match_condition({'priority': {'gte': 10}}, {'priority': 10})
        assert not _match_condition({'priority': {'gt': 10}}, {'priority': 5})

    def test_int_vs_str_comparison(self):
        assert _match_condition({'priority': {'gt': '5'}}, {'priority': '10'})
        assert not _match_condition({'priority': {'gt': '10'}}, {'priority': '5'})

    def test_non_dict_condition(self):
        assert _match_condition(True, {})
        assert not _match_condition(False, {})

    def test_invalid_operator_ignored(self):
        result = _match_condition({'modality': {'unknown_op': 'CT'}}, {'modality': 'CT'})
        assert result is False


class TestEvaluateRoutingRules:
    async def test_ct_routes_to_pacs_a(self):
        rules = [
            {'id': 'r1', 'name': 'CT to PACS-A', 'conditions': {'modality': 'CT'}, 'destination': 'pacs-a', 'priority': 10, 'enabled': True},
        ]
        with patch('services.ingestion.routing.get_conn') as mock_conn, \
             patch('services.ingestion.routing.RoutingRule') as MockRule:
            mock_conn.return_value.__aenter__.return_value = None
            MockRule.return_value.list_all = AsyncMock(return_value=rules)
            destinations = await evaluate_routing_rules({'modality': 'CT'})
            assert len(destinations) == 1
            assert destinations[0]['destination'] == 'pacs-a'

    async def test_no_match_returns_empty(self):
        rules = [
            {'id': 'r1', 'name': 'CT only', 'conditions': {'modality': 'CT'}, 'destination': 'pacs-a', 'priority': 10, 'enabled': True},
        ]
        with patch('services.ingestion.routing.get_conn') as mock_conn, \
             patch('services.ingestion.routing.RoutingRule') as MockRule:
            mock_conn.return_value.__aenter__.return_value = None
            MockRule.return_value.list_all = AsyncMock(return_value=rules)
            destinations = await evaluate_routing_rules({'modality': 'MR'})
            assert destinations == []

    async def test_operator_condition_evaluates(self):
        rules = [
            {'id': 'r1', 'name': 'Urgent', 'conditions': {'accession': {'contains': 'URGENT'}}, 'destination': 'urgent-pacs', 'priority': 1, 'enabled': True},
        ]
        with patch('services.ingestion.routing.get_conn') as mock_conn, \
             patch('services.ingestion.routing.RoutingRule') as MockRule:
            mock_conn.return_value.__aenter__.return_value = None
            MockRule.return_value.list_all = AsyncMock(return_value=rules)
            destinations = await evaluate_routing_rules({'accession': 'URGENT-789', 'modality': 'CT'})
            assert len(destinations) == 1
            assert destinations[0]['destination'] == 'urgent-pacs'

    async def test_multiple_rules_matched(self):
        rules = [
            {'id': 'r1', 'name': 'CT to A', 'conditions': {'modality': 'CT'}, 'destination': 'pacs-a', 'priority': 10, 'enabled': True},
            {'id': 'r2', 'name': 'CT to B', 'conditions': {'modality': 'CT'}, 'destination': 'pacs-b', 'priority': 20, 'enabled': True},
        ]
        with patch('services.ingestion.routing.get_conn') as mock_conn, \
             patch('services.ingestion.routing.RoutingRule') as MockRule:
            mock_conn.return_value.__aenter__.return_value = None
            MockRule.return_value.list_all = AsyncMock(return_value=rules)
            destinations = await evaluate_routing_rules({'modality': 'CT'})
            assert len(destinations) == 2

    async def test_empty_rules(self):
        with patch('services.ingestion.routing.get_conn') as mock_conn, \
             patch('services.ingestion.routing.RoutingRule') as MockRule:
            mock_conn.return_value.__aenter__.return_value = None
            MockRule.return_value.list_all = AsyncMock(return_value=[])
            destinations = await evaluate_routing_rules({})
            assert destinations == []

    async def test_db_error_returns_empty(self):
        with patch('services.ingestion.routing.get_conn') as mock_conn:
            mock_conn.return_value.__aenter__.side_effect = Exception('db down')
            destinations = await evaluate_routing_rules({'modality': 'CT'})
            assert destinations == []

    async def test_string_conditions_parsed(self):
        rules = [
            {'id': 'r1', 'name': 'CT', 'conditions': '{"modality": "CT"}', 'destination': 'pacs-a', 'priority': 10, 'enabled': True},
        ]
        with patch('services.ingestion.routing.get_conn') as mock_conn, \
             patch('services.ingestion.routing.RoutingRule') as MockRule:
            mock_conn.return_value.__aenter__.return_value = None
            MockRule.return_value.list_all = AsyncMock(return_value=rules)
            destinations = await evaluate_routing_rules({'modality': 'CT'})
            assert len(destinations) == 1

    async def test_invalid_rule_conditions_skipped(self):
        rules = [
            {'id': 'r1', 'name': 'Bad', 'conditions': '{invalid json', 'destination': 'pacs-a', 'priority': 10, 'enabled': True},
            {'id': 'r2', 'name': 'Good', 'conditions': '{"modality": "CT"}', 'destination': 'pacs-b', 'priority': 10, 'enabled': True},
        ]
        with patch('services.ingestion.routing.get_conn') as mock_conn, \
             patch('services.ingestion.routing.RoutingRule') as MockRule:
            mock_conn.return_value.__aenter__.return_value = None
            MockRule.return_value.list_all = AsyncMock(return_value=rules)
            destinations = await evaluate_routing_rules({'modality': 'CT'})
            assert len(destinations) == 1
            assert destinations[0]['destination'] == 'pacs-b'

    async def test_tenant_id_filtering(self):
        rules = [
            {'id': 'r1', 'name': 'CT for tenant A', 'conditions': {'modality': 'CT'}, 'destination': 'pacs-a', 'priority': 10, 'enabled': True},
        ]
        with patch('services.ingestion.routing.get_conn') as mock_conn, \
             patch('services.ingestion.routing.RoutingRule') as MockRule:
            mock_conn.return_value.__aenter__.return_value = None
            MockRule.return_value.list_all = AsyncMock(return_value=rules)
            destinations = await evaluate_routing_rules({'modality': 'CT'}, tenant_id='tenant-a')
            MockRule.return_value.list_all.assert_called_once_with(enabled_only=True, tenant_id='tenant-a')
            assert len(destinations) == 1
