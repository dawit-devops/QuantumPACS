# Feature: Tenants — Card Grid with Status Lifecycle

## Current State

Table layout at `/tenants`. Columns: Tenant (name+slug), Domain, Storage & Activity (stats component), Status, Action. Modal for create. Decommission maps to DELETE. Three statuses handled (active, pending, decommissioned). Missing: card grid, `quarantined` status, storage quota editing, provisioning spinner.

## Changes

### Backend (minimal)

**`db/tenants.py`**: Add `storage_quota_bytes` to `get_stats()` response so cards can display quota alongside usage without a separate API call per card.

### Frontend

**`Tenants.tsx`** — rewrite from table to card grid:
- Card per tenant: name + slug + domain at top, status badge (4 statuses with styling), storage bar with `used / quota` + percentage, user count + study count, action buttons (Edit + Decommission/Reactivate)
- **Provisioning**: skeleton/spinner card, actions disabled
- **Quarantined**: orange alert banner, Edit disabled, Decommission available
- **Decommissioned**: greyed out, no actions (view only)
- **Active**: full actions
- Storage bar colors: green <50%, orange 50-75%, red >75%
- Edit modal: name, domain, storage quota (number input in GB)
- Decommission popconfirm: includes retention period warning
- Create modal: name, slug, domain, storage quota (optional, defaults to system limit)

### Security

| Check | Status |
|-------|--------|
| Auth required | ✅ Already behind TENANT_READ/TENANT_ADMIN |
| Audit logged | ✅ Already logs tenant.provisioned / tenant.deleted |
