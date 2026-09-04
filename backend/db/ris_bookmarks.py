"""Study bookmarks and collections persistence (R-08).

Radiologists bookmark studies for teaching, research, or follow-up into
named collections. Two flat tables: bookmark_collections (per-user named
collections, optionally shared) and study_bookmarks (a study reference
bound to a user + optional collection). sync_db self-heals; alembic
migration 107 covers the container path.
"""


class BookmarkCollections:
    name = 'bookmark_collections'

    def __init__(self, conn):
        self.conn = conn

    async def sync_db(self):
        await self.conn.execute("""
        CREATE TABLE IF NOT EXISTS bookmark_collections (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id TEXT NOT NULL DEFAULT 'default',
            user_id TEXT NOT NULL,
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            is_shared BOOLEAN NOT NULL DEFAULT false,
            created_at TIMESTAMPTZ DEFAULT now()
        )
        """)
        await self.conn.execute(
            "CREATE INDEX IF NOT EXISTS ix_bookmark_collections_user"
            " ON bookmark_collections(tenant_id, user_id)")

    async def create(self, *, user_id, name, description, by,
                     tenant_id='default'):
        await self.sync_db()
        row = await self.conn.fetchrow(
            """INSERT INTO bookmark_collections
               (tenant_id, user_id, name, description, created_by)
               VALUES ($1, $2, $3, $4, $5)
               RETURNING *""",
            tenant_id, str(user_id), name, description, str(by or ''),
        )
        return dict(row)

    async def get(self, collection_id, tenant_id='default'):
        row = await self.conn.fetchrow(
            "SELECT * FROM bookmark_collections WHERE id = $1 AND tenant_id = $2",
            str(collection_id), tenant_id,
        )
        return dict(row) if row else None

    async def list(self, tenant_id='default', user_id=None, limit=200,
                   offset=0):
        where = ['tenant_id = $1']
        params = [tenant_id]
        if user_id:
            params.append(str(user_id))
            where.append(f'user_id = ${len(params)}')
        sql = ("SELECT * FROM bookmark_collections WHERE "
               + ' AND '.join(where)
               + f" ORDER BY created_at DESC LIMIT ${len(params)+1}"
                 f" OFFSET ${len(params)+2}")
        rows = await self.conn.fetch(sql, *params, max(int(limit), 1),
                                     max(int(offset), 0))
        return [dict(r) for r in rows]


class StudyBookmarks:
    name = 'study_bookmarks'

    def __init__(self, conn):
        self.conn = conn

    async def sync_db(self):
        await self.conn.execute("""
        CREATE TABLE IF NOT EXISTS study_bookmarks (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id TEXT NOT NULL DEFAULT 'default',
            user_id TEXT NOT NULL,
            study_uid TEXT NOT NULL,
            study_desc TEXT DEFAULT '',
            collection_id TEXT DEFAULT '',
            notes TEXT DEFAULT '',
            created_at TIMESTAMPTZ DEFAULT now()
        )
        """)
        await self.conn.execute(
            "CREATE INDEX IF NOT EXISTS ix_study_bookmarks_user"
            " ON study_bookmarks(tenant_id, user_id)")
        await self.conn.execute(
            "CREATE INDEX IF NOT EXISTS ix_study_bookmarks_study"
            " ON study_bookmarks(study_uid)")

    async def create(self, *, user_id, study_uid, study_desc, collection_id,
                     notes, tenant_id='default'):
        await self.sync_db()
        row = await self.conn.fetchrow(
            """INSERT INTO study_bookmarks
               (tenant_id, user_id, study_uid, study_desc, collection_id, notes)
               VALUES ($1, $2, $3, $4, $5, $6)
               RETURNING *""",
            tenant_id, str(user_id), study_uid, study_desc,
            collection_id or '', notes,
        )
        return dict(row)

    async def get(self, bookmark_id, tenant_id='default'):
        row = await self.conn.fetchrow(
            "SELECT * FROM study_bookmarks WHERE id = $1 AND tenant_id = $2",
            str(bookmark_id), tenant_id,
        )
        return dict(row) if row else None

    async def list(self, tenant_id='default', user_id=None, collection_id=None,
                   limit=200, offset=0):
        where = ['tenant_id = $1']
        params = [tenant_id]
        if user_id:
            params.append(str(user_id))
            where.append(f'user_id = ${len(params)}')
        if collection_id:
            params.append(collection_id)
            where.append(f'collection_id = ${len(params)}')
        sql = ("SELECT * FROM study_bookmarks WHERE "
               + ' AND '.join(where)
               + f" ORDER BY created_at DESC LIMIT ${len(params)+1}"
                 f" OFFSET ${len(params)+2}")
        rows = await self.conn.fetch(sql, *params, max(int(limit), 1),
                                     max(int(offset), 0))
        return [dict(r) for r in rows]

    async def delete(self, bookmark_id, user_id=None, tenant_id='default'):
        if user_id:
            await self.conn.execute(
                "DELETE FROM study_bookmarks WHERE id = $1 AND tenant_id = $2"
                " AND user_id = $3",
                str(bookmark_id), tenant_id, str(user_id),
            )
        else:
            await self.conn.execute(
                "DELETE FROM study_bookmarks WHERE id = $1 AND tenant_id = $2",
                str(bookmark_id), tenant_id,
            )