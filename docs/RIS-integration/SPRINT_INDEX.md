# RIS Sprint Index

**Generated:** 2026-08-18 · **Updated:** 2026-08-18  
**Primary Reference:** [`CONSOLIDATED_SPRINT_PLAN.md`](CONSOLIDATED_SPRINT_PLAN.md)  
**Master Spec:** [`ris-integration-spec.md`](ris-integration-spec.md)

---

## Quick Reference

| Phase | Sprints | Duration | Dev-days | Status |
| :--- | :--- | :--- | :--- | :--- |
| **MVP** | S1–S12 | ~6 months | ~316 | Planning complete |
| **v1.1** | R2-S1–R2-S7 | ~3.5 months | ~280 | Planning complete |
| **v2.0** | R2-S8–R2-S12 | ~2.5 months | ~220 | Planning complete |
| **Total** | **24** | **~12 months** | **~816** | — |

---

## MVP Phase (S1–S12)

| Sprint | Focus | Epics | Key Milestone | Exit Gate |
| :--- | :--- | :--- | :--- | :--- |
| **S1–S2** | Platform Foundation | E-RIS-01 | Auth+RBAC+Isolation green | G6 |
| **S3** | Interface Engine + Registration | E-RIS-02, E-RIS-03 | Real HL7 ORM → order | — |
| **S4–S5** | Scheduling Engine | E-RIS-04, E-RIS-05 | Conflict-free booking | G2 |
| **S6–S7** | MWL/MPPS + Tracking | E-RIS-06, E-RIS-07 | Scanner → tracking live | G1, G3 |
| **S8–S9** | Reporting + Sign-Off | E-RIS-08 | Report → sign → distribute | — |
| **S10** | Critical Results + Distribution | E-RIS-09, E-RIS-10 | Critical loop + ORU to EMR | — |
| **S11** | Billing Capture | E-RIS-11 | Auto charge drop | G4, G5 |
| **S12** | Hardening + UAT | — | G1–G7 all green | MVP |

---

## v1.1 Phase (R2-S1–R2-S7)

| Sprint | Focus | Epics | Key Milestone | Exit Gate |
| :--- | :--- | :--- | :--- | :--- |
| **R2-S1–S2** | Prior-Auth + Reminders | E-RIS2-01, E-RIS2-02 | Prior-auth ≥ 95% | RVG-1 |
| **R2-S3–S4** | Denial + Templates + SR | E-RIS2-03, E-RIS2-04, E-RIS2-06 | Unbilled $0 > 5d | RVG-2 |
| **R2-S5–S6** | IDN + Multi-Site | E-RIS2-05 | Cross-site booking | RVG-3 |
| **R2-S7** | FHIR Read + Gates | E-RIS2-07 | FHIR conformance green | RVG-4 |

---

## v2.0 Phase (R2-S8–R2-S12)

| Sprint | Focus | Epics | Key Milestone | Exit Gate |
| :--- | :--- | :--- | :--- | :--- |
| **R2-S8–S9** | Full FHIR + Portal | E-RIS2-08, E-RIS2-09 | Portal results live | RVG-5 |
| **R2-S10–S12** | AI Coding + Chargeback + Hardening | E-RIS2-10, E-RIS2-11, E-RIS2-12 | V2 go/no-go | RVG-6 |

---

## PACS V2 Sprint Parity (coordinate with RIS)

| Sprint | Focus | Shared with RIS |
| :--- | :--- | :--- |
| **V2-S1–S2** | Advanced Viewer, Measurements | — |
| **V2-S3–S4** | Priors, Cross-Tenant Grants | E-RIS2-05 IDN |
| **V2-S5–S6** | Teleradiology, Export | E-RIS-10 report routing |
| **V2-S7–S8** | AI Ingestion, Migration, Gates | — |
| **V2-S9–S10** | UPS-RS, FHIR/SMART | E-RIS2-08 FHIR server |
| **V2-S11–S12** | FHIRcast, Non-DICOM, Edge | — |
| **V2-S13–S15** | Schema-per-Tenant, Patient, AI Gate | — |

---

## Related Documents

| Document | Description |
| :--- | :--- |
| [`ris-integration-spec.md`](ris-integration-spec.md) | Master implementation spec (schema, APIs, services, architecture) |
| [`CONSOLIDATED_SPRINT_PLAN.md`](CONSOLIDATED_SPRINT_PLAN.md) | **Primary reference** — all 24 sprints with task boards, codebase integration map |
| [`VALIDATION_REPORT.md`](VALIDATION_REPORT.md) | Gap analysis: 167 items, 3 critical gaps found and fixed |
| [`SPRINT_PLAN_CONFORMANCE_REPORT.md`](SPRINT_PLAN_CONFORMANCE_REPORT.md) | Conformance check: 106 items, 12 gaps found and fixed |
| `archive/sprint_mvp_0[1-8]_*.md` | Archived MVP sprint details (daily milestones, risks — superseded by consolidated plan) |
| `../archive/reaserch-RIS-original/` | Original RIS research documents (23 files — superseded by spec + consolidated plan) |

---

## Files in This Directory

```
docs/RIS-integration/
├── CONSOLIDATED_SPRINT_PLAN.md      — Primary sprint plan (48 KB)
├── ris-integration-spec.md          — Master spec (56 KB)
├── VALIDATION_REPORT.md             — Gap analysis (19 KB)
├── SPRINT_PLAN_CONFORMANCE_REPORT.md — Conformance check (16 KB)
├── SPRINT_INDEX.md                  — This file (5 KB)
└── archive/
    └── sprint_mvp_0[1-8]_*.md      — Archived MVP sprint details
```
