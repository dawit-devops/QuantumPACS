# Replicas Page — Backend Requirements

**Route**: `/replicas`
**Role**: PACS Admin
**Storage types**: local (filesystem), s3 (S3-compatible), b2 (Backblaze B2)

---

## Replica List Display

| Field | Type | Notes |
|-------|------|-------|
| id | uuid | |
| type | enum | local / s3 / b2 |
| name | string | User-defined label |
| status | enum | indexing / ok / deleted |
| is_master | bool | Exactly one replica is master |
| sync_delay_seconds | int | How far behind master this replica is |
| sync_progress | float | 0.0–1.0 for indexing state, null otherwise |
| sync_last | datetime \| null | Last successful sync timestamp |
| connection_details | object | Type-specific (see below) |
| total_objects | int | File count |
| total_bytes | bigint | Total stored size |
| created_at | datetime | |
| updated_at | datetime | |

Connection details by type:

- **local**: `{ "path": "/mnt/storage/pacs" }`
- **s3**: `{ "bucket": "my-pacs-replica", "region": "us-east-1", "endpoint": "https://s3.custom.com", "access_key_id": "AKIA***" }`
- **b2**: `{ "bucket": "my-b2-bucket", "endpoint": "https://s3.us-west-004.backblazeb2.com", "access_key_id": "004***" }`

Secret keys (s3_secret_access_key, b2_application_key) are stored server-side and never returned to the frontend.

Display as a table with columns: Type icon, Name, Connection (bucket/path), Status badge, Sync delay, Master badge (star), Actions.

---

## CRUD Operations

### Create
- Choose type → form shows relevant fields
- Secret keys sent once, stored encrypted, never retrieved
- Backend validates connectivity before saving (e.g. `head_bucket` for S3/B2)
- New replica starts in `indexing` state

### Read
- Secret keys are **never** included in response
- Connection details show bucket/path + region, masked key IDs

### Update
- **Type cannot be changed after creation** — delete and recreate
- Name, connection details (non-secret fields), and endpoint are editable
- Changing bucket/path triggers re-index (status → indexing)

### Delete
- Deletes the replica record only — **does not delete stored data**
- If the deleted replica was the master, an error is returned: reassign master first

---

## Setting Master Replica

- Exactly one replica must be master at all times
- Master can be changed to any other `ok`-status replica
- When master changes:
  1. Old master is downgraded to regular replica
  2. New master is marked as master
  3. Sync direction may reverse — all replicas now sync from new master
- Error if trying to set a non-ok replica as master

---

## Sync Status

**Sync daemon**: Polls every 1s, processes batches of 1000 files per cycle.

**Statuses**:
| Status | Meaning | UI |
|--------|---------|----|
| `indexing` | Initial sync or re-index in progress | Progress bar (sync_progress 0.0–1.0), "Indexing X of Y files" |
| `ok` | Sync is caught up | Green badge |
| `deleted` | Replica record marked deleted | Grey badge, no actions |

**Sync delay** (`sync_delay_seconds`):
- Calculated as wall-clock time since the newest object on this replica was confirmed synced to master.
- Updated each sync cycle.
- If a replica is fully caught up, delay ≈ 0–2s (polling interval + network).
- Display format: "2s", "5m 30s", "2h 15m". If delay > 24h, show ">24h".

**Progress during indexing**:
- `sync_progress` = `objects_indexed / total_objects_estimate` (estimate refined as sync runs).
- Show as percentage + "X / Y files".

---

## Health Indicators

| Condition | Indicator |
|-----------|-----------|
| Replica is master | Star badge, "Master" tooltip |
| Sync delay > 5 min | Orange warning icon next to delay |
| Sync delay > 1 hour | Red icon, tooltip "Sync delayed — check connectivity" |
| Status = deleted | Badge only, row dimmed |
| Connectivity check fails (background heartbeat, every 60s) | Red status dot, "Unreachable" text |
| Master is unreachable | Banner at top: "Master replica {name} is unreachable. Sync paused for all replicas." |

---

## Uncertainties & Questions for BE

1. **Indexing vs ok**: What exactly transitions a replica from `indexing` to `ok`? Is it when all existing objects have been synced once, or does it require a full checksum verification?
2. **Sync delay calculation**: Confirm: is it `now() - max(synced_at)` across all files on the replica, or the timestamp of the last successful sync cycle?
3. **Type immutability**: Is changing a replica's type (e.g. local → S3) truly forbidden, or could BE support an in-place migration?
4. **Master downtime**: When master is unreachable:
   - Should the UI allow selecting a new master?
   - Can replicas continue to serve read requests?
   - Does sync queue up and replay when master is back?
5. **Sync progress**: Should the frontend show total sync progress (percentage of files synced across all replicas) or only per-replica delta behind master?
6. **Health check**: Is the connectivity heartbeat separate from the sync daemon, or does sync failure imply unreachable?
