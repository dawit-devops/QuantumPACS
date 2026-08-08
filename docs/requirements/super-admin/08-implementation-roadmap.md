# Implementation Roadmap — Super Admin (R01)

## Artifact Status Overview

| # | Artifact | File | Status | Notes |
|---|----------|------|--------|-------|
| 01 | User Requirements | `01-user-requirements.md` | done | 20 FRs, 14 NFRs; all quantified |
| 02 | Workflow Maps | `02-workflow-maps.md` | done | 5 workflows with Mermaid maps |
| 03 | User Stories | `03-user-stories.md` | done | 17 stories with Given/When/Then AC |
| 04 | UI/UX Requirements | `04-ui-ux-requirements.md` | done | Screens, states, tokens, a11y, responsive |
| 05 | Metrics & SLAs | `05-metrics-slas.md` | done | 5 KPIs with targets and owners |
| 06 | Acceptance Criteria | `06-acceptance-criteria.md` | done | 41 ACs; 40 Pass, 1 GATED |
| 07 | Traceability Matrix | `07-traceability.md` | partial | Created as part of this update; all FR/NFR → AC mappings verified |
| 08 | Implementation Roadmap | `08-implementation-roadmap.md` | partial | Being created; initial draft |

## FR/NFR Implementation Status

### Implemented (Passing ACs)

| FR/NFR ID | Summary | AC Coverage | Effort |
|-----------|---------|-------------|--------|
| FR-R01-01 | Tenant CRUD + provisioning | AC-R01-01, 02, 03 | Small |
| FR-R01-02 | Tenant switcher | AC-R01-04 | Small |
| FR-R01-03 | User management (CRUD, deactivate, password reset, role change) | AC-R01-05, 06 | Small |
| FR-R01-04 | Bulk CSV import with validation report | AC-R01-07 | Small |
| FR-R01-05 | RBAC role management (CRUD, permission catalog) | AC-R01-08, 09 | Medium |
| FR-R01-06 | Storage replica management | AC-R01-10, 11 | Small |
| FR-R01-07 | DICOM routing rules with condition builder | AC-R01-12, 13 | Medium |
| FR-R01-08 | Service API key management (create, rotate, revoke) | AC-R01-14, 15 | Small |
| FR-R01-09 | Integration webhook management + test delivery | AC-R01-35 | Small |
| FR-R01-10 | Audit log review with filters and facets | AC-R01-16, 17, 18 | Medium |
| FR-R01-11 | System metrics dashboards (platform, DICOM-web, HL7, FHIR) | AC-R01-19, 20 | Medium |
| FR-R01-12 | DICOMweb station AE title management | AC-R01-36 | Small |
| FR-R01-13 | FHIR configuration (server, OAuth clients, test requests) | AC-R01-21, 22 | Small |
| FR-R01-14 | HL7 connection config, status, message history | AC-R01-23, 24 | Small |
| FR-R01-15 | OAuth/SSO provider management | AC-R01-25, 26 | Small |
| FR-R01-16 | In-app notifications for admin events | AC-R01-27 | Small |
| FR-R01-17 | Global system health summary (`GET /v2/dashboard/health` aggregate of db/es/redis/storage/dicom_listener/ingestion_service/hl7/fhir/auth; drill-down links) | AC-R01-37 | Medium |
| FR-R01-19 | Audit logging for all admin mutations | AC-R01-05, 28 | Small |
| FR-R01-20 | Permission-based access control (403 for unauthorized) | AC-R01-29 | Small |
| NFR-R01-01 | Admin page load budget (LCP ≤ 2.5s) | AC-R01-30 | Small |
| NFR-R01-02 | Admin list interaction budget (INP ≤ 200ms) | AC-R01-31 | Small |
| NFR-R01-03 | Audit log query performance (≤ 2s p90 on 1M rows) | AC-R01-16 | Medium |
| NFR-R01-04 | Server-side pagination (20–100 page size) | AC-R01-39 | Small |
| NFR-R01-05 | 100% audit coverage for admin mutations | AC-R01-01, 11, 28 | Small |
| NFR-R01-06 | No PHI in URLs, logs, or analytics | AC-R01-06, 15, 26 | Small |
| NFR-R01-07 | Keyboard operability (WCAG 2.1 AA) | AC-R01-32 | Small |
| NFR-R01-08 | Screen reader accessibility (WCAG 2.1 AA) | AC-R01-32 | Small |
| NFR-R01-09 | Tenant switch reflected app-wide (≤ 1s) | AC-R01-04 | Small |
| NFR-R01-11 | Graceful degradation when ES is down | AC-R01-33 | Medium |
| NFR-R01-12 | ≥ 10 concurrent admin sessions | AC-R01-40 | Medium |
| NFR-R01-13 | 30-min idle timeout with re-auth | AC-R01-34 | Small |
| NFR-R01-14 | Audit log retention ≥ 1 year, configurable archive | AC-R01-41 | Small |

### Partially Implemented (GATED — blocked on backend work)

| FR/NFR ID | Summary | Blocking Dependency | AC | Effort |
|-----------|---------|---------------------|----|--------|
| FR-R01-18 | Backup/restore (DB + files) with audit logging | No implementation exists; backlog | AC-R01-38 | Large |

## Dependency-Ordered Implementation Plan

### Phase 1: Foundation (already done)
- Artifacts 01–06 complete; 32 of 33 FR/NFR requirements implemented and passing

### Phase 2: Unblock GATED requirements (next priority)
1. **Backend aggregate health endpoint** — **DONE** (2026-08-05): `GET /v2/dashboard/health` (METRICS_READ) implemented; AC-R01-37 now Pass
   - Owner: Backend team (completed)
   - Blocks: none — AC-R01-37 verified, FR-R01-17 closed
2. **Backup/restore implementation** — required for FR-R01-18 / AC-R01-38
   - Owner: Backend + DevOps
   - Blocks: AC-R01-38, FR-R01-18
   - Effort: Large
   - Requires: DB backup tooling, file snapshot, restore procedure, audit logging

### Phase 3: Traceability and roadmap maintenance
3. **Artifact 07 traceability matrix** — partial; verify all cross-role dependencies with R02–R19 packages as they are generated
4. **Artifact 08 roadmap** — partial; update each sprint as FR/NFR status changes

## Blocking Dependencies

| Blocking Dependency | Blocks | AC | Impact |
|---------------------|--------|----|--------|
| Backup/restore implementation | FR-R01-18 | AC-R01-38 | Backup/restore cannot be tested or validated |

## Next Steps (highest priority)

1. **Implement backup/restore** — unblocks AC-R01-38 and FR-R01-18; Large effort
2. **Regenerate traceability matrix** — update 07-traceability.md when other role packages (R02–R19) are generated to cross-reference R01 dependencies
3. **Update roadmap each sprint** — mark FR/NFR status changes as artifacts 01–06 evolve
