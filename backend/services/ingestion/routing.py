import json

from db.conn import get_conn
from db.routing_rule import RoutingRule
from log import get_logger

log = get_logger(__name__)


def _cmp(a, b):
    if a is None and b is None:
        return 0
    if a is None:
        return -1
    if b is None:
        return 1
    try:
        fa, fb = float(a), float(b)
        if fa > fb:
            return 1
        if fa < fb:
            return -1
        return 0
    except (ValueError, TypeError):
        sa, sb = str(a), str(b)
        if sa > sb:
            return 1
        if sa < sb:
            return -1
        return 0


_OPERATORS = {
    'eq': lambda a, b: a == b,
    'ne': lambda a, b: a != b,
    'contains': lambda a, b: b in (a or ''),
    'gt': lambda a, b: _cmp(a, b) > 0,
    'gte': lambda a, b: _cmp(a, b) >= 0,
    'lt': lambda a, b: _cmp(a, b) < 0,
    'lte': lambda a, b: _cmp(a, b) <= 0,
}


def _match_condition(condition, metadata) -> bool:
    if not isinstance(condition, dict):
        return bool(condition)

    for key, spec in condition.items():
        if key == '$or':
            if not isinstance(spec, list):
                return False
            if not any(_match_condition(c, metadata) for c in spec):
                return False
            continue

        field_val = metadata.get(key)
        if isinstance(spec, dict) and any(op in spec for op in _OPERATORS):
            operator = next(op for op in spec if op in _OPERATORS)
            expected = spec[operator]
            op_fn = _OPERATORS[operator]
            if not op_fn(field_val, expected):
                return False
        else:
            if field_val != spec:
                return False

    return True


async def evaluate_routing_rules(metadata: dict, tenant_id: str = '') -> list[dict]:
    destinations = []
    try:
        async with get_conn() as conn:
            rules = await RoutingRule(conn).list_all(enabled_only=True, tenant_id=tenant_id)
    except Exception:
        log.warning('Failed to load routing rules')
        return destinations

    for rule in rules:
        try:
            conditions = rule.get('conditions', {})
            if isinstance(conditions, str):
                conditions = json.loads(conditions)
            if _match_condition(conditions, metadata):
                destinations.append({
                    'rule_id': str(rule['id']),
                    'rule_name': rule['name'],
                    'destination': rule['destination'],
                })
        except Exception:
            log.warning('Error evaluating rule %s', rule.get('name', '?'), exc_info=True)

    return destinations
