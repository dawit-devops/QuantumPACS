import pytest


def _paired_routes():
    """(marked v1 route, its v2 alias) pairs, in registration order.

    _V2_ALIASES is built in _V1_ROUTES order (skipping excluded prefixes and
    non-Route entries), so the pairing is positional — some v1 routes are
    registered with a literal '/v2/...' path already (dashboard endpoints)
    and must not be mistaken for aliases via path slicing."""
    from api.routes import _V1_ROUTES, _V2_ALIASES, _V2_EXCLUDE_PREFIXES
    from starlette.routing import Route, WebSocketRoute

    marked = [
        r for r in _V1_ROUTES
        if isinstance(r, (Route, WebSocketRoute))
        and getattr(r, '_v2_alias', False)
        and not any(r.path.startswith(p) for p in _V2_EXCLUDE_PREFIXES)
    ]
    assert len(marked) == len(_V2_ALIASES)
    return list(zip(marked, _V2_ALIASES))


@pytest.fixture
def paired():
    return _paired_routes()


class TestV2AliasFramework:
    """NEW #5: every v2()-marked v1 route must be mirrored under /v2 with the
    identical endpoint and methods — a dropped alias is a silent 404 for
    v2 clients, and a broadened method set turns POST-only write endpoints
    (token exchange, webhook test ping, HL7 receiver) into GET-routable
    ones."""

    def test_every_marked_v1_route_gets_an_alias(self, paired):
        assert len(paired) > 10
        for v1, alias in paired:
            expected = v1.path if v1.path.startswith('/v2/') else '/v2' + v1.path
            assert alias.path == expected, v1.path

    def test_alias_endpoints_match_v1(self, paired):
        for v1, alias in paired:
            assert alias.endpoint is v1.endpoint, f'{alias.path} endpoint drifted'

    def test_alias_methods_never_broader_than_v1(self, paired):
        for v1, alias in paired:
            if not hasattr(alias, 'methods'):
                continue
            assert alias.methods == v1.methods, (
                f'{alias.path} methods {alias.methods} drifted from v1 {v1.methods}'
            )

    def test_post_only_write_endpoints_keep_post_only_aliases(self, paired):
        alias_paths = {alias.path: alias for _, alias in paired}
        for path in ('/v2/oauth/token', '/v2/webhooks/test', '/v2/hl7'):
            assert alias_paths[path].methods == {'POST'}, path

    def test_websocket_route_is_aliased(self, paired):
        ws_alias = next(alias for _, alias in paired if alias.path == '/v2/ws')
        ws_v1 = next(v1 for v1, _ in paired if v1.path == '/ws')
        assert ws_alias.endpoint is ws_v1.endpoint
