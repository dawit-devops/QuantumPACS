# Feature: Worklist Polish

## Existing State

Worklist is functional: CRUD, status filters, batch actions, table/calendar views. Gaps:
1. No search input (API supports `search` param)
2. No date range filter (API supports `date_from`/`date_to`)
3. Missing table columns: Procedure ID, Procedure Desc, Study UID, Performed At
4. Pagination broken — `total = items.length` (no server-side count)
5. No station AE endpoint (frontend derives from loaded data)
6. No accession uniqueness enforcement

## Changes

### Backend

**Migration 027** — Add unique constraint on `worklist_entries.accession_number`:
```sql
CREATE UNIQUE INDEX IF NOT EXISTS uq_worklist_accession ON worklist_entries(accession_number) WHERE accession_number != '';
```

**`db/worklist.py:search()`** — Return `(items, total)` tuple instead of just items.

**`api/worklist.py:WorklistHandler.get()`** — Return `{data: items, total: N}` for pagination.

**New `GET /worklist/station-aes`** — Returns list of distinct station AE titles from the database.

### Frontend

- Add search `Input.Search` to toolbar
- Add `DatePicker.RangePicker` to toolbar
- Add columns: Requested Procedure ID, Procedure Description, Study UID, Performed At
- Fix pagination to use `total` from response
- Status guard: disable Mark Performed for non-scheduled entries
- Show Study UID + Performed At as extra detail

### Security

| Check | Status |
|-------|--------|
| Auth required | ✅ All endpoints behind `WORKLIST_READ`/`WORKLIST_WRITE` |
| Input validation | ✅ Pydantic schemas |
| Rate limiting | Not needed |
