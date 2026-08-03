# Implementation Roadmap — Tenant Admin (R02)

## Artifact Status Overview

| # | Artifact | File | Status |
|---|----------|------|--------|
| 01 | User Requirements | `01-user-requirements.md` | done |
| 02 | Workflow Maps | `02-workflow-maps.md` | done |
| 03 | User Stories | `03-user-stories.md` | done |
| 04 | UI/UX Requirements | `04-ui-ux-requirements.md` | done |
| 05 | Metrics & SLAs | `05-metrics-slas.md` | done |
| 06 | Acceptance Criteria | `06-acceptance-criteria.md` | done |
| 07 | Traceability Matrix | `07-traceability.md` | partial |
| 08 | Implementation Roadmap | `08-implementation-roadmap.md` | partial |

## FR/NFR Implementation Status

### Implemented (Passing ACs)

| FR/NFR ID | Summary | AC Coverage | Effort |
|-----------|---------|-------------|--------|
| FR-R02-01 | The system SHALL scope every R02 view and action to the active tenant; cross-ten | AC-R02-01, AC-R02-02 | S |
| FR-R02-02 | The system SHALL allow the tenant admin to manage tenant users: list, create, de | AC-R02-03, AC-R02-04 | S |
| FR-R02-03 | The system SHALL allow the tenant admin to bulk-import tenant users from CSV wit | AC-R02-05 | M |
| FR-R02-04 | The system SHALL allow the tenant admin to manage modality worklists: view, crea | AC-R02-06, AC-R02-07, AC-R02-08 | S |
| FR-R02-05 | The system SHALL allow the tenant admin to register and manage station AE titles | AC-R02-29 | S |
| FR-R02-06 | The system SHALL allow the tenant admin to manage DICOM routing rules within the | AC-R02-09, AC-R02-10 | S |
| FR-R02-07 | The system SHALL allow the tenant admin to manage service API keys for tenant in | AC-R02-11 | S |
| FR-R02-09 | The system SHALL allow the tenant admin to configure the HL7 interface for the t | AC-R02-12, AC-R02-13 | S |
| FR-R02-10 | The system SHALL allow the tenant admin to configure the FHIR server, OAuth clie | AC-R02-14, AC-R02-15 | S |
| FR-R02-11 | The system SHALL allow the tenant admin to review tenant audit logs with event-t | AC-R02-16, AC-R02-17 | S |
| FR-R02-12 | The system SHALL allow the tenant admin to view tenant-scoped metrics (platform  | AC-R02-18 | S |
| FR-R02-13 | The system SHALL allow the tenant admin to receive tenant notifications (replica | AC-R02-21 | M |
| FR-R02-14 | The system SHALL NOT expose global/super-admin items (other tenants, global repl | AC-R02-19 | S |
| FR-R02-16 | The system SHALL log every R02 mutation to the tenant audit log with actor, acti | AC-R02-03, AC-R02-11, AC-R02-22 | S |
| NFR-R02-03 | Cross-tenant access denied | AC-R02-01 | L || NFR-R02-06 | No PHI in URLs, logs, analytics | AC-R02-15 | L |

### Partially Implemented (GATED / Partial)

| FR/NFR ID | Summary | Blocking Dependency | AC | Effort |
|-----------|---------|---------------------|----|--------|
| FR-R02-15 | Tenant storage usage — `GET /tenants/{id}/stats` exists (storage + quota); usage/quota dashboard UI GATED | Usage dashboard endpoint/UI needed | AC-R02-20 | M |

### Missing (Not Started)

| FR/NFR ID | Summary | Reason | AC | Effort |
|-----------|---------|--------|----|--------|
| FR-R02-08 | The system SHALL allow the tenant admin to manage tenant-scoped storage replicas | Not yet scoped | — | L |
| NFR-R02-01 | Tenant admin pages load (LCP) | Not yet scoped | — | L |
| NFR-R02-02 | Admin interactions respond (INP) | Not yet scoped | — | L |
| NFR-R02-04 | Tenant audit queries first page | Not yet scoped | — | L |
| NFR-R02-05 | Worklist/station list freshness | Not yet scoped | — | L |
| NFR-R02-07 | WCAG 2.1 AA for all admin screens | Not yet scoped | — | L |
| NFR-R02-08 | Tenant switch context retained | Not yet scoped | — | L |
| NFR-R02-09 | Tenant isolation under load | Not yet scoped | — | L |
| NFR-R02-10 | Session idle timeout | Not yet scoped | — | L |

## Blocking Dependencies

| Blocking Dependency | Blocks | AC | Impact |
|---------------------|--------|----|--------|

## Next Steps (highest priority)

2. **Scope missing requirements** — 9 FR/NFRs not yet implemented
3. **Update roadmap each sprint** as FR/NFR status changes
