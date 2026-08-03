# Metrics & SLAs — Radiology Trainee/Resident (R13)

| ID | Metric | Target | Measurement | Frequency | Owner |
|----|--------|--------|-------------|-----------|-------|
| M-R13-01 | Supervised worklist load time (LCP) | ≤ 2.0s | Lighthouse CI, RUM | Per release | Frontend |
| M-R13-02 | Draft report auto-save latency | ≤ 300ms | Backend timing | Per auto-save | Backend |
| M-R13-03 | Attending review notification latency | ≤ 5s | WebSocket message timestamp delta | Continuous | Backend |
| M-R13-04 | Teaching file de-identification time | ≤ 2s per case | Backend timing | Per submission | Backend |
| M-R13-05 | Exam list export (CSV) time | ≤ 5s for 500 studies | Backend timing | Per export | Backend |
| M-R13-06 | Worklist real-time sync staleness | ≤ 30s | WebSocket + DB trigger | Continuous | Backend |
| M-R13-07 | Supervised study view load time | ≤ 2.5s (LCP) | Lighthouse CI, RUM | Per release | Frontend |
| M-R13-08 | Draft report completeness indicator update | ≤ 200ms | Frontend timing | Per keystroke | Frontend |
| M-R13-09 | On-call consult response time | ≤ 15min (on-call attending) | WebSocket notification + acceptance | Continuous | Operations |
| M-R13-10 | Attending agreement rate | ≥ 85% (drafts approved without major changes) | Report status analysis | Monthly | Education (R03) |

## SLA Tiers

### Availability
- **Supervised worklist**: 99.9% uptime (educational workflow is critical-path for residents)
- **Draft report editor**: 99.5% uptime (auto-save critical for data integrity)
- **Attending review queue**: 99.5% uptime (bottleneck for report finalization)
- **Teaching file capture**: 99% uptime (educational, not clinical-path)

### Response Time
- **P1 (Worklist/Editor down)**: Incident response ≤ 15min, resolution ≤ 2h
- **P2 (Attending notification delayed > 30s)**: Response ≤ 30min, resolution ≤ 4h
- **P3 (Teaching file de-identification slow)**: Response ≤ 2h, resolution ≤ 8h
- **P4 (Feedback dashboard slow)**: Response ≤ 4h, resolution ≤ 24h

### Support
- **P1**: On-call resident lead + backend on-call
- **P2**: Backend on-call
- **P3**: Next business day
- **P4**: Next business day