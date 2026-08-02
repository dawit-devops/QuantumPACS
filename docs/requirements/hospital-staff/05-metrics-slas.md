# Metrics & SLAs — Other Hospital Staff (R19)

| ID | Metric | Target | Measurement | Frequency | Owner |
|----|--------|--------|-------------|-----------|-------|
| M-R19-01 | Portal LCP (mobile) | ≤ 2.5s on mid-tier phone | Lighthouse CI, RUM | Per release | Frontend |
| M-R19-02 | Patient lookup latency | ≤ 500ms p95 | Synthetic probe | Daily | Backend |
| M-R19-03 | Notification latency | ≤ 60s from finalize | Notification probe | Daily | Backend |
| M-R19-04 | Out-of-scope access rate | 0 successful unauthorized reads | Audit scan | Weekly | Security |
| M-R19-05 | Read-only violation rate | 0 mutations via UI or API | Pen test + E2E | Quarterly | Security |
| M-R19-06 | WCAG 2.2 AA compliance | 100% (portal) | axe-core CI | Per release | Frontend |

## SLA Tiers

- **Availability**: 99.9% for the portal during clinical hours.
- **Security**: zero out-of-scope reads; zero write mutations.
- **Support**: P1 (portal down) response ≤ 15min; P2 ≤ 4h.
