# Requirements Review: Phase 4 — Integration (HL7 + FHIR + Routing)

## Context

QuantumPACS v3.0 adds healthcare interoperability protocols beyond DICOM. Hospitals use HL7 v2.x for patient demographics (ADT) and orders (ORM), and FHIR R4 as the emerging RESTful API standard for EHR integration. This phase makes QuantumPACS a first-class participant in hospital IT ecosystems.

**Principle from PRD**: "RIS integration, not built-in RIS" — provide the endpoints that external RIS/EHR applications use, without becoming a RIS itself.

---

## Scope Breakdown

### F4.1 — HL7 v2.x MLLP Listener (3 weeks)

| Sub-feature | What | Risk |
|---|---|---|
| F4.1a MLLP server | Async TCP server with MLLP framing (0x0B/0x1C0D), configurable port (default 12579), TLS | Low — straightforward asyncio pattern |
| F4.1b ADT handlers | A01 (admit), A08 (update), A03 (discharge), A04/A05 (create) → patient upsert | Medium — field mapping complexity, HL7 variant differences |
| F4.1c ORM handler | O01 → worklist entry creation via ORC/OBR segments → MWL | Medium — segment position varies across HL7 versions |
| F4.1d Audit + errors | SHA-256 hashing per message, NACK on malformed, unknown segments logged | Low — standard pattern |

**ADR-012 adds**: `hl7_messages` table, `hl7_parse_errors` table, patient `meta` JSONB extended with `sync_source`. These are not in the implementation plan checklist but are in the ADR.

### F4.2 — FHIR R4 API (3 weeks)

| Sub-feature | What | Risk |
|---|---|---|
| F4.2a Scaffold | CapabilityStatement at `/api/v2/fhir/metadata`, `application/fhir+json` | Low |
| F4.2b Patient resource | Search by identifier/name/birthdate, read by ID | Low — maps 1:1 to `patients` table |
| F4.2c ImagingStudy resource | Search by patient/accession/modality/started, nested series/instances | Medium — complex nested JSON structure per FHIR spec |
| F4.2d DocumentReference | Search by patient/type/period, links to share URLs | Low — placeholder for v3.1 reports |

### F4.3 — Study Routing Rules (1 week)

| Sub-feature | What | Risk |
|---|---|---|
| F4.3a Rule engine | `routing_rules` table, JSONB conditions evaluated on ingestion | Medium — condition matching could get complex |
| F4.3b CRUD API | Standard CRUD for routing rules | Low |

---

## Gaps & Issues

### 1. ADR-012 vs Implementation Plan Mismatch

ADR-012 specifies a **separate `hl7_messages` audit table** and **`hl7_parse_errors` table** with full raw message retention. The implementation plan only mentions "logged with SHA-256 hash for non-repudiation" without specifying table structure.

**Recommendation**: Follow ADR-012. Create `hl7_messages` table (migration 019). The plan is underspecified here.

### 2. HL7 MLLP Server — Process Model

The plan says "Run in the **ingestion service** (separate process, extracted in Phase 1)". But:
- Phase 1 did NOT extract a separate process for the ingestion service
- The ingestion worker (`worker.py`) runs in-process alongside the Starlette app
- The DICOM AE server runs as a background thread via the lifespan

**Question**: Should the MLLP listener run as:
- (a) Background thread like the DICOM AE server (simpler, consistent)
- (b) Separate asyncio task in the same process (natural for async TCP)
- (c) Truly separate process (per ADR-019, but doesn't exist yet)

**Recommendation**: Option (b) — add asyncio task in the lifespan alongside `_start_dicom()`. This is consistent with the existing pattern and avoids premature process extraction.

### 3. FHIR Route Prefix

Plan specifies `/api/v2/fhir/...` but our current DICOMweb routes are at `/dicomweb/...` (without `/api/v2` prefix). All existing routes are mounted under `/api` in `routes.py`:
```python
routes = [
    Mount('/api', app=Router(routes)),
]
```

So a route `GET /fhir/metadata` becomes `GET /api/fhir/metadata`. If the plan means `/api/v2/fhir/...`, that would be `GET /api/v2/fhir/metadata` → requires either a nested mount or full path in the route.

**Recommendation**: Use `/fhir/...` (becomes `/api/fhir/...` under the `/api` mount). Consistent with how other routes work. Rename `/api/v2/` paths in the plan to match actual routing.

### 4. FHIR Library Choice

Plan says "Add `fhir.resources` or build minimal FHIR resource serializers". The `fhir.resources` library is a validation/ serialization library that ensures FHIR conformance.

**Question**: Do we need strict FHIR validation or can we build minimal dict-based serializers?

**Recommendation**: Build minimal dict-based serializers. FHIR R4 resources are well-specified JSON structures — we don't need a full validation library for 3 resource types. If compliance testing reveals issues later, add `fhir.resources` then.

### 5. Routing Rules — Condition Engine

F4.3a condition JSONB `{"modality": "CT", "study_description": {"contains": "CHEST"}}` needs a matching engine that supports:
- Exact match (string, number)
- `contains` operator (substring)
- `gt`, `lt`, `gte`, `lte` (numeric/date)
- Logical AND (implicit in JSON object keys)
- No OR support specified (is that intentional?)

**Question**: Is OR support needed? Should conditions support `{"$or": [...]}` syntax?

**Recommendation**: Start with implicit AND + exact/contains operators. Add OR/`$or` when a use case requires it. The scope is already 1 week.

### 6. Patient Sync Source Tracking

ADR-012 mentions tagging patients with `sync_source` (hl7/dicom/manual) in the `meta` JSONB column. The implementation plan doesn't mention this.

**Recommendation**: Add sync source tagging — it's essential for audit and conflict resolution when the same patient is updated by both HL7 and DICOM paths with different values.

### 7. HL7 Port Conflict with Existing DICOM Ports

Default HL7 MLLP port is 12579 (plan) vs 2575 (ADR-012). These differ.

**Recommendation**: Use 12579 (plan value — less likely to conflict with common services on 2575 which is sometimes used by other apps). Add to `default_config` as `hl7_mllp_port`.

### 8. No Frontend Implications

Phase 4 is purely backend infrastructure. No new UI components needed. However, existing UI may benefit:
- Patient list could show sync source indicator
- Admin settings could show HL7 listener status
- These are v3.1 concerns

---

## Recommended Build Order

```
Week 1:  F4.1a MLLP server + F4.1b ADT handlers (core HL7 pipeline)
Week 2:  F4.1c ORM handler + F4.1d audit/error handling (complete HL7)
Week 3:  F4.2a FHIR scaffold + F4.2b Patient resource (basic FHIR)
Week 4:  F4.2c ImagingStudy + F4.2d DocumentReference (FHIR complete)
Week 5:  F4.3a Rule engine + F4.3b CRUD API (routing)
Week 6:  Integration tests, edge cases, Phase 4 gate
```

## Dependencies

| Dependency | Purpose | Install |
|---|---|---|
| `hl7` / `python-hl7` | HL7 v2.x message parsing | New |
| `fhir.resources` (optional) | FHIR validation | Deferred |
| `cryptography` | SHA-256 for audit hashing | Already present |

## Key Diagrams to Reference

- ADR-012: HL7 ADT/ORM field mapping tables (columns: HL7 Field → DICOM/PACS Field → Table)
- ADR-019: FHIR resource mapping tables (columns: FHIR Resource → Source Table → Key Maps)
- PRD-v3 §3.2: Integration points overview
- PRD-v3 §4.2: FHIR endpoint specification table

---

## Open Questions for Backend

1. Process model — background asyncio task vs separate process for MLLP?
2. FHIR route prefix — `/fhir/...` vs `/api/v2/fhir/...` under existing `/api` mount?
3. FHIR library — minimal dict builders vs `fhir.resources`?
4. Routing conditions — need `$or`/`$and` operators or just implicit AND?
5. Sync source — track in patient `meta` JSONB or separate column?
6. HL7 message storage — full table with raw content or just hash in log?
7. What happens if MLLP connection drops? Reconnect strategy?
8. TLS for MLLP — self-signed cert during dev, CA-signed in prod?
9. Do we need IP whitelisting in v3.0 or is that v3.1?
10. Should FHIR `ImagingStudy` include an `endpoint` reference to the WADO-RS URL?

## Discussion Log

*Review pending — awaiting backend decisions on open questions.*
