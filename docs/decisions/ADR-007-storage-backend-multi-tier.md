# ADR-007: Multi-Tier Storage Backend

## Status
Accepted

## Date
2026-07-22

## Context
OpenPACS manages medical image files (DICOM) that need to be stored durably, retrieved quickly, and replicated across sites. The original storage used a simple filesystem directory with database metadata. Requirements:

- Durable file storage with integrity verification (SHA-256 hashing)
- Multiple replica locations (local, Backblaze B2, S3-compatible)
- Full-text search over DICOM metadata
- File change audit trail
- Expiring share links for external access

## Decision
Implement a three-tier storage architecture:

1. **Filesystem**: Primary DICOM file store, organized by patient/study/series
2. **PostgreSQL**: File metadata, replica tracking, audit log, share links
3. **Elasticsearch**: DICOM metadata indexing for full-text search across tags

Key components:
- `FileManager` in `backend/files/` — handles file upload/download, hash verification, deduplication
- `ReplicaManager` — asynchronous replication to configured backends (S3, B2, filesystem)
- PostgreSQL NOTIFY trigger on `replicas` table for real-time replication events
- File changes logged in `file_changes` table with user attribution
- File hashing on upload prevents duplicate storage
- Shared files with HMAC-based access tokens and expiration

## Alternatives Considered

### All-in-one S3
- Pros: Simple, durable, no replication management
- Cons: Latency for DICOM viewer; requires internet connectivity; egress costs
- Rejected: Local filesystem is required for low-latency reading station access

### MongoDB GridFS
- Pros: Single database for metadata + files
- Cons: Poor DICOM metadata search; no built-in replication to B2/S3
- Rejected: Elasticsearch provides superior medical metadata search

## Consequences
- Filesystem provides fast local access for the DICOM viewer
- Elasticsearch enables search across patient name, study description, modality, etc.
- Replica system supports heterogeneous backends (S3, B2, NAS)
- File hashing prevents silent data corruption
- Audit trail satisfies compliance requirements for medical data access
