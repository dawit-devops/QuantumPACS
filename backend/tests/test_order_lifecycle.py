"""Order lifecycle state machine tests (E-RIS-03).

Behaviors verified through the service's public interface: valid transitions
apply + audit, illegal transitions raise InvalidTransitionError without
touching the row, missing orders return None.
"""
from unittest.mock import AsyncMock

import pytest

from services.order_lifecycle.service import (
    OrderLifecycleService, InvalidTransitionError, VALID_TRANSITIONS,
)


def _order(status='ORDERED', order_id='ord-1'):
    return {'id': order_id, 'status': status}


def _service(mock_conn):
    return OrderLifecycleService(mock_conn)


class TestValidTransitions:
    @pytest.mark.parametrize('current,next_status', [
        ('ORDERED', 'SCHEDULED'),
        ('SCHEDULED', 'ARRIVED'),
        ('ARRIVED', 'IN_PROGRESS'),
        ('IN_PROGRESS', 'COMPLETED'),
        ('COMPLETED', 'READ'),
        ('READ', 'SIGNED'),
        ('ORDERED', 'CANCELLED'),
        ('CANCELLED', 'ORDERED'),
    ])
    async def test_transition_applies_and_audits(self, current, next_status):
        conn = AsyncMock()
        conn.fetchrow.side_effect = [
            _order(status=current),  # read current order
            {'id': 'ord-1'},  # update returning id
            _order(status=next_status),  # updated row returned
        ]
        result = await _service(conn).transition('ord-1', next_status, 'user-1', 'reason')
        assert result['status'] == next_status
        # audit logged with from/to
        assert conn.execute.await_count == 1

    async def test_transition_audit_details(self):
        conn = AsyncMock()
        conn.fetchrow.side_effect = [
            _order(status='ORDERED'),
            {'id': 'ord-1'},
            _order(status='SCHEDULED'),
        ]
        await _service(conn).transition('ord-1', 'SCHEDULED', 'user-1', 'booked')
        assert conn.execute.await_count == 1
        sql, payload = conn.execute.await_args.args[:2]
        assert 'INSERT INTO logs' in sql
        import json
        data = json.loads(payload)
        assert data['event'] == 'ORDER_STATUS_TRANSITION'
        assert data['actor'] == 'user-1'
        assert data['resource'] == {'type': 'ris_orders', 'id': 'ord-1'}
        assert data['detail'] == {'from': 'ORDERED', 'to': 'SCHEDULED', 'reason': 'booked'}


class TestInvalidTransitions:
    @pytest.mark.parametrize('current,next_status', [
        ('ORDERED', 'SIGNED'),     # skip ahead
        ('ORDERED', 'READ'),
        ('SIGNED', 'COMPLETED'),   # terminal
        ('SCHEDULED', 'READ'),
    ])
    async def test_illegal_transition_raises(self, current, next_status):
        conn = AsyncMock()
        conn.fetchrow.side_effect = [_order(status=current)]
        with pytest.raises(InvalidTransitionError):
            await _service(conn).transition('ord-1', next_status, 'user-1')
        # no update, no audit
        assert conn.fetchrow.await_count == 1
        assert conn.execute.await_count == 0

    async def test_unknown_target_status_raises(self):
        conn = AsyncMock()
        conn.fetchrow.side_effect = [_order(status='ORDERED')]
        with pytest.raises(InvalidTransitionError):
            await _service(conn).transition('ord-1', 'NOT_A_STATUS', 'user-1')


class TestNotFound:
    async def test_missing_order_returns_none(self):
        conn = AsyncMock()
        conn.fetchrow.return_value = None
        result = await _service(conn).transition('missing', 'SCHEDULED', 'user-1')
        assert result is None
        assert conn.execute.await_count == 0


class TestTransitionMap:
    def test_valid_transitions_cover_all_statuses(self):
        statuses = {'ORDERED', 'SCHEDULED', 'ARRIVED', 'IN_PROGRESS',
                    'COMPLETED', 'READ', 'SIGNED', 'CANCELLED'}
        assert set(VALID_TRANSITIONS) == statuses
        for current, allowed in VALID_TRANSITIONS.items():
            assert current not in allowed, f'self-loop on {current}'
            for target in allowed:
                assert target in statuses