# Feature: Notifications — Real-Time Subsystem (v1 Polling)

## Current State

No notification system. Users must manually refresh to discover events.

## Architecture

v1 uses polling (30s interval) for unread count + notification list. Redis pub-sub for real-time delivery is a future enhancement since redis package isn't available in the current Python env.

### Backend

1. **Migration 029**: `notifications` table (id UUID, user_id, event_type, title, body, link, read, created_at)
2. **`db/notifications.py`**: CRUD — create, list, unread_count, mark_read, mark_all_read, dismiss, dismiss_all
3. **`api/notifications.py`**: REST endpoints (list, unread-count, read, read-all, dismiss, dismiss-all)
4. **Event hooks**: Create notifications when:
   - Upload completes (`upload_finish` in api/files.py) → `study.arrived`
   - Share link accessed (`/view/:key` route) → `share.accessed`

### Frontend

1. **`NotificationBell.tsx`**: Bell icon with Badge → click opens Drawer with notification list
2. **Polling**: `useEffect` with 30s interval for unread count; also fetches list on drawer open
3. **Actions**: Mark read, Mark all read, Dismiss, Dismiss all
4. **Sidebar integration**: Add NotificationBell next to user profile/logout area
5. **Routing**: Already on every page via sidebar

### Security

All endpoints require auth. Notifications scoped per-user. Only target user can read/dismiss.
