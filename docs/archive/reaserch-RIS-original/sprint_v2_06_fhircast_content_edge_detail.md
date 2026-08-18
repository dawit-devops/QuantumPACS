# Sprint V2-06 Detail — SMART Viewer Surface (E-V2-10), FHIRcast (E-V2-11), Non-DICOM Content (E-V2-12) & Edge Caching at Scale (E-V2-13)

**Version:** 1.0 · **Date:** 2026-08-05 · **Source:** `requrements/PACS/RELEASE_PLAN_V2.md` E-V2-10 (viewer), E-V2-11, E-V2-12, E-V2-13; `requrements/EMR/RELEASE_PLAN.md` §1 v2.0 (SMART embedded imaging, FHIRcast)
**Cadence:** 2-week sprint (10 working days) · **Squads:** PACS-V2 — 1.5 backend, one frontend, part-time integration engineer (FHIRcast/non-DICOM conformance), Ops/SRE (edge at scale), QA · **Format parity:** `requrements/sprint_v2_01_advanced_viewer_priors_detail.md` … `sprint_v2_05_upsrs_fhir_detail.md`
> **Sprint numbering:** this is sprint detail **V2-06** of the V2 delivery sequence = release-plan roadmap **V2-S11–V2-S12**. Merged because the referring-MD surface and FHIRcast are one EMR-launch program, and non-DICOM content + edge-at-scale both extend the archive layer.

---

## 1. Sprint Goal

> **"A referring physician opens images from the EMR with one click into a simplified read-only surface that follows their EMR context through FHIRcast — while the archive accepts and retrieves non-DICOM content (PDF, video, WSI) and the edge cache scales to multi-site health systems with reads that keep flowing during a cloud outage."**

**Scope in:** referring-MD read-only viewer mode (report + key images + basic tools; PAC-UI-40), EMR-launch landing polish (PAC-UI-39), FHIRcast hub + context-change events (open/close study, user-select) per encounter, authorization + fallback; non-DICOM ingestion (PDF/video/WSI) with metadata model + FHIR DocumentReference linkage + retrieval (video player, WSI pan/zoom), E20 specialty content gated option; edge caching at scale: multi-site edge nodes, prefetch engine scale (distributed queue, bandwidth scheduling), cache invalidation consistency, DR continuity at scale, egress metering per tier/site.

**Scope out (later V2 sprints):** schema-per-tenant escape hatch (V2-07), patient imaging delivery (V2-07), AI utility gate + V2 hardening (V2-07).

**Prior program handoff (required to start):** SMART launch backend + test-EMR harness (V2-05-14…18), full FHIR layer (V2-05-09…13), UPS-RS + result ingestion (V2-05-01…08), prefetch engine (V2-02-01…05), edge cache base (S6-11/12), responsive viewer (V2-01-16/17).

---

## 2. Team Capacity (10 working days)

| Role | FTE | Available dev-days | Notes |
| :--- | :-: | :-: | :--- |
| Backend engineer ×1.5 | 1.5 | 15 | FHIRcast, non-DICOM metadata, edge invalidation |
| Frontend engineer ×1 | 1.0 | 10 | Read-only referring mode, video/WSI viewers, edge dashboard |
| Integration engineer | 0.5 | 5 | FHIRcast + WSI/video conformance |
| Ops/SRE engineer ×0.5 | 0.5 | 5 | Edge node ops, bandwidth scheduling |
| QA | 1.0 | 10 | EMR-launch E2E, content E2E, edge/DR E2E |
| **Total** | **4.5** | **~45** | Total task estimate below: **~33 dev-days** (BE 13.0 · FE 8.5 · INT 3.0 · OPS 3.5 · QA 5.0) — ~12 days slack, absorbed per note below |

> **Slack absorption (not committed):** (a) forward-pull of **E-V2-14 #1** (schema-per-tenant provisioning scaffold) on BE slack; (b) extra WSI conformance corpus; (c) edge-cache failure-injection scenarios. Nothing past E-V2-10 viewer/E-V2-11/E-V2-12/E-V2-13 scope is committed.

---

## 3. Task Board (grouped by source work item)

> Estimates in dev-days. `Owner:` BE = backend, FE = frontend, INT = integration engineer, OPS = ops/SRE, QA = test. `Check:` acceptance check (maps to AC/SL/UI/PRD IDs where applicable).

### 3.1 Referring-MD read-only surface — E-V2-10 #3
**Source:** `PAC/04` PAC-UI-39/40; `PAC/06` PAC-AC-P06-01/03; ADR-009.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| V2-06-01 | Read-only viewer mode: report + key images + basic tools (window/level, zoom, pan); no dictation/edit controls | FE | 2.0 | V2-05-16 | PAC-UI-40 parity; PAC-AC-P06-01 |
| V2-06-02 | Launch landing polish: deep-link to correct study, no search; priors one click; `< 5 s` (PAC-SL-13) | FE | 1.5 | V2-06-01, V2-02-06 | PAC-UI-39; PAC-SL-13 |
| V2-06-03 | Referring-user RBAC: `VIEWER_READ`-class read-only scope; no write/export actions rendered | BE | 1.0 | V2-06-01 | RBAC §6: read-only enforced at UI + API |

**Epic exit contribution:** E-V2-10 #3 (referring-MD surface — VG-7).

### 3.2 FHIRcast context sync — E-V2-11
**Source:** FHIRcast (HL7); PAC-M06; EMR v2.0 FHIRcast; `research/pacs-ris-viewer-integration-spec.md` §5.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| V2-06-04 | FHIRcast hub: topic per encounter (`fhircast.events` on the event backbone, ADR-011), `context-change` events (open-study, close-study, user-select) publish/subscribe | INT | 2.0 | V2-05-14 | Viewer follows EMR context; EMR follows viewer |
| V2-06-05 | Viewer FHIRcast client: subscribe to encounter topic, apply context changes; sync priors/study list | FE | 1.5 | V2-06-04 | PAC-WF7 extension: context sync both directions |
| V2-06-06 | Authorization + failure fallback: context events scoped per session; degrade to manual launch without blocking reads | BE | 1.0 | V2-06-04 | No context loss blocks reading; unauthorized event ignored + audited |

**Epic exit contribution:** E-V2-11 (FHIRcast — VG-7).

### 3.3 Non-DICOM content — E-V2-12
**Source:** PAC-M04; PRD §2.4 (E20); `pacs-ris-architecture-deep-dive.md` §1 (VNA non-DICOM).

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| V2-06-07 | Non-DICOM ingestion: PDF (reports/scanned docs), video (echo/cine), WSI (DICOM WSI SOP classes preferred) via STOW-RS/upload; tiered + tenant-prefixed storage | BE | 2.0 | S3-09 | Objects stored tiered; tenant-isolated |
| V2-06-08 | Metadata model: non-DICOM objects linked to patient/study; FHIR `DocumentReference` linkage | BE | 1.5 | V2-06-07 | Retrievable with correct metadata |
| V2-06-09 | Retrieval: video player (cine/echo), WSI viewer (pan/zoom, pyramid), PDF viewer — read-only | FE | 2.5 | V2-06-07 | PAC-M04: content renders in viewer |
| V2-06-10 | WSI/video conformance: DICOM WSI pyramid SOP classes, video transfer syntaxes in lab harness | INT | 1.0 | V2-06-07 | Repeatable conformance scripts |
| V2-06-11 | E20 specialty gated option: cardiology echo, pathology WSI, POCUS on/off per tenant feature flag | BE | 0.5 | V2-06-09 | Feature-flag gated; storage/retrieval shared path |

**Epic exit contribution:** E-V2-12 (non-DICOM content — VG-8).

### 3.4 Edge caching at scale — E-V2-13
**Source:** `PAC/06` PAC-AC-P04-07; `PAC/05` PAC-SL-03/40/41/42/50; extends S6-11/12 + V2-02 prefetch.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :-: |
| V2-06-12 | Multi-site edge nodes: registration, placement rules, per-site cache quota + quota-aware eviction | OPS | 2.0 | S6-11 | PAC-SL-40 at edge; eviction bounded by quota |
| V2-06-13 | Prefetch engine scale: distributed queue (`prefetch.jobs` topic, ADR-011), bandwidth scheduling across sites, off-peak policies (extend V2-02-03/04) | BE | 1.5 | V2-02-04 | PAC-SL-24 sustained at multi-site load |
| V2-06-14 | Cache invalidation consistency on `storage_objects`/archive changes (extend S6-12) | BE | 1.5 | V2-06-12 | No stale reads after archive change |
| V2-06-15 | DR continuity at scale: reads continue from edge during cloud outage; ingestion buffers; measured in drill | OPS | 1.5 | V2-06-12, S6-13 | PAC-AC-P04-07 at scale; PAC-SL-03/04 |
| V2-06-16 | Egress metering per tier/site: `WADO_BYTES` split for billing + cost control (dims on `usage.events`, ADR-010) | BE | 1.0 | V2-06-12 | PAC-SL-50 accuracy sustained |
| V2-06-17 | Edge ops dashboard: per-site cache hit/eviction/bandwidth; alert on quota pressure | FE | 1.0 | V2-06-12 | Ops visibility; alerts wired |

**Epic exit contribution:** E-V2-13 (edge at scale — VG-8).

### 3.5 Cross-cutting: E2E & gates — VG-7/VG-8 pre-checks
**Source:** `PAC/06` PAC-AC-P06-01/03; `PAC/05` PAC-SL-03/13/40/50/60/61.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| V2-06-18 | EMR-launch E2E: test-EMR → SMART launch → read-only view → FHIRcast open/close context sync → priors | QA | 1.5 | V2-06-01…06 | PAC-AC-P06-01, VG-7 pre-check |
| V2-06-19 | Content E2E: ingest PDF/video/WSI → retrieve → render; feature-flag on/off | QA | 1.5 | V2-06-07…11 | VG-8 pre-check (content) |
| V2-06-20 | Edge/DR E2E: multi-site prefetch → simulate cloud outage → reads from edge; invalidation no-stale; egress meters | QA | 1.5 | V2-06-12…17 | PAC-AC-P04-07, PAC-SL-03/04/50 |
| V2-06-21 | RLS + audit regression on content + FHIRcast routes | QA | 0.5 | V2-06-08/06 | PAC-SL-60/61 |
| V2-06-22 | Performance: WSI pyramid load + edge hit latency under load | QA | 1.0 | V2-06-09/12 | p95 budgets green |
| V2-06-23 | UAT prep: referring-MD + ED-MD scripts (launch, read-only, context sync) | QA | 1.0 | V2-06-18 | Scripts trace to PAC-AC-P06-*/P07-* |
| V2-06-24 | Evidence pack for VG-7/VG-8 pre-checks | QA | 0.5 | V2-06-18…20 | Evidence archived for V2-07 final |

---

## 4. Sprint Milestones

| Milestone | Target | Evidence |
| :--- | :--- | :--- |
| **Day 3** | Read-only mode scaffold; FHIRcast hub topic model; non-DICOM ingest path; edge node registration | V2-06-01, V2-06-04, V2-06-07, V2-06-12 started |
| **Day 5** | Read-only surface + launch landing; FHIRcast client sync; PDF/video retrieval; prefetch scale queue | V2-06-02/03, V2-06-05/06, V2-06-09, V2-06-13 closed |
| **Day 8** | WSI viewer + conformance; edge invalidation + DR continuity; egress metering; ops dashboard | V2-06-10/11, V2-06-14…17 closed |
| **Day 10 (demo)** | EMR-launch + content + edge/DR E2E green; demo: EMR → study < 5 s → FHIRcast sync; outage → edge reads | V2-06-18…24; VG-7/VG-8 pre-checks; sprint review |

---

## 5. Sprint Definition of Done (acceptance checks)

| # | Check | Verifies | Method |
| :-: | :--- | :--- | :--- |
| D1 | One-click EMR launch to correct study < 5 s in read-only mode; no edit controls | PAC-AC-P06-01, PAC-UI-39/40, PAC-SL-13 | V2-06-18 E2E |
| D2 | FHIRcast context sync both directions; fallback degrades gracefully; unauthorized events ignored + audited | VG-7, PAC-SL-60 | V2-06-18 |
| D3 | Non-DICOM content archived tiered + tenant-isolated, retrievable (PDF/video/WSI) | PAC-M04, VG-8 | V2-06-19 |
| D4 | Edge at scale: multi-site prefetch, quota-aware eviction, no stale reads, reads during outage, egress metered | PAC-AC-P04-07, PAC-SL-03/40/50 | V2-06-20 |
| D5 | Read-only RBAC enforced at UI + API | RBAC §6 | V2-06-03 tests |
| D6 | 100% audit on content/FHIRcast events; RLS intact | PAC-SL-60/61 | V2-06-21 |
| D7 | Engineering DoD: `tsc --noEmit` + `vite build` clean; unit tests green; migrations reviewed | release-plan V2 §6 | CI gate |
| D8 | No P0/P1 open defects at sprint close | release-plan V2 §6 | Defect triage |

---

## 6. Risks & Watch Items (Sprint V2-06)

| Risk | Watch indicator | Mitigation |
| :--- | :--- | :--- |
| FHIRcast version/spec drift | V2-06-18 E2E | Spec pinning + test hub; fallback to manual launch (V2-06-06) |
| WSI pyramid performance on large slides | V2-06-22 p95 | Tile-based loading, LOD, render service reuse (V2-01-04) |
| Edge cache consistency (stale reads) | V2-06-20 | Invalidation on archive change (V2-06-14); failure-injection scenarios in slack |
| Multi-site bandwidth cost | PAC-SL-50 | Bandwidth scheduling + off-peak (V2-06-13); egress metering per site |
| Non-DICOM vendor conformance (WSI/video) | V2-06-10 harness | DICOM WSI SOP classes preferred; metadata-first storage; E20 feature-gated |
| EMR v2.0 FHIRcast coordination | VG-7 | Contract-first; test hub; shared freeze dates with EMR-V2 squad |

---

## Traceability

| Source work item | Tasks |
| :--- | :--- |
| E-V2-10 #3 (referring-MD surface) | V2-06-01…03 |
| E-V2-11 (FHIRcast) | V2-06-04…06 |
| E-V2-12 (non-DICOM content) | V2-06-07…11 |
| E-V2-13 (edge caching at scale) | V2-06-12…17 |
| Cross-cutting (EMR-launch/content/edge E2E, RLS/audit, perf, UAT prep) | V2-06-18…24 |
