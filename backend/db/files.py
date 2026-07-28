import asyncpg
from datetime import datetime, timezone
import json

from pypika.functions import Count

from es import es
from db.patient import Patient
from db.study import Study
from db.series import Series
from db.replica_files import ReplicaFiles
from db.table import Table
from db.file_changes import FileChange
from log import get_logger
from storage.storage import Storage

log = get_logger(__name__)


class Files(Table):
    name = 'files'

    async def sync_db(self):
        await self.exec("""
        CREATE TABLE IF NOT EXISTS files (
            id SERIAL PRIMARY KEY,
            patient_id INTEGER NOT NULL REFERENCES patients(id),
            study_id INTEGER NOT NULL REFERENCES studies(id),
            series_id INTEGER NOT NULL REFERENCES series(id),
            name TEXT NOT NULL,
            indexed BOOLEAN NOT NULL DEFAULT FALSE,
            hash TEXT NOT NULL,
            sop_instance_uid TEXT,
            created TIMESTAMP NOT NULL DEFAULT (now() at time zone 'utc'),
            updated TIMESTAMP NOT NULL DEFAULT (now() at time zone 'utc'),
            deleted BOOLEAN NOT NULL DEFAULT FALSE,
            meta JSONB,
            tools_state JSONB
        );
        """)
        await self.exec('CREATE INDEX IF NOT EXISTS files_name on files(name);')
        await self.exec('CREATE INDEX IF NOT EXISTS files_hash on files(hash);')

    @staticmethod
    def from_row(file):
        file = dict(file)
        if file.get('meta'):
            file['meta'] = json.loads(file['meta'])

        if file.get('tools_state'):
            file['tools_state'] = json.loads(file['tools_state'])
        return file

    async def add(self, filedata):
        async with self.conn.transaction():
            patient = await Patient(self.conn).insert_or_select(filedata)
            filedata['patient_db_id'] = patient['id']
            study = await Study(self.conn).insert_or_select(filedata)
            filedata['study_db_id'] = study['id']
            series = await Series(self.conn).insert_or_select(filedata)
            filedata['series_db_id'] = series['id']

            now = datetime.now(timezone.utc)
            q = self.insert().columns(
                'name', 'patient_id', 'study_id', 'series_id', 'meta',
                'indexed', 'hash', 'sop_instance_uid', 'created', 'updated',
            ).insert((
                filedata['name'], patient['id'], study['id'], series['id'], json.dumps(filedata['cleaned']),
                False, filedata['hash'], filedata.get('sop_instance_uid', ''), now, now,
            ), ).returning('id')

            file_id = await self.fetchval(q)

        filedata['id'] = file_id
        filedata['meta'] = filedata['cleaned']
        try:
            await es.index_file(filedata)
        except Exception as e:
            log.warning('ES indexing failed for file %s: %s, will retry via sync loop', file_id, e)
            return filedata
        async with self.conn.transaction():
            q = self.update().where(self.table.id == file_id).set(self.table.indexed, True)
            await self.exec(q)

        return filedata

    async def get(self, filedata):
        PatientT = Patient().table
        StudyT = Study().table
        SeriesT = Series().table
        table = self.table

        q = self.select(
            table.id, table.name,
            table.patient_id.as_('patient_db_id'),
            table.study_id.as_('study_db_id'),
            table.series_id.as_('series_db_id'),
            PatientT.patient_id,
            StudyT.study_id,
            SeriesT.number.as_('series_number'),
        ).join(PatientT).on(
            PatientT.id == table.patient_id
        ).join(StudyT).on(
            StudyT.id == table.study_id
        ).join(SeriesT).on(
            SeriesT.id == table.series_id
        ).where(
            PatientT.patient_id == filedata['patient_id'],
        ).where(
            StudyT.study_id == filedata['study_id'],
        ).where(
            SeriesT.number == filedata['series_number'],
        ).where(
            self.table.name == filedata['name']
        )
        return await self.fetchone(q)

    async def insert_or_select(self, filedata):
        f = await self.get(filedata)
        if f:
            return f
        try:
            return await self.add(filedata)
        except asyncpg.UniqueViolationError:
            return await self.get(filedata)

    def q(self):
        PatientT = Patient().table
        StudyT = Study().table
        SeriesT = Series().table
        table = self.table

        return self.select(
            table.id, table.name,
            table.patient_id.as_('patient_db_id'),
            table.study_id.as_('study_db_id'),
            table.series_id.as_('series_db_id'),
            PatientT.patient_id,
            StudyT.study_id,
            SeriesT.number.as_('series_number'),
            table.meta, table.tools_state, table.deleted,
        ).join(PatientT).on(
            PatientT.id == table.patient_id
        ).join(StudyT).on(
            StudyT.id == table.study_id
        ).join(SeriesT).on(
            SeriesT.id == table.series_id
        )

    async def get_extra(self, file_id):
        PatientT = Patient().table
        StudyT = Study().table
        SeriesT = Series().table
        ReplicaT = ReplicaFiles().table
        table = self.table

        q = self.select(
            table.id, table.name,
            table.patient_id.as_('patient_db_id'),
            table.study_id.as_('study_db_id'),
            table.series_id.as_('series_db_id'),
            PatientT.patient_id,
            StudyT.study_id,
            SeriesT.number.as_('series_number'),
            table.meta, table.tools_state, table.deleted,
            ReplicaT.id.as_('replica_id'),
            ReplicaT.replica_id.as_('replica_replica_id'),
            ReplicaT.file_id.as_('replica_file_id'),
            ReplicaT.location,
            ReplicaT.status.as_('replica_status'),
            ReplicaT.meta.as_('replica_meta'),
        ).join(PatientT).on(
            PatientT.id == table.patient_id
        ).join(StudyT).on(
            StudyT.id == table.study_id
        ).join(SeriesT).on(
            SeriesT.id == table.series_id
        ).left_join(ReplicaT).on(
            ReplicaT.file_id == table.id
        ).where(
            table.id == file_id
        )

        rows = await self.fetch(q)
        if not rows:
            return None

        file = self.from_row(rows[0])
        replicas = []
        seen = set()
        for row in rows:
            rid = row['replica_id']
            if rid and rid not in seen:
                seen.add(rid)
                replicas.append({
                    'id': rid,
                    'replica_id': row['replica_replica_id'],
                    'file_id': row['replica_file_id'],
                    'location': row['location'],
                    'status': row['replica_status'],
                    'meta': json.loads(row['replica_meta']) if row.get('replica_meta') else {},
                })
        file['files'] = replicas
        file['patient'] = await Patient(self.conn).get_extra(file['patient_db_id'])

        return file

    async def get_all(self, limit=1000):
        q = self.q()
        if limit:
            q = q.limit(limit)
        files = await self.fetch(q)
        return [self.from_row(f) for f in files]

    async def get_paginated(self, page=1, per_page=20, search=None):
        q = self.q()
        if search:
            q = q.where(
                (self.table.name.ilike(f'%{search}%')) |
                (Patient().table.patient_id.cast('text').ilike(f'%{search}%'))
            )
        q = q.orderby(self.table.id.desc()).limit(per_page).offset((page - 1) * per_page)
        files = await self.fetch(q)
        data = [self.from_row(f) for f in files]

        count_q = self.select(Count(1)).from_(self.table)
        if search:
            PatientT = Patient().table
            count_q = count_q.join(PatientT).on(PatientT.id == self.table.patient_id)
            count_q = count_q.where(
                (self.table.name.ilike(f'%{search}%')) |
                (PatientT.patient_id.cast('text').ilike(f'%{search}%'))
            )
        total = await self.fetchval(count_q) or 0
        return data, total

    async def unindexed(self):
        q = self.q().where(self.table.indexed == False)
        files = await self.fetch(q)
        return [self.from_row(f) for f in files]

    async def update_tools_state(self, file_id, user_id, data):
        q = self.update().where(
            self.table.id == file_id,
        ).set(
            self.table.tools_state, json.dumps(data),
        )
        await self.exec(q)
        await FileChange(self.conn).add_change(file_id, 'anotations changed', user_id)

    async def update_tag(self, file_id, user_id, data):
        async with self.conn.transaction():
            q = self.select('meta').where(self.table.id == file_id)
            meta = await self.fetchval(q)
            meta = json.loads(meta)

            old = meta[data['key']]
            new = data['value']
            meta[data['key']] = new

            q = self.update().where(self.table.id == file_id).set(self.table.meta, json.dumps(meta))
            await self.exec(q)

            await FileChange(self.conn).add_change(file_id, data['key'], user_id, old, new)

    async def get_by_hash(self, hash):
        q = self.select('*').where(self.table.hash == hash)
        return await self.fetchone(q)

    async def delete(self, file_id, master_id):
        await es.delete(file_id)

        from db.replica import Replica as ReplicaModel
        replica = await ReplicaModel(self.conn).get(master_id)
        if replica:
            storage = await Storage.get(replica)
            file_data = {'id': file_id}
            await storage.delete(file_data)

        async with self.conn.transaction():
            q = self.update().where(self.table.id == file_id).set(self.table.deleted, True)
            await self.exec(q)
            remaining = await ReplicaFiles(self.conn).delete(master_id, file_id)
            if remaining == 0:
                q = self.query().where(self.table.id == file_id).delete()
                await self.exec(q)

    async def delete_all(self):
        async with self.conn.transaction():
            try:
                await es.reset_index()
            except Exception:
                pass
            q = self.query().delete()
            await self.exec(q)
