# Acceptance Criteria — Radiology Service Nursing Team (R11)

| AC ID | Links to | Criteria (Given/When/Then) | Verification Method | Validator Gate |
|-------|----------|----------------------------|---------------------|----------------|
| AC-R11-01 | FR-R11-01 | Given patients in the department, when the worklist opens, then it renders within 2.5s and refreshes within 5s | Automated E2E + probe | Must pass 6.4 |
| AC-R11-02 | FR-R11-02 | Given a checklist, when items are confirmed, then progress renders and all items are required before prep completes | Automated E2E | Must pass 6.4 |
| AC-R11-03 | FR-R11-03 | Given a monitoring session, when vitals are entered, then each reading persists with timestamp and operator within 500ms | Automated E2E + backend timing | Must pass 6.4 |
| AC-R11-04 | FR-R11-04 | Given safety confirmation, when contrast is recorded, then agent/dose/route/time persist and link to the exam | Automated E2E | Must pass 6.4 |
| AC-R11-05 | FR-R11-05 | Given allergy/pregnancy/renal flags, when contrast is attempted without confirmation, then the action is blocked; a positive allergy requires an override with justification | Automated E2E + audit scan | Must pass 6.4 |
| AC-R11-06 | FR-R11-06 | Given a reaction, when logged with type/severity/onset/actions, then escalation to the on-call radiologist fires and is acknowledged within 15min | Escalation probe | Must pass 6.4 |
| AC-R11-07 | FR-R11-07 | Given a sedated exam, when sedation doses and monitoring intervals are recorded, then they persist with timestamps | Automated E2E | Must pass 6.4 |
| AC-R11-08 | FR-R11-08 | Given recovery observations, when discharge criteria are met and discharge is confirmed, then the visit status updates and instructions are printable | Automated E2E | Must pass 6.4 |
| AC-R11-09 | FR-R11-09 | Given a medication administration, when recorded, then dose/route/time/indication persist in the MAR | Automated E2E | Must pass 6.4 |
| AC-R11-10 | FR-R11-10 | Given a handoff note, when saved, then it persists and is visible to the next shift | Automated E2E | Must pass 6.4 |
| AC-R11-11 | NFR-R11-01 | Given the worklist, when measured, then LCP ≤ 2.5s and INP ≤ 200ms | Lighthouse CI, RUM | Must pass 6.4 |
| AC-R11-12 | NFR-R11-06 | Given bedside vitals entry offline, when connectivity returns, then queued readings sync within 2min | Synthetic offline test | Must pass 6.4 |
| AC-R11-13 | NFR-R11-02 | Given the worklist, when measured, then staleness ≤ 5s | Synthetic probe | Must pass 6.4 |
| AC-R11-14 | NFR-R11-03 | Given a vitals submit, when measured, then save completes ≤ 500ms optimistic | Backend timing | Must pass 6.4 |
| AC-R11-15 | NFR-R11-04 | Given a logged reaction, when measured, then escalation reaches physician ack ≤ 15min | Escalation probe | Must pass 6.4 |
| AC-R11-16 | NFR-R11-05 | Given bedside forms, when audited, then WCAG 2.2 AA passes (keyboard, focus, contrast ≥ 4.5:1) | axe-core CI + manual | Must pass 6.4 |

## Excluded Scope / Out of Scope

- Diagnostic image interpretation (R12/R18).
- Image acquisition or dose documentation on the modality (R06/R07).
- Patient registration or scheduling (R08/R04).
- Billing or payment (R09).
