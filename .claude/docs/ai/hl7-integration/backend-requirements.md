# Backend Requirements: HL7 Integration

## Context

HL7 v2.x integration enables RIS-to-PACS workflow — patient demographics updates (ADT) and order entry (ORM) from hospital EHR/HIS systems. This is an integration protocol with **no dedicated UI screens**; it affects data that the frontend displays on existing pages (Worklist, Patient, Study List).

**Current backend implementation**:
- MLLP listener on port 12579 (`backend/services/ingestion/hl7_server.py`)
- HTTP relay at `POST /api/hl7` (`backend/api/hl7.py`)
- SHA-256 hashing of raw HL7 messages for non-repudiation
- Database tables: `hl7_messages`, `hl7_parse_errors` (`backend/db/hl7_message.py`)
- ADT → patient upsert/deactivate/merge in `patients` table
- ORM → worklist entry creation in `worklist_entries` table
- TLS support via configurable cert/key (`hl7_mllp_tls_cert`, `hl7_mllp_tls_key`)
- IP whitelist (`hl7_mllp_allowed_ips`)
- **No outbound webhooks or ORU^R01 result messages**

---

## 1. Supported Message Types

### ADT (Admission/Discharge/Transfer)

| Event | Effect | Frontend Impact |
|-------|--------|-----------------|
| A01 (Admit) | Create/update patient record | Patient appears in Patient page, Study List |
| A03 (Discharge) | Deactivate patient (sets `meta.active = false`) | Patient shows inactive status on Patient page |
| A04 (Registration) | Create/update patient record | Same as A01 |
| A05 (Pre-Admit) | Create/update patient record | Same as A01 |
| A06 (Transfer) | Transfer patient (merge from source to destination) | Source patient marked inactive, destination gets records |
| A07 (Transfer) | Reverse transfer (unmerge) | Source patient re-activated |
| A08 (Update) | Update patient demographics | Patient name/DOB/sex refresh on Patient page |
| A40 (Merge) | Merge patient records | Surviving patient retains all data, merged patient deactivated |

**Patient fields updated**:
- `patient_id` (PID-3.1)
- `patient_name` (PID-5)
- `birth_date` (PID-7)
- `sex` (PID-8)
- `meta.sync_source` set to `"hl7"`
- `meta.tenant_id` set to sending facility
- `meta.active` set to `"false"` on A03 discharge or A06/A40 merge of source
- `meta.merged_into` set to surviving patient ID on A06/A40 merge

### ORM (Order Entry)

| Event | Effect | Frontend Impact |
|-------|--------|-----------------|
| O01 (Order) | Create worklist entry + upsert patient | New entry appears in Worklist page |

**Worklist entry fields created from ORM**:
- `patient_id`, `patient_name`, `patient_birth_date`, `patient_sex` (from PID)
- `accession_number` (ORC-2)
- `requested_procedure_id` (OBR-3)
- `requested_procedure_desc` (OBR-4)
- `modality` (OBR-24)
- `station_ae_title` (OBR-18)
- `scheduled_date` (OBR-7, first 8 chars)
- `scheduled_time` (OBR-7, chars 9-14)

If a worklist entry with the same `accession_number` already exists, the ORM is a no-op (returns success, no duplicate creation).

---

## 2. Message Processing Models

### Transport Options

| Transport | Port | Protocol | Usage |
|-----------|------|----------|-------|
| MLLP (raw TCP) | 12579 | Async TCP with 0x0B/0x1C0x0D framing | Hospital EHR direct connection |
| HTTP relay | 8080 | `POST /api/hl7` with raw HL7 in body | Web-based integration, testing |

### Synchronous vs. Queued

Currently **synchronous** — the HL7 handler (`default_handler` in `hl7_server.py:120`) processes the message inline:
1. Parse HL7 message
2. Store raw message + hash in `hl7_messages` table
3. Execute ADT/ORM handler (which opens a DB connection)
4. Return ACK/NACK

**Implications for frontend**:
- When a message creates a worklist entry, it exists in the DB immediately after the ACK is returned
- There is **no delay** — the next frontend poll/refresh will show the new/updated data
- The frontend **cannot subscribe** to HL7 processing results — no WebSocket event or webhook is emitted for HL7 processing outcomes
- If processing fails, the error is stored in `hl7_parse_errors` table but no notification reaches the frontend

---

## 3. Non-Repudiation

Each HL7 message is SHA-256 hashed before processing:

```python
raw_hash = hashlib.sha256(msg_bytes).hexdigest()
```

The hash is stored in `hl7_messages.raw_hash` with a unique index (`ix_hl7_messages_hash`). The raw message content is stored in `hl7_messages.raw_content` (UTF-8 decoded with `errors='replace'`).

**Frontend visibility**:
- `hl7_messages` table is queryable via admin API for audit trail display
- Each message record includes: `raw_hash`, `raw_content`, `message_type`, `event_type`, `patient_id`, `accession_number`, `sending_facility`, `parsed_fields` (JSONB), `parse_status`, `error_message`, `created_at`
- No current UI exposes the raw HL7 messages or their hashes — the admin HL7 message log would need to be built

---

## 4. Effects on Existing Frontend Pages

### Worklist Page
- **ORM^O01 → worklist entry created**: New entries appear after next page load/refresh
- Fields populated from ORM: accession number, procedure description, modality, scheduled date/time, patient info
- No WebSocket push — frontend must poll or the user must refresh
- Dedup by `accession_number` — if entry exists, ORM is skipped (no update)

### Patient Page
- **ADT A01/A04/A05/A08 → patient updated**: Patient name, DOB, sex, ID change on next load
- **ADT A03 → patient deactivated**: Patient page should show "inactive" status
- **ADT A40/A06 → patient merged**: Surviving patient retains all data; merged patient should show as "merged into [surviving ID]" and be hidden from normal search
- **ADT A07 → patient unmerge**: Source patient re-activated, `merged_into` removed

### Study List Page
- **ADT patient updates affect study records indirectly**: Studies linked to a patient via `studies.patient_id` will reflect the updated patient name/ID
- **No direct HL7 → study table mutation**: Studies are only created via DICOM C-STORE, STOW-RS, or file upload

---

## 5. Gaps

| Gap | Impact | Workaround |
|-----|--------|------------|
| No outbound HL7 (ORU^R01) | Cannot send result notifications back to RIS | RIS must poll or use FHIR |
| No webhook notifications for study completion | Frontend cannot auto-refresh when HL7-triggered study is completed | Manual refresh / polling |
| No WebSocket event for HL7 processing | Frontend cannot show real-time HL7 status | Admin must check HL7 message log |
| No UI for HL7 admin (dashboard, message log, config) | Admins cannot monitor HL7 pipeline or troubleshoot errors | Direct DB queries or logs |
| No partial ADT update granularity | ADT updates replace all patient fields at once (no per-field merge) | OK for current use case |
| No HL7 acknowledgment to frontend | When user uploads via HTTP relay, no processing result returned in UI | HTTP relay returns raw ACK text (not JSON) |

---

## 6. Uncertainties & Questions

### Timing & Visibility
- **When an HL7 message creates a worklist entry, does it immediately appear in the UI or is there a delay?** Immediate (synchronous DB write) — next frontend poll shows it.
- **Can the frontend subscribe to HL7 message processing results (success/failure)?** Not currently — no WebSocket event for HL7.
- **Are HL7 messages processed synchronously or queued?** Synchronously — no message queue.

### Patient Merge (A40/A06)
- **How does the frontend handle the merged patient record?** The surviving patient retains all studies; the merged patient is marked `meta.active = false` with `meta.merged_into = <surviving_id>`. The frontend should:
  - Hide inactive patients from normal search
  - Show "merged into [surviving ID]" on the merged patient's page
  - Link to the surviving patient's studies
- **Does the frontend need to display merged patient history?** Unknown — current Patient page doesn't show merge history.
- **When a patient is deactivated (A03), should their studies still be visible in search?** Unknown — currently no filter for `meta.active` in study search queries.

### Audit Trail
- **Is there a way to view raw HL7 messages from the audit log?** Not in the current UI — the `hl7_messages` table has the data but no frontend exposes it. An admin HL7 message log page would need to be built.
- **Should the SHA-256 hash be displayed in the UI for compliance verification?** Not currently, but needed for HIPAA audit trail compliance.
- **What retention policy applies to raw HL7 messages?** Unknown — raw content can be large; may need archival/cleanup.

### Technical
- **What happens if the MLLP listener is down when a hospital sends a message?** The hospital's sending system will get a TCP connection refused and must retry. No queueing/buffering.
- **Does the HTTP relay (`POST /api/hl7`) support authentication?** Not currently — no `requires_permission` decorator on `Hl7Receiver`.
- **Should the HTTP relay return JSON instead of raw HL7 ACK text?** Currently returns `PlainTextResponse` with ACK/ERR — frontend integrations would benefit from JSON with structured error info.
- **Can the MLLP listener be started/stopped via API?** Not currently — controlled by `lifecycle.py` via config.

---

## 7. Questions for Backend

1. **HLT message retention**: How long are raw HL7 messages and their content retained? Should the frontend provide a retention policy configuration?

2. **Merge visibility**: When ADT A40 merges a patient, does the frontend need to show both patients in search results? Should the merged patient's studies redirect to the surviving patient?

3. **Worklist dedup re-trigger**: If an ORM message arrives with an existing accession_number but different procedure details, should the worklist entry be updated? Currently it's a no-op.

4. **HTTP relay auth**: Should `POST /api/hl7` require authentication (e.g., `DICOMWEB_WRITE` or a new `HL7_WRITE` permission)?

5. **WebSocket events**: Should HL7 processing success/failure emit a WebSocket event so the admin dashboard can show real-time status? Or is the Admin HL7 message log (with polling) sufficient?

6. **ORU^R01 outbound**: Is there a plan to implement outbound HL7 for study completion notifications? The RIS needs to know when a study is complete and report is available.

7. **Error message format**: When `parse_hl7_message` fails, the error is stored as a free-text string. Should it include structured info (segment, field, position) for better admin diagnosis?

8. **Active/inactive patient filtering**: Should the study search (`POST /api/files/search`, QIDO-RS) exclude deactivated patients by default? Currently there's no `meta.active` filter.

9. **MLLP connection health endpoint**: Is there an API to check if the MLLP listener is running and accepting connections? Needed for admin dashboard health indicator.

10. **HL7 message log API**: Is there a paginated, filterable API to query `hl7_messages`? The frontend needs this for an admin HL7 message log. Currently the data is in the DB but no endpoint exposes it.
