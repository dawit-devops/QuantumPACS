# ADR-014: Modular Monolith with Deferred Microservices

## Status
Accepted

## Date
2026-07-25

## Context

QuantumPACS v2.0 is a single Starlette monolith serving REST, WebSocket, and background sync from one process. The v3.0 roadmap (Roadmap.md F14) originally called for full microservices decomposition into 8 services (API Gateway, Ingestion, Metadata, Search, Storage, Viewer, Sync, Notification). This decomplexity comes at a high cost:

- **Operational overhead**: 8 services require 8 Dockerfiles, 8 health checks, 8 log streams, 8 deployment units, and service discovery/mesh.
- **Team learning curve**: The team has no production experience with gRPC, service meshes, or distributed tracing at scale.
- **Migration risk**: Extracting a service incorrectly can cause data loss (e.g., splitting the metadata service from storage without dual-write).
- **Premature optimization**: The current single-process architecture handles ~50 concurrent viewers at ~100 MB/s C-STORE throughput. The 8-service split does not unlock new users; it only enables horizontal scaling beyond a single node.

However, continuing as a pure monolith blocks enterprise adoption: no multi-tenancy, no independent ingest scaling, no fault isolation between API and DICOM processing.

## Decision

Adopt a **modular monolith** architecture for v3.0 with **one extracted service** (ingestion). Full microservices decomposition is deferred to v4.0.

**Modular monolith rules:**

1. **Strict internal module boundaries** — Each domain (auth, metadata, storage, search, notification) has a Python package with a public interface (`Protocol` or abstract base class) and a private implementation. Modules communicate through these interfaces, never through direct imports of implementation internals.
2. **One process, one Docker image** — The monolith runs in a single `uvicorn` process (plus `gunicorn` workers for production). Same Dockerfile as v2.
3. **Ingestion service extracted** — The HL7 MLLP listener and DICOM C-STORE handler run as a separate process. This is the highest-throughput path and benefits most from independent scaling. It communicates with the main monolith via Redis Streams.
4. **Service Registry** — A `ServiceRegistry` class (initialized in the Starlette lifespan) holds all module instances. Route handlers access services through `request.state.services`, never through global imports.
5. **No shared mutable state** — All cross-cutting state flows through Redis Streams, PostgreSQL, or the `ServiceRegistry`. No `import api.ws; ws.files` (the v2 anti-pattern that prevents horizontal scaling).

## Consequences

### Positive

- **Lower migration risk** — The strangler fig pattern (ADR-001) applies: each module boundary can be extracted to a real service in v4.0 without rewriting.
- **Faster delivery** — No service-mesh, gRPC, or container-orchestration learning curve for v3.0.
- **Same deployment model** — Existing `docker-compose.yaml`, `Dockerfile`, `systemd` services, and `scripts/dev.sh` work unmodified.
- **Plan B available** — If scaling demands exceed the monolith's capacity before v4.0, any module can be extracted independently.

### Negative

- **No independent scaling** — The entire monolith scales as one unit. A spike in API traffic also scales the DICOM listener and sync worker (though ingestion is extracted).
- **No fault isolation** — A memory leak in the search module can crash the entire API.
- **Language lock-in** — All services remain Python. A future Rust/Go service for high-throughput DICOM processing would require extraction first.

### Migration Path to v4.0

When full microservices are warranted, each module boundary becomes a separate service:
1. **Metadata Service** — Extracts first (most business logic, most DB access)
2. **Storage Service** — Extracts second (needs streaming API for large files)
3. **Search Service** — Extracts third (ES client becomes internal)
4. **Notification Service** — Extracts fourth (WebSocket pub/sub scales independently)
5. **API Gateway** — Becomes the entry point, routing to all services

## References

- ADR-001: Strangler Fig Modernization Strategy
- PRD-v3.md §3.1 — System Architecture
- IMPLEMENTATION_PLAN-v3.md Phase 1 — Foundation
- "Modular Monolith: A Primer" — Simon Brown, 2022