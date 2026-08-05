# Backend Requirements: Search

## Context

Search is the primary way users find studies on the Study List (Files) page. It is used by all interactive personas — Radiologists, Technologists, Clinicians, and PACS Admins.

The frontend supports three search modes that compose together:

### 1. Global Search Bar

A single text input at the top of the page. Triggers search on debounced input.

**What fields it searches across:**
- Patient Name
- Patient ID
- Accession Number
- Study Description

**Match behavior:** Contains/substring match (not exact, not full-text stemming). Case-insensitive.

**Debounce:** 300ms after last keystroke before firing the search request.

**Special characters:** Backend should handle sanitization. If the query contains characters that break ES/Lucene syntax (e.g., `+ - && || ! ( ) { } [ ] ^ " ~ * ? : \ /`), the backend should escape them or switch to a simple term query.

**Behavior when empty:** Returns all accessible studies (paginated, default sort).

**Broad terms (single character):** Accepted — returns all (or paginated subset of) matching results. Not rejected. The frontend does not enforce minimum query length.

### 2. Column Filter Search

Per-column text input in the table header area for columns: Patient ID, Patient Name, Study ID, Study Description, Series Number, Series Description.

**Match behavior:** Contains/substring match per field. Case-insensitive.

**AND logic:** When multiple column filters are active, they compose as AND. Results must match all active filters.

### 3. Advanced Search Modal

Modal with 12 structured DICOM tag fields:
1. Patient ID
2. Patient Name
3. Patient Age
4. Patient Gender
5. Study ID
6. Study Description
7. Series Number
8. Series Modality
9. Series Description
10. Referring Physician
11. Performing Physician
12. SOP Class UID

**Match behavior:** Contains/substring match per field (same as column filters).

**Logic between fields:** AND — all populated fields must match.

**Logic between modes:** Global search + column filters + advanced search compose as AND across all modes.

## Search Result: Fields Returned

Each result row should include:
- Unique file/study identifier (for detail page link)
- Patient ID (for patient page link)
- Patient Name
- Patient database ID (for patient page link)
- Study ID / Study UID
- Study Description
- Series Number
- Series Description
- Modality
- Study date
- Creation/upload date

## Sorting

Default sort order: by study date descending (newest first).

**Current frontend:** No sort selector — default sort only. If sort controls are added, they should accept: `study_date`, `patient_name`, `created_at` with `asc`/`desc` direction.

## Pagination

Offset-based pagination. The frontend sends `page` (1-indexed) and `pageSize` params.

**Response should include:**
- `results`: array of study/series objects
- `total`: total count of matching results (for "Showing X-Y of Z" display)
- `page`: current page number
- `pageSize`: page size used

**Max results:** No hard cap on page number, but very broad queries (single letter) may return many pages. The frontend handles pagination UI.

## Search State & Bookmarkability

Search state is encoded in the URL as a JSON string.

**What gets encoded:** Global search query, all active column filters, all active advanced search fields, current page number.

**State restoration:** On page load, the frontend reads the URL params, restores all search inputs to their previous state, and re-issues the search query.

## Backend Search Source

Primary search backend is **Elasticsearch** for full-text across all indexed DICOM tags.

### Elasticsearch Details

- Index mappings should support substring/prefix matching on the searchable fields
- Special character escaping as noted above
- Search should be tenant-scoped (index per tenant or filter by tenant field)

### Fallback: QIDO-RS

When Elasticsearch is unavailable (down, timeout, not configured), the backend falls back to DICOMweb QIDO-RS.

**Field differences in fallback mode:**
- Not all 12 advanced search fields may be supported by QIDO-RS — the backend should return an error or silently drop unsupported query params
- QIDO-RS results may lack some study metadata fields that ES/DB provides
- The response format should be normalized to match the ES response shape as closely as possible
- The frontend is notified of fallback mode via a response header or field (e.g., `X-Search-Source: qidors`) and may show a subtle "Search using direct DICOMweb" indicator

## Error Handling

| Scenario | Behavior |
|----------|----------|
| ES down / timeout | Fall back to QIDO-RS automatically. If QIDO-RS also fails, return 503 with message "Search unavailable" |
| Malformed query | Return 400 with details on which param is invalid |
| Special characters in query | Backend sanitizes silently — no error surfaced to user |
| QIDO-RS unsupported field | Return error for that specific field or silently drop it; document which fields are unsupported |
| Tenant has no data | Return empty result set with `total: 0` (not an error) |

## Uncertainties & Questions

- Is global search full-text across all fields or specific fields?
- Are search results sorted by relevance or by a specific field?
- What happens when the search query contains special characters?
- Does advanced search use AND or OR between fields?
- Is there a way to search by date range (study date, creation date)?
- Can I get search suggestions/autocomplete as the user types?
- Are searches with very broad terms (single letter) rejected or returned with pagination?
- Does ES index all DICOM tags or just specific fields?
- Is there a separate per-tenant ES index or a shared index with tenant filter field?
