# Backend Requirements: Notifications (Planned Feature)

## Context

QuantumPACS currently has no notification system. Users must manually refresh or poll to discover state changes. This is a planned feature.

**Current gaps:**
- New studies arrived → Technologist must manually refresh the Study List after uploading
- Worklist status changes → No alert when a C-STORE receipt auto-transitions a worklist entry to `performed`
- Share link accessed → Radiologist has no way to know a referring physician viewed a shared study
- Annotation state changes → Currently broadcast via WebSocket/Redis pub-sub (existing infrastructure), but not surfaced as a notification

**Personas:** All authenticated users, but especially:
- **Technologists** — need to know upload succeeded / study verified
- **Radiologists** — need to know new studies assigned, share links accessed
- **Clinicians** — need to know when a report is ready
- **PACS Admins** — need to know system health events / quota warnings

## Screens/Components

### Notification Badge (Nav)

A badge counter on the main navigation (sidebar or top bar) showing the count of unread notifications.

**Data I need to display:**
- Unread notification count (integer, 0 hides the badge)
- Badge appears on the bell/notification icon in the nav

**Actions:**
- Click bell icon → navigate to notification list page or open a dropdown panel

**States:**
- **0 unread:** No badge shown
- **1+ unread:** Red badge with count; truncated to "99+" if >99

**Business rules:**
- Badge count fetched on page load and periodically (poll every 30s or via WebSocket push)
- Count is user-scoped (per-user, not per-role)

### Notification List (Page or Dropdown Panel)

List of recent notifications sorted newest-first.

**Data I need to display per notification:**
- `id` — unique identifier (for mark-read / dismiss)
- `event_type` — machine-readable type (e.g., `study.arrived`, `study.verified`, `share.accessed`, `worklist.performed`, `annotation.shared`)
- `title` — human-readable short summary (e.g., "New study arrived for John Doe")
- `body` — optional longer description
- `created_at` — ISO 8601 timestamp
- `read` — boolean
- `link` — optional URL to navigate to when clicked (e.g., `/files/{id}`, `/worklist`)

**Actions:**
- Click notification → navigate to `link`, mark as read
- Mark as read (individual)
- Mark all as read
- Dismiss (individual remove)
- Dismiss all

**States:**
- **Loading:** Skeleton list
- **Empty:** "No notifications" with illustration
- **Unread:** Bold/highlighted row; blue dot indicator
- **Read:** Normal weight row; no indicator
- **Error:** Failed to load notifications — retry button

**Pagination:** Offset-based, 20 per page. Include `total` count.

### Notification Preferences (Settings)

Per-user preference for which event types trigger a notification.

**Frontend expectations:**
- Event types listed as toggle switches
- Default: all notification types enabled for each role
- Preferences persisted server-side per user

**Data model:**
```
NotificationPreference {
  user_id: uuid
  event_type: string
  enabled: boolean
}
```

## Real-Time Delivery

**Channel:** WebSocket, piggybacking on the existing Redis pub/sub infrastructure (currently used for annotation sync).

**Expected flow:**
1. Backend publishes notification event to Redis channel
2. WebSocket server picks it up and pushes to connected clients
3. If user is offline (no WebSocket), notification is persisted in DB and delivered on next poll/page load

**Fallback:** Polling every 30s via `GET /api/notifications/unread-count` when WebSocket is unavailable.

## Events That Trigger Notifications

| Event | Trigger | Target User(s) | Link |
|-------|---------|----------------|------|
| `study.arrived` | C-STORE or STOW-RS receipt | Technologist who uploaded, Radiologists in group | `/files/{id}` |
| `study.verified` | Technologist marks upload as verified | Radiologist | `/files/{id}` |
| `worklist.performed` | C-STORE auto-transitions MWL entry to `performed` | Technologist who created entry | `/worklist` |
| `share.accessed` | Share link viewed by external user | Radiologist who created the share | `/files/{id}` |
| `annotation.shared` | Another user adds annotation to a study | All other viewers of that study | `/files/{id}` |
| `report.ready` | Report approved/published | Referring Clinician, ordering physician | `/files/{id}` |
| `quota.warning` | Storage approaching quota | PACS Admin | `/tenants` |
| `system.alert` | Component health degraded | PACS Admin | `/metrics` |

## Retention

- Notifications retained for **90 days**
- Read notifications auto-deleted after 90 days
- Unread notifications retained until read, then 90-day clock starts
- Admins may configure retention period per tenant

## Uncertainties & Questions

- Would WebSocket be the channel for real-time notifications (piggyback on existing Redis channel infrastructure)?
- Should notifications be per-user or per-role?
- How long are notifications retained?
- Can users mark notifications as read or dismiss them?
- Should there be browser push notifications for critical events?
- When there are multiple notifications of the same type for the same resource, should they be grouped (e.g., "3 new studies arrived")?
- Should notifications support actions (e.g., "Verify" button inline in the notification)?
- Is the notification preference per-user or per-role with per-user override?
- Should share-link access notifications be real-time or near-real-time (allow some delay)?
- Do we need an audit trail of sent notifications (HIPAA consideration for PHI access events)?
