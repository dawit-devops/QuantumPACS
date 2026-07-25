from unittest.mock import AsyncMock, MagicMock, patch

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
        )
        assert provider_id == 'new-id-456'
        sql = conn.fetchval.call_args[0][0]
        assert 'INSERT INTO' in sql

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
