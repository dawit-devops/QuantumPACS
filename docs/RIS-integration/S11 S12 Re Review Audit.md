
S11/S12 Re-Review & Audit Report
Verdict
S11: NOT functionally complete — 1 critical defect invalidates the core feature (auto charge drop).
S12: Partially implemented — perf/security engineering landed; ~14 of 35 plan tasks have zero artifacts (UAT, gates, evidence package, runbook, DR drill, WCAG).
The suite is green (2172 backend tests) but heavily mock-based (_Conn fake asserting SQL substrings), which is precisely why the critical bug below is invisible to CI.
CRITICAL (P0)
C-1 · Auto charge drop is dead code — the S8-14 stub still wins every sign-off (S11-03)
Reports.sign() still calls the old stub internally at backend/db/reports.py:154-166 → inserts a bare charge row (no CPT/ICD-10, no patient, charge_amount=0, tenant_id='default'). The handler then calls the real drop_charge() (api/reports.py:330 → :378) — but its idempotency guard WHERE NOT EXISTS (report_id=…) (db/ris_charges.py:71) makes it a silent no-op.
Consequences on every sign:
- Charges carry no coding, no patient data, $0 amount → coder queue unusable (RIS-SL-40 unmet)
- Non-default tenants: row tagged 'default' while queue/reconciliation filter by the real tenant (api/billing.py:822, :946) → charges invisible, capture rate 0%, G4 gate fails
- Migration 077 even preserved 17 legacy coding-less stub rows as PENDING charges
The only test covering this path (test_ris_billing.py:202) asserts SQL contains cpt_code — it never verifies coding resolution or the sign→charge sequence.
HIGH (P1)
#	Finding	Evidence
H-1	FE suggestions broken + no override UI (S11-11) — loadSuggestions() sends accession_number where a procedure description is expected; ILIKE match can never hit. Suggestions are stored but never rendered or editable (editing state unused). Acceptance "CPT suggestions, confirm, override" unmet	frontend/src/billing/BillingQueue.tsx:63-73,171
H-2	indication→ICD-10 is dead code (S11-02) — plan requires "procedure → CPT, indication → ICD-10". suggest_icd10() exists but nothing calls it; drop_charge(indication=…) accepts and ignores it	db/ris_coding.py:97; db/ris_charges.py:219-245
H-3	No billing E2E (S11-12) — all 21 tests are SQL-string mocks; no integration test of sign→charge→queue→confirm→aging. Enabled C-1	backend/tests/test_ris_billing.py
H-4	Claim/denial stubs corrupt state — claim submit leaves charge PENDING with no guard against duplicate claims; denial doesn't flip the charge to DENIED (still counted as unbilled); no 837 JSON payload produced ("Format validated" acceptance unmet)	api/billing.py:892-935
H-5	S12-07 HL7 throughput test is vacuous — tests a locally-defined fake engine appending to a list; zero coverage of the real hl7_engine. "0 failures" proves nothing	tests/test_perf_gates.py:294-319
H-6	S12 exit artifacts missing entirely — evidence package docs/RIS-integration/S12_HARDENING_EVIDENCE.md is referenced by test_perf_gates.py:6-7 but does not exist; no UAT scripts (S12-14..20), G1–G7 verification records (S12-21..27), cutover runbook (S12-29), go/no-go record (S12-30), DR drill (S12-31), WCAG 2.1 AA audit (S12-32)	repo-wide search
MEDIUM (P2)
#	Finding	Evidence
M-1	Aging grouped by date only — plan/spec require date/site/payer (RIS-SL-41); charges table lacks payer/site columns so grouping is impossible without joins. FE test mocks facility_name/payer_name the API never returns	db/ris_charges.py:120; test_ris_billing.py:317-320
M-2	order_id never populated on charges (spec has it NOT NULL) — no charge↔order traceability	migration 077; drop_charge()
M-3	TAT definition inconsistent: metric uses completed_at→sign (S12-33), dashboard uses report created_at→sign (S12-34)	api/reports.py:339; api/ris_dashboard.py:34
M-4	Dashboard gaps: drill-down toggle UI absent (setDrillDown never called); unbilled_aging reduced to a count; no utilization chart / export per S12-35; billing KPI gated on REPORT_READ alone	frontend/src/admin/RISDashboard.tsx:41; api/ris_dashboard.py:26,54
M-5	Perf gates weak/mislabeled: "p95" is actually mean (elapsed/50); S12-01/05 measure mock paths; soft bounds (15s booking vs p95<1.5s SLO) with hard numbers deferred to a nonexistent doc; S12-03 registration perf and S12-06 autosave perf not implemented at all	test_perf_gates.py:36-39,109
M-6	S12-09 RBAC sweep not done for new endpoints (test_rbac_matrix.py predates S11/S12, tests role catalogs not endpoint×perm); S12-10 IDOR covers only 4 endpoints vs "All APIs"; S12-11 audits one event type vs "every write event"	tests cited above
M-7	Reconciliation inflates capture rate: counts DISTINCT report_id including VOID/DENIED charges	db/ris_charges.py:159
M-8	Hot-path smells: seed_defaults() runs 12 INSERTs on every GET /cpt-suggestions; LIKE wildcards unescaped; new billing handlers' audit events omit request_id (inconsistent with same file)	api/billing.py:812,851,909
What's genuinely good
- Migration 077 is exemplary: spec-shaped schema, partial unbilled index, safe rollback, stub-row preservation, documented ADR-029 deviation (tenant_id tag + pool isolation instead of facility_id RLS)
- Real-DB concurrency tests (S12-02 EXCLUDE one-winner, S12-04 state-machine) are correct and meaningful
- Escalation event-loop fix (2e4862f) is sound, mirrors _start_dicom, live-verified
- TAT histogram, dashboard API/UI, sidebar gating, routes, telemetry all correctly registered
Conformance scorecard
Sprint	Tasks planned	Done	Partial	Missing	Broken
S11	15	5	5	1 (E2E)	1 critical (C-1) + stubs
S12	35	10	6	14	1 vacuous test
Proposed remediation plan (awaiting your approval)
Phase 1 — Critical fix (S11 correctness):
1. Remove drop_charge_stub call from Reports.sign() (db/reports.py:154-166) — single drop path via handler; keep guard
2. Wire indication → suggest_icd10() into get_suggestions()/charge creation
3. Add real-DB integration test: sign → assert single fully-coded, correctly-tenanted charge; plus cleanup migration note for the 17 orphan stub rows
Phase 2 — High fixes: FE suggestion lookup by procedure + editable override UI; claim/denial state machine guards (+ minimal 837 JSON shape); replace vacuous HL7 test with engine-level throughput test
Phase 3 — S12 completion: produce S12_HARDENING_EVIDENCE.md, persona UAT scripts (P01–P07), G1–G7 gate checklist, cutover runbook, WCAG checklist for the 5 new pages; add S12-03/06/09 sweeps
