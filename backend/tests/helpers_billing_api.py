"""Shared driver for billing API tests — invokes handlers directly."""

import json

from unittest.mock import patch


async def call_unbilled(user_id=1, tenant='default'):
    """Drive RisUnbilledHandler.get with a minimal scope; return body."""
    from api.billing import RisUnbilledHandler

    scope = type('S', (), {
        'path_params': {},
        'query_params': {},
        'user': type('U', (), {'id': user_id, 'tenant': tenant,
                      'is_authenticated': True, 'admin': True,
                      'permissions': ['*']})(),
    })()
    # HTTPEndpoint needs scope/receive/send; bypass dispatch and
    # invoke the method on a lightweight stand-in instance.
    handler = object.__new__(RisUnbilledHandler)
    resp = await RisUnbilledHandler.get(handler, scope)