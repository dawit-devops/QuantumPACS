from unittest.mock import AsyncMock, patch

import pytest

from db.oauth_providers import OAuthProviders


class TestOAuthProvidersDB:
    @pytest.mark.asyncio
    async def test_get_all_returns_list(self):
        conn = AsyncMock()
        conn.fetch.return_value = [
            {'id': 'p1', 'issuer': 'https://idp.example.com', 'client_id': 'abc',
             'created_at': '2026-01-01', 'updated_at': '2026-01-01'},
            {'id': 'p2', 'issuer': 'https://other.idp.com', 'client_id': 'def',
             'created_at': '2026-01-02', 'updated_at': '2026-01-02'},
        ]
        p = OAuthProviders(conn=conn)
        result = await p.get_all()
        assert len(result) == 2
        assert 'client_secret' not in result[0]

    @pytest.mark.asyncio
    async def test_get_returns_provider(self):
        conn = AsyncMock()
        conn.fetchrow.return_value = {
            'id': 'p1', 'issuer': 'https://idp.example.com', 'client_id': 'abc',
            'created_at': '2026-01-01', 'updated_at': '2026-01-01',
        }
        p = OAuthProviders(conn=conn)
        result = await p.get('p1')
        assert result['issuer'] == 'https://idp.example.com'

    @pytest.mark.asyncio
    async def test_get_returns_none_when_missing(self):
        conn = AsyncMock()
        conn.fetchrow.return_value = None
        p = OAuthProviders(conn=conn)
        result = await p.get('missing')
        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_issuer_finds_provider(self):
        conn = AsyncMock()
        conn.fetchrow.return_value = {
            'id': 'p1', 'issuer': 'https://idp.example.com', 'client_id': 'abc',
        }
        p = OAuthProviders(conn=conn)
        result = await p.get_by_issuer('https://idp.example.com')
        assert result['id'] == 'p1'

    @pytest.mark.asyncio
    async def test_create_returns_id(self):
        conn = AsyncMock()
        conn.fetchval.return_value = 'new-id-456'
        p = OAuthProviders(conn=conn)
        provider_id = await p.create(
            issuer='https://idp.example.com',
            client_id='my-client',
            slug='idp-example-com',
        )
        assert provider_id == 'new-id-456'
        sql = conn.fetchval.call_args[0][0]
        assert 'INSERT INTO' in sql

    async def test_create_auto_generates_slug_from_issuer(self):
        conn = AsyncMock()
        conn.fetchval.return_value = 'pid-1'
        p = OAuthProviders(conn=conn)
        await p.create(
            issuer='https://accounts.google.com',
            client_id='g-client',
        )
        sql = conn.fetchval.call_args[0][0]
        assert 'accounts-google-com' in sql

    @pytest.mark.asyncio
    async def test_patch_updates_fields(self):
        conn = AsyncMock()
        p = OAuthProviders(conn=conn)
        await p.patch('p1', {'client_id': 'new-client', 'enabled': False})
        sql = conn.execute.call_args[0][0]
        assert 'UPDATE' in sql
        assert 'updated_at' in sql

    @pytest.mark.asyncio
    async def test_delete_removes_provider(self):
        conn = AsyncMock()
        p = OAuthProviders(conn=conn)
        await p.delete('p1')
        sql = conn.execute.call_args[0][0]
        assert 'DELETE' in sql

    @pytest.mark.asyncio
    async def test_to_json_removes_client_secret(self):
        data = {
            'id': 'p1', 'issuer': 'https://idp.example.com',
            'client_id': 'abc', 'client_secret': 'shhh',
            'created_at': '2026-01-01', 'updated_at': '2026-01-01',
        }
        result = OAuthProviders.to_json(data)
        assert 'client_secret' not in result
        assert result['issuer'] == 'https://idp.example.com'

    @pytest.mark.asyncio
    async def test_create_encrypts_client_secret(self):
        conn = AsyncMock()
        conn.fetchval.return_value = 'new-id'
        p = OAuthProviders(conn=conn)
        with patch('db.oauth_providers.encrypt_secret', return_value='encrypted_val') as mock_enc:
            await p.create(
                issuer='https://idp.example.com',
                client_id='my-client',
                client_secret='plaintext_secret',
                slug='idp-example-com',
            )
        mock_enc.assert_called_once_with('plaintext_secret')
        sql = conn.fetchval.call_args[0][0]
        assert 'encrypted_val' in sql
        assert 'plaintext_secret' not in sql

    @pytest.mark.asyncio
    async def test_create_skips_encryption_when_secret_empty(self):
        conn = AsyncMock()
        conn.fetchval.return_value = 'new-id'
        p = OAuthProviders(conn=conn)
        with patch('db.oauth_providers.encrypt_secret') as mock_enc:
            await p.create(
                issuer='https://idp.example.com',
                client_id='my-client',
                client_secret='',
                slug='idp-example-com',
            )
        mock_enc.assert_not_called()

    @pytest.mark.asyncio
    async def test_patch_encrypts_client_secret(self):
        conn = AsyncMock()
        p = OAuthProviders(conn=conn)
        with patch('db.oauth_providers.encrypt_secret', return_value='encrypted_val') as mock_enc:
            await p.patch('p1', {'client_secret': 'new_secret', 'enabled': True})
        mock_enc.assert_called_once_with('new_secret')
        sql = conn.execute.call_args[0][0]
        assert 'encrypted_val' in sql
        assert 'new_secret' not in sql

    @pytest.mark.asyncio
    async def test_patch_skips_encryption_when_secret_empty(self):
        conn = AsyncMock()
        p = OAuthProviders(conn=conn)
        with patch('db.oauth_providers.encrypt_secret') as mock_enc:
            await p.patch('p1', {'client_secret': ''})
        mock_enc.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_decrypted_returns_decrypted_secret(self):
        conn = AsyncMock()
        conn.fetchrow.return_value = {
            'id': 'p1', 'issuer': 'https://idp.example.com', 'client_id': 'abc',
            'client_secret': 'encrypted_stored',
        }
        p = OAuthProviders(conn=conn)
        with patch('db.oauth_providers.decrypt_secret', return_value='plaintext_secret') as mock_dec:
            result = await p.get_decrypted('p1')
        assert result['id'] == 'p1'
        assert result['client_secret'] == 'plaintext_secret'
        mock_dec.assert_called_once_with('encrypted_stored')

    @pytest.mark.asyncio
    async def test_get_decrypted_returns_none_when_missing(self):
        conn = AsyncMock()
        conn.fetchrow.return_value = None
        p = OAuthProviders(conn=conn)
        result = await p.get_decrypted('missing')
        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_slug_returns_decrypted_provider(self):
        conn = AsyncMock()
        conn.fetchrow.return_value = {
            'id': 'p1', 'issuer': 'https://idp.example.com', 'client_id': 'abc',
            'client_secret': 'encrypted_stored', 'slug': 'idp-example-com',
        }
        p = OAuthProviders(conn=conn)
        with patch('db.oauth_providers.decrypt_secret', return_value='plaintext_secret') as mock_dec:
            result = await p.get_by_slug('idp-example-com')
        assert result is not None
        assert result['client_secret'] == 'plaintext_secret'
        mock_dec.assert_called_once_with('encrypted_stored')

    @pytest.mark.asyncio
    async def test_get_by_slug_falls_back_to_issuer(self):
        conn = AsyncMock()
        conn.fetchrow.side_effect = [None, {
            'id': 'p1', 'issuer': 'https://idp.example.com', 'client_id': 'abc',
            'client_secret': 'encrypted',
        }]
        p = OAuthProviders(conn=conn)
        with patch('db.oauth_providers.decrypt_secret', return_value='plaintext'):
            result = await p.get_by_slug('https://idp.example.com')
        assert result is not None
        assert result['client_secret'] == 'plaintext'

    @pytest.mark.asyncio
    async def test_get_by_slug_returns_none_when_missing(self):
        conn = AsyncMock()
        conn.fetchrow.return_value = None
        p = OAuthProviders(conn=conn)
        result = await p.get_by_slug('unknown-provider')
        assert result is None


class TestOAuthProvidersGroupsMap:
    """R2-M7: groups_map (IdP group → role slug) is stored as JSONB and
    normalized to a dict for consumers."""

    @pytest.mark.asyncio
    async def test_create_includes_groups_map_json(self):
        conn = AsyncMock()
        conn.fetchval.return_value = 'pid-1'
        p = OAuthProviders(conn=conn)
        await p.create(
            issuer='https://idp.example.com',
            client_id='c',
            slug='idp',
            groups_map={'radiologists': 'radiologist', 'admins': 'platform_admin'},
        )
        sql = conn.fetchval.call_args[0][0]
        assert '"radiologists":"radiologist"' in sql.replace(' ', '')
        assert 'groups_map' in sql

    @pytest.mark.asyncio
    async def test_create_defaults_groups_map_to_empty_object(self):
        conn = AsyncMock()
        conn.fetchval.return_value = 'pid-1'
        p = OAuthProviders(conn=conn)
        await p.create(issuer='https://idp.example.com', client_id='c', slug='idp')
        sql = conn.fetchval.call_args[0][0]
        assert '{}' in sql

    @pytest.mark.asyncio
    async def test_to_json_normalizes_groups_map(self):
        p = OAuthProviders(conn=AsyncMock())
        result = p.to_json({
            'id': 'p1', 'issuer': 'https://idp.example.com',
            'created_at': '2026-01-01', 'updated_at': '2026-01-01',
            'groups_map': '{"radiologists": "radiologist"}',
        })
        assert result['groups_map'] == {'radiologists': 'radiologist'}

    @pytest.mark.asyncio
    async def test_to_json_handles_dict_groups_map(self):
        p = OAuthProviders(conn=AsyncMock())
        result = p.to_json({
            'id': 'p1', 'issuer': 'https://idp.example.com',
            'created_at': '2026-01-01', 'updated_at': '2026-01-01',
            'groups_map': {'admins': 'platform_admin'},
        })
        assert result['groups_map'] == {'admins': 'platform_admin'}

    @pytest.mark.asyncio
    async def test_patch_serializes_groups_map_as_json(self):
        conn = AsyncMock()
        p = OAuthProviders(conn=conn)
        await p.patch('p1', {'groups_map': {'technologists': 'technologist'}})
        sql = conn.execute.call_args[0][0]
        assert '{"technologists": "technologist"}' in sql
