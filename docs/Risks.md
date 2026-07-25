# QuantumPACS — Risk Register

**Version**: 2.0.0
**Status**: Final
**Date**: 2026-07-23

---

## 1. Risk Scoring Methodology

| Rating | Likelihood | Impact |
|--------|------------|--------|
| **1** | Rare (> 5 years) | Negligible (no user impact) |
| **2** | Unlikely (2–5 years) | Minor (single user inconvenience) |
| **3** | Possible (1–2 years) | Moderate (workflow disruption) |
| **4** | Likely (6–12 months) | Major (department-wide outage) |
| **5** | Almost certain (< 6 months) | Critical (data loss / compliance breach) |

**Risk Score** = Likelihood × Impact

| Score Range | Rating | Action |
|-------------|--------|--------|
| 1–6 | Low | Monitor, accept |
| 7–12 | Medium | Mitigate, document |
| 13–19 | High | Active mitigation plan |
| 20–25 | Critical | Immediate action required |

---

## 2. Risk Register

### 2.1 Technical Risks

| ID | Risk | Description | L | I | Score | Mitigation | Owner |
|----|------|-------------|---|---|-------|------------|-------|
| **T-01** | Elasticsearch unavailable | ES connection fails at startup or mid-operation. Search degrades to empty results. | 4 | 3 | **12** | Graceful degradation (`get_client() → None`); PostgreSQL text search fallback planned for v2.1 | Backend |
| **T-02** | PostgreSQL connection pool exhaustion | Spike in concurrent requests exhausts pool of 8 connections. New requests hang or fail. | 3 | 4 | **12** | Pool size configurable; add connection monitoring; implement connection timeout; query optimization | Backend |
| **T-03** | DICOM listener port conflict | Port 11112 already in use by another DICOM application (e.g., Orthanc, dcm4chee). | 3 | 3 | **9** | Configurable port in config.yaml; documented port requirements; installer checks port availability | DevOps |
| **T-04** | Storage backend S3/B2 latency spike | Cloud storage latency increases due to network issues or throttling, causing slow file serving. | 3 | 3 | **9** | Async replication; local master + cloud replica topology; configurable timeout per backend | Backend |
| **T-05** | Large study memory pressure | Viewer loading 10,000+ CT instances exceeds browser memory (target > 2 GB). | 3 | 3 | **9** | Progressive loading; volume streaming; instance count warning in UI beyond 1000 | Frontend |
| **T-06** | Sync daemon single point of failure | Single sync daemon process dies → replication stops until restarted. | 4 | 3 | **12** | systemd auto-restart; multiple sync workers planned for v2.2; health check endpoint for monitoring | DevOps |
| **T-07** | Concurrent write conflicts on tools_state | Two users simultaneously save annotations on the same file → last-write-wins loses one user's data. | 4 | 2 | **8** | WebSocket sync provides near-real-time merge; version counter on tools_state; PATCH partial updates. UI guidance: "Collaborative editing — your changes are synced." | Backend |
| **T-08** | JWT secret key compromised | Attacker gains access to the JWT signing secret and can forge tokens with arbitrary user IDs. | 2 | 5 | **10** | Rotate secret on deployment; document rotation procedure; short token expiry (14d); deactivated user check on every request | Security |
| **T-09** | File hash collision (SHA-256) | Two different DICOM files produce the same SHA-256 hash → second file incorrectly treated as duplicate. | 1 | 4 | **4** | SHA-256 collision probability is negligible. Accept risk. | Backend |
| **T-10** | Elasticsearch index corruption | ES index becomes corrupted due to hardware failure or bug → search returns garbage or empty. | 2 | 3 | **6** | `es_reindex.py` script to rebuild index from DB; documented recovery procedure | DevOps |

### 2.2 Security Risks

| ID | Risk | Description | L | I | Score | Mitigation | Owner |
|----|------|-------------|---|---|-------|------------|-------|
| **S-01** | CORS wide-open in production | `Access-Control-Allow-Origin: *` allows any website to read API responses if user is logged in. | 4 | 4 | **16** | **HIGH** — Configurable CORS origin whitelist planned for v2.1; for now, rely on X-Auth-Pacs custom header (not sent by browser on cross-origin requests automatically). Document in production checklist. | Security |
| **S-02** | Share link interception | Share link transmitted over unencrypted channel (email, SMS) intercepted and used before expiry. | 3 | 3 | **9** | TLS required in production; share links include target path verification (only valid for the specific file); configurable short expiry; access logged in audit trail | Security |
| **S-03** | Brute-force password attack | Attacker attempts many passwords against `/api/login` to crack credentials. | 4 | 3 | **12** | **Medium** — PBKDF2 with 600k iterations slows attacks (~10 attempts/sec); rate limiting and lockout planned for v2.1; no user enumeration in error messages | Security |
| **S-04** | Path traversal in LocalStorage | Carefully crafted file names could escape the storage directory via `..` sequences. | 2 | 5 | **10** | Mitigated: `os.path.basename(os.path.normpath(part))` strips directory components from all path segments | Backend |
| **S-05** | PHI in server logs | Debug logging might include DICOM metadata containing PHI (patient name, ID). | 3 | 4 | **12** | Log only non-PHI identifiers; sanitize log messages in production; DICOM metadata logged at DEBUG level only, disabled by default | Backend |
| **S-06** | Session fixation via temp key | An attacker crafts a URL with `?key=` pointing to their share, and a victim opens it → victim's session gets the attacker's temp key. | 2 | 2 | **4** | Low risk — temp key only allows viewing the specific shared file; no write access. No persistent state is compromised. | Security |
| **S-07** | Deactivated user with valid JWT | User is deactivated but their JWT token is still valid for up to 14 days. | 3 | 3 | **9** | Mitigated: `Users.is_active()` check on every authenticated request, not just at login | Backend |
| **S-08** | DICOM listener as attack vector | pynetdicom/pydicom parsing vulnerability allows remote code execution via malformed DICOM. | 2 | 5 | **10** | Run DICOM listener in same process as API (not sandboxed); keep pynetdicom/pydicom up to date; monitor CVEs; fuzz testing planned for v2.1 | Security |

### 2.3 Operational Risks

| ID | Risk | Description | L | I | Score | Mitigation | Owner |
|----|------|-------------|---|---|-------|------------|-------|
| **O-01** | Database connection failure | PostgreSQL goes down or network partition occurs → API cannot serve any requests. | 3 | 5 | **15** | **HIGH** — Connection pool retries on startup (30 attempts, 1s interval); monitoring alert on pool health; DB connection timeout; consider read-replica for failover | DevOps |
| **O-02** | Storage disk full (local backend) | Local storage filesystem reaches 100% capacity → new uploads fail, existing files unreadable. | 3 | 4 | **12** | Configurable disk usage alert threshold; tiered storage (local → cloud) reduces local growth; document capacity planning formula | DevOps |
| **O-03** | Docker container resource exhaustion | Container runs out of memory or file descriptors under load → OOM kill of API or sync daemon. | 3 | 4 | **12** | Docker memory limits; health checks (Caddy → API → DB); systemd auto-restart; monitoring | DevOps |
| **O-04** | Upgrade causes schema migration failure | Alembic migration fails partway through → DB in inconsistent state → manual recovery required. | 3 | 4 | **12** | Test migrations against copy of production data; always run migrations in a transaction; document rollback procedure; maintain DB backup before upgrade | DevOps |
| **O-05** | Backup failure | Automated backup fails silently → no recoverable backup exists when needed. | 3 | 5 | **15** | **HIGH** — Backup verification after each run; separate backup monitoring; documented restore procedure with periodic drill | DevOps |
| **O-06** | TLS certificate expiry | Caddy's HTTPS certificate expires → all web/API traffic fails with certificate error. | 3 | 3 | **9** | Automated renewal via Let's Encrypt; monitoring for cert expiry (alert at 30, 14, 7, 1 day); documented manual renewal procedure | DevOps |
| **O-07** | Slow query degradation under load | Unoptimized database query slows as study count grows → API latency increases for all users. | 4 | 3 | **12** | ES handles primary search (fast); SQL queries have LIMIT/OFFSET and indexed WHERE clauses; monitoring on query latency; query plan review before each release | Backend |
| **O-08** | Modality sends duplicate studies | Modality configured to send all studies repeatedly (e.g., misconfigured auto-retry) → storage and DB bloat. | 3 | 2 | **6** | SHA-256 deduplication prevents duplicate file storage; insert_or_select prevents duplicate DB records. Monitor for high dedup rate as alert trigger | Backend |

### 2.4 Regulatory & Compliance Risks

| ID | Risk | Description | L | I | Score | Mitigation | Owner |
|----|------|-------------|---|---|-------|------------|-------|
| **R-01** | HIPAA compliance gaps | Missing required safeguards: no BAAs, no audit controls for access, no encryption at rest documentation. | 2 | 5 | **10** | HIPAA compliance skill engaged; document all controls in compliance matrix; BAAs with cloud providers; encryption-at-rest documentation; access audit trail review | Compliance |
| **R-02** | DICOM conformance deviations | QuantumPACS deviates from DICOM standard in a way that causes modality compatibility issues. | 3 | 3 | **9** | pynetdicom provides standards-compliant SCP; DICOM conformance statement document built; test with multiple modality vendors | Backend |
| **R-03** | PHI data residency violation | Cloud storage backend stores PHI in a geographic region not compliant with local regulations (GDPR, HIPAA). | 2 | 5 | **10** | Document storage region configuration per backend; S3/B2 region selection in replica config; on-premises storage option (local backend) | Compliance |
| **R-04** | Audit log inadequacy for legal discovery | Change logs lack sufficient detail (e.g., who viewed which study, not just who changed it). | 3 | 3 | **9** | Current audit covers writes (changes, deletes, shares); read-access logging planned for v2.1; log retention policy documentation | Compliance |

### 2.5 Deployment Risks

| ID | Risk | Description | L | I | Score | Mitigation | Owner |
|----|------|-------------|---|---|-------|------------|-------|
| **D-01** | Modality cannot connect to DICOM listener | Hospital network firewall blocks port 11112 between modality subnet and PACS server. | 4 | 4 | **16** | **HIGH** — Document port requirements in deployment guide; provide IT with network configuration checklist; support for TLS-wrapped DICOM (DICOM TLS) planned for v2.1 | DevOps |
| **D-02** | Incorrect storage configuration | Administrator misconfigures S3/B2 credentials or path → files stored but inaccessible. | 3 | 3 | **9** | Storage configuration validation on save; test write on init; replica status dashboard shows errors; recovery procedure: correct config → re-index | DevOps |
| **D-03** | Timezone misconfiguration | Server timezone not set to UTC → log timestamps, share link expiration, and token expiry calculations are inconsistent. | 3 | 2 | **6** | Document that server must use UTC; Docker base image defaults to UTC; log timestamps explicitly in UTC format | DevOps |
| **D-04** | Insufficient ulimit for DICOM listener | System file descriptor limit too low → DICOM listener cannot accept new modality connections under load. | 2 | 3 | **6** | Document ulimit recommendation (65535) in deployment guide; systemd service file includes LimitNOFILE=65536 | DevOps |

---

## 3. Risk Matrix (Heat Map)

```
Likelihood
   5 ──── ──── ──── ──── ────
        │    │    │    │ T-01 │
        │    │    │ S-1│ S-07 │
   4    │    │    │ D-1│ O-01 │
        │    │    │ O-07│O-05 │
        │    │    │    │ S-03 │
   3 ────┼────┼────┼────┼────
        │    │T-02│T-06│O-02 │
        │    │T-03│R-01│O-03 │
        │    │R-04│R-02│O-04 │
        │    │    │D-02│R-03 │
   2 ────┼────┼────┼────┼────
        │T-10│T-08│S-02│S-04 │
        │    │    │S-08│S-05 │
        │    │    │    │     │
   1 ────┼────┼────┼────┼────
        │T-09│S-06│    │     │
        │    │    │    │     │
        │    │    │    │     │
        └──────────────────────
           1    2    3    4    5
                    Impact
```

**Zone Legend**:
- Green (1–6): Accept / Monitor
- Yellow (7–12): Mitigate / Document
- Red (13–19): Active mitigation required
- Purple (20–25): Immediate action

---

## 4. Top 5 Critical Risks

| Rank | ID | Risk | Score | Status | Mitigation Lead |
|------|----|------|-------|--------|-----------------|
| 1 | **S-01** | CORS wide-open in production | **16** | Active — v2.1 will add configurable origin whitelist | Security |
| 2 | **D-01** | Modality cannot connect to DICOM listener | **16** | Mitigated — documented in deployment guide. Future: DICOM TLS | DevOps |
| 3 | **O-01** | Database connection failure | **15** | Mitigated — retry logic, documented recovery | DevOps |
| 4 | **O-05** | Backup failure | **15** | Active — automated backup planned for v2.2 | DevOps |
| 5 | **T-01** | Elasticsearch unavailable | **12** | Mitigated — graceful degradation | Backend |

---

## 5. Risk Response Plans

### RRP-01: CORS Wide-Open (S-01)

**Trigger**: Production deployment without CORS configuration.

**Response**:
1. Immediate: Add `Access-Control-Allow-Origin: <deployment-host>` to production config
2. Short-term (v2.1): Implement configurable CORS origin whitelist with environment variable
3. Long-term: Document in production checklist; add CI check that warns if CORS is `*`

**Verification**: OWASP ZAP scan shows no CORS vulnerability.

### RRP-02: Database Connection Failure (O-01)

**Trigger**: API health check returns 500 due to database connection error.

**Response**:
1. Check PostgreSQL is running: `systemctl status postgresql` / `docker ps`
2. Check network connectivity: `pg_isready -h <host> -p <port>`
3. Check pool exhaustion: `SELECT count(*) FROM pg_stat_activity WHERE state = 'active';`
4. If pool exhausted: `SELECT pg_terminate_backend(pid)` for idle transactions
5. If DB down: restore from latest backup (see DRP-01)

**Prevention**:
- Pool monitoring alert (threshold: 80% utilization)
- Connection timeout (30s) to prevent hung requests
- Read-replica for query load (planned v2.2)

### RRP-03: Backup & Disaster Recovery (O-05)

**Trigger**: Data loss event or corruption requiring restoration.

**Recovery Procedure**:
```
1. Stop API, sync, and DICOM services
2. Restore PostgreSQL:
   ./manage db restore --file /backup/2026-07-22.sql

3. Restore file storage:
   rsync -av /backup/storage/ /path/to/master/storage/

4. Re-index Elasticsearch:
   python es_reindex.py

5. Verify data integrity:
   SELECT count(*) FROM files WHERE deleted = FALSE;
   SELECT count(*) FROM patients;

6. Start services:
   scripts/dev.sh start
```

**Prevention**:
- Daily automated backup (cron/systemd timer)
- Backup to separate storage (S3 bucket)
- Monthly restore drill

### RRP-04: Security Incident Response

**Trigger**: Suspected unauthorized access or PHI breach.

**Response**:
1. Isolate: Stop API, revoke all JWT tokens (restart service with new secret)
2. Investigate: Search audit logs (`file_changes`, `logs`) for suspicious activity
3. Notify: Follow HIPAA breach notification procedures (60-day window)
4. Remediate: Patch vulnerability, rotate credentials, document incident

**Prevention**:
- JWT secret rotation on each deployment
- Audit log retention ≥ 6 years (HIPAA requirement)
- Failed login attempt monitoring

---

## 6. Monitoring & Alerting (Planned v2.1)

| Metric | Threshold | Action | Risk Triggered |
|--------|-----------|--------|----------------|
| API p95 latency | > 500ms | Alert on-call | O-07 |
| DB connection pool % | > 80% | Alert, auto-scale pool | T-02 |
| ES cluster health | Not green | Alert | T-01, T-10 |
| DICOM listener uptime | Down | Auto-restart via systemd | T-03 |
| Storage disk usage | > 85% | Alert, archive old studies | O-02 |
| Replica sync lag | > 30 min | Alert | T-04 |
| Failed login attempts/min | > 10 | Alert (possible brute force) | S-03 |
| Backup status | Failed | Alert on-call | O-05 |
| Certificate expiry | < 30 days | Alert | O-06 |

---

## 7. Assumptions & Constraints

| ID | Assumption/Constraint | Impact if False |
|----|-----------------------|-----------------|
| A-01 | Network between services has < 5ms latency | Higher latency will cause API timeouts and poor viewer experience |
| A-02 | PostgreSQL is deployed on dedicated or adequately provisioned hardware | Under-resourced DB will become bottleneck under load |
| A-03 | Modalities send valid DICOM conforming to standard | Non-conformant DICOM will be rejected or produce incorrect metadata |
| A-04 | Hospital IT manages TLS termination at the load balancer | Without TLS, PHI transmitted in cleartext over network |
| A-05 | Elasticsearch is optional and can be absent | Search degrades to empty results but no data loss |
| A-06 | JWT secret is rotated regularly | Stale secret increases risk of token forgery |
| A-07 | Only one master storage backend at a time | Concurrent masters would cause split-brain replication conflicts |
| A-08 | Storage backends are trusted (no client-side encryption) | Cloud storage provider could access PHI; BAA required |

---

## 8. v3.0 Risk Register (Addition)

**Version**: 3.0.0-draft
**Date**: 2026-07-25
**Source**: PRD-v3.md §4.2, IMPLEMENTATION_PLAN-v3.md §Risk Register

### Scoring (Same as §1)

### 8.1 Infrastructure & Architecture Risks

| ID | Risk | L | I | Score | Mitigation | Owner |
|----|------|---|----|----|-----------|-------|
| v3-I-01 | DB-per-tenant connection pool memory exhaustion at scale (50+ tenants) | 3 | 4 | 12 | Idle pool eviction after 5 min TTL; max pools configurable; per-pool cap at 8 connections | Backend |
| v3-I-02 | Redis Streams consumer lag during ingestion burst (150 MB/s C-STORE) | 3 | 3 | 9 | Monitor consumer group lag via Prometheus; auto-scale consumers by lag threshold; maxlen=100k | Backend |
| v3-I-03 | Single Redis node becomes bottleneck under v3 load | 2 | 3 | 6 | Redis cluster mode available if needed; streams are not sharded in OSS Redis | DevOps |
| v3-I-04 | Modular monolith cannot scale beyond 200 concurrent viewers | 2 | 3 | 6 | Extraction path per ADR-014; each module can become independent service | Backend |
| v3-I-05 | Performance regression from OpenTelemetry tracing overhead | 2 | 2 | 4 | Configurable sampling rate (0.1 prod, 1.0 staging); console exporter in dev | Backend |

### 8.2 Auth & Security Risks

| ID | Risk | L | I | Score | Mitigation | Owner |
|----|------|---|----|----|-----------|-------|
| v3-S-01 | OAuth/OIDC integration failure with hospital IdP | 4 | 4 | 16 | Test against Azure AD, Okta, Keycloak before GA; support multiple OAuth libraries; local JWT fallback | Backend |
| v3-S-02 | RBAC permission misconfiguration leads to unintended access | 3 | 4 | 12 | Default roles reviewed by radiology domain expert; permission audit log; property-based fuzz tests | Backend |
| v3-S-03 | JIT provisioning creates accounts with wrong role from IdP groups claim | 2 | 3 | 6 | Audit log all JIT creations; super-admin approval mode available (disabled by default) | Backend |
| v3-S-04 | Cross-tenant data leak due to connection routing bug | 2 | 5 | 10 | Property-based fuzz test with 1000 iterations per CI run; database-per-tenant provides DB-level isolation | Backend |
| v3-S-05 | Token revocation race — blocked token used before Redis blocklist entry propagates | 2 | 3 | 6 | Blocklist TTL = token expiry; worst case: token valid for remaining TTL (max 1 hour) | Backend |

### 8.3 Integration & Interoperability Risks

| ID | Risk | L | I | Score | Mitigation | Owner |
|----|------|---|----|----|-----------|-------|
| v3-I20-01 | HL7 MLLP message parsing errors with non-standard HL7 variants | 4 | 2 | 8 | Log and skip unknown segments; fuzz testing with real HL7 samples from 3+ hospital systems | DICOM/HL7 |
| v3-I20-02 | DICOMweb QIDO-RS performance degradation with large result sets (100k+ studies) | 3 | 3 | 9 | Pagination enforced (max 1000); keyset pagination for deep offsets; ES-backed query | Backend |
| v3-I20-03 | DICOMweb spec interpretation differs from IHE expectations | 3 | 4 | 12 | Self-certification test suite runs in CI; external Connectathon before GA | DICOM/HL7 |
| v3-I20-04 | FHIR resource mapping complexity exceeds estimate | 3 | 3 | 9 | Ship Patient + ImagingStudy only; DocumentReference + DiagnosticReport deferred to v3.1 | Backend |
| v3-I20-05 | STOW-RS multipart parsing fails for large payloads (>1 GB) | 2 | 3 | 6 | Stream multipart parser; test with 2 GB synthetic study before GA | Backend |

### 8.4 Frontend Risks

| ID | Risk | L | I | Score | Mitigation | Owner |
|----|------|---|----|----|-----------|-------|
| v3-F-01 | Mobile-responsive viewer performance poor on low-end tablets | 3 | 3 | 9 | Progressive image loading (thumbnail → full-res); reduced bandwidth mode for mobile | Frontend |
| v3-F-02 | Frontend v3 scope exceeds team capacity | 4 | 3 | 12 | Feature flags for mobile viewer and metrics dashboard; defer lower-priority UI to v3.1 | Frontend |
| v3-F-03 | OAuth login flow UX confusion (users don't know to click SSO button) | 2 | 2 | 4 | Clear labeling; demo video in release notes; smooth fallback to local JWT | Frontend |
| v3-F-04 | PWA service worker cache serves stale study data | 2 | 3 | 6 | Cache-first for static assets, network-first for study data; cache invalidation on new version | Frontend |

### 8.5 Migration & Deployment Risks

| ID | Risk | L | I | Score | Mitigation | Owner |
|----|------|---|----|----|-----------|-------|
| v3-M-01 | Phase 0 (hardening) schedule slips, delaying v3 timeline | 3 | 4 | 12 | Hardening runs in parallel with v3 planning and ADR authoring; hardening is hard gate at Phase 2 | Backend |
| v3-M-02 | Multi-tenant Alembic migration conflicts on per-tenant DBs | 3 | 5 | 15 | Run migrations per-tenant sequentially; migration test suite iterates over all tenant DBs; rollback plan per ADR-016 | Backend |
| v3-M-03 | v2→v3 upgrade for existing single-tenant deployments is disruptive | 3 | 3 | 9 | v2 instances become one tenant in v3; documented migration script; v1 API continues to work | DevOps |
| v3-M-04 | API v1→v2 migration confuses existing integrations | 2 | 3 | 6 | Deprecation headers with 12+ month sunset; documented upgrade guide per ADR §8.3 | Backend/DevOps |
| v3-M-05 | Team context-switching across 8 phases reduces velocity | 4 | 3 | 12 | Parallel tracks with dedicated sub-branches; one phase owner per track | Engineering Manager |

### 8.6 Top 5 Critical Risks (Score ≥ 12)

| Rank | ID | Risk | Score | Action |
|------|----|------|-------|--------|
| 1 | v3-S-01 | OAuth/OIDC integration failure with hospital IdP | 16 | Test against 3+ IdPs before GA; maintain local JWT fallback |
| 2 | v3-M-02 | Multi-tenant Alembic migration conflicts | 15 | Sequential per-tenant migrations; rollback plan; CI test on N tenant DBs |
| 3 | v3-I-01 | DB-per-tenant pool memory exhaustion | 12 | Idle eviction; max pools cap; per-pool connection limit |
| 4 | v3-S-02 | RBAC permission misconfiguration | 12 | Role review process; audit log for permission changes; fuzz testing |
| 5 | v3-I20-03 | DICOMweb conformance gaps | 12 | Self-certification CI; IHE Connectathon before GA |

### 8.7 Monitoring & Alerting — v3 Additions

Refer to `docs/PRD-v3.md` §6 (Success Evaluation) and ADR-020 (Observability Stack) for the full v3 monitoring plan. Key additions:

| Metric | Source | Threshold | Action |
|--------|--------|-----------|--------|
| Redis consumer group lag | Prometheus (stream lag gauge) | > 1000 | Alert, investigate consumer health |
| DB pool utilization per tenant | Prometheus (per-tenant gauge) | > 80% | Alert, consider larger pool or connection leak |
| OAuth login failure rate | Prometheus (login counter) | > 10% in 5 min | Alert, IdP may be down or misconfigured |
| DICOMweb endpoint latency p99 | Prometheus (histogram) | > 1s | Alert, investigate query or storage bottleneck |
| Tenant provisioning time | CI integration test | > 60s | Investigate DB creation or migration performance |

### 8.8 Assumptions & Constraints (v3 Specific)

| ID | Assumption/Constraint | Impact if False |
|----|-----------------------|-----------------|
| v3-A-01 | Redis is available and performs within latency budget (< 1ms p99) | Without Redis, streams fall back to no-queue (direct PG writes); auth cache falls back to DB query per request |
| v3-A-02 | Target tenant count ≤ 50 per deployment | Beyond 50, DB-per-tenant operational cost (N pools, N backups, N migrations) may exceed ops capacity |
| v3-A-03 | Hospital IT can provision a PostgreSQL database per tenant | Without PG automation, tenant provisioning is manual and slow |
| v3-A-04 | External RIS/EHR applications support HL7 v2.5.1 or FHIR R4 | Legacy systems may require HL7 v2.3 or custom Z-segments; documented in integration guide |
| v3-A-05 | OIDC IdP is accessible from the deployment network | Air-gapped deployments cannot use OAuth/OIDC; local JWT remains available |
| v3-A-06 | DICOMweb clients support multipart/related with application/dicom | Legacy clients may require WADO-URI (implemented); pure DICOMweb clients are the target |
