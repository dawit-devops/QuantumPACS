# pacs_admin — Backend Inventory (Phase 5a)
Date: 2026-08-28 | Baseline commit: 19012b3
Skills invoked: iam-audit (dead grants)

## Route coverage summary

pacs_admin has 21 reachable surfaces (15 original + 6 PACS-ops from R1). The backend API walk confirmed all expected endpoints return 200 for read operations and 403 for writes (where the write permission is not held). See [PLAN.md](PLAN.md) walk table for per-route results.

## ORPHANED (should surface)

None found within pacs_admin's scope. The super_admin walk (Phase 5a, commit 56bd560) performed a global inventory of 344 routes × 245 frontend call paths and found 19 ORPHANED handlers — all were triaged and decided (O8 Reconciliation wired, O9 Denial Import wired, rest deferred). The R1 grant additions (DICOMWEB_READ, HL7_READ, REPLICA_READ, ROUTING_READ) unlocked existing fully-wired UI surfaces — no new orphans.

## INTERNAL (no UI by design)

All `/ris/patients/*`, `/ris/orders/*`, `/ris/appointments/*`, `/ris/checkin/*`, `/ris/resources/*`, `/ris/scheduling/*`, `/ris/protocols/*`, `/ris/corrective-actions/*` — clinical/workflow routes for other roles (technologist, receptionist, care_coordinator). Not in pacs_admin's scope.

## DEAD (removal/wiring candidates)

The pre-existing dead grants STORAGE_ADMIN, INTERFACE_ADMIN, INTERFACE_MONITOR (gating zero backend endpoints) were addressed by the R1 decision: the PACS-ops surfaces now gate on the correct permissions (DICOMWEB_READ, HL7_READ, REPLICA_READ, ROUTING_READ) which pacs_admin holds. The old dead grants remain in the grant set (harmless, retained for spec matrix alignment).

## Findings specific to pacs_admin

1. **F2**: `_can_assign_role` subset check (users.py:52-65) blocks R2-16's intent — pacs_admin can only assign the `pacs_admin` role itself. Every clinical/operational built-in role contains permissions pacs_admin lacks (EXAM_READ, EXAM_WRITE, etc. for technologist; REPORT_WRITE, REPORT_SIGN for radiologist) → assigning any clinical role returns 403 "Target role exceeds your own grants". This is a security control against privilege escalation, but it contradicts the R2-16 comment. Decision needed: relax the subset check for built-in roles, or update R2-16 docs.

2. **F3**: Dashboard health/metrics panels 403 for pacs_admin (no METRICS_READ). tenant_admin gets METRICS_READ via LEGACY_TENANT_ADMIN union; pacs_admin has no legacy union. The Admin Dashboard is the landing page — its core panels degrade gracefully but show empty states. Decision needed: add METRICS_READ to pacs_admin, or accept degraded dashboard.