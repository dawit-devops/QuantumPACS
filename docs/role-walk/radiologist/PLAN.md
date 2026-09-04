# radiologist — Walk Plan (Phase 4)

Date: 2026-08-27
Order: Sidebar order (Reading section first — the role's workspace)

## Walk order

1. Reading Worklist `/reading` — landing; list exams awaiting report; filters (status/modality/search/radiologist); pagination; open into console
2. Reading Console `/reading/:examId` — core: viewer (stack, W/L, zoom/pan), tools (length/rect/angle/arrow), annotations (persist via `files/{id}`), report dictation (findings/impression/recommendations), draft save, submit, sign
3. Teaching Library `/teaching` — browse teaching files; add case from console
4. Peer Review `/peer-review` — inbox; accept/decline; open (PHI guard); submit discrepancy score
5. Critical Results `/critical` — flagged reports; ack/deliver
6. Report Templates `/admin/report-templates` — template library (REPORT_TEMPLATE_ADMIN now enforced for create/publish/rollback)
7. Files `/` + `/files/:id` — study/file browser; viewer entry; annotations
8. Patient `/patients/:id` — patient chart (read-only)
9. Acquisition (view-only): My Exams `/exams`, Modality Worklist `/worklist`, Tracking `/tracking`, Schedule `/schedule-board`, Calendar `/schedule`, Resources `/schedule/resources`
10. Coordination (view-only): Orders `/orders`, Prior Auth `/prior-auth`, Reminders `/reminders`, Care Plans `/care-plans`, Communications `/communications`
11. Front Desk Today's Schedule `/frontdesk/schedule` (SCHEDULE_READ visible)
12. Account `/account`, Notifications

## Expected API calls (per function)

| # | Function | Expected API (method + path → status) |
|---|---|---|
| 1 | Reading Worklist | `GET /reports/reading-list?status=&modality=&radiologist=me` → 200 |
| 2 | Reading Console | `GET /reports/{exam_id}` → 200; `GET /reports/{exam_id}/images` → 200; `GET /reports/priors?patient_id=` → 200; `PUT /reports/{exam_id}` → 200; `POST /reports/{exam_id}/submit` → 200; `POST /reports/{exam_id}/sign` → 200 |
| 3 | Teaching Library | `GET /teaching-files` → 200; `POST /teaching-files` → 201 |
| 4 | Peer Review | `GET /peer-reviews` → 200; `GET /peer-reviews/{id}` → 200; `POST /peer-reviews/{id}/accept|decline|submit` → 200 |
| 5 | Critical Results | `GET /notifications/critical` → 200; `POST /notifications/critical/{id}/ack` → 200 |
| 6 | Report Templates | `GET /ris/report-templates` → 200; `POST /ris/report-templates` → 201 (REPORT_TEMPLATE_ADMIN); `POST /ris/report-templates/{id}/publish|rollback` → 200 |
| 7 | Files | `GET /files?` → 200; `GET /files/{id}` → 200; `GET /files/{id}/changes` → 200 |
| 8 | Patient | `GET /patients/{id}` → 200 |
| 9 | Acquisition | `GET /exams` → 200; `GET /worklist` → 200; `GET /ris/tracking` → 200; `GET /ris/tracking/kpi` → 200; `GET /ris/appointments` → 200 |
| 10 | Coordination | `GET /orders` → 200; `GET /ris/prior-auth` → 200; `GET /ris/reminders/config|log` → 200; `GET /ris/care-plans` → 200; `GET /ris/communications` → 200 |
| 11 | Today's Schedule | `GET /ris/appointments?date=` → 200 |
| 12 | Account | `GET /account/profile|preferences` → 200 |

## Excluded routes (verify 403/redirect)
- Admin console (`/admin`, `/admin/ris-dashboard`, `/admin/staff-schedule`, `/dicomweb*`) → redirect to landing (adminOnly)
- QA/Billing/Portal/Metrics/Nursing → 403/redirect
- Nursing Prep `/nursing` → hidden

## Execution
**Phase 5a**: Unsupervised backend walk — curl each endpoint with `acme.radiologist` token, verify 2xx + tenant scoping
**Phase 5b**: Supervised browser walk — navigate each route as radiologist, exercise viewer/tools/report lifecycle, record
