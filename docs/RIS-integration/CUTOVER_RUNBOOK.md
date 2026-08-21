# QuantumPACS + RIS — Cutover Runbook (S12-29)

**Branch:** `feature/ris-integration` → `v3-dev` → `release/v3.N`
**Scope:** deploy, verify, and roll back the integrated PACS+RIS MVP.
Companion evidence: `docs/RIS-integration/S12_HARDENING_EVIDENCE.md` (G1–G7).

---

## 1. Preflight (T-60 min)

| # | Check | Command / signal | Pass condition |
|---|-------|------------------|----------------|
| P1 | CI green on release candidate | pipeline on `v3-dev` / `phase/**` | all jobs pass |
| P2 | Full test suite green | `pytest` backend + `vitest run` frontend | 0 failures |
| P3 | Migrations replay cleanly on a scratch DB | fresh DB → `alembic upgrade head` | head = latest revision, no errors |
| P4 | Images buildable | `docker compose build postgres backend frontend` | images tagged |
| P5 | Backups current | latest `pg_dump` per database < 24 h old; restore spot-checked | dump restores into scratch DB |
| P6 | Config secrets present | `backend/config.local.yaml` or env: non-default `secret`, `DB_*` set | `assert_production_secret()` passes |
| P7 | Change window + comms sent | maintenance banner scheduled; stakeholders notified | ack from on-call + service owner |

## 2. Deploy sequence (T-0)

Order matters: infrastructure → database → stateless services.

1. **Enable maintenance mode** (`/api/admin/status`) so the login page
   shows the banner and DICOM routes drain.
2. **PostgreSQL**: `docker compose up -d postgres` (custom
   `quantumpacs-postgres:18`). Wait for readiness before anything touches it.
3. **Redis**: `docker compose up -d redis`.
4. **Backend**: `docker compose up -d backend`. The image entrypoint runs
   `python -m alembic upgrade head` **fail-fast** — if the container exits,
   fix the migration before proceeding (never bypass to "get it running").
   - Watch: `docker logs -f quantumpacs-backend-1` until uvicorn binds.
5. **Frontend**: `docker compose up -d frontend`.
6. **Elasticsearch** (optional): `docker compose up -d es`; search degrades
   gracefully if absent.

## 3. Verification signals (T+10)

| Signal | How | Pass |
|--------|-----|------|
| Health | `curl :8080/api/health` and `/api/v2/health` | 200 |
| Login | super-admin login via UI | token issued |
| MWL | C-FIND from a mapped station AE | entries returned |
| Tracking board | open `/worklist` tracking view | rows render, KPIs populate |
| Report sign-off | sign a test report | TAT histogram increments (`ris_report_tat_seconds`) |
| Billing queue | check `/billing` after the sign | charge row present |
| Background engines | `journalctl`/container logs | escalation, prior-auth alert, reminder monitor lines present |
| Tenant isolation | login as tenant user, hit another tenant's study id | 403/404 |

Smoke = all eight. Any red → rollback decision within the window (§5).

## 4. Post-deploy

- Disable maintenance mode.
- Monitor error rate + p95 latency for 30 min (Prometheus:
  `ris_hl7_messages_total`, `ris_mpps_latency_seconds`,
  `ris_report_tat_seconds`, `ris_charge_drop_latency_seconds`).
- Announce completion; file follow-ups for any soft-gate warnings.

## 5. Rollback procedure

Trigger criteria: verification smoke failure, error-rate spike, data
integrity signal, or P0 regression post-cutover.

1. **Stop traffic**: re-enable maintenance mode.
2. **Application rollback** (schema-compatible changes):
   `docker compose up -d --no-deps --force-recreate backend frontend`
   pinned to the previous image tags. App-level rollback is always safe;
   do this first even when a schema downgrade will follow.
3. **Schema rollback** (only if the incident is caused by a migration):
   - Identify the breaking revision: `alembic history` vs deployed tag.
   - Run its `downgrade()` against the target DB **after** taking a fresh
     backup of the affected tables.
   - Prefer forward-fix over downgrade whenever the window allows — every
     migration in `backend/migrations/versions/` ships a working
     `downgrade()`, but downgrades still discard data written under the
     new schema.
4. **Database restore** (last resort, corruption only):
   stop backend → drop/recreate affected DB → `pg_restore` the preflight
   dump (P5) → start backend (entrypoint replays migrations to head).
5. **Verify**: repeat §3 smoke suite.
6. **Postmortem**: record timeline, root cause, and gate the next cutover
   on the resulting action items.

## 6. Rollback rehearsal checklist (pre-GO)

Executed once per release train on staging:

- [ ] Previous-tag backend/frontend images retained in the registry
- [ ] `alembic downgrade` exercised for the release's newest migration
- [ ] Restore-from-dump rehearsed into a scratch DB (P5 proof)
- [ ] Maintenance-mode toggle verified end-to-end
- [ ] Time-to-rollback measured (target ≤ 15 min app-only, ≤ 60 min full)

## 7. Comms plan

| When | Audience | Message |
|------|----------|---------|
| T-24 h | All clinical users | maintenance window notice |
| T-60 min | On-call, service owner | go/no-go confirmation |
| T-0 | All users | banner active (login page) |
| Rollback | Same as deploy | incident notice + ETA |
| T+1 day | Stakeholders | verification summary + soft-gate notes |

---

**Out of scope for this document** (manual activities, tracked in the
evidence package): DR drill execution (S12-31), WCAG full audit (S12-32),
per-persona UAT sign-off (S12-14…20), go/no-go meeting record (S12-30).
