# Metrics & SLAs — Radiology Technician (R07)

| ID | Metric | Target | Measurement | Frequency | Owner |
|----|--------|--------|-------------|-----------|-------|
| M-R07-01 | Worklist load time (LCP) | ≤ 2.0s | Lighthouse CI, RUM | Per release | Frontend |
| M-R07-02 | Image preview latency | ≤ 500ms from acquisition | Frontend timing | Per acquisition | Frontend |
| M-R07-03 | Exam completion handoff latency | ≤ 5s to radiologist worklist | WebSocket message timestamp delta | Continuous | Backend |
| M-R07-04 | Dose parameter logging | ≤ 100ms per acquisition | Backend timing | Per acquisition | Backend |
| M-R07-05 | Reject image processing | ≤ 2s from flag to rejection recorded | Backend timing | Per rejection | Backend |
| M-R07-06 | Worklist real-time sync staleness | ≤ 30s from exam status change | WebSocket + DB trigger | Continuous | Backend |
| M-R07-07 | Exam completion to radiologist notification | ≤ 5s | WebSocket latency | Per exam completion | Backend |
| M-R07-08 | PACS push success rate | ≥ 99% | PACS push status counter | Weekly | Backend |
| M-R07-09 | Reject rate per exam | ≤ 5% (industry benchmark) | Reject count / total acquisitions | Monthly | QA (R05) |
| M-R07-10 | Protocol compliance rate | ≥ 95% (views completed as prescribed) | View compliance JSONB | Monthly | QA (R05) |

## SLA Tiers

### Availability
- **Worklist**: 99.9% uptime (clinical workflow is critical-path)
- **Image preview**: 99.5% uptime (acquisition depends on real-time preview)
- **Dose tracking**: 99.5% uptime (regulatory requirement)
- **PACS push**: 99.9% uptime (images must be available for radiologist reading)

### Response Time
- **P1 (Worklist down)**: Incident response ≤ 15min, resolution ≤ 2h
- **P2 (Image preview slow > 1s)**: Response ≤ 30min, resolution ≤ 4h
- **P3 (Dose logging delay)**: Response ≤ 2h, resolution ≤ 8h
- **P4 (PACS push delayed)**: Response ≤ 4h, resolution ≤ 24h

### Support
- **P1**: On-call technician lead + backend on-call
- **P2**: Backend on-call
- **P3**: Next business day
- **P4**: Next business day