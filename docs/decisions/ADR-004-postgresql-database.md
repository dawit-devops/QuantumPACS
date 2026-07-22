# ADR-004: PostgreSQL Database with asyncpg and Alembic

## Status
Accepted

## Date
2026-07-22

## Context
The original database layer used synchronous SQLite for development and raw psycopg2 for production, with no connection pooling and no migration system. Schema changes required manual SQL scripts. Requirements:

- Async database access (non-blocking DICOM ingestion)
- Connection pooling for concurrent study uploads
- Migration system for version-controlled schema changes
- PostgreSQL-specific features (JSONB, CTE, full-text search)
- Minimal dependency footprint

## Decision
Use `asyncpg` for database access with a singleton `Database` class wrapping an async connection pool, and `Alembic` for schema migrations.

Key components:
- `db/database.py`: `Database` class with `setup()` (pool creation), `acquire()` (connection from pool), `close()` (graceful shutdown)
- `db/conn.py`: Global `get_database()` accessor with legacy `get_conn()` backward-compat wrapper
- `db/queries.py`: Raw SQL via PyPika query builder (not ORM — explicit SQL control)
- `backend/migrations/`: Alembic migration environment with `env.py` and version scripts
- `backend/alembic.ini`: Alembic configuration

Schema design:
- `users` — authentication and role (admin flag)
- `patients` — DICOM patient records with JSONB metadata
- `studies` — DICOM studies linked to patients
- `series` — DICOM series linked to studies
- `files` — individual DICOM instances with hash, metadata, tools_state
- `file_changes` — audit trail for file modifications
- `replicas` / `replica_files` — multi-site file replication
- `shared_files` — expiring share links with hash-based access
- `logs` — generic event log
- `notify_event()` trigger — PostgreSQL NOTIFY for real-time replica updates

## Alternatives Considered

### SQLAlchemy async (with asyncpg driver)
- Pros: ORM with migration support via Alembic
- Cons: Heavy abstraction; SQLAlchemy async was immature at project start
- Rejected: Raw SQL via PyPika gives more control for DICOM-specific queries

### SQLite (status quo)
- Pros: Zero configuration, embedded
- Cons: No concurrent write support, no JSONB, no LISTEN/NOTIFY
- Rejected: Not suitable for production multi-user PACS

## Consequences
- Full control over SQL — optimized for DICOM query patterns
- Alembic provides reproducible, version-controlled migrations
- Connection pooling handles concurrent study ingestion
- PostgreSQL LISTEN/NOTIFY powers real-time replica synchronization
- No ORM means more verbose query code but better performance
