# Sprint V2-01 Detail — Advanced Viewer Tools & Measurement Persistence (E-V2-01 · E-V2-08 responsive)

**Version:** 1.0 · **Date:** 2026-08-05 · **Source:** `requrements/PACS/RELEASE_PLAN_V2.md` E-V2-01, E-V2-08 (responsive viewer)
**Cadence:** 2-week sprint (10 working days) · **Squads:** PACS-V2 — two frontend engineers (viewer), two backend engineers (render service + SR/GSPS), part-time integration engineer, QA
> **Sprint numbering:** this is sprint detail **V2-01** of the V2 delivery sequence = release-plan roadmap **V2-S1–V2-S2**. The two sprints are merged because the advanced-viewer epic (E-V2-01) is one continuous viewer program; the responsive viewer (E-V2-08 #3) rides along on the same viewer codebase.

---

## 1. Sprint Goal

> **"A radiologist can fully interrogate anatomy in the zero-footprint viewer: MPR/MIP/3D/PET-CT fusion and a complete measurement suite that persist to DICOM SR/GSPS and export into the report — with first-frame load still under 3 seconds on multi-GB studies — while referring physicians get a responsive read-only viewer on tablets and phones that never caches PHI."**

**Scope in:** MPR engine, MIP/MinIP modes, 3D volume rendering (client + server-side render service), PET/CT fusion, full cine, measurement suite (length/angle/ROI/ellipse/line profile/volumetric), DICOM SR/GSPS persistence + retrieval + co-reader policy, measurement export to report, performance budget on 2+ GB studies, responsive viewer (touch gestures, adaptive layout, no-PHI-cache policy).

**Scope out (later V2 sprints):** priors prefetch engine + priors panel (V2-02), cross-tenant grants (V2-02), teleradiology (V2-03), export/share UI (V2-04), AI ingestion/overlays (V2-04), UPS-RS (V2-05), FHIR/SMART (V2-05/06), non-DICOM/edge scale (V2-06), schema-per-tenant/patient delivery/AI gate (V2-07).

**Prior program handoff (required to start):** MVP viewer shell + viewport basics (S4-14/15), frame-level WADO-RS progressive streaming (S4-06), hanging protocols (S4-17), DICOMweb IUA/OAuth2 gate (S4-08), `storage_objects` + tiered retrieval (S3-09/10), audit triggers + `app.facility_id` middleware (S1-07/14), worklist + critical-flag/key-image plumbing (S4-11/20/21).

---

## 2. Team Capacity (10 working days)

| Role | FTE | Available dev-days | Notes |
| :--- | :-: | :-: | :--- |
| Frontend engineer ×2 | 2.0 | 20 | MPR/3D/fusion rendering, measurement UI, responsive viewer |
| Backend engineer ×2 | 2.0 | 20 | Server-side render service, SR/GSPS persistence API, perf |
| Integration engineer | 0.5 | 5 | DICOM SR/GSPS conformance tooling |
| QA | 1.0 | 10 | Advanced-tools acceptance, perf budget, RLS/audit regression |
| **Total** | **5.5** | **~55** | Total task estimate below: **~46 dev-days** (FE 22.0 · BE 16.5 · INT 2.5 · QA 5.0) — ~9 days slack, absorbed per note below |

> **Slack absorption (not committed):** (a) forward-pull of **E-V2-02 #1/#2** (prefetch trigger + prior resolution) once the viewer measurement layer is proven; (b) perf rework time for MPR/3D on the 2+ GB reference set; (c) additional SR conformance corpus. Nothing past E-V2-01/E-V2-08 responsive scope is committed.

---

## 3. Task Board (grouped by source work item)

> Estimates in dev-days. `Owner:` FE = frontend, BE = backend, INT = integration engineer, QA = test. `Check:` acceptance check (maps to AC/UI/SL IDs where applicable).

### 3.1 MPR / MIP / 3D rendering — E-V2-01 #1/2/3
**Source:** `PAC/06` PAC-AC-P01-04; `PAC/04` PAC-UI-16; `research/pacs-ris-viewer-integration-spec.md` §5 (progressive); PAC-SL-10/11.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| V2-01-01 | MPR engine: axial/coronal/sagittal reconstruction from volume series (CT/MR); reformat viewport + scroll/cine on reformats | FE | 3.0 | S4-15 | PAC-AC-P01-04: MPR renders correctly and interactively on reference CT/MR |
| V2-01-02 | MIP/MinIP render modes (slab thickness control) for CT angiography/interventional workflows | FE | 1.5 | V2-01-01 | MIP/MinIP correct on reference MRA/CTA studies |
| V2-01-03 | 3D volume rendering (VR): client-side WebGL with transfer-function presets; progressive LOD on multi-GB studies | FE | 3.0 | V2-01-01 | VR works on 2+ GB CT; viewport never blocks (PAC-AC-P01-10 style) |
| V2-01-04 | Server-side render service: WADO-RS-render-style JPEG/PNG tiles for thin clients (teleradiology/low-power devices); tile cache + metering hook | BE | 2.5 | V2-01-03 | Thin-client MPR/3D preview renders; bytes metered (PAC-SL-50) |
| V2-01-05 | PET/CT fusion: rigid alignment of PET pair, blending slider, SUV display toggle, MPR-linked fusion | FE | 2.0 | V2-01-01 | PAC-AC-P01-04: fusion toggles on PET/CT pairs |
| V2-01-06 | Full cine: loop modes (forward/reverse/ping-pong), speed control, frame stepping, cine on reformats | FE | 1.0 | V2-01-01 | PAC-UI-16 cine controls work; no viewport block |

**Epic exit contribution:** E-V2-01 #1–#5 (interactive MPR/MIP/3D/fusion/cine — PAC-AC-P01-04).

### 3.2 Measurement suite & DICOM SR/GSPS persistence — E-V2-01 #6/7/8
**Source:** `PAC/06` PAC-AC-P01-04 (measurements); `PAC/04` PAC-UI-22 (persist via DICOM SR/GSPS, visible to co-readers per policy); report-template linkage (MVP key-image path S4-21).

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| V2-01-07 | Measurement tools: length, angle, ROI (area/mean), ellipse, line profile, volumetric (MPR-linked) | FE | 3.0 | V2-01-01 | Numeric results display accurately (PAC-AC-P01-04) |
| V2-01-08 | Annotation layer: labels, arrows, freehand; per-user/per-study visibility policy | FE | 1.5 | V2-01-07 | PAC-UI-22: annotations persist with the study |
| V2-01-09 | DICOM SR/GSPS writer: measurements/annotations serialized to DICOM SR (TID 300) + GSPS; SOP instance per series | BE | 2.0 | V2-01-07 | Conformance tool validates SR/GSPS against standard |
| V2-01-10 | SR/GSPS storage + retrieval API: store via STOW-RS path, retrieve with series; versioning on re-save | BE | 1.5 | V2-01-09 | PAC-UI-22: measurements survive reload and device switch |
| V2-01-11 | Measurement export to report template: key measurements auto-linked as text/thumbnails at sign time | BE | 1.0 | V2-01-10, S4-21 | Report carries measurements + key images (PAC-AC-P01-07 extension) |
| V2-01-12 | SR/GSPS conformance corpus + validation suite (TID 300 templates, GSPS presentation states) | INT | 2.5 | V2-01-09 | ≥ 95% of corpus validates; 0 corrupt writes |

**Epic exit contribution:** E-V2-01 #6/7/8 (measurements persist + export — VG-1).

### 3.3 Performance budget on multi-GB studies — E-V2-01 #9
**Source:** `PAC/05` PAC-SL-10/11; `PAC/06` PAC-AC-P01-08/10.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| V2-01-13 | Perf harness extension: MPR/3D/fusion scenarios on the 2+ GB CT + MR reference sets; p95 budgets for open, reformat, VR first-tile | QA | 1.5 | V2-01-01…V2-01-06 | PAC-SL-10/11 p95 assertions green (no regression) |
| V2-01-14 | Render-path tuning: frame batching, transfer-syntax caching, prefetch window, tile LOD strategy | FE | 2.0 | V2-01-13 | First-frame < 3 s maintained with tools active |
| V2-01-15 | Server-side render pool sizing + cache eviction; metering of rendered bytes | BE | 1.0 | V2-01-04 | Render service SLOs met; PAC-SL-50 bytes metered |

**Epic exit contribution:** E-V2-01 #9 (performance budget — VG-1).

### 3.4 Responsive viewer — E-V2-08 #3
**Source:** `PAC/06` PAC-AC-P06-03; `PAC/04` PAC-UI-42/43.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| V2-01-16 | Responsive layout: adaptive series strip + viewport on tablet/phone (portrait/landscape), limited-but-useful toolset | FE | 1.5 | V2-01-07 | PAC-AC-P06-03: layout adapts; touch works |
| V2-01-17 | Touch gestures: pinch zoom, swipe series, tap-to-window-level; screen-lock-on-blur + session timeout | FE | 1.0 | V2-01-16 | PAC-UI-43: no PHI cached on device; lock on blur |
| V2-01-18 | Shared-device caution: no localStorage of PHI, in-memory render cache only, logout on blur | FE | 0.5 | V2-01-17 | Device-cache audit pass (PAC-SL-60 view events intact) |

**Epic exit contribution:** E-V2-08 #3 (responsive viewer — PAC-AC-P06-03).

### 3.5 Cross-cutting: audit, RLS & E2E — VG-1
**Source:** `PAC/05` PAC-SL-60/61; `PAC/06` PAC-AC-P01-04.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| V2-01-19 | Audit: measurement/annotation create/update/delete, SR/GSPS writes, render-tile egress logged | BE | 1.0 | V2-01-10 | PAC-SL-60: 100% of scripted events logged |
| V2-01-20 | RLS regression on SR/GSPS + render objects (cross-facility query returns 0 rows) | QA | 0.5 | V2-01-10 | PAC-SL-61-style isolation assertion green |
| V2-01-21 | Advanced-tools E2E: CT-chest → MPR → 3D → measurement → SR save → reload → report link | QA | 1.5 | V2-01-07…V2-01-12 | PAC-AC-P01-04, PAC-UI-22 pass in staging |
| V2-01-22 | Responsive E2E: tablet flow open → pinch/swipe → session-timeout → no cached PHI | QA | 1.0 | V2-01-16…18 | PAC-AC-P06-03, PAC-UI-43 pass |
| V2-01-23 | Perf sign-off: full PAC-SL-10/11 suite with tools active; budget recorded | QA | 0.5 | V2-01-13…15 | p95 budget artifact archived |
| V2-01-24 | UAT prep: radiologist advanced-tools script (MPR/3D/fusion/measurements) + referring-MD responsive script | QA | 1.0 | V2-01-21/22 | Scripts trace to PAC-AC-P01-04/P06-03 |

---

## 4. Sprint Milestones

| Milestone | Target | Evidence |
| :--- | :--- | :--- |
| **Day 3** | MPR engine live on reference CT; measurement primitives in viewer; render service scaffold | V2-01-01/07/04 started; conformance tooling run |
| **Day 5** | MIP/3D/VR + fusion first pass; SR writer produces valid SR; responsive shell | V2-01-02/03/05/09/16 closed; SR validates |
| **Day 8** | Measurement export to report; perf tuning; touch gestures + device policy; audit wired | V2-01-10…V2-01-12, V2-01-13/14, V2-01-17/19 closed |
| **Day 10 (demo)** | E2E + perf suites green; demo: CT → MPR → 3D → measure → SR → report link; tablet flow | V2-01-21…V2-01-24; VG-1 pre-checks; sprint review |

---

## 5. Sprint Definition of Done (acceptance checks)

| # | Check | Verifies | Method |
| :-: | :--- | :--- | :--- |
| D1 | MPR/MIP/MinIP/3D/fusion/cine render correctly and interactively on CT/MR | PAC-AC-P01-04 | V2-01-21 E2E |
| D2 | Measurements display accurate numerics and persist via DICOM SR/GSPS across reload/device switch | PAC-AC-P01-04, PAC-UI-22 | V2-01-09…12 + V2-01-21 |
| D3 | Measurement/key-image export into report template at sign | PAC-AC-P01-07 (extension) | V2-01-11 + report E2E |
| D4 | First-frame < 3 s p95 preserved with tools active on 2+ GB studies | PAC-SL-10/11, PAC-AC-P01-08/10 | V2-01-13/23 perf suite |
| D5 | Responsive viewer: touch + adaptive layout; no PHI cached; lock on blur | PAC-AC-P06-03, PAC-UI-42/43 | V2-01-22 |
| D6 | 100% audit on measurement/SR/render events; RLS isolation intact | PAC-SL-60/61 | V2-01-19/20 |
| D7 | Engineering DoD: `tsc --noEmit` + `vite build` clean; unit tests green; migrations reviewed (SR/GSPS tables) | release-plan V2 §6 | CI gate |
| D8 | No P0/P1 open defects at sprint close | release-plan V2 §6 | Defect triage |

---

## 6. Risks & Watch Items (Sprint V2-01)

| Risk | Watch indicator | Mitigation |
| :--- | :--- | :--- |
| MPR/3D client rendering performance on multi-GB CT | PAC-SL-10/11 p95 | Server-side render service (V2-01-04), LOD + tile caching (V2-01-14); perf harness from Day 1 |
| SR/GSPS conformance drift (vendor interpretation) | V2-01-12 validation | Conformance corpus + validator; versioned templates; 0 corrupt writes gate |
| Measurement export coupling to report template | V2-01-11 sign-path | Reuse key-image linkage (S4-21); report template extension is a RIS-side contract |
| WebGL availability on hospital machines | V2-01-03/04 fallback | Render-service JPEG/PNG fallback for non-WebGL clients |
| **FE capacity at/over budget (22 of 20 dev-days)** | Velocity vs. 20 FE-days | Sequence after BE deps; responsive viewer (V2-01-16…18) slips into slack; render service absorbs load |
| RLS gap on new SR/GSPS/render tables | Isolation regression (V2-01-20) | `NOBYPASSRLS` + `FORCE ROW LEVEL SECURITY` convention from `pacs-ris-multitenancy.md` §3 |

---

## Traceability

| Source work item | Tasks |
| :--- | :--- |
| E-V2-01 #1 (MPR) | V2-01-01 |
| E-V2-01 #2 (MIP/MinIP) | V2-01-02 |
| E-V2-01 #3 (3D VR) | V2-01-03/04 |
| E-V2-01 #4 (PET/CT fusion) | V2-01-05 |
| E-V2-01 #5 (cine full) | V2-01-06 |
| E-V2-01 #6 (measurement suite) | V2-01-07/08 |
| E-V2-01 #7 (SR/GSPS persistence) | V2-01-09/10 |
| E-V2-01 #8 (report export) | V2-01-11 |
| E-V2-01 #9 (performance) | V2-01-13…15, V2-01-23 |
| E-V2-08 #3 (responsive viewer) | V2-01-16…18, V2-01-22 |
| Cross-cutting (audit, RLS, E2E, UAT prep) | V2-01-19…21, V2-01-24 |
