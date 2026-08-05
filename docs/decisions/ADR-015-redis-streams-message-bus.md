# ADR-015: Redis Streams as the v3 Message Bus

## Status
Accepted

## Date
2026-07-25

## Context

v2.0 uses PostgreSQL `LISTEN/NOTIFY` as its inter-process event bus. The `notify_event()` trigger on the `replicas` table publishes events to the `events` channel, which `sync.py` consumes to trigger replica sync. This works for the single-worker v2 architecture but has limitations:

- **No at-least-once delivery** — If the consumer crashes between receiving a NOTIFY and processing it, the message is lost. PostgreSQL NOTIFY is "fire and forget" with no persistence.
- **No consumer groups** — Multiple workers can subscribe to the same channel, but all receive every message. There is no built-in work distribution.
- **No message persistence** — NOTIFY messages exist only in shared memory (`max_queue_size: 8kB by default`). A backlog of events during a consumer outage is silently dropped.
- **No replay** — If a consumer needs to re-process old events (e.g., after a bug fix), there is no way to replay from a checkpoint.
- **Single channel** — All event types share one channel. v3 needs separate streams for ingestion, sync, notifications, and auth events.

v3 needs an event bus that supports:
1. At-least-once delivery with consumer groups
2. Message persistence for replay and backlog tolerance
3. Multiple streams with independent consumer groups
4. Monitoring of consumer lag
5. Cross-service communication (monolith ↔ ingestion service)

## Options Considered

| Option | Durability | Consumer Groups | Operational Cost | Notes |
|--------|-----------|----------------|------------------|-------|
| **Redis Streams** | In-memory (configurable persistence) | Yes (consumer groups) | Low (Redis already deployed) | Reuses existing Redis from v2 (db=0..4) |
| Kafka | Disk-persistent, replicated | Yes (consumer groups) | High (new cluster, ZK/KRaft) | Overkill for v3 scale (MB/s, not GB/s) |
| NATS JetStream | Disk-persistent | Yes (push/pull) | Medium (new binary) | Viable alternative, but new dependency |
| PostgreSQL LISTEN/NOTIFY + outbox table | Persistent (outbox table) | No (all workers get all) | Low (no new infra) | Requires polling or triggers for consumer group emulation |
| RabbitMQ | Disk-persistent | Yes (competing consumers) | Medium (new binary) | Good fit but adds 3rd message broker |

## Decision

Use **Redis Streams** as the primary message bus for v3.0. Four streams:

| Stream | Consumer Group(s) | Payload | TTL | maxlen |
|--------|------------------|---------|-----|--------|
| `events:ingestion` | `sync-worker`, `replica-worker`, `search-indexer` | `{study_uid, series_uid, instance_uid, hash, timestamp}` | 7 days | 100,000 |
| `events:sync` | `replica-worker` | `{replica_id, file_id, action}` | 24 hours | 10,000 |
| `events:notify` | `ws-broadcaster`, `webhook-sender` | `{file_id, change_type, by_user}` | 1 hour | 10,000 |
| `events:auth` | `token-blocklist` | `{jti, reason}` | 14 days | 100,000 |

**Key mechanics:**

1. **At-least-once delivery**: Consumer groups with explicit `XACK` after processing. If consumer crashes, pending entries are re-delivered.
2. **Persistence**: Redis AOF (Append-Only File) with `appendfsync everysec`. Acceptable durability for the event bus (irrecoverable data is in PostgreSQL, not in the bus).
3. **Backward compatibility**: A `PgNotifyBridge` process subscribes to the legacy `events` channel and publishes to Redis Streams so the existing `sync.py` worker continues to function during transition.
4. **Monitoring**: Consumer group lag (`XPENDING`, `XINFO GROUPS`) exposed as Prometheus gauges.

## Consequences

### Positive

- **No new infrastructure** — Redis is already deployed and configured (used for auth cache, token blocklist, rate limiting, WS pubsub).
- **Familiar operational model** — The team already manages Redis; no Kafka/ZK cluster or NATS binary to learn.
- **Existing code reuse** — `aioredis` already in requirements.
- **Graceful degradation** — If Redis is down, the system falls back to direct PostgreSQL writes (no queue, same as v2). The `events:ingestion` stream is not on the critical path for C-STORE or STOW-RS — those write directly to PostgreSQL + storage.

### Negative

- **In-memory base** — If Redis crashes before AOF flush, queued events are lost. Acceptable because the source of truth is PostgreSQL. Lost events cause missed sync/replication, which is caught by periodic reconciliation (v2 already does full-storage walks).
- **Single-node bottleneck** — Redis Streams are not sharded in open-source Redis. At v3 scale (target: 150 MB/s C-STORE), a single Redis node is sufficient. Cluster mode available if needed.
- **No exactly-once** — At-least-once means duplicate events are possible. Consumers must be idempotent (they already are — SHA-256 dedup).

## References

- ADR-014: Modular Monolith with Deferred Microservices
- PRD-v3.md §3.7 — Redis Streams Message Bus
- IMPLEMENTATION_PLAN-v3.md F1.1 — Redis Streams setup
- "Redis Streams in Practice" — Redis Labs, 2023