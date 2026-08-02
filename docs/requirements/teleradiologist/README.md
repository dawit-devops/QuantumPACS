# Requirements Package — Teleradiologist (R18)

| Field | Value |
|-------|-------|
| **Version** | 1.2.0 |
| **Status** | draft |
| **Generated** | 2026-08-03 |
| **Changelog** | [CHANGELOG.md](CHANGELOG.md) |

## Codebase Alignment (verified 2026-08-03)

**Presentation layer**: role-based; see artifact 04 — "Role-Based Routing &
Navigation": teleradiologists use the same viewer/worklist as R12 over a secure remote
session.

**Implemented**: remote viewing, annotations, shares (same as R12). **GATED**: offline/edge
packages, preliminary→final routing, second-opinion consult queue, secure remote
access config, structured reporting (shared R12 gap) — flagged to backend.

## Role Summary

**Persona**: Board-certified radiologist providing remote reading services for off-hours coverage, preliminary/stat reads, second opinions, and consultations.

**Context**: Works from home office or remote reading center; covers multiple hospital sites; provides 24/7/365 emergency coverage; requires high-bandwidth secure remote access; handles time-sensitive critical findings; may work across time zones.

**Top tasks (by frequency)**:
1. Access and read stat/urgent studies remotely (multiple times per shift)
2. Generate preliminary reports for off-hours coverage (daily)
3. Communicate critical findings to on-call clinicians (as needed)
4. Provide second opinions and consultations (daily)
5. Review and finalize preliminary reports (daily)
6. Access prior studies for comparison (every study)

**Pain points**: 
- VPN/connectivity issues during critical stat reads
- Slow image loading over WAN
- No offline access when connectivity drops
- Difficulty distinguishing preliminary vs final report states
- Manual communication of critical findings (no automated escalation)
- Credential management across multiple hospital systems
- Lack of mobile fallback for urgent consultations

**Devices**: 
- Primary: High-resolution dual-monitor workstation (home office)
- Secondary: Laptop (travel/backup)
- Mobile: Tablet/phone (urgent consultations only, limited viewer)

**Working patterns**: 
- Off-hours shifts (nights, weekends, holidays)
- High-acuity/time-sensitive work (stat reads ≤ 30min turnaround)
- Distributed attention across multiple sites
- Requires immediate critical finding notification
- Low tolerance for connectivity failures

**PHI exposure**: Full diagnostic access to all imaging and patient demographics — requires HIPAA audit trail, secure remote access (VPN/SSO), no PHI on personal devices outside encrypted channels.

## Artifact Index

| # | Artifact | File | Status |
|---|----------|------|--------|
| 01 | User Requirements | `01-user-requirements.md` | draft |
| 02 | Workflow Maps | `02-workflow-maps.md` | draft |
| 03 | User Stories | `03-user-stories.md` | draft |
| 04 | UI/UX Requirements | `04-ui-ux-requirements.md` | draft |
| 05 | Metrics & SLAs | `05-metrics-slas.md` | draft |
| 06 | Acceptance Criteria | `06-acceptance-criteria.md` | draft |
| 07 | Traceability Matrix | `07-traceability.md` | draft |
| 08 | Implementation Roadmap | `08-implementation-roadmap.md` | draft |

## Cross-Role Dependencies

### Upstream Dependencies (Data Providers)
- **R06/R07 (Technologists/Technicians)**: Exam completion triggers worklist assignment
- **R04 (Service Coordinator)**: Stat/priority triage affects worklist ordering
- **R02 (Tenant Admin)**: Remote access configuration, VPN/SSO setup
- **R15 (External RIS)**: Order context, scheduling data via HL7/FHIR
- **R16 (External EMR)**: Patient demographics, clinical context

### Downstream Dependencies (Data Consumers)
- **R14 (Referring Clinician)**: Report delivery, critical findings notification
- **R12 (Staff Radiologist)**: Preliminary report review and finalization
- **R03 (Service Director)**: Turnaround time metrics, coverage analytics

### Peer Dependencies
- **R12 (Staff Radiologist)**: Shared viewer/reporting tools, consultation workflow
- **R13 (Resident)**: Teaching case access, supervision workflow (teleradiologist may supervise remotely)

## Integration Contracts

### Required APIs (existing)
- `GET /api/studies` — Study search and worklist
- `GET /api/studies/{id}` — Study metadata
- `GET /api/studies/{id}/viewer` — DICOM viewer launch
- `POST /api/reports` — Report creation
- `PUT /api/reports/{id}` — Report update/finalization
- `GET /api/reports/{id}` — Report retrieval

### Required APIs (new/flagged for v3)
- `GET /api/v2/worklists/teleradiology` — Remote worklist with site/priority filtering
- `POST /api/v2/reports/{id}/finalize` — Preliminary → final state transition
- `POST /api/v2/critical-findings` — Critical finding notification with escalation
- `GET /api/v2/studies/{id}/offline-package` — Downloadable offline study bundle
- `GET /api/v2/users/me/sites` — Multi-site access for tenant-switching
- `POST /api/v2/consultations` — Consultation request/response workflow

### System Integrations
- **SSO/OAuth**: Azure AD, Okta (v3.0 requirement per PRD-v3.md)
- **VPN**: Hospital VPN or zero-trust network access
- **Critical findings escalation**: Email, SMS, pager integration (out-of-band notification)
- **Audit logging**: All remote access, study views, report actions logged with IP/location

## Regulatory & Compliance

### HIPAA Requirements
- **Minimum necessary**: Access limited to assigned worklist studies
- **Audit trail**: All remote access, study views, PHI exports logged with timestamp, IP, geolocation
- **Encryption**: TLS 1.3 for transport, AES-256 for data at rest
- **BAA**: Teleradiology service provider requires Business Associate Agreement
- **Breach notification**: Remote access failures logged; suspicious activity triggers security review

### Teleradiology-Specific Compliance
- **State licensure**: System must verify radiologist license matches study site state (out of scope for PACS, policy enforcement)
- **ACR Teleradiology Practice Guidelines**: 
  - Stat reads ≤ 30min
  - Preliminary reports clearly marked
  - Critical findings communicated within 15min
  - Remote radiologist credentials verified

### Quality Assurance (R05 interface)
- Turnaround time tracking (stat vs routine)
- Discrepancy rate (preliminary vs final)
- Critical finding communication latency

## Open Questions & Risks

1. **Offline study package format**: DICOMDIR? Encrypted ZIP? Web-based offline PWA cache?
2. **Multi-site credential management**: Single sign-on across tenants? Per-tenant credentials?
3. **Mobile viewer capabilities**: Full diagnostic reading or consultative review only?
4. **Preliminary report workflow**: Auto-assignment to on-site radiologist for finalization? Notification mechanism?
5. **Bandwidth requirements**: Minimum WAN speed for diagnostic reading? Fallback for low-bandwidth scenarios?
6. **Critical finding escalation**: Automated paging/SMS? Integration with hospital on-call system?
7. **Liability**: Does PACS log preliminary vs final state transitions for malpractice defense?

## Related Documentation

- [PRD-v3.md](../../PRD-v3.md) — OAuth/SSO, multi-tenant, DICOMweb requirements
- [User-Stories.md](../../User-Stories.md) — E3 (Study Viewing), E4 (Reporting)
- [SECURITY_AUDIT.md](../../SECURITY_AUDIT.md) — Remote access security findings
- [PRODUCTION_READINESS_REVIEW.md](../../PRODUCTION_READINESS_REVIEW.md) — Auth, audit, performance issues

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for the full version history.
