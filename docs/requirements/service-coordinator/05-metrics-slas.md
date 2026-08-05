# Metrics & SLAs — Radiology & Service Coordinator (R04)

| ID | Metric | Target | Measurement | Frequency | Owner |
|----|--------|--------|-------------|-----------|-------|
| M-R04-01 | Schedule board load time (LCP) | ≤ 2.0s | Lighthouse CI, RUM | Per release | Frontend |
| M-R04-02 | Exam assignment API latency | ≤ 500ms p95 | Backend timing middleware | Continuous | Backend |
| M-R04-03 | Worklist refresh staleness (new assignments) | ≤ 5s | WebSocket message timestamp delta | Continuous | Backend |
| M-R04-04 | Conflict detection latency | ≤ 200ms after drag/drop | Frontend performance timing | Per interaction | Frontend |
| M-R04-05 | Utilization dashboard filter response | ≤ 300ms | Backend timing | Per filter change | Backend |
| M-R04-06 | Schedule board scroll performance | 60fps with 500+ exams | Frame timing via DevTools | Per release | Frontend |
| M-R04-07 | Exam reorder API success rate | ≥ 99.5% | API success counter | Weekly | Backend |
| M-R04-08 | WebSocket connection stability | ≤ 1 reconnect per hour | Connection event log | Continuous | Backend |
| M-R04-09 | Handoff report generation time | ≤ 5s for shift with ≤20 pending exams | Backend timing | Per generation | Backend |
| M-R04-10 | Bulk reassignment operation time | ≤ 2s for ≤10 exams | Backend timing | Per operation | Backend |

## SLA Tiers

### Availability
- **Schedule board**: 99.9% uptime (clinical scheduling is critical-path)
- **Utilization dashboard**: 99.5% uptime (reporting, not clinical-path)
- **Staffing roster**: 99.5% uptime (admin tool, not clinical-path)

### Response Time
- **P1 (Schedule board down)**: Incident response ≤ 15min, resolution ≤ 2h
- **P2 (Assignment API slow > 2s)**: Response ≤ 30min, resolution ≤ 4h
- **P3 (Dashboard chart rendering slow)**: Response ≤ 4h, resolution ≤ 24h

### Support
- **P1**: On-call coordinator + backend on-call
- **P2**: Backend on-call
- **P3**: Next business day