# Metrics & SLAs — Staff Radiologist (R12)

Clinical reading SLOs. Infrastructure SLOs are owned by R01/R02; R12 owns the
reading-path experience and throughput.

## Metrics

| ID | Metric | Target | Measurement | Frequency | Owner |
|----|--------|--------|-------------|-----------|-------|
| M-R12-01 | Study open → first instance rendered | ≤ 2s p90 (LAN) | Synthetic probe / RUM | Per release | Frontend |
| M-R12-02 | Series/instance navigation INP | ≤ 200ms p75 | RUM | Per release | Frontend |
| M-R12-03 | Worklist load | ≤ 2s p90 | Synthetic probe | Daily | Backend |
| M-R12-04 | Worklist staleness (STAT arrivals) | ≤ 30s | Synthetic probe | Daily | Backend |
| M-R12-05 | Pan/zoom smoothness | 60fps at loaded window; no full-frame re-fetch for pan | Performance instrumentation | Per release | Frontend |
| M-R12-06 | Report autosave cadence | ≤ 10s; zero drafts lost on drop | Integration test | Per release | Frontend/Backend |
| M-R12-07 | Report save round-trip | ≤ 1s p90 | Synthetic probe (GATED) | Weekly | Backend |
| M-R12-08 | Annotation persistence load | Parallel to first image; adds ≤ 500ms to full readiness | Instrumentation | Per release | Frontend |
| M-R12-09 | Sharing creation | ≤ 2s | API probe | Per release | Backend |
| M-R12-10 | Critical escalation end-to-end | Notification to referring clinician ≤ 5s after confirm (GATED) | Synthetic event probe | Weekly | Backend |
| M-R12-11 | Concurrent reading sessions | ≥ 50 (existing requirement) | Load test | Per release | Platform |

## SLA Tiers

| Tier | Scope | Availability | Response |
|------|-------|--------------|----------|
| P1 — critical | Study open, viewer interactions, worklist | 99.9% | Response ≤ 15 min; fix ≤ 4h |
| P2 — major | Priors, annotations, sharing | 99.5% | Response ≤ 1h; fix ≤ 24h |
| P3 — minor | Report panel, presets (when shipped) | 99% | Response ≤ 4h; fix next release |
| P4 — monitoring | Browser search (ES-dependent) | best effort | Next business day |

## Turnaround Alignment (with R03/R04)

- STAT studies: interpretation started ≤ 30 min of completion; preliminary read ≤ 1h.
- Routine: interpretation ≤ 24h.
- R12 owns the reading-time component; R03/R04 dashboards measure end-to-end.

## Reporting

- R12 metrics feed R03 service-director dashboards (throughput, turnaround) and R05
  QA (reading quality, annotation accuracy via audit).
- Escalation tracking (W4) is a safety metric reviewed weekly by R05.
