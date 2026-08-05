# QuantumPACS v3 — Product Roadmap

**Version**: 3.0.0-draft
**Status**: Draft
**Date**: 2026-07-25
**Supersedes**: `docs/Roadmap.md` for v3+ scope
**Companion**: [PRD-v3.md](PRD-v3.md), [IMPLEMENTATION_PLAN-v3.md](IMPLEMENTATION_PLAN-v3.md)

---

## 1. Release Strategy

QuantumPACS v3 follows a **feature-based release cadence** with **semantic versioning**:

| Version | Cadence | Scope |
|---------|---------|-------|
| v2.0.x | Monthly (maintained until v3.0 GA) | Security patches, critical bug fixes only |
| v3.0.x | Quarterly post-GA | Bug fixes, security patches, performance improvements |
| v3.1.x | Q4 2027 | RIS bundle: scheduling, worklist, reporting, physician portal |
| v3.2.x | Q1 2028 | AI inference pipeline, structured report editor |
| v4.0 | H2 2028 | Full microservices decomposition, API v1 sunset |

---

## 2. Current State (v2.0.0 — July 2026)

### Delivered

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
| Architecture decisions | ✅ | 13 ADRs (incl. v3 additions) |

### Known Gaps Addressed by v3.0

| Gap | v3.0 Feature | Phase |
|-----|-------------|-------|
| No multi-tenancy | Database-per-tenant provisioning | Phase 2 |
| No DICOMweb API | QIDO-RS, STOW-RS, WADO-RS, WADO-URI | Phase 3 |
| No OAuth/SSO | OAuth 2.0 + OIDC with Azure AD, Okta, Keycloak | Phase 2 |
| No RBAC | Role-permission model replacing `admin` boolean | Phase 2 |
| No HL7/FHIR | HL7 v2.x MLLP + FHIR R4 Patient/ImagingStudy | Phase 4 |
| No MWL SCP | DICOM Modality Worklist C-FIND | Phase 3 |
| No C-MOVE/C-GET | PACS-to-PACS DICOM networking | Phase 3 |
| No mobile viewer | Touch-optimized responsive viewer + PWA | Phase 6 |
| No metrics dashboard | Prometheus metrics + admin dashboard | Phase 5–6 |
| No API versioning | `/api/v2/*` with v1→v2 migration path | Phase 8 |
| Production hardening | 12 critical + 32 high findings resolved | Phase 0 |

---

## 3. v3.0 — Enterprise Integration (Q3 2026 – Q2 2027)

**Theme**: From single-site PACS to enterprise imaging platform.
**Target**: June 2027

### Phase Summary

| Phase | Theme | Duration | Start | End |
|-------|-------|----------|-------|-----|
| 0 | Production Hardening | 9 sprints (~3 weeks) | Immediately | Ongoing |
| 1 | Foundation | 2 weeks | After P0 | +2 weeks |
| 2 | Auth & Tenancy | 6 weeks | After P1 | +8 weeks |
| 3 | DICOM Core | 8 weeks | After P2 | +16 weeks |
| 4 | Integration | 6 weeks | After P3 | +22 weeks |
| 5 | Observability | 2 weeks | After P4 | +24 weeks |
| 6 | Frontend v3 | 8 weeks | After P5 | +32 weeks |
| 7 | Verification | 3 weeks | After P6 | +35 weeks |
| 8 | Migration | 2 weeks | After P7 | +37 weeks |
| **v3.0 GA** | **Release** | **—** | **After P8** | **~June 2027** |

### Key Milestones

```
Q3 2026          Q4 2026          Q1 2027          Q2 2027
│                │                │                │
├── Phase 0 ─────┤                │                │
│ (Hardening)    │                │                │
├── Phase 1 ─────┤                │                │
│ (Foundation)   │                │                │
├── Phase 2 ─────┼────────────────┤                │
│ (Auth/Tenancy) │                │                │
├── Phase 3 ─────┼────────────────┼────────────────┤
│ (DICOM Core)   │                │                │
├── Phase 4 ─────┼────────────────┼────────────────┤
│ (Integration)  │                │                │
├── Phase 5 ─────┤                │                │
│ (Observability)│                │                │
├── Phase 6 ─────┼────────────────┼────────────────┤
│ (Frontend v3)  │                │                │
├── Phase 7 ─────┼────────────────┼────────────────┤
│ (Verification) │                │                │
├── Phase 8 ─────┼────────────────┼────────────────┤
│ (Migration)    │                │                │
│                │                │                │
│           v3.0 GA ●──────────────────────────────┤
│                │                │                │
└──────────────────────────────────────────────────┘
```

---

## 4. v3.1 — RIS Bundle (H2 2027)

**Theme**: Turn QuantumPACS into a combined PACS + RIS.
**Target**: December 2027

### Features (Preliminary — Full Plan in Q3 2027)

| Feature | Effort | Dependencies | Notes |
|---------|--------|-------------|-------|
| Patient scheduling & appointment mgmt | 6 weeks | HL7, MWL (v3.0) | Receptionist flow |
| Order entry with DICOM MWL integration | 4 weeks | Phase 3 MWL | Technologist flow |
| Radiologist reporting workspace | 8 weeks | Phase 3 SR viewer | Dictation, templates, DICOM SR |
| Referring physician portal | 4 weeks | Phase 2 OAuth, Phase 6 mobile | Web-based study + report access |
| Billing-lite (CPT/ICD-10 codes, invoices) | 4 weeks | Scheduling | Cashier flow |
| Built-in structured report editor | 4 weeks | None | TID 1500 / 2000 template editor |
| Full FHIR DiagnosticReport + DocumentReference | 4 weeks | Phase 4 FHIR | EHR integration |

---

## 5. v3.2 — AI & Advanced Features (Q1 2028)

| Feature | Effort | Notes |
|---------|--------|-------|
| AI inference pipeline (DICOM SEG export → ML → overlay) | 6 weeks | Webhook-based, app stores results |
| Structured report viewer with SR tree renderer | 4 weeks | DICOM SR TID 1500/2000 |
| Automated backup/restore CLI | 2 weeks | `./manage db backup/restore` |
| Role delegation & sub-admin UI | 3 weeks | Extends Phase 2 RBAC |

---

## 6. v4.0 — Next-Generation Architecture (H2 2028)

**Theme**: Modular monolith → full microservices.
**Target**: December 2028

| Feature | Effort | Notes |
|---------|--------|-------|
| Full microservices decomposition (8 services) | 16 weeks | Per ADR-014 |
| DICOMweb v2 (additional resources, bulk data) | 4 weeks | Extends Phase 3 |
| Multi-region active-active replication | 12 weeks | Requires microservices |
| API v1 sunset | 2 weeks | Removes `/api/v1/*` endpoints |
| GraphQL API alongside REST | 4 weeks | Optional query flexibility |

---

## 7. Dependency Graph

```
v2.0.0                    v3.0                          v3.1                    v3.2                    v4.0
  │                         │                              │                       │                       │
  ├── Phase 0 ──────────────┤                              │                       │                       │
  │   Hardening             │                              │                       │                       │
  │                         │                              │                       │                       │
  ├── Phase 1 ──────────────┤                              │                       │                       │
  │   Redis Streams         │                              │                       │                       │
  │   Module boundaries     │                              │                       │                       │
  │   Tenant registry       │                              │                       │                       │
  │                         │                              │                       │                       │
  ├── Phase 2 ──────────────┤                              │                       │                       │
  │   DB-per-tenant  ───────┼────── OAuth OIDC ────────────┤                       │                       │
  │   RBAC model     ───────┼────── Role delegation ───────┼───────────────────────┤                       │
  │                         │                              │                       │                       │
  ├── Phase 3 ──────────────┤                              │                       │                       │
  │   MWL SCP ──────────────┼────── MWL for RIS ──────────┤                       │                       │
  │   C-MOVE/C-GET ─────────┤                              │                       │                       │
  │   DICOMweb     ─────────┼────── DICOMweb v2 ───────────┼───────────────────────┤                       │
  │                         │                              │                       │                       │
  ├── Phase 4 ──────────────┤                              │                       │                       │
  │   HL7 MLLP ─────────────┼────── HL7 for RIS ──────────┤                       │                       │
  │   FHIR R4   ────────────┼────── FHIR report ──────────┤                       │                       │
  │                         │                              │                       │                       │
  ├── Phase 5 ──────────────┤                              │                       │                       │
  │   Observability         │                              │                       │                       │
  │                         │                              │                       │                       │
  ├── Phase 6 ──────────────┤                              │                       │                       │
  │   Mobile viewer ────────┼────── Portal for RIS ────────┤                       │                       │
  │   RBAC UI ──────────────┤                              │                       │                       │
  │   Tenant switcher       │                              │                       │                       │
  │   OAuth screen          │                              │                       │                       │
  │   Metrics dashboard     │                              │                       │                       │
  │                         │                              │                       │                       │
  ├── Phase 7 ──────────────┤                              │                       │                       │
  │   k6 + ZAP + IHE        │                              │                       │                       │
  │                         │                              │                       │                       │
  ├── Phase 8 ──────────────┤                              │                       │                       │
  │   v1→v2 migration       │                              │                       │                       │
  │                         │                              │                       │                       │
  │    v3.0 GA ●────────────┤                              │                       │                       │
  │                         ├── Scheduling ────────────────┤                       │                       │
  │                         │   Worklist ──────────────────┤                       │                       │
  │                         │   Reporting workspace ───────┤                       │                       │
  │                         │   Physician portal ──────────┤                       │                       │
  │                         │   Billing-lite ──────────────┤                       │                       │
  │                         │   SR editor ─────────────────┤                       │                       │
  │                         │                              │                       │                       │
  │                         │     v3.1 GA ●────────────────┤                       │                       │
  │                         │                              ├── AI pipeline ─────────┤                       │
  │                         │                              │   SR viewer ──────────┤                       │
  │                         │                              │   Backup/restore ─────┤                       │
  │                         │                              │   Sub-admin UI ───────┤                       │
  │                         │                              │                       │                       │
  │                         │                              │    v3.2 GA ●──────────┤                       │
  │                         │                              │                       ├── Microservices ──────┤
  │                         │                              │                       │   DICOMweb v2 ────────┤
  │                         │                              │                       │   Multi-region ───────┤
  │                         │                              │                       │   API v1 sunset ──────┤
  │                         │                              │                       │   GraphQL API ────────┤
  │                         │                              │                       │                       │
  │                         │                              │                       │   v4.0 GA ●───────────┘
```

---

## 8. Deprecation & Migration

### 8.1 Deprecation Policy

| Version | Status | Support |
|---------|--------|---------|
| v2.0.x | Current (until v3.0 GA) | Security patches, critical bug fixes |
| v3.0.x | GA target June 2027 | Full support |
| v2.0.x | Legacy (after v3.0 GA) | Critical security patches only, 12-month grace |
| v1.x | EOL | No support |

### 8.2 Upgrade Paths

| From | To | Downtime | Migration Steps |
|------|----|----------|-----------------|
| v2.0.x | v3.0 (single-tenant) | < 5 min | Alembic migrations + config changes + service restart; `/api/*` continues to work |
| v2.0.x | v3.0 (multi-tenant) | Hours | Requires tenant data export/import; v2 instance becomes one tenant in v3 |
| v3.0.x | v3.1.x | < 5 min | Alembic migrations + config + service restart |
| v3.0.x | v4.0 | Hours to days | Requires redeployment as microservices; DB schema migration; API v1 removal |

### 8.3 API Versioning

| Phase | Prefix | Status |
|-------|--------|--------|
| v2.0–v3.0 transition | `/api/*` | Active (aliased to `/api/v1/*`) |
| v3.0 GA | `/api/v1/*` | Deprecated (`X-API-Deprecated`, `X-API-Sunset-Date` headers) |
| v3.0 GA | `/api/v2/*` | Stable (recommended for all new integrations) |
| v4.0 | `/api/v1/*` | Removed |
| v4.0 | `/api/v2/*` | Stable |
| v4.0+ | `/api/v3/*` | Future (when v2 is deprecated) |

---

## 9. Resource Estimation

### 9.1 Engineering Team

| Role | v3.0 (Phases 1–8) | v3.1 (RIS) | v3.2 (AI) | v4.0 (Microsvcs) |
|------|-------------------|------------|-----------|-------------------|
| Backend (Python) | 2–3 FTE | 2 FTE | 2 FTE | 4 FTE |
| Frontend (React/TypeScript) | 1–2 FTE | 2 FTE | 1 FTE | 2 FTE |
| DevOps | 0.5 FTE | 0.5 FTE | 0.5 FTE | 1.5 FTE |
| DICOM/HL7 domain expert | 1 FTE (contract) | 1 FTE (contract) | 0.5 FTE | 0.5 FTE |
| QA | 1–2 FTE | 1 FTE | 1 FTE | 2 FTE |
| **Total** | **~6–8 FTE** | **~6.5 FTE** | **~5 FTE** | **~10 FTE** |

### 9.2 Infrastructure (Monthly, per medium tenant)

| Resource | v3.0 | v3.1 (with RIS) | v4.0 (microservices) |
|----------|------|-----------------|----------------------|
| Compute | 2 vCPU, 4 GB RAM | 4 vCPU, 8 GB RAM | 8 vCPU, 16 GB RAM (per service cluster) |
| PostgreSQL | 2 vCPU, 4 GB RAM | 4 vCPU, 8 GB RAM | 4 vCPU, 8 GB RAM (primary + replica) |
| Redis | 1 GB RAM | 2 GB RAM | 4 GB RAM (cluster) |
| Storage | Variable | Variable + report storage | Variable (per service) |
| Bandwidth | 1 Gbps | 1 Gbps | 10 Gbps (internal) |

---

## 10. Risks by Release

### v3.0 Risks

See full register in [PRD-v3.md §4.2](PRD-v3.md#42-technical-risks) and [IMPLEMENTATION_PLAN-v3.md §Risk Register](IMPLEMENTATION_PLAN-v3.md#risk-register).

### v3.1 RIS Risks

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| RIS scope creep (scheduling, billing, reporting all new) | High | High | Strict MVP per ADR; feature flags for billing |
| HL7 ORM mapping varies by RIS vendor | Medium | High | Documented field mapping table; configurable overrides |
| Physician portal duplicates share-link functionality | Medium | Low | Merge share-link and portal UX into one code path |
| Billing codes (CPT/ICD-10) complexity | High | Medium | MVP: manual code entry only; deferred auto-coding to v4 |

### v3.2 AI Risks

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| ML model integration latency | Medium | High | Async pipeline with progress indicators |
| DICOM SEG export performance | Medium | Medium | Streaming export; chunked DICOM SEG construction |
| Unknown AI vendor APIs | High | Medium | Adapter pattern: each AI vendor gets a plugin |

### v4.0 Risks

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Microservices decomposition scope creep | High | Very High | Strict ADR; phased service extraction; feature flags |
| Performance regression from network hops | High | High | gRPC for internal communication; caching layer |
| Database migration: monolith → services | High | Critical | Strangler fig pattern; dual-write during transition |
| Team learning curve for new architecture | High | Medium | Internal spike sessions; pair programming |

---

*This roadmap is the forward-looking companion to `docs/PRD-v3.md` and `docs/IMPLEMENTATION_PLAN-v3.md`. It supersedes the v3 sections of `docs/Roadmap.md` for all future planning.*