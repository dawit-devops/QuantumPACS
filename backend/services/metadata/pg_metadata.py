from typing import Any, Callable, Optional

from pypika import Table as PypikaTable
from pypika.dialects import PostgreSQLQuery as Query

from db.conn import get_conn
from services.interfaces import MetadataService


class PgMetadataService:
    _patients = PypikaTable('patients')
    _studies = PypikaTable('studies')
    _series = PypikaTable('series')
    _files = PypikaTable('files')

    def __init__(self, conn_provider: Optional[Callable] = None):
        self._conn_provider = conn_provider or get_conn

    async def _fetch(self, q):
        async with self._conn_provider() as conn:
            return await conn.fetch(str(q))

    async def _fetchrow(self, q):
        async with self._conn_provider() as conn:
            return await conn.fetchrow(str(q))

    async def _execute(self, q):
        async with self._conn_provider() as conn:
            return await conn.execute(str(q))

    async def get_patient(self, patient_id: str) -> Optional[dict[str, Any]]:
        q = Query.from_(self._patients).select('*').where(
            self._patients.patient_id == patient_id
        )
        row = await self._fetchrow(q)
        return dict(row) if row else None

    async def get_study(self, study_id: str) -> Optional[dict[str, Any]]:
        q = Query.from_(self._studies).select('*').where(
            self._studies.study_id == study_id
        )
        row = await self._fetchrow(q)
        return dict(row) if row else None

    async def get_series(self, series_id: str) -> Optional[dict[str, Any]]:
        q = Query.from_(self._series).select('*').where(
            self._series.number == series_id
        )
        row = await self._fetchrow(q)
        return dict(row) if row else None

    async def add_file(self, file_data: dict[str, Any]) -> dict[str, Any]:
        cols = [c for c in ('patient_id', 'study_id', 'series_id', 'name', 'meta')
                if c in file_data]
        vals = tuple(file_data[c] for c in cols)
        q = Query.into(self._files).insert(*vals).columns(*cols)
        q = q.on_conflict(self._files.name).do_nothing()
        q = q.returning('id')
        row = await self._fetchrow(q)
        if row:
            return {'id': row['id']}
        sel = Query.from_(self._files).select('id').where(
            self._files.name == file_data.get('name', '')
        )
        existing = await self._fetchrow(sel)
        return {'id': existing['id']} if existing else {'id': -1}

    async def get_file(self, file_id: str) -> Optional[dict[str, Any]]:
        q = Query.from_(self._files).select('*').where(
            self._files.id == file_id
        )
        row = await self._fetchrow(q)
        return dict(row) if row else None

    async def search_studies(self, query: dict[str, Any]) -> dict[str, Any]:
        search_term = query.get('query', '')
        limit = int(query.get('results', 10))
        page = int(query.get('page', 1))
        offset = (page - 1) * limit

        q = Query.from_(self._studies).select(
            self._studies.id, self._studies.study_id,
            self._studies.description, self._studies.accession_number,
            self._patients.patient_id, self._patients.name,
        ).join(self._patients).on(
            self._patients.id == self._studies.patient_id
        )

        if search_term:
            like = f'%{search_term}%'
            q = q.where(
                (self._patients.name.ilike(like))
                | (self._studies.description.ilike(like))
                | (self._studies.accession_number.ilike(like))
            )

        q = q.orderby(self._studies.id).limit(limit).offset(offset)
        rows = await self._fetch(q)
        return {'data': [dict(r) for r in rows], 'total': len(rows)}
