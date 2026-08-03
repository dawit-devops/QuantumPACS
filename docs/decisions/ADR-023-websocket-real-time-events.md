# ADR-023: WebSocket Transport for Real-Time Events

## Status
Accepted

## Date
2026-08-02

## Context
The frontend needs live updates for shared files and replica sync (a collaborator
opens a file; a DICOM study lands on another replica). Polling every replica is
expensive; the existing PostgreSQL LISTEN/NOTIFY replication channel must reach
browsers without exposing database details.

## Decision

- Single JSON WebSocket endpoint at `/api/v2/ws` (`WebsocketHandler`,
  `backend/api/ws.py`).
- **Authentication**: the auth middleware attaches `scope['user']` for both HTTP
  and WS requests. Browsers obtain a short-lived (`1 min`) JWT from
  `GET /api/v2/ws_token` and pass it as `?ws_token=` (or a header) — full JWTs
  never travel in query strings; the ephemeral ws_token is the only
  URL-carried credential (see ADR-024 for the same pattern).
- **Subscription model**: clients send `{type: 'open', file: <id>}` to register
  interest in a file. The server keeps `local_clients[file]` and, when Redis
  pub/sub is available, subscribes to the file's channel (`_channel(f)`) so
  events broadcast on any replica fan out to all connected browsers.
- **Messaging**: JSON envelopes with a `type` field (`open`, `send_state`,
  heartbeats, file events).
- **Robustness**: heartbeats keep the socket alive; `on_connect` failures
  (no middleware user, no state) are silently ignored so sockets never crash
  the connection; reconnect logic on the client re-subscribes.

## Alternatives Considered

- Server-Sent Events (SSE): simpler but one-way only; file collaboration needs
  client→server signaling.
- Long-polling: no push latency benefit, more request churn.

## Consequences

- Real-time file-state fan-out across replicas with a single multiplexed
  connection per browser.
- Clients must fetch a fresh `ws_token` per (re)connect — cheap, one HTTP call.
- No PHI is ever sent over WS without an authenticated channel (scope user or
  share-key grant from ADR-024).
