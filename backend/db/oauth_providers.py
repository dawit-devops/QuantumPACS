import re
from urllib.parse import urlparse

from api.encryption import decrypt_secret, encrypt_secret
from db.table import Table


def _slug_from_issuer(issuer: str) -> str:
    hostname = urlparse(issuer).hostname
    if hostname:
        return re.sub(r'[^a-z0-9-]+', '-', hostname).strip('-')
    return re.sub(r'[^a-z0-9-]+', '-', issuer.lower()).strip('-') or 'provider'


class OAuthProviders(Table):
    name = 'oauth_providers'

    async def sync_db(self):
        pass

    @staticmethod
    def to_json(data):
        data = dict(data)
        data['created_at'] = str(data.get('created_at', ''))
        data['updated_at'] = str(data.get('updated_at', ''))
        data.pop('client_secret', None)
        return data

    async def get_all(self):
        q = self.select('*').orderby(self.table.issuer)
        data = await self.fetch(q)
        return [self.to_json(d) for d in data]

    async def get_public(self):
        """Enabled providers only — the anonymous list shown on the login
        page for SSO buttons. to_json already strips client_secret."""
        q = self.select('*').where(self.table.enabled.eq(True)).orderby(self.table.issuer)
        data = await self.fetch(q)
        return [self.to_json(d) for d in data]

    async def get(self, provider_id):
        q = self.select('*').where(self.table.id == provider_id)
        data = await self.fetchone(q)
        return self.to_json(data) if data else None

    async def get_by_issuer(self, issuer):
        q = self.select('*').where(self.table.issuer == issuer)
        data = await self.fetchone(q)
        return dict(data) if data else None

    async def get_decrypted(self, provider_id):
        q = self.select('*').where(self.table.id == provider_id)
        data = await self.fetchone(q)
        if data is None:
            return None
        result = dict(data)
        result['client_secret'] = decrypt_secret(result.get('client_secret', ''))
        return result

    async def get_by_slug(self, slug):
        q = self.select('*').where(self.table.slug == slug)
        data = await self.fetchone(q)
        if data:
            result = dict(data)
            result['client_secret'] = decrypt_secret(result.get('client_secret', ''))
            return result
        q = self.select('*').where(self.table.issuer == slug)
        data = await self.fetchone(q)
        if data:
            result = dict(data)
            result['client_secret'] = decrypt_secret(result.get('client_secret', ''))
            return result
        return None

    async def create(self, issuer, client_id, client_secret='',
                     jwks_uri=None, token_url=None, redirect_uri=None,
                     scope='openid email profile', groups_claim='groups',
                     auto_provision=True, enabled=True, tenant_id=None,
                     slug=None, default_role='patient'):
        if slug is None:
            slug = _slug_from_issuer(issuer)
        encrypted_secret = encrypt_secret(client_secret) if client_secret else ''
        q = self.insert().columns(
            self.table.tenant_id, self.table.issuer, self.table.client_id,
            self.table.client_secret, self.table.jwks_uri, self.table.token_url,
            self.table.redirect_uri, self.table.scope, self.table.groups_claim,
            self.table.auto_provision, self.table.enabled,
            self.table.slug, self.table.default_role,
        ).insert(
            tenant_id, issuer, client_id, encrypted_secret,
            jwks_uri, token_url, redirect_uri, scope, groups_claim,
            auto_provision, enabled,
            slug, default_role,
        ).returning(self.table.id)
        return await self.fetchval(q)

    async def patch(self, provider_id, data):
        q = self.update().where(self.table.id == provider_id)
        for key, value in data.items():
            if key in ('id', 'created_at'):
                continue
            if key == 'client_secret' and value:
                value = encrypt_secret(value)
            q = q.set(self.table.field(key), value)
        q = q.set(self.table.updated_at, 'NOW()')
        await self.exec(q)

    async def delete(self, provider_id):
        q = self.query().where(self.table.id == provider_id).delete()
        await self.exec(q)
