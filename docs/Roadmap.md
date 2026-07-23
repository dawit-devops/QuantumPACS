# QuantumPACS — Product Roadmap

**Version**: 2.0.0
**Status**: Final
**Date**: 2026-07-23

---

## 1. Release Strategy

QuantumPACS follows a **time-based release cadence** with **semantic versioning**:

| Version | Cadence | Scope |
|---------|---------|-------|
| v2.0.x | Monthly | Patch releases: bug fixes, security updates, minor enhancements |
| v2.1.x | Quarterly | Feature releases: new capabilities, workflow improvements |
| v2.2.x | Quarterly | Feature releases: integration, scalability |
| v3.0 | Annual | Major architecture evolution |

Each release includes:
- Updated CHANGELOG.md
- Alembic migration scripts for schema changes
- Updated Docker image tags (`quantumpacs:v2.1.0`, `quantumpacs:latest`)
- Release notes with upgrade instructions

---

## 2. Current State (v2.0.0 — Delivered July 2026)

### Capabilities

| Area | Status | Detail |
|------|--------|--------|
| DICOM C-STORE SCP | ✅ | All storage SOP classes, port 11112 |
| Study search | ✅ | Elasticsearch full-text, field filters, advanced modal |
| Zero-footprint viewer | ✅ | Cornerstone3D, 10 tools, annotations, WebSocket sync |
| Patient browser | ✅ | Study/series/file tree navigation |
| Pluggable storage | ✅ | Local, S3, B2 with async replication |
| Auth & user management | ✅ | JWT, PBKDF2, admin roles, user lifecycle |
| Share links | ✅ | Expiring HMAC-authenticated URLs |
| Audit logging | ✅ | File changes, system logs |
| Admin panel | ✅ | Users, replicas, logs |
| Docker deployment | ✅ | Single image with Caddy reverse proxy |
| CI/CD | ✅ | GitHub Actions: lint, test, build, publish |
| Architecture decisions | ✅ | 10 ADRs covering all major decisions |

### Known Gaps

| Gap | Impact | Addressed In |
|-----|--------|-------------|
| No DICOM MWL SCP | Modalities cannot query worklist | v2.1 |
| No HL7/FHIR | No EHR/RIS integration | v2.1 (HL7) / v2.2 (FHIR) |
| No OAuth/SSO | No enterprise identity provider support | v2.2 |
| No multi-tenancy | Single-organization only | v2.2 |
| No DICOMweb API | Not DICOM JSON compliant | v3.0 |
| No C-MOVE/C-GET | Can't query other PACS | v3.0 |
| No AI/ML pipeline | No CAD integration | v2.2 |
| No structured reports | No SR viewer/editor | v2.2 |
| Mobile UX not optimized | Poor experience on tablets/phones | v3.0 |

---

## 3. v2.1 — Integration & Hardening (Q3 2026)

**Theme**: Connect the PACS to the hospital ecosystem.

**Target**: September 2026

### Features

#### F1: DICOM Modality Worklist (MWL) SCP
**Priority**: P1 | **Effort**: 3 weeks | **Dependency**: None

- Implement DICOM MWL SCP (`C-FIND` support) on port 11112
- Allow modalities to query scheduled procedures
- Web UI for building and managing worklist entries
- Worklist entries linked to patient records

**Acceptance**: Modality can query worklist by date/patient and retrieve scheduled procedure steps.

#### F2: DICOM Print Management SCP
**Priority**: P2 | **Effort**: 2 weeks | **Dependency**: None

- Implement DICOM Basic Print Management SCP
- Support for hardcopy grayscale and color
- Configurable print destinations (DICOM printers on network)

**Acceptance**: Modality can send images to a DICOM printer through QuantumPACS.

#### F3: HL7 v2.x ADT/ORM Ingestion
**Priority**: P1 | **Effort**: 4 weeks | **Dependency**: None

- MLLP listener for HL7 v2.x messages (ADT-A01, ADT-A04, ORM-O01)
- Parse patient demographics, order information
- Auto-create or update patient/study records on ADT messages
- Map HL7 fields to DICOM tags for pre-populated worklist entries
- TLS support for MLLP

**Acceptance**: HL7 ADT messages create/update patient records; ORM messages create worklist entries.

#### F4: Study Routing Rules
**Priority**: P2 | **Effort**: 2 weeks | **Dependency**: HL7 (for modality-based routing)

- Configurable rules: `IF modality=CT AND study_description CONTAINS "CHEST" THEN route_to=replica_2`
- Rule engine evaluated on file ingestion
- Web UI for rule CRUD
- Rule ordering and conflict detection

**Acceptance**: Incoming studies are automatically copied to target replica based on configurable rules.

#### F5: Production Security Hardening
**Priority**: P1 | **Effort**: 2 weeks | **Dependency**: None

- CORS origin whitelist (configurable, default lock to same-origin)
- Rate limiting middleware (token bucket per IP)
- Brute-force protection on `/api/login` (5 attempts → 5-min lockout)
- Security headers: HSTS, CSP, X-Frame-Options, X-Content-Type-Options
- TLS configuration documentation
- Secrets management documentation (env vars, not config files)

**Acceptance**: Passes OWASP ZAP baseline scan with 0 high-risk findings.

#### F6: Prometheus Metrics
**Priority**: P2 | **Effort**: 1 week | **Dependency**: None

- `/api/metrics` endpoint with Prometheus text format
- Metrics: request count, latency (p50/p95/p99), active viewers, storage usage, DICOM throughput
- Grafana dashboard template

**Acceptance**: Metrics endpoint returns valid Prometheus-format data; Grafana dashboard displays key PACS metrics.

#### F7: UI Polish
**Priority**: P2 | **Effort**: 2 weeks | **Dependency**: None

- Delete confirmation dialog (Popconfirm)
- WebSocket reconnect with exponential backoff
- Cornerstone3D initialization fix (remove `window.ctinit` global hack)
- Remove unused `history.ts`
- Make `editableFields` configurable via admin panel
- Tooltip descriptions on all viewer toolbar buttons
- Keyboard shortcuts reference (`?` key → modal)

**Acceptance**: All UI debt items from the known-technical-debt list resolved.

### v2.1 Release Summary

| Feature | Type | Effort | Risk | Dependencies |
|---------|------|--------|------|-------------|
| DICOM MWL SCP | New | 3w | Medium | pynetdicom expertise |
| DICOM Print SCP | New | 2w | Low | pynetdicom expertise |
| HL7 ADT/ORM | New | 4w | High | HL7 parsing library, MLLP |
| Study routing | New | 2w | Low | Replica system (exists) |
| Security hardening | Improvement | 2w | Low | Config system |
| Prometheus metrics | New | 1w | Low | Starlette middleware |
| UI polish | Improvement | 2w | Low | — |
| **Total** | | **~16w** | | |

---

## 4. v2.2 — Enterprise Scale (Q1 2027)

**Theme**: Scale from single-department to enterprise-wide.

**Target**: January 2027

### Features

#### F8: FHIR R4 API
**Priority**: P1 | **Effort**: 6 weeks | **Dependency**: None

- FHIR R4 resources: `Patient`, `ImagingStudy`, `DocumentReference`, `Endpoint`
- `GET`, `POST`, `PUT` for supported resources
- `_search` parameters for patient ID, accession, modality, date range
- SMART-on-FHIR backend services auth
- FHIR JSON + XML support
- OpenAPI / FHIR CapabilityStatement

**Acceptance**: External EHR systems can query and retrieve imaging study metadata via FHIR R4.

#### F9: Multi-Tenancy
**Priority**: P1 | **Effort**: 8 weeks | **Dependency**: None

- Tenant isolation (schema-per-tenant or shared-schema with tenant_id column)
- Tenant-aware middleware (extract tenant from subdomain or header)
- Per-tenant configuration (storage backends, auth providers, routing rules)
- Super-admin dashboard for tenant management
- Tenant provisioning API (create tenant, configure storage, create admin user)
- Migration tool for single-tenant → multi-tenant

**Acceptance**: Two independent organizations can share one QuantumPACS deployment with full data isolation.

#### F10: OAuth 2.0 / OpenID Connect SSO
**Priority**: P1 | **Effort**: 4 weeks | **Dependency**: Multi-tenancy (for per-tenant IdP)

- OAuth 2.0 authorization code flow
- OpenID Connect identity provider integration (Azure AD, Okta, Keycloak)
- Configurable per-tenant IdP
- Automatic user provisioning on first login (JIT)
- Token exchange: OAuth access token → QuantumPACS JWT

**Acceptance**: Users can log in with their corporate Azure AD/Okta credentials without creating QuantumPACS-specific accounts.

#### F11: AI/ML Inference Pipeline
**Priority**: P2 | **Effort**: 6 weeks | **Dependency**: None

- DICOM SEG export: convert annotations to DICOM Segmentation objects
- Inference trigger: webhook on file ingestion → external ML service
- ML result ingestion: parse DICOM SEG/SR results → display as overlays in viewer
- Configurable inference endpoints per modality
- Inference result caching and versioning

**Acceptance**: External AI service receives incoming study → returns DICOM SEG → overlay displayed in Cornerstone3D.

#### F12: Structured Report (SR) Viewer & Editor
**Priority**: P2 | **Effort**: 4 weeks | **Dependency**: None

- DICOM SR viewer (TID 1500 mammography CAD, TID 2000 basic diagnostic)
- SR tree renderer with coded entry display
- Basic SR editor (template-based)
- SR export to PDF
- SR search in study list

**Acceptance**: Radiologist can view and edit structured reports in the browser.

#### F13: Automated Backup & Restore
**Priority**: P2 | **Effort**: 2 weeks | **Dependency**: None

- `./manage db backup` — PostgreSQL dump + file store snapshot
- `./manage db restore` — restore from backup
- Configurable backup schedule (cron-based via systemd timer)
- S3-compatible backup destination
- Backup integrity verification (checksum)

**Acceptance**: Administrator can backup and restore the full system state (DB + files) with a single command.

### v2.2 Release Summary

| Feature | Type | Effort | Risk | Dependencies |
|---------|------|--------|------|-------------|
| FHIR R4 API | New | 6w | High | FHIR specification complexity |
| Multi-tenancy | New | 8w | Very High | Architecture-wide impact |
| OAuth 2.0 / OIDC | New | 4w | Medium | Multi-tenancy |
| AI inference pipeline | New | 6w | High | ML service external |
| SR viewer/editor | New | 4w | Medium | Medical terminology |
| Backup & restore | New | 2w | Low | — |
| **Total** | | **~30w** | | |

---

## 5. v3.0 — Next-Generation Architecture (Q3 2027)

**Theme**: Evolve from monolith to composable platform.

**Target**: July 2027

### Features

#### F14: Microservices Decomposition
**Priority**: P1 | **Effort**: 16 weeks | **Dependency**: Multi-tenancy

Decompose monolith into services:

| Service | Responsibility | Language | Communication |
|---------|---------------|-----------|---------------|
| **API Gateway** | Auth, routing, rate limiting, tenant resolution | Python (Starlette) | HTTP/gRPC |
| **Ingestion Service** | DICOM C-STORE, HL7 MLLP, file validation | Python (pynetdicom) | Message queue |
| **Metadata Service** | Patient, study, series CRUD | Python | REST/gRPC |
| **Search Service** | ES indexing + query | Python | REST |
| **Storage Service** | File read/write, replication, tiering | Python | REST + streaming |
| **Viewer Service** | WADO-RS, frame extraction, thumbnail | Python (Pillow/GDCM) | REST |
| **Sync Service** | Replication, indexing, cleanup | Python | Message queue |
| **Notification Service** | WebSocket pub/sub, webhooks | Python | WebSocket + HTTP |

#### F15: DICOMweb API (QIDO-RS, STOW-RS, WADO-RS)
**Priority**: P1 | **Effort**: 6 weeks | **Dependency**: Microservices

- **QIDO-RS**: Query based on DICOM tags, returning JSON/XML
- **STOW-RS**: Store DICOM instances via HTTP POST/PUT
- **WADO-RS**: Retrieve studies/series/instances via HTTP GET
- **WADO-URI**: Legacy URI-based retrieve
- DICOM JSON model for all metadata
- Content-Type negotiation (`application/dicom+json`, `application/dicom+xml`)

**Acceptance**: External systems can use DICOMweb to query, store, and retrieve studies without DICOM networking.

#### F16: PACS-to-PACS Communication (C-MOVE / C-GET)
**Priority**: P1 | **Effort**: 4 weeks | **Dependency**: None

- DICOM C-MOVE SCP/SCU for study routing between PACS
- DICOM C-GET for pull-based retrieval
- Configurable remote PACS destinations
- Study-level retrieve with progress tracking

**Acceptance**: QuantumPACS can send studies to and retrieve studies from external PACS via DICOM networking.

#### F17: Mobile-Responsive Viewer
**Priority**: P2 | **Effort**: 6 weeks | **Dependency**: None

- Touch-optimized viewer controls (pinch zoom, swipe scroll, tap to toggle tools)
- Responsive layout: sidebar collapses to bottom tab bar
- Thumbnail filmstrip for series navigation on small screens
- Reduced bandwidth mode (JPEG compressed preview, progressive quality)
- PWA support (offline-capable study cache, install prompt)

**Acceptance**: Radiologist can view studies on an iPad or mobile browser with touch-optimized controls and acceptable load times.

#### F18: Role Delegation & Sub-Admin
**Priority**: P2 | **Effort**: 3 weeks | **Dependency**: Multi-tenancy

- Granular role-based access control (RBAC)
- Built-in roles: super-admin, tenant-admin, radiologist, technologist, referring-physician, auditor
- Custom role creation with per-permission assignment
- Scope: read/write/delete per resource type (files, users, replicas, logs)
- Sub-admin: tenant-level admin who cannot access super-admin settings

**Acceptance**: Administrator can create custom roles with fine-grained permissions and assign them to users.

### v3.0 Release Summary

| Feature | Type | Effort | Risk | Dependencies |
|---------|------|--------|------|-------------|
| Microservices | Refactor | 16w | Very High | Multi-tenancy |
| DICOMweb API | New | 6w | High | Microservices |
| C-MOVE/C-GET | New | 4w | Medium | — |
| Mobile viewer | New | 6w | Medium | — |
| Role delegation | New | 3w | Low | Multi-tenancy |
| **Total** | | **~35w** | | |

---

## 6. Dependency Graph

```
v2.0          v2.1              v2.2                   v3.0
  │              │                 │                      │
  ├── MWL ───────┤                 │                      │
  ├── Print ─────┤                 │                      │
  ├── HL7 ───────┤                 │                      │
  ├── Routing ───┤                 │                      │
  ├── Security ──┤                 │                      │
  ├── Metrics ───┤                 │                      │
  └── UI Polish ─┤                 │                      │
                  │                 │                      │
                  ├── FHIR ────────┤                      │
                  ├── Multi-tenant ┼─────── OAuth ────────┤
                  │                 │       RBAC ─────────┤
                  ├── AI Pipe ─────┤             │        │
                  ├── SR ──────────┤             │        │
                  └── Backup ──────┤             │        │
                                     │                    │
                                     ├── Microservices ───┤
                                     │       │            │
                                     │       ├── DICOMweb │
                                     │       └── C-MOVE   │
                                     ├── Mobile Viewer ──┤
                                     └── Role Delegation ─┘
```

---

## 7. Release Cadence & Timeline

```
                Q3 2026          Q1 2027          Q3 2027
                │                │                │
v2.0    ────────● (Jul 2026)
                │
v2.1    ────────┼────────────────● (Sep 2026)
                │                │
v2.1.1  ────────┼────● (Oct)     │
v2.1.2  ────────┼─────────● (Nov)│
                │                │
v2.2    ────────┼────────────────┼────────────────● (Jan 2027)
                │                │                │
v2.2.1  ────────┼────────────────┼─────● (Feb)    │
v2.2.2  ────────┼────────────────┼──────────● (Mar)│
                │                │                 │
v3.0    ────────┼────────────────┼─────────────────┼───● (Jul 2027)
```

---

## 8. Deprecation & Migration

### 8.1 Deprecation Policy

| Version | Status | Support |
|---------|--------|---------|
| v2.0.x | Current | Full support: security patches, bug fixes, documentation |
| v1.x | EOL | No support |

### 8.2 Upgrade Paths

| From | To | Downtime | Migration Steps |
|------|----|----------|-----------------|
| v2.0.x | v2.1.x | < 5 min | Alembic migration + config changes + service restart |
| v2.1.x | v2.2.x | < 5 min | Alembic migration + config changes + service restart (single-tenant) |
| v2.2.x | v3.0 | Hours to days | Requires redeployment as microservices; DB schema migration; API versioning transition |

### 8.3 API Versioning Strategy

- **v2.x**: All API endpoints at `/api/*` (no version prefix)
- **v3.0**: Introduce `/api/v1/*` and `/api/v2/*` prefixes
  - `/api/v1/*` → legacy v2.x endpoints (deprecated)
  - `/api/v2/*` → new v3.0 endpoints (stable)
- Deprecation headers: `X-API-Deprecated: true` on v1 endpoints after v3.1
- Sunset policy: v1 endpoints removed at v4.0 (12 months after deprecation)

---

## 9. Resource Estimation

### 9.1 Engineering Team

| Role | v2.1 | v2.2 | v3.0 |
|------|------|------|------|
| Backend (Python) | 2 FTE | 3 FTE | 4 FTE |
| Frontend (React/TypeScript) | 1 FTE | 1 FTE | 2 FTE |
| DevOps | 0.5 FTE | 0.5 FTE | 1 FTE |
| DICOM/HL7 domain expert | 1 FTE (contract) | 0.5 FTE | 0.5 FTE |
| QA | 0.5 FTE | 1 FTE | 1 FTE |
| **Total** | **5 FTE** | **6 FTE** | **8.5 FTE** |

### 9.2 Infrastructure (Monthly, per tenant)

| Resource | v2.1 | v2.2 (single-tenant) | v3.0 (microservices) |
|----------|------|----------------------|----------------------|
| Compute | 1 vCPU, 2 GB RAM | 2 vCPU, 4 GB RAM | 4 vCPU, 8 GB RAM (per service cluster) |
| PostgreSQL | 2 vCPU, 4 GB RAM | 4 vCPU, 8 GB RAM | 4 vCPU, 8 GB RAM (primary + replica) |
| Storage | Variable (based on study volume) | Variable | Variable (per service) |
| Bandwidth | 1 Gbps | 1 Gbps | 10 Gbps (internal) |

---

## 10. Risks by Release

### v2.1 Risks

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| HL7 parsing library maturity | Medium | High | Fuzzing tests; fallback to regex parser |
| MWL complexity with modalities | Medium | Medium | Test with real modalities (GE, Siemens, Canon) |
| Rate limiting breaks existing integrations | Low | Medium | Configurable per-IP whitelist |
| Security hardening breaks legacy clients | Low | Medium | Documented migration guide; grace period |

### v2.2 Risks

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Multi-tenancy adds unbounded complexity | Medium | Very High | Strict schema-per-tenant decision; ADR before implementation |
| FHIR implementation differs from spec | Medium | High | FHIR connectathon participation; extensive validation test suite |
| OAuth integration failure with hospital IdP | High | High | Support multiple OAuth libraries; test with Azure AD, Okta, Keycloak |
| AI pipeline latency unacceptable | Medium | Medium | Async processing; progress indicators in UI |
| User resistance to RBAC changes | Low | Medium | Migration tools; backward-compatible role assignments |

### v3.0 Risks

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Microservices decomposition scope creep | High | Very High | Strict ADR; phased service extraction; feature flags |
| DICOMweb spec compliance gaps | Medium | High | IHE Connectathon testing; third-party validation |
| Performance regression from network hops | High | High | gRPC for internal communication; caching layer |
| Team learning curve for new architecture | High | Medium | Internal spike sessions; pair programming |
| Database migration from monolith to services | High | Critical | Strangler fig pattern; dual-write during transition |
