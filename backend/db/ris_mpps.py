"""MPPS events persistence (S6-08).

Tracks every DICOM Modality Performed Procedure Step message (N-CREATE,
N-SET) for audit and troubleshooting. Each event captures the accession
number, event type, resulting MPPS status, the study UID if provided,
and the raw DICOM dataset serialized as JSONB.
"""
from datetime import datetime, timezone

from pypika import Order
from db.table import Table


class RisMppsEvents(Table):
    name = 'ris_mpps_events'

    async def sync_db(self):
        await self.exec("""
        CREATE TABLE IF NOT EXISTS ris_mpps_events (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            accession_number TEXT NOT NULL DEFAULT '',
            event_type TEXT NOT NULL DEFAULT '',
            mpps_status TEXT NOT NULL DEFAULT '',
            study_uid TEXT DEFAULT '',
            station_ae_title TEXT DEFAULT '',
            raw_message JSONB DEFAULT '{}',
            tenant_id TEXT,
            created_at TIMESTAMPTZ DEFAULT now()
        )
        """)
        await self.exec("""
        CREATE INDEX IF NOT EXISTS ix_ris_mpps_accession
            ON ris_mpps_events (accession_number)
        """)
        await self.exec("""
        CREATE INDEX IF NOT EXISTS ix_ris_mpps_created
            ON ris_mpps_events (created_at)
        """)
        await self.exec("""
        CREATE INDEX IF NOT EXISTS ix_ris_mpps_tenant
            ON ris_mpps_events (tenant_id)
        """)

    async def create(self, accession_number, event_type, mpps_status,
                     study_uid='', station_ae_title='', raw_message=None):
        """Insert a new MPPS event and return its id."""
        import json
        from db.conn import get_tenant_slug
        now = datetime.now(timezone.utc)
        msg = json.dumps(raw_message) if raw_message is not None else '{}'
        q = (self.insert().columns(
                'accession_number', 'event_type', 'mpps_status',
                'study_uid', 'station_ae_title', 'raw_message',
                'tenant_id', 'created_at',
            ).insert((
                accession_number, event_type, mpps_status,
                study_uid, station_ae_title, msg,
                get_tenant_slug() or 'default', now,
            )).returning('id'))
        eid = await self.fetchval(q)
        return eid

    async def list_by_accession(self, accession_number, limit=50):
        """Return events for a given accession, newest first."""
        q = (self.select(self.table.star)
             .where(self.table.accession_number == accession_number)
             .orderby(self.table.created_at, order=Order.desc)
             .limit(limit))
        rows = await self.fetch(q)
        return [dict(r) for r in rows]
