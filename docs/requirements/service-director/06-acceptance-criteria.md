# Acceptance Criteria — Radiology Service Director (R03)

**Version**: 1.0.0 (v3.0 scope)
**Status**: Final
**Date**: 2026-08-02

---

## Validator Gate Methodology

Every acceptance criterion in this document is written to be **provable by visual evidence or automated test**, following the ui-visual-validator convention: *"default assumption: NOT achieved until proven otherwise."*

### Verification Output Format
Each AC verification records:
```
From the visual evidence/verification, I observe [specific observation] —
goal: [achieved / partially achieved / not achieved]
```

### Mandatory Verification Checklist (Section 6.4 of skill)
Applied to every AC claiming a UI outcome:
- [ ] AC stated in observable terms (not "implemented in code")?
- [ ] AC specifies measurable contrast ≥ 4.5:1 where color is used?
- [ ] AC covers focus indicators and keyboard operability?
- [ ] AC specifies responsive breakpoint behavior?
- [ ] AC covers loading, empty, error, and success states?
- [ ] AC requires design-token compliance (no off-system colors/type)?
- [ ] Has failure evidence been actively searched (reverse validation)?
- [ ] Does "different" actually mean "correct"?

---

## Acceptance Criteria Matrix (v3.0 Must Priority)

### FR-R03-01: Service KPI Dashboard

| AC ID | Links to | Criteria (Given/When/Then) | Verification Method | Validator Gate |
|-------|----------|----------------------------|---------------------|----------------|
| AC-R03-01-01 | FR-R03-01 | **Given** logged in as `service_director`, **when** navigating to `/dashboard`, **then** four KPI cards render: Study Volume (with 7-day sparkline), Turnaround Time (STAT p95 + Routine p95), Modality Utilization (%), Staffing Coverage (%), each displaying current value + trend. | Playwright: assert 4 cards with `role="region"` + `aria-label` containing metric name + value | ✓ Observable: card count, role, aria-label; ✓ Token: cards use `--bg-surface`, `--radius-lg`; Search for: missing aria-label, wrong role |
| AC-R03-01-02 | NFR-R03-01, M-R03-01 | **Given** dashboard loads with cached data, **when** Lighthouse CI runs on `/dashboard`, **then** LCP ≤ 2.5s and TTI ≤ 3s. | Lighthouse CI (GitHub Actions gate); screenshot evidence | ✓ Observable: Lighthouse score ≥ 90; Search for:Third-party scripts, large images blocking LCP |
| AC-R03-01-03 | NFR-R03-02, M-R03-03 | **Given** dashboard displayed, **when** 5 minutes elapse, **then** each widget auto-refreshes via background `useQuery` refetch, and ARIA live region (polite) announces "Dashboard updated, N KPIs refreshed" without focus loss or modal interruption. | Synthetic probe: timestamp widget last-update field at T0, wait 5min, assert updated at T+5min; axe-core: live region present with `aria-live="polite"` | ✓ Observable: timestamp delta; ✓ A11y: live region; Search for: focus stealing, notification covering content |
| AC-R03-01-04 | FR-R03-01 | **Given** navigating to `/dashboard` with no cached data, **when** widgets fetch, **then** each KPI card shows skeleton loader (shimmer animation) matching final card dimensions (280×140px), card announced as `aria-busy="true"`. | Visual test: capture screenshot during loading; assert skeleton visible; axe-core: `aria-busy` attribute present | ✓ Observable: skeleton visible in screenshot; ✓ A11y: aria-busy; ✓ States: loading; Search for: layout shift when data loads |
| AC-R03-01-05 | FR-R03-01 | **Given** tenant has zero studies, **when** dashboard loads, **then** each KPI card shows "No data available" with "Run first study" CTA button (primary style, links to `/files`), not a blank card or spinner. | Visual test: seed empty tenant, screenshot dashboard, assert CTA present and clickable | ✓ Observable: CTA visible + clickable; ✓ States: empty; ✓ Token: CTA uses `--color-primary`; Search for: spinner hanging, empty card body |
| AC-R03-01-06 | FR-R03-01 | **Given** one analytics API endpoint returns 500, **when** error occurs, **then** affected KPI card shows error banner (red `--color-error` bg) with "Failed to load" text and "Retry" button (secondary style); other widgets remain functional with their data. | Error injection: mock API 500 on one widget; screenshot; assert other widgets intact | ✓ Observable: error banner + retry; ✓ States: error; ✓ Token: `--color-error`; Search for: entire dashboard crash, no retry option |
| AC-R03-01-07 | NFR-R03-08, M-R03-22 | **Given** keyboard-only navigation (no mouse), **when** tabbing through dashboard, **then** focus order is logical (top-left KPI → top-right → ... → bottom-right), each card has visible focus ring (2px solid `--color-primary`, offset 2px), and screen reader announces full KPI label (e.g., "Study Volume: 1,247 studies, up 12% from last week"). | Manual: tab through dashboard, record focus order; axe-core: focus-visible styles, aria-label completeness; screen reader test | ✓ Observable: focus ring visible; ✓ A11y: contrast ≥ 4.5:1 for ring; ✓ Token: `--color-primary` ring; Search for: focus ring missing, wrong tab order, incomplete aria-label |
| AC-R03-01-08 | NFR-R03-09, M-R03-23 | **Given** KPI trend indicator visible (↑/↓/→), **when** viewed in Coblis color-blind simulator (protanopia), **then** trend direction is identifiable by icon shape (↑=up, ↓=down, →=neutral) AND color, not color alone. | Visual: screenshot trend indicators; apply Coblis protanopia filter; assert icon visible | ✓ Observable: icon visible in simulator; Search for: color-only trend (no icon), ambiguous icon |
| AC-R03-01-09 | NFR-R03-10, M-R03-24 | **Given** dashboard at viewport 768px (tablet), **when** responsive breakpoint triggers, **then** KPI cards stack in single column (full width), all functionality preserved (auto-refresh, drill-through, export), text remains ≥ 13px. | Responsive test: Playwright screenshot at 768px; assert 1-col layout; assert tab navigation works | ✓ Observable: single column in screenshot; ✓ Responsive: breakpoint behavior; Search for: text overflow, hidden controls, broken focus |

### FR-R03-02: Real-time Modality Capacity Heatmap

| AC ID | Links to | Criteria (Given/When/Then) | Verification Method | Validator Gate |
|-------|----------|----------------------------|---------------------|----------------|
| AC-R03-02-01 | FR-R03-02 | **Given** Capacity tab open, **when** heatmap renders, **then** 7-day × 24-hour × 6-modality grid displays (1,008 cells max), each cell color-coded: green `--heatmap-low` (<80%), yellow `--heatmap-medium` (80-95%), red `--heatmap-high` (95-110%), critical `--heatmap-critical` (>110%) with pattern overlay. | Visual: screenshot heatmap; assert cell colors match token values; assert pattern overlays present on yellow/red/critical | ✓ Observable: colors + patterns in screenshot; ✓ Token: all `--heatmap-*` tokens; Search for: missing pattern, wrong color threshold, cell overflow |
| AC-R03-02-02 | NFR-R03-02, M-R03-14 | **Given** new HL7 ORM^O01 arrives scheduling a CT study, **when** message processed (≤ 5s), **then** corresponding heatmap cell updates via WebSocket/SSE within 5 minutes total, without full page reload. | Integration test: send ORM message, track cell update timestamp, assert delta ≤ 5min | ✓ Observable: cell value changes; Search for: stale data, full reload, missed update |
| AC-R03-02-03 | FR-R03-02 | **Given** heatmap cell visible, **when** hovering (desktop) or tapping (touch), **then** tooltip shows: Modality, Date, Timeslot, Scheduled count, Capacity, Utilization %, Equipment status (up/down). | Playwright: hover cell, assert tooltip with all 7 fields; axe-core: tooltip has `role="tooltip"` | ✓ Observable: tooltip shows all fields; ✓ A11y: role; Search for: truncated tooltip, missing equipment status |
| AC-R03-02-04 | FR-R03-02 | **Given** red or critical cell (utilization >95%), **when** clicked, **then** modal opens listing scheduled studies (Patient initials, Accession, Procedure, Referring Physician) + "Notify Coordinator" button (R04). | Playwright: click red cell, assert modal with study list + button; axe-core: modal `aria-modal`, focus trap | ✓ Observable: modal + list + button; ✓ A11y: focus trap; Search for: modal without list, missing notify button |
| AC-R03-02-05 | NFR-R03-03, M-R03-05 | **Given** heatmap with 1,008 cells, **when** rendering completes, **then** total render ≤ 1s and CLS < 0.1 (no layout shift during render). | Performance: Playwright trace render time; Lighthouse CLS check | ✓ Observable: render time < 1s in trace; Search for: layout shift, slow virtualization |
| AC-R03-02-06 | NFR-R03-08, NFR-R03-10 | **Given** keyboard navigation in heatmap, **when** using arrow keys, **then** focus moves logically: ←/→=timeslot, ↑/↓=day; Enter opens detail modal; Escape closes modal and returns focus to originating cell. | Keyboard test: Playwright keyboard events, record focus path | ✓ Observable: focus path matches; ✓ A11y: keyboard operable; Search for: focus lost after Escape, wrong arrow direction |
| AC-R03-02-07 | NFR-R03-09, M-R03-23 | **Given** heatmap color legend visible, **when** viewed in Coblis (protanopia, deuteranopia, tritanopia), **then** each utilization band is distinguishable by pattern overlay (green=none, yellow=diagonal lines, red=dots, critical=crosshatch) in addition to color. | Visual: screenshot legend + cells; apply 3 Coblis filters; assert patterns visible | ✓ Observable: patterns in simulator; Search for: indistinguishable bands, missing pattern |
| AC-R03-02-08 | NFR-R03-02 | **Given** cell updates via WebSocket, **when** update occurs, **then** ARIA live region (polite) announces "CT Monday 08:00 updated: 22 scheduled, 20 capacity, 110% utilization" without focus change or modal interruption. | axe-core: live region present; Integration: trigger WS update, assert announcement | ✓ Observable: announcement text; ✓ A11y: polite live region; Search for: focus steal, announcement not triggered |
| AC-R03-02-09 | FR-R03-02 | **Given** no schedule data exists for modality (e.g., FL), **when** heatmap renders, **then** that modality's cells show "No schedule data" with muted pattern (`--text-muted` color); if API fails, retry button appears on modality row header. | Visual: seed tenant with no FL schedule, screenshot; Error: mock API 500, assert retry on row | ✓ Observable: muted cells + text; ✓ States: empty + error; Search for: blank cells, no retry on API fail |

### FR-R03-03: Protocol Compliance Scorecard

| AC ID | Links to | Criteria (Given/When/Then) | Verification Method | Validator Gate |
|-------|----------|----------------------------|---------------------|----------------|
| AC-R03-03-01 | FR-R03-03 | **Given** Protocol tab open, **when** scorecard loads, **then** table displays columns: Protocol Code, Name, Modality, Studies Reviewed, Compliance %, Avg Dose (DLP), Status (Pass/Fail badge with ✓/✗ icon), Trend (7-day sparkline SVG). | Playwright: assert column headers; screenshot; assert sparkline SVG present | ✓ Observable: columns + badges + sparklines; ✓ Token: `--color-success/error`; Search for: missing column, badge without icon |
| AC-R03-03-02 | FR-R03-03, FR-R03-05 | **Given** protocol row with <95% compliance, **when** clicked, **then** side panel slides down showing: missing sequences per study, dose outliers, corrective actions, and "View Studies" button linking to `/files?protocol=X`. | Playwright: click row, assert panel visible with sections + button; navigation test | ✓ Observable: panel + sections + button; Search for: panel without gaps, broken link |
| AC-R03-03-03 | FR-R03-03 | **Given** compliance % cell visible, **when** hovered, **then** tooltip shows: numerator (passing studies), denominator (total reviewed), ACR benchmark threshold, last QA review date. | Playwright: hover cell, assert tooltip with 4 fields | ✓ Observable: tooltip fields; Search for: truncated data, missing ACR threshold |
| AC-R03-03-04 | NFR-R03-08, NFR-R03-10 | **Given** scorecard table with keyboard, **when** tabbing in, **then** arrow keys navigate cells, Home/End jump to row ends, table has `role="grid"` with `role="columnheader"` announced. | Keyboard test + axe-core | ✓ Observable: arrow nav works; ✓ A11y: grid role; Search for: no grid role, tab key escaping |
| AC-R03-03-05 | NFR-R03-09, M-R03-23 | **Given** Status badge (green Pass, red Fail), **when** viewed in grayscale, **then** each badge has text label ("Pass"/"Fail") AND icon (✓/✗) in addition to color. | Visual: screenshot badges; apply grayscale filter; assert text+icon visible | ✓ Observable: text + icon; Search for: color-only badge |
| AC-R03-03-06 | NFR-R03-07, M-R03-09 | **Given** 50 protocols × 100 studies each (5,000 rows), **when** scorecard loads, **then** API response p95 ≤ 300ms, table renders with react-window virtualization, smooth scroll (60fps). | k6: API load test; Performance: scroll test, rAF timing | ✓ Observable: p95 ≤ 300ms in k6 output; Search for: non-virtualized rendering, scroll jank |

### FR-R03-04: SLA Tracking & Breach Alerts

| AC ID | Links to | Criteria (Given/When/Then) | Verification Method | Validator Gate |
|-------|----------|----------------------------|---------------------|----------------|
| AC-R03-04-01 | FR-R03-04, M-R03-16 | **Given** STAT study created at T0, **when** `now() - T0 > 30min` AND `report.signed_at IS NULL`, **then** breach badge appears on SLA KPI card (red, pulsing border), breach list updates with study ID, modality, minutes overdue, assigned radiologist. | Time simulation: create study, advance clock 31min, assert badge + list entry | ✓ Observable: pulsing badge + list row; ✓ Token: `--color-error`; Search for: badge without pulse, list missing radiologist |
| AC-R03-04-02 | FR-R03-04, M-R03-17 | **Given** routine study created at T0, **when** `now() - T0 > 24h` AND `report.signed_at IS NULL`, **then** amber badge appears in breach list (non-pulsing), routine p95 KPI updates. | Time simulation: create study, advance clock 25h, assert amber badge | ✓ Observable: amber badge; ✓ Token: `--color-warning`; Search for: pulsing routine badge (should not pulse) |
| AC-R03-04-03 | FR-R03-04 | **Given** SLA tab open with breaches, **when** breach list renders, **then** table shows: Study ID, Patient (initials only, no full name), Modality, Type (STAT/Routine), Minutes Overdue, Assigned Radiologist, Status (Pending/Escalated/Resolved), pagination at 20/page. | Playwright: assert columns, pagination, initials-only patient field; screenshot | ✓ Observable: columns + pagination + initials; ✓ HIPAA: no full name; Search for: full patient name, no pagination |
| AC-R03-04-04 | FR-R03-04 | **Given** STAT breach exceeds 60 minutes, **when** threshold crossed, **then** in-app notification sent to assigned radiologist + Service Coordinator (R04), audit log entry created with study_uid, breach_type, notified_users[]. | Integration: simulate 61min breach, assert notification dispatch + audit entry | ✓ Observable: notification + audit log; Search for: missing audit, no R04 notification |
| AC-R03-04-05 | NFR-R03-08 | **Given** breach alert appears, **when** ARIA live region fires, **then** screen reader announces "Critical: STAT study ACC12345 overdue by 45 minutes" (assertive), focus is NOT moved (non-modal, non-focus-stealing). | axe-core: assertive live region; Manual: screen reader announcement, verify focus unchanged | ✓ Observable: announcement + focus preserved; ✓ A11y: assertive, non-modal; Search for: focus stolen, modal blocking |
| AC-R03-04-06 | NFR-R03-07, M-R03-13 | **Given** breach detection job runs every 1 minute, **when** checking 10,000 active studies, **then** job completes ≤ 10s, API p95 for breach list query ≤ 300ms. | Load test: seed 10k studies, trigger job, measure duration; k6: API p95 | ✓ Observable: job duration ≤ 10s; Search for: slow query, missing index |

### FR-R03-05: KPI Drill-through to Study List

| AC ID | Links to | Criteria (Given/When/Then) | Verification Method | Validator Gate |
|-------|----------|----------------------------|---------------------|----------------|
| AC-R03-05-01 | FR-R03-05 | **Given** "CT Utilization 85%" KPI card visible, **when** clicked, **then** Files page opens at `/files?modality=CT&date_range=last_7d`, search box shows applied filter, table displays only CT studies from last 7 days. | Playwright: click card, assert URL, assert filtered rows | ✓ Observable: URL + filtered rows; Search for: wrong filter, empty table |
| AC-R03-05-02 | FR-R03-05 | **Given** drill-through URL `/files?modality=CT&date_range=last_7d`, **when** URL loaded fresh (bookmark), **then** identical filtered view renders without dashboard context. | Playwright: direct URL navigation, assert same result | ✓ Observable: same filter applied; Search for: lost filter on direct load |
| AC-R03-05-03 | FR-R03-05 | **Given** on drilled-through Files page, **when** viewing breadcrumb, **then** shows "Dashboard > CT Utilization > Studies" with "CT Utilization" clickable returning to dashboard. | Playwright: assert breadcrumb text + click returns to `/dashboard` | ✓ Observable: breadcrumb + navigation; Search for: missing breadcrumb, broken back link |
| AC-R03-05-04 | NFR-R03-03, M-R03-04 | **Given** KPI card clicked, **when** Files page loads, **then** transition completes ≤ 1s (including API search + table render). | Playwright: timing from click to table rendered | ✓ Observable: timing < 1s; Search for: slow search, blocking render |
| AC-R03-05-05 | NFR-R03-08, NFR-R03-10 | **Given** KPI card activated via keyboard (Enter/Space), **when** Files page loads, **then** focus moves to first interactive element (search box), page title updates to "Studies - CT Utilization Filter". | Keyboard test: focus card, Enter, assert focus on search box; assert document.title | ✓ Observable: focus on search box; ✓ A11y: focus management; Search for: focus lost, generic title |

### FR-R03-10: Report Builder (Template-based)

| AC ID | Links to | Criteria (Given/When/Then) | Verification Method | Validator Gate |
|-------|----------|----------------------------|---------------------|----------------|
| AC-R03-06-01 | FR-R03-10 | **Given** Reports tab open, **when** modal opens, **then** 5 template cards display: Monthly Volume Summary, Turnaround by Modality, Protocol Compliance, Capacity Utilization, SLA Breach Detail; each with name, description, estimated generation time. | Playwright: assert 5 cards with required fields; screenshot | ✓ Observable: 5 cards + fields; Search for: missing template, wrong description |
| AC-R03-06-02 | FR-R03-10 | **Given** "Monthly Volume Summary" selected, **when** parameter modal opens, **then** fields shown: Date Range (preset: Last Month + Custom), Modality Filter (multi-select: All/CT/MR/US/DX/MG/FL), Output Format (CSV/PDF radio), with sensible defaults pre-selected. | Playwright: open modal, assert all fields + defaults (Last Month, All, CSV) | ✓ Observable: fields + defaults; Search for: no default, missing modality option |
| AC-R03-06-03 | NFR-R03-04, M-R03-10 | **Given** parameters set (Last Month, All, CSV), **when** "Generate CSV" clicked, **then** CSV downloads with filename `monthly_volume_2026-07.csv`, columns: Date, Modality, Study Count, Series Count, Total Size (GB), completion ≤ 30s, toast "Generated in Ns". | Playwright: generate, assert download + filename + columns; timing | ✓ Observable: CSV file + columns + timing; Search for: wrong filename, missing column, > 30s |
| AC-R03-06-04 | NFR-R03-05, M-R03-11 | **Given** parameters set (Last Month, All, PDF), **when** "Generate PDF" clicked, **then** PDF downloads with filename `monthly_volume_2026-07.pdf`, containing: title page, summary table, charts (bar: volume by modality, line: daily trend), vector graphics (not rasterized), completion ≤ 60s. | Playwright: generate, assert download; PDF inspection: assert vector text (zoomable) | ✓ Observable: PDF + pages + vector; Search for: rasterized chart, > 60s, missing chart |
| AC-R03-06-05 | FR-R03-10 | **Given** "Generate" clicked, **when** processing, **then** button shows spinner + "Generating... N%", modal disabled (not dismissible without cancel), progress updates every 5s via polling, "Cancel" button available. | Playwright: click generate, assert spinner + progress; poll 5s; assert cancel works | ✓ Observable: spinner + progress + cancel; ✓ States: loading; Search for: modal dismissible, no cancel, stale progress |
| AC-R03-06-06 | FR-R03-10 | **Given** report generation fails (mock 500), **when** error occurs, **then** modal shows error banner (red, "Generation failed: [reason]"), "Retry" button (re-runs with same params), "Change Parameters" link (returns to form); no partial file downloaded. | Error injection: mock API 500; assert banner + buttons; assert no file | ✓ Observable: error banner + buttons; ✓ States: error; Search for: partial download, no retry, stuck spinner |
| AC-R03-06-07 | NFR-R03-08, NFR-R03-10 | **Given** Report Builder modal opened via keyboard, **when** Tab pressed, **then** focus trapped within modal (cycles through form fields), Escape closes modal and returns focus to triggering template card. | Keyboard test: tab cycle, Escape focus return; axe-core: focus trap | ✓ Observable: focus trap + return; ✓ A11y: keyboard; Search for: focus escaping modal, no return on Escape |
| AC-R03-06-08 | NFR-R03-08 | **Given** report generating, **when** progress updates, **then** ARIA live region (polite) announces "Report generation N% complete" without focus change. | axe-core: polite live region; Manual: screen reader announces progress | ✓ Observable: announcement; ✓ A11y: polite live; Search for: no live region, focus stolen |

### FR-R03-12: Widget Export (CSV/PDF)

| AC ID | Links to | Criteria (Given/When/Then) | Verification Method | Validator Gate |
|-------|----------|----------------------------|---------------------|----------------|
| AC-R03-07-01 | FR-R03-12 | **Given** any KPI card or chart widget, **when** hovered (desktop) or focused (keyboard/touch), **then** export dropdown appears with "Export CSV" and "Export PDF" options. | Playwright: hover widget, assert dropdown; keyboard: focus widget, Enter, assert dropdown | ✓ Observable: dropdown visible; ✓ A11y: keyboard accessible; Search for: hover-only (no keyboard), options hidden |
| AC-R03-07-02 | NFR-R03-04, M-R03-10 | **Given** "Export CSV" clicked on Modality Utilization chart, **when** download starts, **then** CSV downloads (`modality_utilization_2026-08-02.csv`) with columns: Modality, Scheduled, Capacity, Utilization %, Date; completes ≤ 30s. | Playwright: export, assert filename + columns + timing | ✓ Observable: file + columns + timing; Search for: wrong columns, > 30s |
| AC-R03-07-03 | NFR-R03-05, M-R03-11 | **Given** "Export PDF" clicked on Turnaround Trend chart, **when** download starts, **then** PDF downloads (`turnaround_trend_2026-08-02.pdf`) with chart as vector graphic (zoom to 400%, text crisp), axis labels, legend, timestamp; completes ≤ 60s. | Playwright: export, assert filename; PDF inspection: zoom 400%, assert crisp text | ✓ Observable: PDF + vector chart; Search for: rasterized chart (blurry at 400%) |
| AC-R03-07-04 | NFR-R03-04 | **Given** widget export with 10,000 data points, **when** export runs, **then** backend streams response (chunked transfer-encoding), browser shows download progress immediately, memory usage < 100MB. | Backend: assert `Transfer-Encoding: chunked`; Browser: DevTools memory profile | ✓ Observable: chunked header + memory; Search for: blocking response, memory > 100MB |
| AC-R03-07-05 | NFR-R03-08, NFR-R03-10 | **Given** export button focused via keyboard, **when** Enter pressed, **then** dropdown opens with focus on first option, arrow keys navigate, Enter selects, Escape closes and returns focus to button. | Keyboard test: full cycle; axe-core: dropdown ARIA | ✓ Observable: full keyboard cycle; ✓ A11y: keyboard; Search for: focus lost on dropdown open |

### FR-R03-14: Dashboard Access Audit

| AC ID | Links to | Criteria (Given/When/Then) | Verification Method | Validator Gate |
|-------|----------|----------------------------|---------------------|----------------|
| AC-R03-08-01 | FR-R03-14, M-R03-26 | **Given** dashboard loads, **when** page mounts, **then** audit entry created: `{user_id, tenant, action: 'dashboard_view', widgets: [...], timestamp, ip_address}` in `dashboard_audit` table. | DB query: assert entry exists after page load | ✓ Observable: DB row present; Search for: missing entry, wrong action type |
| AC-R03-08-02 | FR-R03-14 | **Given** KPI card clicked (drill-through), **when** navigation occurs, **then** audit entry: `{user_id, action: 'kpi_drillthrough', source_kpi: 'ct_utilization', target_url, timestamp}`. | DB query: assert entry after click | ✓ Observable: entry with source + target; Search for: missing source_kpi |
| AC-R03-08-03 | FR-R03-14 | **Given** widget export clicked, **when** download starts, **then** audit entry: `{user_id, action: 'export', type: 'csv'\|'pdf', widget: 'modality_utilization', record_count: N, timestamp}`. | DB query: assert entry after export | ✓ Observable: entry with type + count; Search for: missing record_count |
| AC-R03-08-04 | FR-R03-14 | **Given** report generated, **when** export completes, **then** audit entry: `{user_id, action: 'report_generate', template_id, format, recipients[], timestamp}`. | DB query: assert entry after report | ✓ Observable: entry with template + recipients; Search for: missing recipients |
| AC-R03-08-05 | FR-R03-14 | **Given** any audit entry written, **when** entry inspected, **then** no PHI (patient name, MRN, accession) included UNLESS action was drill-through to specific study (then only `study_uid` with `justification: 'drillthrough_from_kpi'`). | Code review: audit log schema + sample entries; DB: grep for PHI patterns | ✓ Observable: no PHI in aggregate entries; ✓ HIPAA: min necessary; Search for: MRN in log, name in log |
| AC-R03-08-06 | FR-R03-14 | **Given** Auditor role queries `/api/v2/audit/dashboard-access?user_id=X&date_range=last_30d`, **when** results return, **then** paginated entries with all fields, CSV export available, and only own-tenant data visible (no cross-tenant). | API test: query as auditor, assert pagination + fields; cross-tenant: assert empty for other tenant | ✓ Observable: paginated results; ✓ HIPAA: tenant-scoped; Search for: cross-tenant leak, no pagination |

### FR-R03-15: RBAC Service Director Role

| AC ID | Links to | Criteria (Given/When/Then) | Verification Method | Validator Gate |
|-------|----------|----------------------------|---------------------|----------------|
| AC-R03-09-01 | FR-R03-15 | **Given** admin at `/roles`, **when** roles table loads, **then** `service_director` appears in built-in roles (non-deletable), with permissions: `METRICS_READ`, `ANALYTICS_READ`, `ANALYTICS_EXPORT`, `REPORT_BUILD`. | Playwright: assert role row + permissions; assert delete disabled | ✓ Observable: role present + non-deletable; Search for: deletable built-in, wrong permissions |
| AC-R03-09-02 | FR-R03-15 | **Given** user with `service_director` role, **when** accessing `/dashboard`, **then** access granted (200); **when** accessing `/users` or `/tenants`, **then** access denied (403). | API test: JWT with service_director, GET `/dashboard` (200), GET `/users` (403), GET `/tenants` (403) | ✓ Observable: 200 + 403; Search for: access to /users, missing 403 |
| AC-R03-09-03 | FR-R03-15 | **Given** `service_director` user logs in, **when** JWT issued, **then** token `permissions` claim includes 4 analytics permissions, `role` claim = `service_director`. | Decode JWT (jwt.io or code), assert claims | ✓ Observable: claims present; Search for: missing permissions, wrong role |
| AC-R03-09-04 | FR-R03-15, NFR-A1 | **Given** `service_director` in Tenant A, **when** analytics API executes, **then** all queries scoped to Tenant A database; querying Tenant B data returns empty. | Cross-tenant test: seed both tenants, query as Tenant A, assert no Tenant B data | ✓ Observable: no cross-tenant data; ✓ HIPAA: isolation; Search for: tenant leak |
| AC-R03-09-05 | FR-R03-15 | **Given** `service_director` user logged in, **when** sidebar renders, **then** only "Dashboard" and "Account" visible; Admin submenu hidden (no Users, Tenants, Roles, Logs, Replicas). | Playwright: assert sidebar items; assert admin submenu absent | ✓ Observable: sidebar items; Search for: admin submenu visible, extra items |

---

## Excluded Scope / Out of Scope (Explicit)

The following are explicitly NOT covered by these acceptance criteria:

### Out of Scope — Other Roles' Workflows
- Radiologist reading workflow (R12) — covered by `persona-radiologist.md`
- Technologist acquisition workflow (R06/R07) — covered by `persona-technologist.md`
- Patient registration (R08) — covered by RIS implementation skill
- Billing/cashier (R09) — separate requirements package
- DICOM image viewing/measurement tools (Epic E3) — covered by User-Stories.md

### Out of Scope — v3.0 Deferred (Will-Not-Ship in v3.0)
- FR-R03-06: Staffing vs Demand Forecast (7-day) — v3.1
- FR-R03-07: Equipment Downtime Impact Analysis — v3.1
- FR-R03-08: Protocol Gap Analysis (DICOM tag validation) — v3.1
- FR-R03-09: SLA Breach Root-Cause Categorization — v3.1
- FR-R03-11: Scheduled Report Delivery (email/webhook cron) — v3.1
- FR-R03-13: Configurable Alerting (per-KPI threshold rules) — v3.1

### Out of Scope — Architecture / Platform
- Multi-site federation UI (cross-tenant study sharing) — v3.x per ADR-022
- AI/CAD integration (inference overlays, segmentation display) — v3.2 per PRD-v3
- Full drag-drop report canvas (custom report builder) — v3.1+
- Custom HL7/FHIR field mappings (only standard v2.5/R4 supported in v3.0)
- Mobile-native app (responsive PWA only, no iOS/Android builds)
- Blockchain-based audit (PostgreSQL audit only, no DLT integration)

### Out of Scope — Assumptions
- R15 RIS and R16 EMR integrations are assumed functional (test fixtures used; real IdP testing separate)
- Protocol registry schema (protocols, qa_scores tables) is specified but not yet implemented — backend team must create migration
- Modality capacity config table is specified but not yet implemented — backend team must create
- Report PDF generation engine choice (Puppeteer vs jsPDF) is an implementation decision, not an AC

---

## Traceability Summary

| FR/NFR ID | AC Count | Coverage Status |
|-----------|----------|----------------|
| FR-R03-01 | 9 | ✓ Complete (AC-R03-01-01 through -09) |
| FR-R03-02 | 9 | ✓ Complete (AC-R03-02-01 through -09) |
| FR-R03-03 | 6 | ✓ Complete (AC-R03-03-01 through -06) |
| FR-R03-04 | 6 | ✓ Complete (AC-R03-04-01 through -06) |
| FR-R03-05 | 5 | ✓ Complete (AC-R03-05-01 through -05) |
| FR-R03-10 | 8 | ✓ Complete (AC-R03-06-01 through -08) |
| FR-R03-12 | 5 | ✓ Complete (AC-R03-07-01 through -05) |
| FR-R03-14 | 6 | ✓ Complete (AC-R03-08-01 through -06) |
| FR-R03-15 | 5 | ✓ Complete (AC-R03-09-01 through -05) |
| NFR-R03-01 | 1 | ✓ Covered by AC-R03-01-02 |
| NFR-R03-02 | 3 | ✓ Covered by AC-R03-01-03, -02-02, -02-08 |
| NFR-R03-03 | 2 | ✓ Covered by AC-R03-02-05, -05-04 |
| NFR-R03-04 | 3 | ✓ Covered by AC-R03-06-03, -07-02, -07-04 |
| NFR-R03-05 | 2 | ✓ Covered by AC-R03-06-04, -07-03 |
| NFR-R03-06 | 1 | ✓ Covered by AC-R03-02-05 |
| NFR-R03-07 | 3 | ✓ Covered by AC-R03-03-06, -04-06, metric M-R03-09 |
| NFR-R03-08 | 9 | ✓ Covered by AC-R03-01-07, -02-06, -03-04, -04-05, -05-05, -06-07, -06-08, -07-05, -09 |
| NFR-R03-09 | 3 | ✓ Covered by AC-R03-01-08, -02-07, -03-05 |
| NFR-R03-10 | 7 | ✓ Covered by AC-R03-01-09, -02-06, -03-04, -05-05, -06-07, -07-05, responsive |

**Total AC count**: 59
**All FRs have ≥1 AC**: ✓
**All ACs link to FR/NFR**: ✓