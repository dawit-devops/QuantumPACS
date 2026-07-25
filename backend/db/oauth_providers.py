from db.table import Table


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

    async def get(self, provider_id):
        q = self.select('*').where(self.table.id == provider_id)
        data = await self.fetchone(q)
        return self.to_json(data) if data else None

    async def get_by_issuer(self, issuer):
        q = self.select('*').where(self.table.issuer == issuer)
        data = await self.fetchone(q)
        return dict(data) if data else None

    async def create(self, issuer, client_id, client_secret='',
                     jwks_uri=None, token_url=None, redirect_uri=None,
                     scope='openid email profile', groups_claim='groups',
                     auto_provision=True, enabled=True, tenant_id=None):
        q = self.insert().columns(
            self.table.tenant_id, self.table.issuer, self.table.client_id,
            self.table.client_secret, self.table.jwks_uri, self.table.token_url,
            self.table.redirect_uri, self.table.scope, self.table.groups_claim,
            self.table.auto_provision, self.table.enabled,
        ).insert(
            tenant_id, issuer, client_id, client_secret,
            jwks_uri, token_url, redirect_uri, scope, groups_claim,
            auto_provision, enabled,
        ).returning(self.table.id)
        return await self.fetchval(q)

    async def patch(self, provider_id, data):
        q = self.update().where(self.table.id == provider_id)
        for key, value in data.items():
            if key in ('id', 'created_at'):
                continue
            q = q.set(self.table.field(key), value)
        q = q.set(self.table.updated_at, 'NOW()')
        await self.exec(q)

    async def delete(self, provider_id):
        q = self.query().where(self.table.id == provider_id).delete()
        await self.exec(q)
