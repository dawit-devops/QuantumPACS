from unittest.mock import AsyncMock

import pytest

from db.table import Table


class TestTableRegistry:
    def setup_method(self):
        Table.tables.clear()

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
        t = Table()
        assert C in t.tables

    def test_register_same_class_twice(self):
        class D(Table):
            name = 'd'
        Table.register(D)
        Table.register(D)
        assert Table.tables.count(D) == 2


class TestTableQuery:
    def setup_method(self):
        Table.tables.clear()

    def test_query_returns_pypika_query_object(self):
        class PatientTable(Table):
            name = 'patients'
        t = PatientTable()
        q = t.query()
        assert 'Query' in type(q).__name__

    def test_select_returns_valid_sql(self):
        class PatientTable(Table):
            name = 'patients'
        t = PatientTable()
        q = t.select('id', 'name')
        sql = str(q)
        assert 'SELECT' in sql
        assert 'id' in sql
        assert 'name' in sql
        assert '"patients"' in sql

    def test_select_star(self):
        class PatientTable(Table):
            name = 'patients'
        t = PatientTable()
        q = t.select('*')
        assert str(q) == 'SELECT * FROM "patients"'

    def test_update_requires_set(self):
        class PatientTable(Table):
            name = 'patients'
        t = PatientTable()
        table = t.table
        q = t.update().set('name', 'test').where(table.id == 1)
        sql = str(q)
        assert sql.startswith('UPDATE')
        assert '"patients"' in sql

    def test_insert_requires_values(self):
        class PatientTable(Table):
            name = 'patients'
        t = PatientTable()
        q = t.insert().columns('id', 'name').insert(1, 'Alice')
        sql = str(q)
        assert sql.startswith('INSERT INTO')
        assert '"patients"' in sql

    def test_alias_in_query(self):
        class PatientTable(Table):
            name = 'patients'
        t = PatientTable(alias='p')
        q = t.select('id')
        sql = str(q)
        assert '"patients"' in sql or '"p"' in sql


class TestTableAsync:
    def setup_method(self):
        Table.tables.clear()

    @pytest.mark.asyncio
    async def test_sync_db_raises_not_implemented(self):
        class MyTable(Table):
            name = 'test'
        t = MyTable()
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

