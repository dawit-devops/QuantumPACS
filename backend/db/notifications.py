import uuid


class Notifications:
    def __init__(self, conn=None):
        self.conn = conn

    async def create(self, user_id, event_type, title, body=None, link=None):
        nid = str(uuid.uuid4())
        await self.conn.execute(
            'INSERT INTO notifications (id, user_id, event_type, title, body, link) VALUES ($1, $2, $3, $4, $5, $6)',
            nid, user_id, event_type, title, body, link,
        )
        return nid

    async def get_all(self, user_id, offset=0, limit=20):
        rows = await self.conn.fetch(
            'SELECT id, user_id, event_type, title, body, link, read, created_at '
            'FROM notifications WHERE user_id = $1 ORDER BY created_at DESC LIMIT $2 OFFSET $3',
            user_id, limit, offset,
        )
        return [self._format(r) for r in rows]

    async def count_all(self, user_id):
        return await self.conn.fetchval(
            'SELECT COUNT(*) FROM notifications WHERE user_id = $1', user_id,
        )

    async def unread_count(self, user_id):
        return await self.conn.fetchval(
            'SELECT COUNT(*) FROM notifications WHERE user_id = $1 AND NOT read', user_id,
        )

    async def mark_read(self, notification_id, user_id):
        await self.conn.execute(
            'UPDATE notifications SET read = TRUE WHERE id = $1 AND user_id = $2',
            notification_id, user_id,
        )

    async def mark_all_read(self, user_id):
        await self.conn.execute(
            'UPDATE notifications SET read = TRUE WHERE user_id = $1 AND NOT read', user_id,
        )

    async def dismiss(self, notification_id, user_id):
        await self.conn.execute(
            'DELETE FROM notifications WHERE id = $1 AND user_id = $2',
            notification_id, user_id,
        )

    async def dismiss_all(self, user_id):
        await self.conn.execute(
            'DELETE FROM notifications WHERE user_id = $1', user_id,
        )

    @staticmethod
    def _format(row):
        return {
            'id': row['id'],
            'user_id': row['user_id'],
            'event_type': row['event_type'],
            'title': row['title'],
            'body': row['body'],
            'link': row['link'],
            'read': row['read'],
            'created_at': str(row['created_at']),
        }
