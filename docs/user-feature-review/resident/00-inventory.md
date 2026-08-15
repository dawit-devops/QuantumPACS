# 00 — Resident Surface Inventory

Role: `resident` — `MATRIX_B_RES` permissions (backend/api/permissions.py:257)
Landing: `/reading/home` (Resident Home — navigator.ts:264)
Workspace: `reading` (clinical-scoped; navigator.ts:64)
Login: `test.resident` / `Test@123456` (seed_test_users.py, platform-side)

## Reachable surfaces (walked live, 2026-08-14)

| # | Route | Page | Permission gate | Walkthrough result |
|---|-------|------|-----------------|--------------------|
| 1 | `/reading/home` | ResidentHome (frontend/src/radiologist/ResidentHome.tsx) | REPORT_READ | Loads. Queue counts (STAT/Urgent/Routine), Feedback & Progress, Teaching Library (placeholder), recent exams. Auto-refresh 30s. Evidence: `01-resident-home.png` |
| 2 | `/reading` | ReadingWorklist | REPORT_READ | Loads. Status/modality filters, patient/accession search, referring physician search, "Assigned to me" + "Awaiting review" checkboxes. Empty queue (all resident exams co-signed FINAL → leave queue). |
| 3 | `/reading/:examId` | ReadingConsole | REPORT_READ | Loads for claimed exam. Report stepper Draft→Submitted→Co-signed; FINAL banner with signer + timestamp. Evidence: `04-reading-console-final.png` |
| 4 | `/schedule-board` | ScheduleBoard | SCHEDULE_READ (route) | **FAILS**: page errors "Missing permission: WORKLIST_READ". Nav exposes it (Acquisition menu) but backend needs WORKLIST_READ the resident lacks. Evidence: `02-schedule-board-failure.png` |
| 5 | `/` | Files | STUDY_READ/FILE_READ | Loads: search, advanced, study table with real studies (10/page, pagination). |
| 6 | `/files/:id` | Detail viewer | FILE_READ | Cornerstone viewport loads DICOM (CT_small.dcm), Image/Data/Share/Changes/Measures tabs. Evidence: `03-files-detail-viewer.png` |
| 7 | `/account` | Account | auth | Profile, role, permissions list, change-password form. |
| 8 | Notifications bell | Notifications popover | — | 3 items: 2× "Report co-signed" (with attending action), 1× "Report returned for revision" (with feedback text). Read-all/dismiss-all work. |
| 9 | `/users` (probe) | — | USER_READ (not held) | Correctly bounced to `/reading/home` — gates work. |

## API calls observed (network)
- `GET /api/ws_token` 200, `GET /api/reports/reading-list?radiologist=me` 200
- `GET /api/notifications/unread-count` 200
- `GET /api/v2/tenants` **403** (expected — platform-only; called by schedule page)
- `GET /api/schedule?…` → 403 WORKLIST_READ (surface #4 failure)

## Console issues
- `[issue] A form field element should have an id or name attribute (count: 2)` — worklist filter selects.
- No JS errors during walkthrough.
