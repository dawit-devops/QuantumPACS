# ADR-028: Enterprise dcm4chee Archive Migration with Weasis Viewer

## Status

Accepted

## Date

2026-08-15

## Context

QuantumPACS currently stores DICOM through a hand-rolled pynetdicom stack:

- **C-STORE SCP** on port 11112 (`backend/dcm/server.py`, AE `QUANTUMPACS`) with
  C-FIND query support (Patient/Study Root, query-only, no C-MOVE)
- **Modality Worklist C-FIND SCP** on the same port (or an optional dedicated
  `dicom_mwl_port`), backed by the `worklist_entries` table
- **DICOMweb** (QIDO-RS / WADO-RS / STOW-RS / WADO-URI) implemented in
  `backend/api/dicomweb.py` on the HTTP port
- **HL7 MLLP** ADT/ORM ingestion on port 12579 (`services/ingestion/hl7_server.py`)
  — out of scope for this migration, stays as-is

Ingestion (`backend/dcm/store.py::store_instance`) extracts metadata, writes the
file to the storage backend (local/S3/B2), upserts patient/study/series rows,
publishes `study.stored` events, enforces tenant quotas, routes replicas, and
auto-matches worklist entries.

The hand-rolled DIMSE stack has production gaps this migration closes:

- No C-MOVE (modalities cannot pull priors), no DICOM SR support, no HL7→DICOM
  modality bridging, no proven archive-grade storage/retention tooling
- DICOMweb is a partial re-implementation of PS3.18; conformance and edge-case
  risk stays on QuantumPACS
- Weasis, the de-facto open-source DICOM viewer, integrates natively with
  dcm4chee via `weasis-pacs-connector` but has no supported path into
  QuantumPACS's custom store

Decision scope: replace the DIMSE/DICOMweb storage surface with an enterprise
dcm4chee archive in front of the existing QuantumPACS application, and add a
Weasis launch path. The QuantumPACS application layer (RBAC, tenancy,
worklists, reports, exams, FHIR, HL7, routing, quota, replicas, ES search)
remains the system of record for business metadata.

### Baseline inventory (2026-08-15, dev database)

| Tenant | Studies | Series | Instances | Patients | Bytes |
|--------|---------|--------|-----------|----------|-------|
| default | 9 | 9 | 12 | 8 | 8 964 kB |
| (NULL — pre-tenant rows) | 8 | 8 | 8 | 7 | 710 kB |
| **Total** | **16** | **16** | **20** | **15** | **9.7 MB** |

- Storage backend: local only (no S3/B2 keys configured); 20 replica rows
- `dicom_ae_tenant_map` empty → every calling AE routes to the `default`
  tenant; `dicom_mwl_port` empty → MWL served on the C-STORE port
- Backfill at this scale is trivial (< 100 studies; a few seconds via C-STORE)

## Decision

Adopt **dcm4chee 5.35.0** as the DICOM archive in front of QuantumPACS
(Option B — "dcm4chee forwards to QuantumPACS"), running the **unsecured**
archive image behind the QuantumPACS HTTP proxy, plus the
**weasis-pacs-connector 8.0.0** on the same WildFly instance.

### Target topology

```
Modalities ─C-STORE / C-FIND MWL─▶ dcm4chee-arc 5.35.0 (11112, AE DCM4CHEE)
      │                             ├─ slapd-dcm4chee 2.6.13-35.0 (389)
      │                             ├─ postgres-dcm4chee 17.9-35 (host 5433)
      │                             ├─ weasis-pacs-connector 8.0.0 (8082, same WildFly)
      │                             └─ /var/local/dcm4chee-arc/{storage,wildfly}
      │ export (REST→C-STORE) ▼
      └──────────────────────▶ QuantumPACS SCP (11113, AE QUANTUMPACS)
                                  → store_instance(): metadata+ES+quota+routing+replicas+MWL match (unchanged)
Frontend (Cornerstone) → /dicomweb/* proxy → dcm4chee QIDO/WADO-RS
Frontend "Open in Weasis" → /api/weasis/launch (authz) → connector → Weasis 4.x desktop → WADO-URI → dcm4chee
worklist_entries → MWL-RS (POST /mwlitems, status, DELETE) → dcm4chee MWL SCP
```

The sync contract (Option B): dcm4chee is the primary DICOM object store.
QuantumPACS keeps a **thin C-STORE SCP on port 11113** (AE `QUANTUMPACS`) that
feeds `store_instance()` unchanged — dcm4chee pushes instances to it via the
export REST API. `store_instance()`'s SOP-UID dedup makes this idempotent, so
the metadata pipeline stays the single source of truth for business data while
dcm4chee owns pixel storage and DICOM-level services.

### Components (pinned)

| Component | Version | Source |
|---|---|---|
| dcm4chee archive | `dcm4che/dcm4chee-arc-psql:5.35.0` (unsecured variant) | Docker Hub |
| LDAP | `dcm4che/slapd-dcm4chee:2.6.13-35.0` | Docker Hub |
| Archive PostgreSQL | `dcm4che/postgres-dcm4chee:17.9-35` | Docker Hub (PG 17; separate container — do **not** share QuantumPACS PG 18) |
| Weasis connector | `weasis-pacs-connector.war` **8.0.0** (vendored, SHA256-pinned) | SourceForge `dcm4che/files/Weasis` |
| Weasis client | **4.x** desktop, Java 17+, installed per workstation | weasis.org |
| Elasticsearch | **none** for dcm4chee (optional feature; QuantumPACS ES 9.5.0 stays separate) | — |

### Port mapping

| Service | dcm4chee default | Host mapping | Notes |
|---|---|---|---|
| DICOM C-STORE/C-FIND | 11112 | 11112 | Modalities point here |
| WildFly HTTP (REST + connector) | 8080 | 8082 | Bound to 127.0.0.1 (dev) / internal network (prod) |
| Archive PostgreSQL | 5432 | 5433 | Separate container, no clash with QuantumPACS PG |
| LDAP | 389 / 636 | 389 / 636 | slapd container |
| WildFly admin | 9990 / 9993 | 9990 / 9993 | 127.0.0.1 only |
| HL7 (dcm4chee) | 2762 | 2762 | Off until needed |
| Syslog | 2575 / 12575 | 12575 | Off until needed |
| arc-ui | 18080 | off by default | — |

QuantumPACS pynetdicom SCP moves from 11112 → **11113** (transition) with AE
`QUANTUMPACS`; HL7 MLLP on 12579 stays unchanged.

### Sync contract (Phases 3+)

- **Dual-write during transition**: modalities C-STORE to dcm4chee (11112);
  dcm4chee export → C-STORE to QuantumPACS (11113); QuantumPACS continues
  serving business metadata + DICOMweb proxy. `store_instance()` untouched —
  double storage is acceptable at dev scale and idempotent via SOP-UID.
- **`services/dcm4chee_sync.py`**: QIDO-RS watermark poll → export REST →
  feed SCP, so studies stored while the feed was down self-heal.
  **Implemented 2026-08-16**: a daemon thread (`start_dcm4chee_sync()`, gated
  on `dicom_proxy=true`, `dcm4chee_sync_interval` default 30 s) scans the
  archive QIDO-RS (`GET /aets/{ae}/rs/studies?includefield=0020000D`, paged
  by `offset`/`limit`) and diffs against the QuantumPACS `studies` table —
  the QP table *is* the watermark, so no extra state table is needed.
  Studies the archive holds but QP does not know are re-exported via
  `POST /aets/{ae}/dimse/{ae}/studies/{uid}/export/dicom:{feedAE}?queue=true`
  (200/202 accepted); `store_instance()`'s SOP-UID dedup keeps re-exports
  idempotent. Deviations from the ADR text: the QIDO-RS "watermark" is
  realised as a full diff against the QP studies table (simpler than a
  persisted cursor and self-healing for arbitrarily old gaps); export REST
  returned 200 (not 202) on the live archive for queued exports, so both
  are accepted.
- **Export API**: `POST /aets/{aet}/dimse/{movescp}/studies/{study}/export/dicom:{destination}`
  (`?queue=true` → 202) — exact form verified in the Phase 1 spike (fallback:
  `POST .../rs/studies/{study}/export/{exporterID}`).
- **MWL**: dcm4chee serves modalities. QuantumPACS mirrors `worklist_entries`
  via MWL-RS (`POST /mwlitems` full-payload update, `POST .../status/{status}`
  with SCHEDULED → STARTED → COMPLETED mapping, cancel → `DELETE /mwlitems/{studyUID}/{spsID}`).
  **Implemented 2026-08-16** (`backend/api/mwl_sync.py`, `mwl_sync_interval`
  default 10 s, migration 060 adds `mwl_synced_at`/`mwl_sync_error`): a
  patient-first flow (`POST /aets/{ae}/rs/patients` upsert before
  `POST .../mwlitems` — the archive links MWL items to existing patients),
  a deterministic top-level StudyInstanceUID derived from the row so MWL-RS
  POST upserts instead of generating a fresh UID per push, and a status
  mapping of scheduled→SCHEDULED, in_progress→STARTED (dcm4chee has no
  "IN PROGRESS" value — the ADR's wording is realised as STARTED), and
  performed→COMPLETED. CANCELLED rows mirror as `DELETE /mwlitems/{uid}/{spsID}`.
- **DICOMweb proxy**: `backend/api/dicomweb.py` in proxy mode forwards
  QIDO-RS / WADO-RS / frames / WADO-URI to dcm4chee. The ZIP archive endpoint
  has no dcm4chee equivalent — QuantumPACS streams WADO-RS and zips itself.
  `/dicomweb/admin*` stays QuantumPACS-local (metrics reflect proxied traffic —
  documented limitation). STOW-RS forwarded to dcm4chee.
- **Tenancy**: QuantumPACS keeps per-tenant isolation in the application layer
  (files table, tenant scoping). dcm4chee operates as a shared archive; the
  AE→tenant map (`dicom_ae_tenant_map`) keeps gating where needed.

### Weasis integration

- **Launch**: backend `GET /api/weasis/launch?studyUID=...|patientID=...`
  authorizes against the `files` table (like `/dicomweb/admin*`), then 302s to
  `http://{arc-host}:8082/weasis-pacs-connector/weasis?studyUID={uid}&cdb`
  (`&cdb` required — client-only launch). Patient-level launch uses
  `patientID=` for the patient tab.
- **UI**: "Open in Weasis" buttons on StudyBrowser rows, the Detail page, and
  patient level; disabled when `weasis_enabled=false`.
- **Deployment**: `Dockerfile.arc` = `FROM dcm4che/dcm4chee-arc-psql:5.35.0` +
  `COPY weasis-pacs-connector.war /docker-entrypoint.d/deployments/` + config
  files `weasis-pacs-connector.properties` (WADO base URL `aets/DCM4CHEE/wado`,
  `transferSyntax=*`, `hosts.allow`) and `dicom-dcm4chee-arc.properties` into
  `standalone/configuration`.
- **Security**: dev uses `hosts.allow` + optional `encrypt.key`; production
  must add TLS at the edge and the connector's `access_token` `-secure` mode.
- **Desktop client is a requirement** (documented in README): the browser-only
  path stays on Cornerstone3D via the proxy.

### New config keys

`dcm4chee_url` (container DNS `http://dcm4chee-arc:8080/dcm4chee-arc`, dev
override `http://localhost:8082/dcm4chee-arc`), `dcm4chee_ae=DCM4CHEE`,
`dicom_proxy` (bool), `dicom_cstore_port=11113`, `weasis_enabled` (default
false), `weasis_launch_url` (default `http://localhost:8082/weasis-pacs-connector`).

### Rollout phases

1. **Phase 0 (this ADR)**: baseline inventory + ADR
2. **Phase 1**: parallel dcm4chee deployment (`docker/dcm4chee/` compose +
   `Dockerfile.arc` + `scripts/dev.sh` wiring). Gates: DICOM echo on 11112;
   connector launch page; export spike (store → export → feed → `files` row)
3. **Phase 2**: backfill (< 100 studies, `scripts/export_to_dcm4chee.py`).
   Gates: instance-count parity; Weasis 4.x desktop opens a backfilled study
4. **Phase 3**: transition (proxy, sync workers, MWL-RS, Weasis buttons).
   Gates: MWL parity, new-study end-to-end, ZIP, quota/routing via feed
5. **Phase 4**: cutover (`dicom_enabled=false`, 48–72 h soak; rollback = stop
   dcm4chee + `dicom_proxy=false` + repoint modalities)
6. **Phase 5**: decommission pynetdicom SCP/MWL/Q-R code paths (separate PRs)

## Consequences

### Positive

- Enterprise archive: C-MOVE, DICOM SR, proven retention/storage, standard
  DICOMweb conformance, Weasis out of the box
- `store_instance()` untouched → quota, routing, replicas, MWL auto-match,
  ES indexing, reports/exams continue to work with zero changes
- Rollback is trivial (proxy off, modalities repointed); both stores keep data
- Frontend Cornerstone path unchanged (proxy); dev/test scale makes backfill
  and double-storage costs negligible

### Negative

- Two stores during Phases 3–4 (dcm4chee + QuantumPACS files) — acceptable at
  dev scale, resolved at cutover
- Proxy-mode DELETE removes the study from the archive only; QP `files` rows
  persist, so QP-native surfaces can still list deleted studies until the
  archive and QP stores are reconciled at cutover
- Unsecured dcm4chee behind the proxy only; TLS + connector `access_token`
  required for production (tracked as follow-up)
- dcm4chee runs without its Elasticsearch integration (no cross-archive search)
- Multi-tenancy: dcm4chee is a shared archive; tenant isolation stays in the
  QuantumPACS layer (AE→tenant gating only where configured)
- Extra services to operate (LDAP + archive PG 17 + WildFly); 11112/8080/5432
  remapped to avoid clashes

### Risks

| # | Risk | Sev | Mitigation |
|---|---|---|---|
| R1 | Metadata split-brain | Crit | Option B feed SCP + parity gates |
| R2 | Backfill integrity | High | UID-level verification, resumeable script |
| R3 | Port conflicts (11112/8080/5432) | High | Remap: 11112 dcm4chee, 11113 feed, 8082 arc, 5433 archive PG |
| R4 | Frontend viewer breakage | High | `/dicomweb/*` proxy; zero frontend diff for Cornerstone |
| R5 | MWL rewiring | High | MWL-RS sync + C-FIND parity test |
| R6 | Store-path feature loss | Med-High | `store_instance()` untouched; retriggered via 11113 |
| R7 | Multi-tenancy limits (shared archive) | Med | Tenant isolation in QuantumPACS layer; per-tenant AEs for gating |
| R8 | Unsecured dcm4chee exposure | Med | 127.0.0.1 bindings, internal-only, proxy-mediated |
| R9 | pynetdicom decommission blast radius | Med | Feature-flag disable first, code removal later |
| R10 | ES sharing | Low | dcm4chee runs without its ES integration |
| R11 | PG major mismatch (17 vs 18) | Low | Separate archive PG 17 container |
| R12 | Weasis native client install | Low | Documented requirement; Cornerstone remains for browser-only |
| R13 | Connector/WADO PHI egress surface | Med | `hosts.allow`, `encrypt.key`, TLS at edge, `-secure` later |
| R14 | SourceForge artifact drift | Low | Vendored war + SHA256 pin |
| R15 | Version pairing (connector↔arc↔client) | Low | Pinned matrix above; Phase 1/2 gates |

## References

- ADR-011 (DICOM MWL SCP), ADR-018 (DICOMweb API) — surface being replaced
- ADR-007 (multi-tier storage), ADR-016 (DB-per-tenant multi-tenancy) — invariants preserved
- dcm4chee 5.35.0 official docker-compose (docker/dcm4chee/), weasis-pacs-connector 8.0.0 (SourceForge)
- DICOM PS3.18 (DICOMweb), PS3.4 (DIMSE C-STORE/C-FIND/C-MOVE)
