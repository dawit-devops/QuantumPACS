"""RIS staff time-off persistence — DM-07 staff schedule management."""

from datetime import date, datetime, timezone

from db.table import Table


def _as_date(value):
    """Coerce a date object or ISO string to a date (None when empty)."""
    if value is None or value == '':
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


class RisStaffTimeOff(Table):
    name = 'ris_staff_time_off'

    async def create(self, data):
        now = datetime.now(timezone.utc)
        data = dict(data)
        data.setdefault('created_at', now)
        data.setdefault('updated_at', now)
        data.setdefault('status', 'REQUESTED')
        data['start_date'] = _as_date(data.get('start_date'))
        data['end_date'] = _as_date(data.get('end_date'))
        q = self.insert().columns(*data.keys()).insert(*data.values()).returning('*')
        row = await self.fetchone(q)
        return dict(row) if row else None

    async def get(self, entry_id):
        q = self.select('*').where(self.table.id == entry_id)
        row = await self.fetchone(q)
        return dict(row) if row else None

    async def list_for_tenant(self, tenant_id, status=None):
        q = self.select('*').where(self.table.tenant_id == tenant_id)
        if status:
            q = q.where(self.table.status == status)
        q = q.orderby(self.table.start_date.desc(), self.table.staff_name)
        rows = await self.fetch(q)
        return [dict(r) for r in rows]

    async def update_status(self, entry_id, status):
        now = datetime.now(timezone.utc)
        q = self.update().set(self.table.status, status)
        q = q.set(self.table.updated_at, now)
        q = q.where(self.table.id == entry_id).returning('*')
        row = await self.fetchone(q)
        return dict(row) if row else None

    async def approved_in_range(self, tenant_id, start_date, end_date, modality=None):
        """Approved time-off overlapping [start, end], optionally scoped to a
        modality. Used by the coverage-gap detector."""
        q = (self.select('staff_id', 'staff_name', 'modality', 'start_date', 'end_date')
             .where(self.table.tenant_id == tenant_id)
             .where(self.table.status == 'APPROVED')
             .where(self.table.start_date <= end_date)
             .where(self.table.end_date >= start_date))
        if modality:
            q = q.where((self.table.modality == modality) | (self.table.modality == ''))
        rows = await self.fetch(q)
        return [dict(r) for r in rows]
