"""Per-user notification preferences (super_admin review P1-1).

Resolution order: an explicit notification_prefs row wins; an absent row
falls back to the role default. The role default exists so the platform
admin's bell stops accumulating clinical upload receipts (study.arrived
fan-out for the uploader) while operational alerts stay ON — a user can
always opt back in per event type.
"""

# Admin-scoped roles whose default notification profile mutes clinical
# lifecycle events (tenant_admin review P2-4). Mirrors ADMIN_SCOPED_ROLES in
# frontend/src/navigator.ts — kept local to avoid a backend->frontend import.
ADMIN_SCOPED_ROLE_SLUGS = frozenset({
    'super_admin', 'tenant_admin', 'pacs_admin', 'emr_admin',
})

# Clinical event types are noise for the platform admin: they describe a
# single file/study lifecycle action, not a platform condition the admin
# must act on. Keep in sync with the frontend preference-page grouping.
CLINICAL_EVENT_TYPES = frozenset({
    'study.arrived',
    'study.verified',
    'worklist.performed',
    'share.accessed',
    'annotation.shared',
    'report.ready',
})

class NotificationPrefs:
    # Every event type the bell can carry — the preference-page catalog.
    # Absent rows resolve to role defaults (see default_enabled).
    EVENT_CATALOG = frozenset({
        'study.arrived',
        'study.verified',
        'worklist.performed',
        'share.accessed',
        'annotation.shared',
        'report.ready',
        'storage.quota_breach',
        'quota.warning',
        'system.alert',
        'exam.assigned',
        'report.returned',
        'report.signed',
    })
    def __init__(self, conn=None):
        self.conn = conn

    async def get(self, user_id):
        """Return {event_type: enabled} for rows the user has explicitly set."""
        rows = await self.conn.fetch(
            'SELECT event_type, enabled FROM notification_prefs '
            'WHERE user_id = $1',
            user_id,
        )
        return {r['event_type']: bool(r['enabled']) for r in rows}

    async def set(self, user_id, prefs):
        """Upsert explicit {event_type: bool} rows for one user."""
        for event_type, enabled in prefs.items():
            await self.conn.execute(
                'INSERT INTO notification_prefs (user_id, event_type, enabled) '
                'VALUES ($1, $2, $3) '
                'ON CONFLICT (user_id, event_type) '
                'DO UPDATE SET enabled = EXCLUDED.enabled',
                user_id, str(event_type), bool(enabled),
            )

    @staticmethod
    def default_enabled(role_slug, event_type):
        """Role default when no explicit pref row exists.

        Every admin-scoped role (super_admin, tenant_admin, pacs_admin,
        emr_admin) mutes clinical lifecycle events by default (tenant_admin
        review P2-4): ops alerts stay ON, upload receipts are noise for
        whoever operates the platform. A user can always opt back in per
        event type. Mirrors the frontend ADMIN_SCOPED_ROLES set.
        """
        if role_slug in ADMIN_SCOPED_ROLE_SLUGS and event_type in CLINICAL_EVENT_TYPES:
            return False
        return True

    async def is_enabled(self, user_id, event_type, role_slug=None):
        """True when a user should receive this event type.

        Explicit rows win; otherwise the role default applies. role_slug
        should be the recipient's role (request.user.role_slug for the
        uploader path, the fan-out role for notify_role).
        """
        val = await self.conn.fetchval(
            'SELECT enabled FROM notification_prefs '
            'WHERE user_id = $1 AND event_type = $2',
            user_id, str(event_type),
        )
        if val is not None:
            return bool(val)
        return self.default_enabled(role_slug, event_type)
