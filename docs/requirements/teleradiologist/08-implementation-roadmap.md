# Implementation Roadmap — Teleradiologist (R18)

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

### Missing (Not Started)

| FR/NFR ID | Summary | Reason | AC | Effort |
|-----------|---------|--------|----|--------|
| FR-R18-01 | As a teleradiologist, the system SHALL provide a dedicated remote worklist filte | Not yet scoped | — | L |
| FR-R18-02 | The system SHALL display worklist freshness indicator showing last sync timestam | Not yet scoped | — | L |
| FR-R18-03 | The system SHALL support secure remote access via SSO (OAuth/OIDC) with multi-si | Not yet scoped | — | L |
| FR-R18-04 | The system SHALL provide full DICOM viewer functionality identical to on-site ra | Not yet scoped | — | L |
| FR-R18-05 | The system SHALL load first image of a study (500-instance CT) in ≤ 2.5s over WA | Not yet scoped | — | L |
| FR-R18-06 | The system SHALL prefetch next 3 worklist studies in background while current st | Not yet scoped | — | L |
| FR-R18-07 | The system SHALL allow preliminary report creation with explicit "Preliminary" s | Not yet scoped | — | L |
| FR-R18-08 | The system SHALL allow teleradiologist to escalate preliminary report to final i | Not yet scoped | — | L |
| FR-R18-09 | The system SHALL provide critical findings notification workflow with escalation | Not yet scoped | — | L |
| FR-R18-10 | The system SHALL log critical finding timestamp and clinician notification metho | Not yet scoped | — | L |
| FR-R18-11 | The system SHALL provide consultation request/response workflow with study link  | Not yet scoped | — | L |
| FR-R18-12 | The system SHALL support voice dictation integration (Dragon Medical, Microsoft  | Not yet scoped | — | L |
| FR-R18-13 | The system SHALL provide offline study package download for studies assigned to  | Not yet scoped | — | L |
| FR-R18-14 | The system SHALL sync offline report drafts when connectivity is restored | Not yet scoped | — | L |
| FR-R18-15 | The system SHALL display multi-site dashboard showing worklist counts and turnar | Not yet scoped | — | L |
| FR-R18-16 | The system SHALL allow teleradiologist to mark study as "Consulted" when providi | Not yet scoped | — | L |
| FR-R18-17 | The system SHALL provide mobile viewer for urgent consultations with limited dia | Not yet scoped | — | L |
| FR-R18-18 | The system SHALL display prior studies comparison in side-by-side layout with sy | Not yet scoped | — | L |
| FR-R18-19 | The system SHALL track and display turnaround time per study (from assignment to | Not yet scoped | — | L |
| FR-R18-20 | The system SHALL alert teleradiologist when assigned STAT study exceeds 20min wi | Not yet scoped | — | L |
| FR-R18-21 | The system SHALL provide secure messaging to referring clinician for result noti | Not yet scoped | — | L |
| FR-R18-22 | The system SHALL support multi-monitor layout profiles (2-monitor, 3-monitor, la | Not yet scoped | — | L |
| FR-R18-23 | The system SHALL display patient allergy/contrast reaction warnings prominently  | Not yet scoped | — | L |
| FR-R18-24 | The system SHALL provide hanging protocol templates optimized for common remote  | Not yet scoped | — | L |
| NFR-R18-01 | Remote worklist load time | Not yet scoped | — | L |
| NFR-R18-02 | Worklist real-time sync staleness | Not yet scoped | — | L |
| NFR-R18-03 | DICOM viewer first-image load (500-inst CT, WAN) | Not yet scoped | — | L |
| NFR-R18-04 | DICOM viewer interaction responsiveness (pan/zoom/scroll) | Not yet scoped | — | L |
| NFR-R18-05 | Report autosave interval | Not yet scoped | — | L |
| NFR-R18-06 | Offline study package generation | Not yet scoped | — | L |
| NFR-R18-07 | Critical findings notification latency | Not yet scoped | — | L |
| NFR-R18-08 | System availability for remote access | Not yet scoped | — | L |
| NFR-R18-09 | Session timeout for inactive remote sessions | Not yet scoped | — | L |
| NFR-R18-10 | Concurrent remote viewer sessions per teleradiologist | Not yet scoped | — | L |
| NFR-R18-11 | VPN/SSO authentication time | Not yet scoped | — | L |
| NFR-R18-12 | Audit log retention for remote access | Not yet scoped | — | L |
| NFR-R18-13 | Bandwidth utilization for background prefetch | Not yet scoped | — | L |
| NFR-R18-14 | Mobile viewer compatibility | Not yet scoped | — | L |
| NFR-R18-15 | Keyboard accessibility for all worklist and viewer actions | Not yet scoped | — | L |
| NFR-R18-16 | Screen reader support for non-viewer UI | Not yet scoped | — | L |
| NFR-R18-17 | TLS version for remote access | Not yet scoped | — | L |
| NFR-R18-18 | Geographic latency tolerance | Not yet scoped | — | L |

## Blocking Dependencies

| Blocking Dependency | Blocks | AC | Impact |
|---------------------|--------|----|--------|

## Next Steps (highest priority)

2. **Scope missing requirements** — 42 FR/NFRs not yet implemented
3. **Update roadmap each sprint** as FR/NFR status changes
