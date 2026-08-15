"""Backup registry (super_admin review P2-1).

Each row tracks one on-demand metadata-manifest backup: status lifecycle
(running -> completed | failed), the artifact key on the master replica
storage, file/byte counts and the triggering admin. Audit events
system.backup_completed / system.backup_failed are emitted by the API layer.
"""

import uuid


class Backups:
    def __init__(self, conn=None):
        self.conn = conn

    async def create(self, status='running', kind='metadata',
                     artifact_key=None, size_bytes=0, files_count=0,
                     bytes_count=0, created_by=None):
        bid = str(uuid.uuid4())
        await self.conn.execute(
            'INSERT INTO backups (id, status, kind, artifact_key, size_bytes, '
            'files_count, bytes_count, created_by) '
            'VALUES ($1, $2, $3, $4, $5, $6, $7, $8)',
            bid, status, kind, artifact_key, int(size_bytes),
            int(files_count), int(bytes_count), created_by,
        )
        return bid

    async def finish(self, bid, status, artifact_key=None, size_bytes=0,
                     files_count=0, bytes_count=0):
        await self.conn.execute(
            'UPDATE backups SET status = $2, artifact_key = COALESCE($3, artifact_key), '
            'size_bytes = $4, files_count = $5, bytes_count = $6 '
            'WHERE id = $1',
            bid, status, artifact_key, int(size_bytes),
            int(files_count), int(bytes_count),
        )

    async def get(self, bid):
        row = await self.conn.fetchrow(
            'SELECT * FROM backups WHERE id = $1', str(bid),
        )
        return self._format(row) if row else None

    async def list_all(self, limit=50):
        rows = await self.conn.fetch(
            'SELECT * FROM backups ORDER BY created_at DESC LIMIT $1', limit,
        )
        return [self._format(r) for r in rows]

    async def delete(self, bid):
        await self.conn.execute(
            'DELETE FROM backups WHERE id = $1', str(bid),
        )

    @staticmethod
    def _format(row):
        return {
            'id': str(row['id']),
            'status': row['status'],
            'kind': row['kind'],
            'artifact_key': row['artifact_key'],
            'size_bytes': int(row['size_bytes'] or 0),
            'files_count': int(row['files_count'] or 0),
            'bytes_count': int(row['bytes_count'] or 0),
            'created_by': row['created_by'],
            'created_at': str(row['created_at']),
        }
