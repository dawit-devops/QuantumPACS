from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from db.table import Table


class _AsyncContextMock(AsyncMock):
    async def __aenter__(self):
        return self
    async def __aexit__(self, *args):
        pass


class TestTableRegistry:
    def setup_method(self):
        self._saved_tables = list(Table.tables)
        Table.tables.clear()

    def teardown_method(self):
        Table.tables.clear()
        Table.tables.extend(self._saved_tables)

    def test_register_adds_class(self):
        class MyTable(Table):
            name = 'my_table'
        Table.register(MyTable)
        assert MyTable in Table.tables

    def test_register_adds_multiple(self):
        class A(Table):
            name = 'a'
        class B(Table):
            name = 'b'
        Table.register(A)
        Table.register(B)
        assert A in Table.tables
        assert B in Table.tables

    def test_tables_is_shared_across_instances(self):
        class C(Table):
            name = 'c'
        Table.register(C)
        t = Table(conn=MagicMock())
        assert C in t.tables

    def test_register_same_class_twice(self):
        class D(Table):
            name = 'd'
        Table.register(D)
        Table.register(D)
        assert Table.tables.count(D) == 2


class TestTableQuery:
    def setup_method(self):
        self._saved_tables = list(Table.tables)
        Table.tables.clear()

    def teardown_method(self):
        Table.tables.clear()
        Table.tables.extend(self._saved_tables)

    def test_query_returns_pypika_query_object(self):
        class PatientTable(Table):
            name = 'patients'
        t = PatientTable(conn=MagicMock())
        q = t.query()
        assert 'Query' in type(q).__name__

    def test_select_returns_valid_sql(self):
        class PatientTable(Table):
            name = 'patients'
        t = PatientTable(conn=MagicMock())
        q = t.select('id', 'name')
        sql = str(q)
        assert 'SELECT' in sql
        assert 'id' in sql
        assert 'name' in sql
        assert '"patients"' in sql

    def test_select_star(self):
        class PatientTable(Table):
            name = 'patients'
        t = PatientTable(conn=MagicMock())
        q = t.select('*')
        assert str(q) == 'SELECT * FROM "patients"'

    def test_update_requires_set(self):
        class PatientTable(Table):
            name = 'patients'
        t = PatientTable(conn=MagicMock())
        table = t.table
        q = t.update().set('name', 'test').where(table.id == 1)
        sql = str(q)
        assert sql.startswith('UPDATE')
        assert '"patients"' in sql

    def test_insert_requires_values(self):
        class PatientTable(Table):
            name = 'patients'
        t = PatientTable(conn=MagicMock())
        q = t.insert().columns('id', 'name').insert(1, 'Alice')
        sql = str(q)
        assert sql.startswith('INSERT INTO')
        assert '"patients"' in sql

    def test_alias_in_query(self):
        class PatientTable(Table):
            name = 'patients'
        t = PatientTable(conn=MagicMock(), alias='p')
        q = t.select('id')
        sql = str(q)
        assert '"patients"' in sql or '"p"' in sql


class TestTableAsync:
    def setup_method(self):
        self._saved_tables = list(Table.tables)
        Table.tables.clear()

    def teardown_method(self):
        Table.tables.clear()
        Table.tables.extend(self._saved_tables)

    @pytest.mark.asyncio
    async def test_sync_db_raises_not_implemented(self):
        class MyTable(Table):
            name = 'test'
        t = MyTable(conn=MagicMock())
        with pytest.raises(TypeError, match='NotImplemented'):
            await t.sync_db()

    @pytest.mark.asyncio
    async def test_fetch_calls_conn_fetch(self):
        conn = AsyncMock()
        conn.fetch.return_value = [{'id': 1}]
        class MyTable(Table):
            name = 'test'
        t = MyTable(conn=conn)
        result = await t.fetch('SELECT 1')
        conn.fetch.assert_called_once_with('SELECT 1')
        assert result == [{'id': 1}]

    @pytest.mark.asyncio
    async def test_fetchone_calls_conn_fetchrow(self):
        conn = AsyncMock()
        conn.fetchrow.return_value = {'id': 1}
        class MyTable(Table):
            name = 'test'
        t = MyTable(conn=conn)
        result = await t.fetchone('SELECT 1')
        conn.fetchrow.assert_called_once_with('SELECT 1')
        assert result == {'id': 1}

    @pytest.mark.asyncio
    async def test_fetchval_calls_conn_fetchval(self):
        conn = AsyncMock()
        conn.fetchval.return_value = 42
        class MyTable(Table):
            name = 'test'
        t = MyTable(conn=conn)
        result = await t.fetchval('SELECT 1')
        conn.fetchval.assert_called_once_with('SELECT 1')
        assert result == 42

    @pytest.mark.asyncio
    async def test_exec_calls_conn_execute(self):
        conn = AsyncMock()
        conn.execute.return_value = 'INSERT 0 1'
        class MyTable(Table):
            name = 'test'
        t = MyTable(conn=conn)
        result = await t.exec('INSERT INTO test VALUES (1)')
        conn.execute.assert_called_once_with('INSERT INTO test VALUES (1)')
        assert result == 'INSERT 0 1'

    @pytest.mark.asyncio
    async def test_files_insert_or_select_toctou(self):
        import asyncpg
        conn = MagicMock()
        from db.files import Files
        f = Files(conn)
        f.get = AsyncMock(side_effect=[None, {'id': 42, 'name': 'test.dcm'}])
        f.add = AsyncMock(side_effect=asyncpg.UniqueViolationError('duplicate key'))
        result = await f.insert_or_select({'name': 'test.dcm'})
        assert result['id'] == 42
        assert f.get.call_count == 2
        f.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_files_insert_or_select_returns_existing(self):
        conn = MagicMock()
        from db.files import Files
        f = Files(conn)
        f.get = AsyncMock(return_value={'id': 42, 'name': 'existing.dcm'})
        result = await f.insert_or_select({'name': 'existing.dcm'})
        assert result['id'] == 42

    @pytest.mark.asyncio
    async def test_files_delete_calls_storage_delete(self):
        tx = _AsyncContextMock()
        conn = AsyncMock()
        conn.transaction = MagicMock(return_value=tx)
        conn.fetchval = AsyncMock(return_value=0)
        conn.execute = AsyncMock()
        conn.fetchrow = AsyncMock(return_value={'id': 1, 'type': 'local', 'location': '/tmp'})

        mock_storage = MagicMock()
        mock_storage.delete = AsyncMock()

        from db.files import Files, set_es_indexer, set_storage_provider
        mock_indexer = AsyncMock()
        set_es_indexer(mock_indexer)
        set_storage_provider(AsyncMock(return_value=mock_storage))

        f = Files(conn)
        await f.delete(file_id=42, master_id=1)

        assert mock_storage.delete.called

    @pytest.mark.asyncio
    async def test_fetch_with_select_query(self):
        conn = AsyncMock()
        conn.fetch.return_value = [{'id': 1, 'name': 'Alice'}]
        class PatientTable(Table):
            name = 'patients'
        t = PatientTable(conn=conn)
        q = t.select('id', 'name')
        result = await t.fetch(q)
        conn.fetch.assert_called_once_with(str(q))
        assert result == [{'id': 1, 'name': 'Alice'}]

