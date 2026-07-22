# ADR-001: Strangler Fig Modernization Strategy

## Status
Accepted

## Date
2026-07-22

## Context
OpenPACS is a production medical image management system (PACS) with a legacy codebase built around Python 3.7-era patterns: procedural routes, global mutable state, synchronous database access via raw SQLite/SQLAlchemy, and a Jinja2-templated frontend. The system processes DICOM studies, manages file storage replicas, and serves a web viewer.

Key challenges:
- Tight coupling between HTTP handlers and database logic
- No typed request validation — all parameters parsed manually
- Global singleton database connection with no pooling
- Frontend mixed Jinja2 templates per-route
- No automated test coverage
- Dependencies severely outdated (PyJWT 1.x, elasticsearch 7.x, etc.)

The system must remain fully operational during modernization — no downtime, no data loss, no regression in functionality.

## Decision
Use the Strangler Fig pattern for incremental modernization:

1. **Phase 0 (Foundation)**: Pin runtime deps, add test framework, CI pipeline
2. **Phase 1 (Security)**: Upgrade PyJWT to 2.x, centralize token logic, beef up auth
3. **Phase 2 (Framework)**: Port from async def soup to Starlette-structured app
4. **Phase 3 (Storage)**: Wrap SQLite/raw pg in asyncpg pool, add Alembic
5. **Phase 4 (Testing)**: Add pytest fixtures, integration tests for key endpoints
6. **Phase 5 (CI/CD)**: GitHub Actions for lint + test + build
7. **Phase 6 (Observability)**: Structured logging, health check endpoint
8. **Phase 7 (TypeScript)**: Ambient type declarations, JS → TS migration
9. **Phase 8 (UI)**: antd 3 → 4 → 5, Vite, Cornerstone3D

Each phase maintains a passing build and backward compatibility. The legacy frontend (Jinja2) remains until Phase 8 is fully verified.

## Alternatives Considered

### Big-bang rewrite
- Pros: Clean architecture from day one
- Cons: Months of development before any value; massive regression risk
- Rejected: Unacceptable for a production medical system

### Lift-and-shift to a new framework in one pass
- Pros: Single migration window
- Cons: Too many simultaneous changes to debug; rollback impossible
- Rejected: Strangler Fig allows per-phase rollback

## Consequences
- Each phase independently deployable and testable
- Rollback means reverting a single phase
- Slower overall delivery but much lower risk
- Some intermediate duplication (two auth systems, two DB wrappers) is acceptable
- Phases 1-8 completed successfully; future phases can continue the pattern
