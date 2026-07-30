# Tenants Page — Backend Requirements

**Route**: `/tenants`
**Role**: PACS Admin
**Isolation**: database-per-tenant

---

## Tenant List Display

| Field | Type | Notes |
|-------|------|-------|
| name | string | Human-readable, e.g. "Memorial Hospital West" |
| slug | string | URL-safe identifier, e.g. `memorial-west` |
| domain | string \| null | Custom domain, e.g. `pacs.memorialwest.com` |
| user_count | int | Number of active users in tenant |
| status | enum | provisioning / active / quarantined / decommissioned |
| storage_used_bytes | bigint | Current storage consumed |
| storage_quota_bytes | bigint | Maximum allowed storage |
| storage_pct | float | Computed: `storage_used_bytes / storage_quota_bytes * 100` |

Display as a card grid. Each card shows name, slug, domain, user count icon, status badge, storage usage bar (with percentage label), and action buttons.

Storage bar color thresholds:
- **Green** `< 50%` — normal
- **Orange** `50–75%` — warning
- **Red** `> 75%` — critical

---

## Tenant States & UI Treatment

| Status | Behavior | UI Treatment |
|--------|----------|-------------|
| `provisioning` | DB being created, resources allocated | Spinner badge, skeleton card body, actions disabled |
| `active` | Normal operation | Normal display, all actions available |
| `quarantined` | Suspicious activity detected, read-only | Orange warning banner on card, Edit disabled, Decommission available |
| `decommissioned` | Data retention period, no access | Card greyed out, name/domain struck through, no actions (view only) |

Expected provisioning time: **< 60 seconds** (DB creation + initial schema migration + default role seeding).

---

## Provisioning a New Tenant

Required fields:
- **name** — display name
- **slug** — unique, URL-safe, auto-suggested from name
- **domain** — optional, unique if set
- **storage_quota_bytes** — default from system config, overridable

Backend responsibilities:
1. Validate slug + domain uniqueness
2. Create database with name `tenant_{slug}`
3. Run Alembic migrations on new DB
4. Seed default roles (admin, user, viewer)
5. Create initial admin user with temporary password
6. Return tenant record + initial credentials
7. If any step fails, roll back (drop DB, clean up)

---

## Actions

### Edit Tenant
- **Name** — always editable
- **Domain** — editable, must remain unique; clearing sets to null
- **Storage quota** — editable; changing it does not retroactively affect over-quota state but updates thresholds for future checks

### Decommission Tenant
1. Set status → `decommissioned`
2. Revoke all active sessions/tokens for tenant users
3. Disable login for tenant (auth returns 403)
4. Data is **not** deleted — retained per retention policy (configurable, default 90 days)
5. After retention period, a background job permanently drops the tenant DB
6. Decommission is **not reversible** without manual DBA intervention

---

## Storage Quota Enforcement

**Soft limit** — tenant can exceed quota but receives warning indicators in UI. No automatic read-only enforcement. A background check (runs every 5 min) logs warnings when a tenant exceeds quota. Enforcement (blocking new uploads) is a future v3 feature.

Storage usage is updated by a periodic aggregation job (every 15 min) that sums DICOM file sizes per tenant.

---

## Uncertainties & Questions for BE

1. **Editable fields**: Are any fields besides name, domain, and storage quota editable on an existing tenant? What about slug?
2. **Decommission data fate**: Confirm retention period duration and whether data is hard-deleted at expiry or just anonymized.
3. **Quota enforcement**: Confirm soft limit is acceptable for v3. When hard enforcement is added, should it block C-STORE at the DICOM level or only REST API uploads?
4. **Storage display**: Should the UI show absolute GB values (e.g. "342 GB / 1 TB") alongside the percentage bar, or percentage only?
5. **Provisioning API**: Does the create endpoint return the initial admin credentials synchronously, or should it return a task ID for polling?
6. **Domain uniqueness**: Is domain unique across all tenants or nullable-only? What about empty string vs null?
