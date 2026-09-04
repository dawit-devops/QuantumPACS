# Product Requirements Document: QuantumPACS

**Version**: 2.0.0
**Status**: Draft
**Date**: 2026-07-23
**Audience**: Engineering Team, Hospital IT / PACS Administrators, Radiology Leadership
**Expanded Documents**:
- [UX & Functionality](UX-Functionality.md) — Personas, workflows, UI states, interaction flows
- [Technical Specifications](Technical-Specifications.md) — Architecture, API spec, DB schema, deployment
- [User Stories](User-Stories.md) — Complete story catalog with Gherkin acceptance criteria
- [Roadmap](Roadmap.md) — Phased feature delivery through v3.0
- [Risks](Risks.md) — Full risk register with response plans

---

## 1. Executive Summary

### Problem Statement

Hospitals and imaging centers rely on PACS for diagnostic image management, but existing solutions are either prohibitively expensive vendor lock-in systems (GE, Philips, Siemens) or outdated open-source projects with poor UX, no modern web viewer, and complex deployment. Radiology departments need a zero-footprint, standards-compliant PACS that works on any device, integrates with existing DICOM modalities, and provides fast, reliable access to studies — without per-workstation licenses or proprietary hardware.

### Proposed Solution

QuantumPACS is an open-source, production-grade enterprise PACS with a modern web frontend (Cornerstone3D zero-footprint viewer), DICOM-compliant storage and networking (pynetdicom SCP), pluggable multi-tier storage backends (local, S3, B2), and a RESTful API designed for integration. It ships as a single Docker image or runs natively on Linux.

### Success Criteria (Measured Against Existing Deployment)

| KPI | Target | Method |
|-----|--------|--------|
| Study retrieval latency (first image visible) | <= 2s for a 500-instance CT study over LAN | Automated Playwright timing |
| DICOM C-STORE SCP throughput | >= 100 MB/s sustained | Load test with large studies |
| Concurrent web viewer sessions | >= 50 simultaneous users without degradation | k6 / Artillery load test |
| System uptime | >= 99.9% excluding planned maintenance | Uptime monitoring |
| Deployment time (new site, Docker) | <= 30 minutes for engineer | Timed install procedure |

---

## 2. User Experience & Functionality

> **Expanded document**: [`UX-Functionality.md`](UX-Functionality.md) — 6 detailed personas, 12 end-to-end interaction flows, component state matrix for 20 UI components, theme tokens, responsive breakpoints, accessibility audit, and performance budgets.
>
> **User story catalog**: [`User-Stories.md`](User-Stories.md) — 36 user stories across 8 epics with Gherkin-style acceptance criteria.

### User Personas

| Persona | Role | Goals | Pain Points |
|---------|------|-------|-------------|
| **Radiologist** | Reads and interprets medical images | Fast study access, multi-planar reconstruction, measurement tools, window/level adjustment | Fat client installs, VPN requirements, slow study loading |
| **Technologist** | Operates modalities, verifies image quality | Quick upload confirmation, study completeness check, patient data accuracy | Modality worklist complexity, retake delays |
| **PACS Administrator** | Manages system, users, storage, replication | Simple deployment, storage tiering, usage monitoring, backup strategy | Vendor lock-in, complex configuration, proprietary formats |
| **Hospital IT** | Deploys and maintains infrastructure | Docker-based deployment, standard protocols (DICOM, HTTPS), audit logging | Proprietary hardware dependencies, licensing overhead |
| **Referring Physician** | Views studies and reports via web | Simple web access, no login barriers for shared links, cross-platform | Multiple PACS logins, slow image loading on mobile |

### User Stories

#### U1: Study Viewing (Radiologist)

> As a radiologist, I want to open a study in my browser and scroll through slices with standard tools (pan, zoom, window/level, measurement) so that I can make a diagnosis without installing any software.

**Acceptance Criteria:**
- Opens any DICOM study in < 2s first-image latency over LAN
- Supports stack scroll, pan, zoom, window/level tools
- Supports length, angle, ROI, elliptical ROI, and arrow annotation measurements
- Annotations persist and sync in real-time across open sessions via WebSocket
- Displays full DICOM metadata in an editable table with change audit trail

#### U2: Study Search (All Users)

> As a user, I want to search studies by patient ID, name, study description, or modality so that I can quickly find relevant exams.

**Acceptance Criteria:**
- Search returns results within 500ms for 10k-study dataset
- Supports partial/fuzzy matching across Patient ID, Patient Name, Study Description, Series Description, Modality, SOP Class UID
- Results display patient, study, series hierarchy
- Advanced search modal allows querying by individual DICOM tags

#### U3: DICOM Upload (Technologist)

> As a technologist, I want to send DICOM studies from any modality to QuantumPACS so that images are available for reading immediately.

**Acceptance Criteria:**
- Supports DICOM C-STORE SCP on port 11112
- Auto-extracts patient, study, series metadata from received DICOM files
- Deduplicates files via SHA-256 hash
- Stores files in patient/study/series directory hierarchy
- Rejects malformed or non-DICOM payloads gracefully

#### U4: File Sharing (Radiologist / Referring Physician)

> As a radiologist, I want to generate expiring share links for referring physicians so that they can view studies without creating an account.

**Acceptance Criteria:**
- Share links expire at configurable time (default: 7 days)
- Shared link opens viewer directly, no login required
- Share links use HMAC-authenticated URLs with temp keys
- Audit log records share creation and access

#### U5: User & Replica Management (PACS Admin)

> As a PACS administrator, I want to manage users, configure storage replicas, and view system logs so that I can operate the system securely.

**Acceptance Criteria:**
- Create, deactivate users; reset passwords
- Set user roles: admin, standard
- Add/remove storage replicas (local, S3, B2)
- Configure sync delay per replica
- View real-time replica status from dashboard
- View and search system audit logs

#### U6: Multi-Tier Storage (PACS Admin)

> As a PACS administrator, I want to configure tiered storage with automatic replication so that I can balance performance and cost.

**Acceptance Criteria:**
- Supports 3 backends: Local filesystem, S3-compatible, Backblaze B2
- Can set one master and multiple replica backends
- Async replication via PostgreSQL LISTEN/NOTIFY daemon
- Replica status visible in admin panel
- Failed replicas retry automatically

### Non-Goals

- Not a full RIS (Radiology Information System) — no scheduling, billing, or reporting workflow
- Not a VNA (Vendor Neutral Archive) replacement — no HL7/FHIR integration (planned)
- No AI/ML inference engine — no computer-aided diagnosis (CAD) built in
- No DICOM Modality Worklist (MWL) SCP — modalities must push studies via C-STORE
- No DICOM Print Management SCP
- No native mobile app — responsive web only
- No multi-tenancy in current version — single-organization deployment

---

## 3. Technical Specifications

> **Expanded document**: [`Technical-Specifications.md`](Technical-Specifications.md) — Full architecture diagrams, 22-endpoint API reference with request/response examples, WebSocket protocol, DDL for all 10 tables, 3 storage backend internals, auth flow diagram, ES mapping, DICOM listener flow, Cornerstone3D component tree, deployment topology, testing strategy, and 11-item technical debt register.

### Architecture Overview

```
┌─────────────┐      ┌──────────┐      ┌─────────────────┐
│  Modality    │─────▶│ DICOM    │─────▶│  PostgreSQL     │
│  (C-STORE)   │      │ Listener │      │  (Metadata +    │
│              │      │ :11112   │      │   Audit Log)    │
└─────────────┘      └────┬─────┘      └─────────────────┘
                          │                    │
                          ▼                    ▼
                   ┌──────────────┐    ┌─────────────────┐
                   │  Local FS    │    │  Sync Daemon    │
                   │  (Master)    │◀───│  (LISTEN/NOTIFY)│
                   └──────┬───────┘    └────────┬────────┘
                          │                     │
                          ▼                     ▼
                   ┌──────────────┐    ┌─────────────────┐
                   │  S3 / B2     │    │  Elasticsearch  │
                   │  (Replica)   │    │  (Search Index)  │
                   └──────────────┘    └─────────────────┘

┌──────────────────────────────────────────────────────┐
│                    Web Tier                           │
│  ┌─────────┐   ┌──────────┐   ┌──────────────────┐  │
│  │ Browser │──▶│ Caddy    │──▶│ Starlette API     │  │
│  │ (React +│   │ :80      │   │ :8080 (REST + WS) │  │
│  │ CS3D)   │   │ Reverse  │   │ JWT Auth          │  │
│  └─────────┘   │ Proxy    │   └──────────────────┘  │
│                └──────────┘                          │
└──────────────────────────────────────────────────────┘
```

**Data Flow (Study Upload -> View):**
1. Modality sends DICOM C-STORE to listener on port 11112
2. Listener extracts metadata, writes file to master storage
3. File metadata (patient, study, series) upserted into PostgreSQL
4. Sync daemon (triggered via LISTEN/NOTIFY) indexes file into Elasticsearch
5. Sync daemon copies file to configured replica backends
6. User searches via browser -> Starlette API -> ES query -> PostgreSQL -> response
7. User opens study -> browser loads Cornerstone3D -> fetches DICOM data via API -> renders

### Integration Points

| Integration | Protocol | Port | Details |
|-------------|----------|------|---------|
| DICOM C-STORE SCP | DICOM (pynetdicom) | 11112 | Accepts all Storage SOP Classes |
| REST API | HTTPS | 80 (Caddy) -> 8080 (Starlette) | Full CRUD for studies, users, replicas |
| WebSocket | WSS | 80 -> 8080 | Real-time annotation sync |
| PostgreSQL | TCP | 5432 | Metadata, auth, audit, replication events |
| Elasticsearch | HTTP | 9200 | Full-text search index (optional, graceful degradation) |
| S3 API | HTTPS | Configurable | Replica storage backend |
| B2 API | HTTPS | Configurable | Replica storage backend |

### API Surface

All endpoints under `/api/`:

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/api/health` | Health check | No |
| POST | `/api/login` | Authenticate, returns JWT | No |
| POST | `/api/change_password` | Change own password | Yes |
| GET | `/api/files` | Search studies | Yes |
| POST | `/api/files/upload` | Upload DICOM file | Yes |
| GET | `/api/files/{id}` | File metadata | Yes |
| POST | `/api/files/{id}` | Update tools_state/tag | Yes |
| DELETE | `/api/files/{id}` | Delete file | Admin |
| GET | `/api/files/{id}/changes` | File change audit trail | Yes |
| POST | `/api/files/{id}/share` | Generate share link | Yes |
| GET | `/api/files/{id}/data` | Serve DICOM file data | Yes |
| GET | `/api/files/download_token` | Get download auth token | Yes |
| GET | `/api/files/download.zip` | Bulk download as ZIP | Yes |
| GET | `/api/files/download.csv` | Export metadata as CSV | Yes |
| GET | `/api/patients/{id}` | Patient detail with studies | Yes |
| GET/POST | `/api/replicas` | List / add replicas | Admin |
| POST/DELETE | `/api/replicas/{id}` | Update / delete replica | Admin |
| GET/POST | `/api/users` | List / create users | Admin |
| POST | `/api/users/deactivate` | Deactivate user | Admin |
| POST | `/api/users/new_password` | Reset user password | Admin |
| GET | `/api/logs` | View system audit logs | Admin |
| GET | `/api/ws_token` | Get WebSocket auth token | Yes |
| WS | `/api/ws` | Real-time annotation sync | Token |

### Authentication & Authorization

- **Protocol**: JWT (HS256, 14-day default expiry)
- **Header**: `X-Auth-Pacs: <token>` (custom header)
- **Fallback**: `?token=<token>` query param for WebSocket and share links
- **Share Links**: Temporary HMAC-authenticated URLs with `shared_files` table
- **Password Hashing**: PBKDF2-HMAC-SHA256, 600k iterations, 16-byte salt
- **Roles**: `admin` and `standard`
- **Exempt endpoints**: `/api/login`, `/api/health`, OPTIONS preflight

### Database Schema

8 tables managed via Alembic + auto-sync at startup:

| Table | Purpose | Key Notes |
|-------|---------|-----------|
| `users` | Authentication & roles | CITEXT username, PBKDF2 password |
| `patients` | Patient demographics | JSONB for extensible metadata |
| `studies` | Study records | FK to patients, unique per patient |
| `series` | Series records | FK to studies, unique per study |
| `files` | File/instance records | JSONB meta + tools_state, SHA-256 hash |
| `file_changes` | Audit trail | FK to files + users |
| `replicas` | Storage backend config | Master flag, sync delay |
| `replica_files` | Replica file mapping | Per-replica file status |
| `logs` | System audit log | Timestamped event log |
| `shared_files` | Expiring share links | FK CASCADE on file delete |

### Security & Privacy

| Concern | Implementation |
|---------|---------------|
| Authentication | JWT tokens with short expiry, PBKDF2 password hashing |
| Transport security | TLS termination via Caddy (reverse proxy) |
| Audit logging | All file changes logged with user ID and timestamp |
| Share link security | HMAC-authenticated temp keys, configurable expiry |
| Path traversal | Validated in LocalStorage `get_path()` |
| CORS | Wide-open for dev (`Access-Control-Allow-Origin: *`), tighten for production |
| SQL injection | Parameterized queries via asyncpg + PyPika query builder |
| Authentication bypass | All routes opt-in to auth; only `/login` and `/health` exempt |

### Deployment Architecture

**Production (Docker):**
```
Caddy (:80)  ──proxy──▶  Gunicorn + Uvicorn workers (:8080)
                              │
                              ├── PostgreSQL (:5432)
                              ├── DICOM Listener (:11112)
                              ├── Sync Daemon (background)
                              └── Elasticsearch (:9200, optional)
```

**Development (systemd services):**
```
systemd --user:
  quantumpacs-backend.service  (uvicorn app:app :8080)
  quantumpacs-frontend.service (vite :5173)
  quantumpacs-postgres-1       (Docker container :5432)
```

---

## 4. Technical Risks & Mitigations

> **Expanded document**: [`Risks.md`](Risks.md) — 25 risks across 5 categories (Technical, Security, Operational, Regulatory, Deployment), scored L×I, heat map, top 5 critical risks with detailed response plans, monitoring alerting thresholds, and 8 assumptions/constraints.

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Elasticsearch dependency failure | Search degrades gracefully | High (ES often unavailable in constrained envs) | Fallback to PostgreSQL text search; search returns empty instead of crashing |
| DICOM listener port conflict (11112) | Modality cannot connect | Medium | Configurable port; documented port requirements |
| PostgreSQL connection pool exhaustion | API hangs under load | Low | Pool size configurable (default: 8); monitor with `pg_stat_activity` |
| Storage backend S3/B2 latency | Replication delay | Medium | Async replication; replica status visible in admin panel |
| JWT secret rotation | All sessions invalidated | Low | Documented procedure; short-lived tokens minimize impact |
| Large study load times (>1000 instances) | Poor radiologist experience | Medium | Progressive image loading in Cornerstone3D; volume streaming |

---

## 5. Roadmap

> **Expanded document**: [`Roadmap.md`](Roadmap.md) — Detailed feature breakdown with effort estimates (person-weeks), dependency graph, release cadence timeline, upgrade/deprecation policy, API versioning strategy, and resource estimation per release.

### Current (v2.0.0 — Delivered)

- Core PACS: DICOM SCP, web viewer, search, auth, user management
- Pluggable storage backends (Local, S3, B2) with async replication
- Elasticsearch search indexing
- Real-time annotation sync via WebSocket
- Expiring share links
- Admin panel: users, replicas, audit logs
- Docker deployment with Caddy reverse proxy
- 10 ADRs documenting all architectural decisions
- CI pipeline (lint, test, build, Docker publish)

### v2.1 (Next — 1-2 months)

- DICOM Modality Worklist (MWL) SCP
- DICOM Print Management SCP
- HL7 v2.x ADT/ORM message ingestion for patient/order integration
- Study-level routing rules (auto-route studies to specific replicas by modality)
- Rate limiting and enhanced CORS for production hardening
- Prometheus metrics endpoint (`/api/metrics`)

### v2.2 (Medium-term — 3-6 months)

- FHIR R4 API (Patient, ImagingStudy, DocumentReference resources)
- Multi-tenancy for multi-hospital deployments
- OAuth 2.0 / OpenID Connect SSO integration
- AI inference pipeline: DICOM SEG export -> external ML engine -> results display
- Structured report (SR) viewer and editor
- Automated backup/restore for PostgreSQL + file store

### v3.0 (Long-term — 6-12 months)

- Microservices decomposition (separate viewer, storage, search, ingestion services)
- DICOM JSON / DICOMweb (QIDO-RS, STOW-RS, WADO-RS) API
- PACS-to-PACS DICOM C-MOVE / C-GET
- Built-in structured reporting with templates
- Role-based PACS admin delegation (sub-admin per modality or location)
- Mobile-responsive viewer with touch-optimized controls

---

## 6. Competitive Landscape

| Feature | QuantumPACS | Orthanc | DCM4CHEE | Commercial (GE/Philips/Siemens) |
|---------|-------------|---------|----------|-------------------------------|
| Zero-footprint web viewer | Cornerstone3D (full tools) | Basic HTML viewer | Basic HTML viewer | Proprietary plugin required |
| DICOM SCP | Yes (all storage SOPs) | Yes | Yes | Yes |
| Multi-tier storage | Local, S3, B2 | Local only | Local + S3 | Proprietary only |
| REST API | Comprehensive | Good | Moderate | Vendor-specific SDK |
| Deployment | Single Docker image | Docker available | Complex EAR deploy | Appliance/hardware |
| License | MIT (open source) | GPLv3 | LGPLv2 | Proprietary (perpetual + annual) |
| Cost | Free | Free | Free | $50k-$500k+ per site |
| Active development | 2026 | Yes | Slowing | Vendor-dependent |

---

## 7. Success Evaluation

### Engineering Metrics (Internal)

- **Test coverage**: >= 80% for backend logic, >= 60% for frontend components
- **API response times**: 95th percentile <= 500ms for all endpoints under load
- **Build time**: Full Docker build <= 10 minutes (CI)
- **Zero critical CVEs**: All production dependencies scanned via `pip-audit` / `npm audit`

### Operational Metrics (Hospital IT)

- **Deployment time**: <= 30 minutes for a Docker-based installation
- **Upgrade time**: <= 5 minutes downtime for schema migration
- **Storage efficiency**: Deduplication via SHA-256 hash reduces redundant storage
- **Backup RPO**: <= 24 hours (configurable PostgreSQL backup + file store sync)

### Clinical Metrics (Radiology Leadership)

- **Study load time**: <= 2s to first image for a typical CT (500 instances)
- **Uptime**: >= 99.9% excluding planned maintenance windows
- **User satisfaction**: Target SUS (System Usability Scale) score >= 75 in post-deployment survey

---

*This PRD reflects the current state of QuantumPACS v2.0.0 and its planned evolution. For deeper detail, see the companion documents above and the ADRs in `docs/decisions/`. For implementation guidance, see `CLAUDE.md` and `README.md`.*
