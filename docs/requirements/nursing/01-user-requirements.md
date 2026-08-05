# User Requirements — Radiology Service Nursing Team (R11)

**Version**: 1.0.0 (v3.0 scope)
**Status**: Draft
**Date**: 2026-08-02

## Functional Requirements

| ID | Requirement | Priority | Notes |
|----|-------------|----------|-------|
| FR-R11-01 | **Nursing Worklist**: Display patients needing nursing care (prep, contrast, monitoring, recovery) with status (waiting, in prep, in procedure, recovery, discharged). Auto-refresh from check-in/exam status. | Must | Feeds from R08 check-in + R06/R07 exam status |
| FR-R11-02 | **Patient Prep Checklist**: Structured pre-procedure prep checklist (fasting, labs, consent verified) with item-by-item confirmation. | Must | Checklist per procedure type |
| FR-R11-03 | **Vitals Capture**: Record vitals (BP, HR, SpO2, temperature, respiration) with timestamp and operator; support repeated readings during monitoring. | Must | Vitals log per patient |
| FR-R11-04 | **Contrast Administration Record**: Record contrast agent, dose, route, rate, and time; link to the exam and dose records. | Must | Supports R06/R07 dose documentation |
| FR-R11-05 | **Allergy & Safety Verification**: Pre-contrast screening (allergy, pregnancy, renal function) with required confirmation before contrast is administered. | Must | From HL7 ADT allergy flags + nurse confirmation |
| FR-R11-06 | **Adverse Reaction Response**: Log adverse reactions with type, severity, onset, and actions; trigger escalation to the on-call radiologist/physician. | Must | Escalation ≤ 15min |
| FR-R11-07 | **Sedation Monitoring**: For sedated exams, record sedation doses and monitoring intervals (vitals + sedation score). | Should | Sedation records per exam |
| FR-R11-08 | **Post-Procedure Recovery & Discharge**: Record recovery observations and discharge criteria; print discharge instructions. | Must | Recovery workflow |
| FR-R11-09 | **Medication Administration Record (MAR)**: Record administered medications (pre-medication, rescue) with dose, route, time, and indication. | Must | MAR per patient visit |
| FR-R11-10 | **Handoff Notes**: Record structured handoff notes between nursing shifts and to technologists/radiologists. | Should | Handoff between shifts |

## Non-Functional Requirements

| ID | Requirement | Target | Measurement |
|----|-------------|--------|-------------|
| NFR-R11-01 | Nursing worklist load time | LCP ≤ 2.5s, INP ≤ 200ms | Lighthouse CI, RUM |
| NFR-R11-02 | Worklist freshness | ≤ 5s staleness | Synthetic probe |
| NFR-R11-03 | Vitals/checklist save latency | ≤ 500ms optimistic | Backend timing |
| NFR-R11-04 | Adverse reaction escalation | ≤ 15min to physician ack | Escalation probe |
| NFR-R11-05 | WCAG 2.2 AA compliance | 100% (bedside forms) | axe-core CI + manual |
| NFR-R11-06 | Offline tolerance for vitals entry | Queue + sync ≤ 2min | Synthetic offline test |

## Codebase Status (verified 2026-08-03)

**GATED**: All FR-R11-NN nursing requirements are aspirational v3.0 — no nursing
worklist, prep, vitals, or contrast routes/endpoints exist. Nursing accounts today
have only Files/patient read-only views. Requires new backend nursing module +
permissions flagged to backend. See artifacts 04/07/08.

## Assumptions & Constraints

- A1: Contrast administration is nurse-initiated but requires prior allergy/safety verification (FR-R11-05).
- A2: Vitals and MAR data may be entered at the bedside on tablet — needs offline tolerance.
- A3: Adverse reaction escalation must reach the on-call radiologist (R12) or teleradiologist (R18) within 15 minutes.
- A4: No diagnostic image interpretation by nursing.
- A5: All nursing documentation is audited (who, what, when).
