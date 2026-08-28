# tenant_admin — Backlog (open items from walk)

Session: role-walk/tenant_admin (branch feature/ris-integration, 2026-08-28).
Fixes applied during the walk (F2/F3/F5/F6 + O1) are closed and committed — see
[PLAN.md](PLAN.md) findings table. This file tracks items that were **deferred,
kept-by-decision, or discovered but not fixed** during the walk. Triage into
sprints per priority.

| ID | Severity | Area | Item | Source | Status |
|----|----------|------|------|--------|--------|
| BL-001 | Medium | Auth / RBAC (iam-audit) | Replace the legacy `user.admin` boolean path: `_is_platform_admin` (backend/api/tenants.py:35-38) and other admin gates use the parallel `user.admin` column instead of an explicit `SYSTEM_ADMIN`-or-`super_admin` role check. Fragile legacy bypass — tenant_admin is correctly scoped today (admin=false) but the pattern violates the centralized-`can()` principle. | G4 / R2 (Phase 3, DEFER approved) | Open |
| BL-002 | Low | Docs | ~~ADR-017 `tenant_admin` row still reads "All resources within tenant: all actions"~~ — **RESOLVED**: R1 UPDATE-DOCS applied in 2306d0c (docs/decisions/ADR-017 line 75 now "Tenant-scoped operational admin…"). Kept as a closed reference row. | G1 / R1 (Phase 3, UPDATE-DOCS) | Closed (2306d0c) |
| BL-003 | Low | Backend startup | `load_maintenance_state` (backend/api/admin.py:70-82) logs `AttributeError: 'str' object has no attribute 'get'` at startup — `PlatformState.get` returns the raw JSONB `value` (backend/db/platform_state.py:21), which is a string when the row holds a JSON string, then `st.get('active')` fails. Non-fatal (wrapped in try/except) but noisy and hides the real maintenance state. Fix: coerce/parse the value in `PlatformState.get` or guard in `load_maintenance_state`. | Session note (noticed in journal, not investigated during walk) | Open |
| BL-004 | Low | Permissions (least-privilege) | Dead grants `STORAGE_ADMIN` and `CDS_ADMIN` sit in the tenant_admin grant set (and pacs_admin) but no route gates on them — nothing in the backend is unlocked by them. User decision was KEEP; recorded here for a future least-privilege trim if the platform later wires storage/CDS surfaces. | O2 (Phase 5a, KEEP by user decision) | Open (decision: KEEP) |
| BL-005 | Low | Interface ops | Exception-retry endpoint gates `HL7_WRITE`, not `INTERFACE_ADMIN` — tenant_admin can monitor but not replay failed HL7 exceptions. Matches prior routing-gate decision (INTERFACE_ADMIN is monitor-only). No code change; document if tenant admins need replay capability in future. | F4 (Phase 5a, KEEP consistent with prior decision) | Open (decision: KEEP) |

## Definition of done / triage hints

- **BL-001** (highest priority): replace `user.admin` checks with a role-based helper (e.g. `is_system_admin(user)`), then drop/stop-populating the legacy column. Target: IAM-hardening sprint.
- **BL-003**: confirm repro (startup log), then fix `PlatformState.get` to return parsed dict or guard with `isinstance(st, dict)`.
- **BL-004**: only if/when storage/CDS admin surfaces are wired — re-evaluate the grant set.
- **BL-005**: product decision — document as known limitation or add a replay permission.
