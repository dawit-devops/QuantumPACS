# ADR-002: Starlette Backend Framework

## Status
Accepted

## Date
2026-07-22

## Context
The original backend used a minimal async HTTP server with ad-hoc routing via raw ASGI handling. As the system grew, this became difficult to maintain — no structured routing, no middleware pipeline, no exception handling framework. The requirements for a backend framework:

- Async-first for DICOM I/O and database operations
- Lightweight — no full Django inclusion
- Middleware support for auth, logging, CORS
- WebSocket support for real-time viewer events
- Strong typing ecosystem compatibility (Pydantic)

## Decision
Use Starlette as the web framework with Uvicorn + Gunicorn for production serving.

Key implementation details:
- Starlette `Route` objects for structured endpoint definitions
- `AuthenticationMiddleware` for token-based auth on every request
- Custom HTTP middleware for request logging, CORS headers, SPA fallback
- `HTTPException` handler for consistent error responses
- Lifespan events (`on_event('startup')`) for DB pool and service initialization
- Uvicorn workers under Gunicorn (`api_conf.py`) for production

## Alternatives Considered

### FastAPI
- Pros: Auto-generated OpenAPI docs, built-in Pydantic validation
- Cons: Extra abstraction layer; Phase 2 was about reducing complexity
- Rejected: Starlette is FastAPI's foundation — can add Pydantic validation via `parse_body()` without full FastAPI

### Django + Channels
- Pros: Full ecosystem, ORM, admin panel
- Cons: Heavy; conflicts with existing async patterns; overkill for an API-focused service
- Rejected: Too much overhead for a focused DICOM API server

### Flask
- Pros: Simple, well-known
- Cons: Sync-only; would require gevent monkey-patching for async
- Rejected: Not suitable for async DICOM operations

## Consequences
- Starlette provides a clean middleware stack for auth, CORS, and logging
- Lightweight enough to run alongside DICOM listener processes
- Can add FastAPI later if OpenAPI docs become a priority
- Team needs familiarity with Starlette patterns (low risk — Starlette is well-documented)
