# 07 — Backlog (tracked follow-up items)

Session: user-feature-review/resident (feature/resident-workflow-polish, 2026-08-14).

| ID | Severity | Area | Item | Source | Status |
|----|----------|------|------|--------|--------|
| BL-001 | Low (dev-env) | E2E / dev provisioning | `loginAsAdmin` cannot authenticate: the `admin` password hash in the dev DB (random init-time value from `scripts/dev.sh` `openssl rand`) matches no env var (`pa55w0rd`, `.env SUPERADMIN_PASS`). `e2e/role-based-access.spec.ts` "Admin deep-link denial … /schedule-board" times out at login. Pre-existing — reproduced on pristine baseline. Fix: reset/rotate the dev-DB admin password to a known value (or align `E2E_ADMIN_PASS` with the DB hash) in dev provisioning. | Phase 4 E2E run | Open |
| BL-002 | Low | Teaching Library (ResidentHome) | Add "Ask your attending to curate a case" action button once the teaching-file workflow ships (design D-5); guided copy ships now to avoid a dead button. | 03-handoff.md P2-1 / 05-implementation.md | Open (deferred) |

## Definition of done

- BL-001: `npx playwright test --project=chromium e2e/role-based-access.spec.ts` passes in dev without env tweaks.
- BL-002: button navigates to the teaching-file curation flow when it exists; update `docs/user-feature-review/resident/06-e2e-report.md` P2-1 row accordingly.
