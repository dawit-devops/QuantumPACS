# Radiologist User Guide — QuantumPACS

Version: `feature/ris-integration` @ `bbe5c25` | Role: `radiologist` | Applies to: tenant-bound clinical workspace (`reading`)

## 1. About this role

The **radiologist** interprets imaging studies and produces diagnostic reports.
It is a clinical role whose home workspace is **Reading**. From the Reading
Worklist you open exams into the Reading Console, where you view images
(Cornerstone3D viewer), apply measurement/annotation tools, dictate structured
findings/impression, and move the report through **Draft → Preliminary →
Final** (sign-off). You also manage peer reviews, acknowledge critical results,
curate the teaching library, and use report templates.

This role is tenant-bound (you see your own facility's patients/studies) but
holds `CROSS_TENANT_READ` for teleradiology coverage work. It does **not** have
access to admin console, QA, Billing, Portal, or Metrics surfaces.

- Landing page after sign-in: **Reading Worklist** (`/reading`)
- Seeded login (dev): `acme.radiologist` / `Test@123456`

## 2. Signing in

1. Open the QuantumPACS URL and pick the tenant (e.g. **acme**).
2. Enter `acme.radiologist` and your password.
3. You land on the **Reading Worklist**.

## 3. Getting around

The sidebar (Reading section opens by default):

| Section | Items |
|---|---|
| **Reading** | Teaching Library, Reading Worklist, Peer Review, Critical Results |
| **Acquisition** | My Exams, Modality Worklist, Tracking Board, Schedule, Calendar, Resources (view-only) |
| **Coordination** | Orders, Prior Auth, Reminders, Care Plans, Communications, Patient Search (view-only) |
| **Admin** | Report Templates (only item — the rest of the admin console is hidden) |
| **Front Desk** | Today's Schedule (view-only) |
| **Files** | Files (study/file browser + viewer entry) |
| **Account** | Account, Notifications, Dark Mode, Logout |

## 4. Surface-by-surface guide

### 4.1 Reading Worklist  (`/reading`)
- Purpose: exams handed off for interpretation — your daily queue.
- How to: filter by **report status**, **modality**, patient/accession search,
  referring physician; toggle **Assigned to me**, **Awaiting review**,
  **Unread only**. "Signed today" counter shows your daily output. Auto-refreshes
  every 30 s.
- Actions per exam: **Continue** (resume an existing draft) or **Take**
  (claim the exam into your queue). "Assigned to me" narrows to your claims.
- Status: **PASS**.

### 4.2 Reading Console  (`/reading/:examId`)
- Purpose: the core workspace — images + report on one screen.
- How to:
  - **Viewer**: stack scroll (wheel), Pan (left-drag), Zoom (right-drag), Window
    Level (middle-drag). Keyboard: `1`-`6` tools (Pan/Length/Rect/Ellipse/Angle/
    Arrow), `7`/`e` eraser, `8` Cobb angle, `9` probe, `0` circle ROI, `i`
    invert, `r` rotate, `h`/`v` flip, `p` cycle W/L preset, `l` layout, `s` save
    annotations, `c` clear, `f`/`Esc` fullscreen, `←`/`→` prev/next image,
    `+`/`-` zoom, `?` help.
  - **Annotate**: measurements persist automatically to the file (`tools_state`);
    annotation changes sync live over the websocket for shared viewing.
  - **Report**: pick a **Report Template** to seed Findings/Impression (always
    review and tailor), write **Findings**, **Impression** (required to sign),
    and optional **Recommendations**.
  - **Workflow buttons**: **Save Draft**, **Mark Preliminary**, **Sign Report**,
    **Flag Critical**, **Submit to Teaching File**, **Immersive** (fullscreen
    viewer), **Version history**, **Prior reports**.
- Status: **PASS**. Note: exams without a stored DICOM study show "No imaging
  available" and the report renders full-width.

### 4.3 Teaching Library  (`/teaching`)
- Purpose: curated teaching cases for education.
- How to: browse by modality/body part/diagnosis/difficulty; submit a case from
  the Reading Console ("Submit to Teaching File") with teaching points and
  differential diagnosis.
- Status: **PASS**.

### 4.4 Peer Review  (`/peer-review`)
- Purpose: discrepancy-level reviews of signed reports assigned to you.
- How to: open an assigned review (only the assigned reviewer or the report
  author can open it — PHI guard), accept/decline, submit a discrepancy level
  with comment. The `peer_review.opened` event is audited.
- Status: **PASS** (empty state when nothing assigned).

### 4.5 Critical Results  (`/critical`)
- Purpose: reports flagged critical; acknowledge and manage delivery.
- How to: view flagged findings, acknowledge, track recipients.
- Status: **PASS** (empty state when none flagged).

### 4.6 Report Templates  (`/admin/report-templates`)
- Purpose: the template library that seeds your dictation.
- How to: browse by modality; **Edit** a template; view **History** (versions).
  Creating/publishing/rolling back templates requires `REPORT_TEMPLATE_ADMIN`
  (enforced — you hold it).
- Status: **PASS**.

### 4.7 Acquisition surfaces (view-only)
- **My Exams** `/exams` — technologist worklist (your facility's exams).
- **Modality Worklist** `/worklist` — scheduled-procedure worklist.
- **Tracking Board** `/tracking` — exam lifecycle tracking.
- **Schedule** `/schedule-board`, **Calendar** `/schedule`,
  **Resources** `/schedule/resources` — scheduling views.
- Status: **PASS** (view-only by design).

### 4.8 Coordination surfaces (view-only)
- **Orders** `/orders` — imaging requests across the facility.
- **Prior Auth** `/prior-auth`, **Reminders** `/reminders`,
  **Care Plans** `/care-plans`, **Communications** `/communications`,
  **Patient Search** — coordination views.
- Status: **PASS** (view-only by design).

### 4.9 Files  (`/`)
- Purpose: study/file browser + the DICOM viewer entry.
- How to: search studies/images, open a study into the viewer (annotations
  persist per file), download selection (zip/csv).
- Status: **PASS**.

### 4.10 Account  (`/account`) & Notifications (bell)
- Profile, password change, notification preferences; in-app feed.
- Status: **PASS**.

## 5. Common workflows (walkthroughs)

### 5.1 Read and sign a study (the core daily loop)
1. **Reading Worklist** → find an exam (or filter to **Assigned to me**).
2. Click **Take** to claim it (or **Continue** to resume a draft).
3. In the **Reading Console**: scroll through the series; use tools to measure
   (e.g. `2` Length, `3` Rectangle) — measurements auto-save.
4. Pick a **Report Template** for the modality (CT Head, CT Chest, etc.), then
   tailor **Findings** and **Impression**.
5. **Save Draft** as you work (auto-saves too). When confident: **Mark
   Preliminary** (if required by your workflow) then **Sign Report**.
6. The report is now **Final** and (in billing environments) auto-drops to the
   billing queue for coding.

### 5.2 Flag a critical finding
1. In the **Reading Console**, click **Flag Critical**.
2. The exam appears under **Critical Results** (`/critical`) for acknowledgement
   and recipient delivery.

### 5.3 Complete a peer review
1. **Peer Review** → open the assigned review.
2. Review the report + exam context, then **Submit** a discrepancy level with
   your comment.

### 5.4 Add a teaching case
1. In the **Reading Console**, click **Submit to Teaching File**.
2. Add title, diagnosis, teaching points, and differential diagnosis, then save.
3. Browse it later under **Teaching Library**.

### 5.5 Use prior reports for comparison
1. In the **Reading Console**, open **Prior reports**.
2. The patient's earlier reports (same modality by default) are listed for quick
   comparison — this access is audited (`report.priors_opened`).

## 6. Permissions summary

- Full grant set (23): read access to patients, orders, schedule, prior auth,
  worklist, reports, results, studies, files, exams, charts, medication orders;
  plus `REPORT_WRITE`, `REPORT_SIGN`, `CRITICAL_RESULTS_WRITE`,
  `REPORT_TEMPLATE_ADMIN`, `WORKLIST_WRITE`, `STUDY_EXPORT`,
  `PEER_REVIEW_READ/WRITE`, `DICOMWEB_READ` (legacy), and `CROSS_TENANT_READ`.
- **Cannot do**: admin console (Dashboard/RIS/Staff/Interface/DICOMweb console —
  hidden by `adminOnly`), QA, Billing, Portal, Metrics, Nursing, Front Desk
  registration/queue. Report Templates IS reachable.
- **Report lifecycle**: Draft (save), Preliminary, Final (sign); submitted/signed
  reports are locked against further edits (return-for-revision flow required).
- **Templates**: create/publish/rollback require `REPORT_TEMPLATE_ADMIN` (enforced
  on the backend since the role-walk).

## 7. Troubleshooting & known limits

- **"No imaging available"** in the console: the exam has no stored DICOM study
  yet — the report still works full-width.
- **Annotations not appearing**: re-open from the worklist (state is persisted to
  the file); check that measurement tools are active (keyboard shortcuts above).
- **Peer Review shows empty**: no reviews assigned to you yet.
- **Teleradiology cross-tenant access**: `CROSS_TENANT_READ` unlocks other
  tenants' studies granted to you; the dev `hf` tenant DB is now provisioned so
  cross-tenant reads no longer 500.
- **Cannot open admin console**: by design — clinical roles are excluded even
  when they hold a relevant legacy permission (e.g. DICOMweb console is now
  admin-scoped on both UI and API).
- **Security notes**: role-walk gaps — no MFA (HIGH), access token in
  `localStorage` (HIGH), token in login body (MEDIUM) are tracked for the
  IAM-hardening sprint.

---

*Generated by the supervised-role-walk skill (Phase 6) from SCOPE/PLAN/LEDGER +
backend/frontend inventories, 2026-08-27.*
