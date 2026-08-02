# User Requirements — Teleradiologist (R18)

**Role ID**: R18  
**Generated**: 2026-08-02  
**Version**: 1.0.0

---

## Functional Requirements

| ID | Requirement | Priority | Notes |
|----|-------------|----------|-------|
| FR-R18-01 | As a teleradiologist, the system SHALL provide a dedicated remote worklist filtered by site, priority (STAT/urgent/routine), and assignment status | Must | See W1 workflow |
| FR-R18-02 | The system SHALL display worklist freshness indicator showing last sync timestamp and connection status | Must | Real-time confidence for remote readers |
| FR-R18-03 | The system SHALL support secure remote access via SSO (OAuth/OIDC) with multi-site tenant switching | Must | v3.0 OAuth per PRD-v3.md U-v3.5 |
| FR-R18-04 | The system SHALL provide full DICOM viewer functionality identical to on-site radiologist (R12) access | Must | Feature parity: MPR, MIP, 3D, hanging protocols |
| FR-R18-05 | The system SHALL load first image of a study (500-instance CT) in ≤ 2.5s over WAN (10 Mbps connection) | Must | Performance target for remote reading |
| FR-R18-06 | The system SHALL prefetch next 3 worklist studies in background while current study is being read | Should | Reduces wait time between studies |
| FR-R18-07 | The system SHALL allow preliminary report creation with explicit "Preliminary" state flag | Must | Distinct from final reports |
| FR-R18-08 | The system SHALL allow teleradiologist to escalate preliminary report to final if credentialed for that site | Should | Workflow flexibility for credentialed readers |
| FR-R18-09 | The system SHALL provide critical findings notification workflow with escalation checklist | Must | ACR guideline: critical findings ≤ 15min |
| FR-R18-10 | The system SHALL log critical finding timestamp and clinician notification method (phone/page/secure message) | Must | Medico-legal documentation |
| FR-R18-11 | The system SHALL provide consultation request/response workflow with study link and messaging | Should | Second opinion workflow |
| FR-R18-12 | The system SHALL support voice dictation integration (Dragon Medical, Microsoft Speech) | Could | Efficiency for high-volume shifts |
| FR-R18-13 | The system SHALL provide offline study package download for studies assigned to the teleradiologist | Should | Connectivity failure mitigation |
| FR-R18-14 | The system SHALL sync offline report drafts when connectivity is restored | Should | Offline resilience |
| FR-R18-15 | The system SHALL display multi-site dashboard showing worklist counts and turnaround time per site | Must | Coverage visibility |
| FR-R18-16 | The system SHALL allow teleradiologist to mark study as "Consulted" when providing second opinion | Should | Distinct from primary read |
| FR-R18-17 | The system SHALL provide mobile viewer for urgent consultations with limited diagnostic capability | Could | Emergency fallback |
| FR-R18-18 | The system SHALL display prior studies comparison in side-by-side layout with synchronized scrolling | Must | Standard reading workflow |
| FR-R18-19 | The system SHALL track and display turnaround time per study (from assignment to preliminary report) | Must | R05 QA metrics |
| FR-R18-20 | The system SHALL alert teleradiologist when assigned STAT study exceeds 20min without report initiation | Must | Proactive escalation |
| FR-R18-21 | The system SHALL provide secure messaging to referring clinician for result notification | Should | Alternative to phone notification |
| FR-R18-22 | The system SHALL support multi-monitor layout profiles (2-monitor, 3-monitor, laptop single-screen) | Must | Home office ergonomics |
| FR-R18-23 | The system SHALL display patient allergy/contrast reaction warnings prominently in viewer | Must | Patient safety |
| FR-R18-24 | The system SHALL provide hanging protocol templates optimized for common remote reading scenarios (chest CT, trauma pan-scan, neuro stroke) | Should | Reading efficiency |

## Non-Functional Requirements

| ID | Requirement | Target | Measurement |
|----|-------------|--------|-------------|
| NFR-R18-01 | Remote worklist load time | LCP ≤ 2.0s, INP ≤ 200ms | Lighthouse CI from remote IP, 10 Mbps throttle |
| NFR-R18-02 | Worklist real-time sync staleness | ≤ 5s from exam completion to worklist appearance | WebSocket latency + DB trigger |
| NFR-R18-03 | DICOM viewer first-image load (500-inst CT, WAN) | ≤ 2.5s p95 | Playwright + network throttle, 10 Mbps |
| NFR-R18-04 | DICOM viewer interaction responsiveness (pan/zoom/scroll) | INP ≤ 200ms | Cornerstone3D event timing |
| NFR-R18-05 | Report autosave interval | ≤ 10s, optimistic update | TanStack Query mutation |
| NFR-R18-06 | Offline study package generation | ≤ 30s for 500-instance study | Backend ZIP generation |
| NFR-R18-07 | Critical findings notification latency | ≤ 30s from report save to clinician notification | Audit log timestamp delta |
| NFR-R18-08 | System availability for remote access | ≥ 99.95% (excl. maintenance) | Synthetic uptime monitor from 3 geo locations |
| NFR-R18-09 | Session timeout for inactive remote sessions | 15 min idle → warning, 20 min → logout | Token expiry + client-side timer |
| NFR-R18-10 | Concurrent remote viewer sessions per teleradiologist | ≥ 3 simultaneous studies (multi-tab) | WebSocket connection limit |
| NFR-R18-11 | VPN/SSO authentication time | ≤ 3s from SSO redirect to worklist display | OAuth flow + token exchange |
| NFR-R18-12 | Audit log retention for remote access | ≥ 7 years | HIPAA compliance |
| NFR-R18-13 | Bandwidth utilization for background prefetch | ≤ 30% of available bandwidth | Adaptive prefetch throttle |
| NFR-R18-14 | Mobile viewer compatibility | iOS Safari 15+, Android Chrome 90+ | BrowserStack matrix |
| NFR-R18-15 | Keyboard accessibility for all worklist and viewer actions | 100% keyboard-operable, WCAG 2.1 AA | Automated a11y scan + manual test |
| NFR-R18-16 | Screen reader support for non-viewer UI | ARIA labels, NVDA/JAWS compatible | Manual accessibility audit |
| NFR-R18-17 | TLS version for remote access | TLS 1.3 only, no legacy fallback | SSL Labs scan |
| NFR-R18-18 | Geographic latency tolerance | Functional at ≤ 150ms RTT, degraded 150-300ms | k6 latency injection |

## Security & Compliance Requirements

| ID | Requirement | Target | Notes |
|----|-------------|--------|-------|
| SEC-R18-01 | Remote access requires SSO authentication + MFA | 100% enforcement | No fallback password login for remote IPs |
| SEC-R18-02 | All remote sessions logged with IP, geolocation, device fingerprint | 100% coverage | HIPAA audit trail |
| SEC-R18-03 | Remote access restricted to pre-approved IP ranges or VPN | Policy enforcement | Configurable per tenant |
| SEC-R18-04 | Remote session re-authentication after 4 hours | Token refresh flow | Reduce credential exposure window |
| SEC-R18-05 | No PHI in browser localStorage or sessionStorage | Zero tolerance | All PHI in memory or encrypted IndexedDB |
| SEC-R18-06 | Remote study views logged with view duration and actions (zoom/pan/measure) | Audit detail | Medico-legal defense |
| SEC-R18-07 | Offline study packages encrypted with AES-256, password-protected | 100% enforcement | Encrypted ZIP or container |
| SEC-R18-08 | Remote access from public/untrusted networks blocked | Policy enforcement | Detect open WiFi, warn user |
| SEC-R18-09 | Suspicious activity detection (impossible travel, unusual hours, high volume) | Real-time alerting | Security ops integration |
| SEC-R18-10 | Remote teleradiologist credentials verified against state license database | Pre-access check | Out of PACS scope, policy enforcement |

## Codebase Status (verified 2026-08-03)

**Implemented**: remote viewer, annotations, shares (same as R12). **GATED**:
FR-R18 offline/edge packages, preliminary→final routing, second-opinion consult
queue, secure remote access config, structured reporting (shared R12 gap) — flagged
to backend. See artifacts 04/07/08.

## Assumptions & Constraints

### Technical Assumptions
- Teleradiologist has minimum 10 Mbps symmetric WAN connection (diagnostic reading threshold per ACR)
- Teleradiologist workstation meets minimum specs: dual 4K monitors, 16GB RAM, discrete GPU for 3D rendering
- Hospital provides VPN access or zero-trust network with SSO integration
- DICOM studies compressed with lossless JPEG 2000 or RLE for WAN transmission efficiency

### Regulatory Constraints
- Teleradiologist must hold active medical license in state where patient is located (policy enforcement, not PACS)
- Preliminary reports must be reviewed by on-site radiologist within 24 hours (R12 workflow)
- Critical findings require direct clinician communication (phone/page), not email alone
- Remote access audit logs retained for 7 years per HIPAA

### Operational Constraints
- Teleradiology service operates 24/7/365 with guaranteed ≤ 30min STAT turnaround
- Teleradiologist covers 2-5 hospital sites simultaneously
- Maximum 15 studies per 8-hour shift for diagnostic quality (RBRVS productivity baseline)
- Off-hours coverage has fewer IT support resources (self-service troubleshooting required)

### Integration Constraints
- SSO integration requires OAuth/OIDC provider (Azure AD, Okta) per v3.0 roadmap
- Critical findings escalation requires integration with hospital on-call/paging system (out of scope for initial release)
- Voice dictation requires third-party integration (Dragon Medical, Microsoft Speech) — plugin architecture

### Excluded Scope (Explicit Non-Requirements)
- No built-in tele-consultation video conferencing (use Zoom/Teams separately)
- No automatic report signing without radiologist review (all reports require explicit sign-off)
- No AI-assisted preliminary reports (AI inference out of scope per PRD-v3.md)
- No direct modality control from remote location (read-only access)
- No remote PACS administration (R01/R02 functions restricted to on-site or VPN-only access)

## API Dependency Analysis

### Existing APIs (v2.0)
- ✅ `GET /api/studies` — Worklist retrieval
- ✅ `GET /api/studies/{id}` — Study metadata
- ✅ `GET /api/studies/{id}/viewer` — Viewer launch
- ✅ `POST /api/reports` — Report creation
- ✅ `PUT /api/reports/{id}` — Report update
- ⚠️ `GET /api/reports/{id}` — Report retrieval (needs preliminary/final state field)

### New APIs Required (flag for v3.0)
- ❌ `GET /api/v2/worklists/teleradiology` — Remote worklist with site/priority/assignment filters
  - Query params: `site`, `priority`, `status`, `assignee`, `modality`, `date_range`
  - Response: paginated study list with turnaround time, assignment timestamp, critical flag
  - Real-time: WebSocket `/ws/worklists/teleradiology` for live updates
- ❌ `POST /api/v2/reports/{id}/finalize` — Transition preliminary → final
  - Body: `{ "final": true, "finalized_by": "user_id", "finalized_at": "timestamp" }`
  - Response: updated report with state change audit
- ❌ `POST /api/v2/critical-findings` — Critical finding notification
  - Body: `{ "report_id", "finding_text", "urgency", "clinician_notified", "notification_method", "notification_timestamp" }`
  - Triggers: email/SMS/page to on-call clinician (integration point)
- ❌ `GET /api/v2/studies/{id}/offline-package` — Downloadable offline study bundle
  - Response: encrypted ZIP with DICOM files, viewer HTML, decryption key
  - Size limit: 2GB per package
- ❌ `GET /api/v2/users/me/sites` — Multi-site access list for tenant-switching
  - Response: `[{ "tenant_id", "site_name", "worklist_count", "stat_count" }]`
- ❌ `POST /api/v2/consultations` — Consultation request/response
  - Body: `{ "study_id", "requesting_user", "question", "priority" }`
  - Response: consultation ID, notification to teleradiologist
- ❌ `POST /api/v2/worklists/teleradiology/prefetch` — Background prefetch hint
  - Body: `{ "study_ids": ["id1", "id2", "id3"] }`
  - Response: prefetch job queued

### Backend Feasibility Notes
- **Real-time worklist sync**: Requires WebSocket endpoint + PostgreSQL LISTEN/NOTIFY (existing `notify_event()` trigger can be extended)
- **Offline packages**: Requires background job queue (Celery/Redis) for ZIP generation; DICOM decompression for offline viewer
- **Critical findings escalation**: Requires integration with hospital notification system (Twilio API for SMS, PagerDuty for paging) — plugin architecture
- **Multi-site tenant-switching**: Requires per-tenant JWT token exchange; frontend tenant context state management
- **Prefetch optimization**: Requires predictive prefetch algorithm (next N studies in worklist order); CDN/edge cache for WAN optimization

### Delegate to `frontend-to-backend-requirements` skill for:
- Detailed API contracts (request/response schemas, error codes, rate limits)
- WebSocket message format for real-time worklist updates
- Offline package encryption scheme and viewer bundle structure
- Multi-site authentication token exchange flow

### Delegate to `rest-api-design` skill for:
- RESTful resource design for consultations, critical findings
- API versioning strategy (v2 endpoints)
- Rate limiting for remote access endpoints
- OpenAPI spec generation
