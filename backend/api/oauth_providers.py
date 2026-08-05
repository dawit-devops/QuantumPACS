from starlette.endpoints import HTTPEndpoint

from api.rbac import requires_permission
from api.permissions import Permission
from api.response import ok, created, not_found
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


class PublicOAuthProvidersHandler(HTTPEndpoint):
    """Anonymous GET for the login page's SSO buttons. Admitted by
    TokenAuth._PUBLIC_PATHS; returns only enabled providers (to_json
    strips client_secret)."""

    async def get(self, request):
        async with get_conn() as conn:
            providers = await OAuthProviders(conn).get_public()
        return ok({'data': providers})
