from starlette.endpoints import HTTPEndpoint

import httpx

from api.rbac import requires_permission
from api.permissions import Permission
from api.response import ok, created, not_found, api_error
from api.validate import parse_body
from api.schemas.oauth_providers import CreateOAuthProviderRequest, UpdateOAuthProviderRequest
from db.conn import get_conn
from db.oauth_providers import OAuthProviders


class OAuthProvidersHandler(HTTPEndpoint):
    @requires_permission(Permission.TENANT_ADMIN)
    async def get(self, request):
        async with get_conn() as conn:
            providers = await OAuthProviders(conn).get_all()
        return ok({'data': providers})

    @requires_permission(Permission.TENANT_ADMIN)
    async def post(self, request):
        body = await parse_body(CreateOAuthProviderRequest, request)
        async with get_conn() as conn:
            existing = await OAuthProviders(conn).get_by_issuer(body.issuer)
            if existing:
                return ok({'error': 'Provider with this issuer already exists'})
            provider_id = await OAuthProviders(conn).create(
                issuer=body.issuer, client_id=body.client_id,
                client_secret=body.client_secret,
                jwks_uri=body.jwks_uri, token_url=body.token_url,
                redirect_uri=body.redirect_uri, scope=body.scope,
                groups_claim=body.groups_claim,
                groups_map=body.groups_map,
                auto_provision=body.auto_provision, enabled=body.enabled,
                tenant_id=body.tenant_id,
                slug=body.slug,
                default_role=body.default_role,
            )
        return created({'id': provider_id})


class OAuthProviderHandler(HTTPEndpoint):
    @requires_permission(Permission.TENANT_ADMIN)
    async def get(self, request):
        provider_id = request.path_params['id']
        async with get_conn() as conn:
            provider = await OAuthProviders(conn).get(provider_id)
        if not provider:
            return not_found('OAuth provider not found')
        return ok(provider)

    @requires_permission(Permission.TENANT_ADMIN)
    async def put(self, request):
        provider_id = request.path_params['id']
        body = await parse_body(UpdateOAuthProviderRequest, request)
        async with get_conn() as conn:
            provider = await OAuthProviders(conn).get(provider_id)
            if not provider:
                return not_found('OAuth provider not found')
            await OAuthProviders(conn).patch(
                provider_id,
                body.model_dump(exclude_none=True),
            )
        return ok({})

    @requires_permission(Permission.TENANT_ADMIN)
    async def delete(self, request):
        provider_id = request.path_params['id']
        async with get_conn() as conn:
            provider = await OAuthProviders(conn).get(provider_id)
            if not provider:
                return not_found('OAuth provider not found')
            await OAuthProviders(conn).delete(provider_id)
        return ok({})

    @requires_permission(Permission.TENANT_ADMIN)
    async def post(self, request):
        """ADM-16: Test OIDC connection — hit discovery + JWKS endpoints."""
        provider_id = request.path_params['id']
        async with get_conn() as conn:
            provider = await OAuthProviders(conn).get(provider_id)
        if not provider:
            return not_found('OAuth provider not found')
        issuer = provider.get('issuer', '')
        discovery_url = f"{issuer.rstrip('/')}/.well-known/openid-configuration"
        jwks_uri = provider.get('jwks_uri') or ''
        results: dict = {}
        async with httpx.AsyncClient(timeout=10) as client:
            # Discovery
            try:
                resp = await client.get(discovery_url)
                results['discovery'] = {
                    'status': resp.status_code,
                    'ok': resp.status_code == 200,
                }
                if resp.status_code == 200:
                    doc = resp.json()
                    if not jwks_uri:
                        jwks_uri = doc.get('jwks_uri', '')
                        results['discovery']['jwks_uri'] = jwks_uri
            except Exception as e:
                results['discovery'] = {'ok': False, 'error': str(e)}
            # JWKS
            if jwks_uri:
                try:
                    resp = await client.get(jwks_uri)
                    results['jwks'] = {
                        'status': resp.status_code,
                        'ok': resp.status_code == 200,
                    }
                except Exception as e:
                    results['jwks'] = {'ok': False, 'error': str(e)}
        all_ok = all(r.get('ok') for r in results.values())
        return ok({'results': results, 'ok': all_ok})


class PublicOAuthProvidersHandler(HTTPEndpoint):
    """Anonymous GET for the login page's SSO buttons. Admitted by
    TokenAuth._PUBLIC_PATHS; returns only enabled providers (to_json
    strips client_secret)."""

    async def get(self, request):
        async with get_conn() as conn:
            providers = await OAuthProviders(conn).get_public()
        return ok({'data': providers})
