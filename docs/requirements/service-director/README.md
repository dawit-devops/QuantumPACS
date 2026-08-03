# R03 — Radiology & Imaging Service Director Requirements Package

| Field | Value |
|-------|-------|
| **Version** | 1.2.1 |
| **Status** | approved |
| **Generated** | 2026-08-03 |
| **Changelog** | [CHANGELOG.md](CHANGELOG.md) |

---

## Codebase Alignment (verified 2026-08-03; re-verified post-merge 4d136e0)

**Presentation layer**: role-based; see artifact 04 — "Role-Based Routing &
Navigation". Today the service director can only view `/metrics` + `/dashboard/metrics`
(read-only) plus Files. **All KPI/capacity/protocol/SLA dashboards, report builder,
exports, and dashboard-access audit are GATED** — no `/analytics/*` endpoints exist.
Since the v3-dev merge (`4d136e0`), `PermissionRoute` (`frontend/src/auth/PermissionRoute.tsx`)
enforces role-based access at the URL boundary, and `REPORT_READ/WRITE/SIGN` +
`service_director`-relevant slugs became visible in the catalog — but `REPORT_*` is
reading-report scoped (R12), NOT the analytics report builder, and the
`service_director` built-in role still does not exist in `BUILT_IN_ROLES`.

**Implemented**: Metrics dashboard (platform). **GATED**: FR-R03-01..05, FR-R03-10,
FR-R03-12, FR-R03-14, FR-R03-15 + all v3.1 items (needs `ANALYTICS_*` permission
slugs + `service_director` built-in role + endpoints flagged to backend).

---

## Role Profile

| Attribute | Detail |
|-----------|--------|
| **ID** | R03 |
| **Role** | Radiology & Imaging Service Director (Senior Radiologist) |
| **Persona** | Senior radiologist with operational/leadership accountability for the imaging service line. Works in admin office + reading room; reviews dashboards daily; presents to hospital leadership monthly; does not perform routine image interpretation but may do QA reads. |
| **Access Tier** | Read + full analytics (tenant-scoped); no write access to studies/files; can configure reporting parameters. |
| **Top Tasks (by frequency)** | 1. Review service KPI dashboards (daily) — volume, turnaround, modality utilization<br>2. Monitor capacity & staffing against demand (daily)<br>3. Protocol governance & QA compliance review (weekly)<br>4. SLA oversight & vendor performance (weekly)<br>5. Report to hospital leadership / board (monthly) |
| **Pain Points** | • Dashboards require manual SQL/PowerBI exports (no embedded analytics)<br>• No real-time capacity view — data is stale by hours<br>• SLA tracking is spreadsheet-based, not system-native<br>• Protocol compliance data scattered across PACS/RIS/QA tools<br>• No drill-through from KPI to study-level detail |
| **Devices** | Desktop (primary), tablet for rounding; dual-monitor standard; no mobile requirement |
| **Working Patterns** | Dashboard-first workflow; scheduled review cadences; deep-dive on exceptions |
| **PHI Exposure** | Aggregate analytics only — minimum necessary (HIPAA). No direct patient identifiers in dashboards unless drilling to study detail (requires justification audit log). |

---

## Artifact Index

| # | File | Description | v3.0 Status |
|---|------|-------------|-------------|
| 01 | `01-user-requirements.md` | Functional (FR-R03-NN) & Non-Functional (NFR-R03-NN) requirements, MoSCoW prioritized | **Complete (v3.0 Must only)** |
| 02 | `02-workflow-maps.md` | End-to-end workflow maps as Mermaid sequenceDiagrams with HL7/FHIR field mappings (inbound + reverse) | **Complete** |
| 03 | `03-user-stories.md` | User stories (US-R03-NN) with Given/When/Then AC, WCAG 2.2 AA, performance targets | **Complete (9 v3.0 stories)** |
| 04 | `04-ui-ux-requirements.md` | Screen inventory, component state matrix, design token references (existing + proposed), A11y, responsive | **Complete** |
| 05 | `05-metrics-slas.md` | Quantified KPIs (M-R03-NN) with targets, measurement methods, frequency, owners; SLA tiers | **Complete** |
| 06 | `06-acceptance-criteria.md` | Validator-gated AC matrix mapped to FR/NFR IDs; verification methods; out-of-scope | **Complete (v3.0 Must ACs)** |
| 07 | `07-traceability.md` | FR/NFR → AC traceability, cross-artifact dependencies, cross-role dependencies, integration contracts | **Complete** |
| 08 | `08-implementation-roadmap.md` | Dependency-ordered implementation plan with status (done/partial/missing) per artifact | **Complete** |

---

## v3.0 vs v3.1 Scope Split

### v3.0 (Must Priority — This Package)
- FR-R03-01: Service KPI Dashboard
- FR-R03-02: Real-time Modality Capacity Heatmap
- FR-R03-03: Protocol Compliance Scorecard
- FR-R03-04: SLA Tracking (STAT ≤30min, routine ≤24h)
- FR-R03-05: KPI Drill-through to Study List
- FR-R03-10: Report Builder (Template-based, 5 templates)
- FR-R03-12: Export (CSV ≤30s, PDF ≤60s for 10k rows)
- FR-R03-14: Dashboard Access Audit (HIPAA min necessary)
- FR-R03-15: RBAC Service Director Role

### v3.1 (Should/Could — Deferred)
- FR-R03-06: Staffing vs Demand Forecast (7-day)
- FR-R03-07: Equipment Downtime Impact Analysis
- FR-R03-08: Protocol Gap Analysis (missing sequences)
- FR-R03-09: SLA Breach Root-Cause Categorization
- FR-R03-11: Scheduled Report Delivery (email/webhook)
- FR-R03-13: Configurable Alerting (threshold rules)

---

## Cross-Role Dependencies

| Dependency | Source Role | Integration | Field Mapping |
|------------|-------------|-------------|---------------|
| **Scheduling Data** | R15 External RIS | HL7 ORM^O01 (inbound) | See Artifact 02 for full field mapping |
| **Study Status → RIS** | R15 External RIS | HL7 ORM^O01 / OML (reverse) | Accession + study_uid + status → RIS |
| **Patient Demographics** | R16 External EMR | FHIR R4 Patient (inbound) | See Artifact 02 for full field mapping |
| **QA Scores** | R05 QI/QA Team | Structured QA DB | Protocol ID, sequence compliance, dose metrics |
| **Turnaround Timestamps** | R12 Staff Radiologist | Report signing | `study.created` → `report.signed_at` |
| **Equipment Status** | R10 Biomedical Engineer | Equipment registry | Modality uptime, PM schedule, downtime events |
| **Worklist Status** | R04 Service Coordinator | MWL status | `worklist_entries.status` (scheduled/performed/cancelled) |

---

## New API Endpoints Required (v3.0)

| Endpoint | Method | Purpose | Permission |
|----------|--------|---------|------------|
| `/api/v2/analytics/dashboard` | GET | KPI aggregates | `METRICS_READ` |
| `/api/v2/analytics/capacity` | GET | Heatmap + scheduled counts | `METRICS_READ` |
| `/api/v2/analytics/protocol-compliance` | GET | Scorecard + gaps | `METRICS_READ` |
| `/api/v2/analytics/sla` | GET | Turnaround + breaches | `METRICS_READ` |
| `/api/v2/reports/generate` | POST | Template report generation | `METRICS_READ` |
| `/api/v2/reports/templates` | GET | List report templates | `METRICS_READ` |
| `/api/v2/audit/dashboard-access` | POST | Log dashboard view/export | `METRICS_READ` |

---

## New Permission Slugs Required

```python
ANALYTICS_READ = 'ANALYTICS_READ'
ANALYTICS_EXPORT = 'ANALYTICS_EXPORT'
REPORT_BUILD = 'REPORT_BUILD'
REPORT_SCHEDULE = 'REPORT_SCHEDULE'
ALERT_MANAGE = 'ALERT_MANAGE'
```

Add to `PERMISSION_GROUPS['Analytics']` and new `service_director` built-in role.

---

## Design System Extensions (Proposed)

| Semantic Token | Primitive Ref | Description |
|----------------|---------------|-------------|
| `chart-axis-color` | `primitive.color.slate-500` | Chart axis labels |
| `chart-grid-color` | `primitive.color.slate-200` | Chart grid lines |
| `chart-tooltip-bg` | `primitive.color.slate-900` | Tooltip background |
| `heatmap-low` | `primitive.color.emerald-500` | Under-capacity |
| `heatmap-medium` | `primitive.color.amber-500` | Near-capacity |
| `heatmap-high` | `primitive.color.red-500` | Over-capacity |
| `heatmap-critical` | `#7F1D1D` | Critical over-capacity |
| `kpi-trend-up` | `primitive.color.emerald-500` | Positive trend |
| `kpi-trend-down` | `primitive.color.red-500` | Negative trend |
| `kpi-trend-neutral` | `primitive.color.slate-500` | Neutral trend |
| `canvas-dropzone-bg` | `primitive.color.slate-50` | Report builder drop zone |
| `canvas-grid-line` | `primitive.color.slate-200` | Report builder grid |

---

## Quality Gate Checklist

- [x] All 8 files exist with correct ID prefixes (FR-R03, NFR-R03, US-R03, AC-R03, M-R03)
- [x] Every FR has ≥1 AC; every AC links to FR/NFR
- [x] All 4 states (loading/empty/error/success) specified per data widget
- [x] Performance targets quantified (LCP ≤2.5s, freshness ≤5min, export ≤30s/60s)
- [x] 7 API endpoints flagged with response shapes
- [x] WCAG 2.2 AA ACs concrete (contrast, focus, keyboard, ARIA live)
- [x] Workflows W1-W4 with standard HL7/FHIR field mappings (inbound + reverse)
- [x] Design tokens: existing referenced + 13 proposed semantic tokens
- [x] Report Builder = template-based (5 templates, parameter modal)
- [x] Validator gate: every AC observable/measurable; reverse validation noted
- [x] Cross-role deps table with R15/R16/R05/R12/R10/R04
- [x] Out-of-scope explicitly listed

---

## Out of Scope (Explicit)

- Radiologist reading workflow (R12)
- Technologist acquisition workflow (R06/R07)
- Patient registration (R08)
- Billing (R09)
- DICOM image viewing/measurement (E3)
- Multi-site federation UI (v3.x per ADR)
- AI/CAD integration (v3.2 per PRD)
- Custom HL7/FHIR field mappings (uses standard v2.5/R4 only)
- Advanced report canvas (drag-drop) — v3.1+

---

*Generated by pacs-requirements-architect skill pipeline. See `CLAUDE.md` Section 8 for methodology.*