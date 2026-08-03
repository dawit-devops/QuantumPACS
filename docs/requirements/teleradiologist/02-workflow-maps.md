# End-to-End Workflow Maps — Teleradiologist (R18)

**Role ID**: R18  
**Generated**: 2026-08-02  
**Version**: 1.0.0

---

## Workflow W1: Remote STAT Study Reading (frequency: multiple per shift, criticality: critical)

**User Intent**: Rapidly access and interpret urgent imaging for off-hours coverage with critical finding communication.

```mermaid
sequenceDiagram
    actor TR as Teleradiologist
    participant UI as Web UI
    participant WS as WebSocket
    participant API as Backend API
    participant DB as PostgreSQL
    participant Notif as Notification Service
    participant Clinician as On-Call Clinician

    Note over TR: Off-hours shift at home office
    TR->>UI: Login via SSO (Azure AD/Okta)
    UI->>API: OAuth code exchange
    API->>DB: Validate user, get sites & roles
    DB-->>API: User profile + site list
    API-->>UI: JWT token + tenant context
    UI-->>TR: Worklist dashboard (multi-site)

    Note over TR: WebSocket connection for live updates
    UI->>WS: Connect /ws/worklists/teleradiology
    WS-->>UI: Connection established

    Note over DB,WS: STAT study completed by R06
    DB->>WS: notify_event('worklist_update')
    WS-->>UI: New STAT study alert (audio + visual)
    UI-->>TR: "New STAT: CT Head - Site A"

    TR->>UI: Click STAT study row
    UI->>API: GET /api/v2/worklists/teleradiology?priority=STAT
    API->>DB: SELECT studies WHERE priority='STAT' AND status='pending'
    DB-->>API: Study list with assignment status
    API-->>UI: 200 + study metadata
    
    Note over UI: Background prefetch next 3 studies
    UI->>API: POST /api/v2/worklists/teleradiology/prefetch
    API-->>UI: 202 Accepted (job queued)

    TR->>UI: Open viewer for STAT study
    UI->>API: GET /api/studies/{id}/viewer
    API->>DB: SELECT study + series + instances
    DB-->>API: DICOM metadata + file paths
    API-->>UI: 200 + viewer config + WADO-URI URLs
    
    Note over UI: Cornerstone3D loads images
    UI-->>TR: First image displayed (LCP target: ≤2.5s)

    Note over TR: Reviews images, identifies subdural hematoma
    TR->>UI: Navigate series, MPR reconstruction
    UI-->>TR: Interactive viewer (INP target: ≤200ms)

    TR->>UI: Open report editor
    UI->>API: POST /api/reports (draft=true, preliminary=true)
    API->>DB: INSERT report (status='draft', type='preliminary')
    DB-->>API: Report ID
    API-->>UI: 201 + report ID

    Note over TR: Dictates findings (voice recognition)
    TR->>UI: Type/dictate report text
    UI->>API: PUT /api/reports/{id} (autosave every 10s)
    API->>DB: UPDATE report SET body=...
    DB-->>API: Success
    API-->>UI: 200 (optimistic update)

    Note over TR: Identifies critical finding
    TR->>UI: Mark as "Critical Finding"
    UI->>API: POST /api/v2/critical-findings
    API->>DB: INSERT critical_finding (report_id, urgency='critical')
    DB-->>API: Critical finding ID
    API->>Notif: Trigger escalation (SMS/page to on-call)
    Notif->>Clinician: SMS: "Critical finding: subdural hematoma - Dr. [TR]"
    API-->>UI: 201 + escalation ticket ID
    UI-->>TR: "Critical finding escalation sent"

    Note over TR: Phones on-call clinician directly (ACR guideline)
    TR->>Clinician: Phone call to discuss finding
    Clinician-->>TR: Acknowledged, patient to OR

    TR->>UI: Log clinician notification
    UI->>API: PUT /api/v2/critical-findings/{id}/notification-log
    API->>DB: UPDATE critical_finding SET clinician_notified_at=NOW(), method='phone'
    DB-->>API: Success
    API-->>UI: 200

    TR->>UI: Sign preliminary report
    UI->>API: PUT /api/reports/{id} (status='preliminary', signed=true)
    API->>DB: UPDATE report SET status='preliminary', signed_at=NOW()
    DB-->>API: Success
    API-->>UI: 200
    UI-->>TR: "Preliminary report signed - 18min from assignment"

    Note over TR: Report enters R12 finalization queue
    DB->>WS: notify_event('report_preliminary')
    WS-->>UI: Update worklist (study status: 'prelim complete')
```

### Friction & Cognitive Load Points
- **SSO login latency**: OAuth redirect + token exchange can take 5-10s over WAN — user perceives delay before seeing worklist
- **First-image load time**: 2.5s target may feel slow for STAT cases — aggressive prefetch and CDN caching needed
- **Dual workflow (report + phone)**: Teleradiologist must context-switch from UI to phone for critical findings — no automated dialing integration
- **Multi-site monitoring**: Visual scanning across multiple site tabs — lacks unified "all sites STAT" alert board
- **VPN instability**: Home network VPN drops can interrupt workflow mid-study — offline fallback needed

### Error & Exception Paths
1. **SSO authentication failure**: 
   - User sees "Unable to authenticate with [Provider]" 
   - Fallback: retry SSO, contact IT support
   - No password fallback for security
2. **WebSocket connection failure**:
   - UI shows "Live updates disconnected" warning banner
   - Fallback: poll API every 30s for worklist updates
   - Reconnect on network recovery
3. **Image load timeout (>10s)**:
   - UI shows "Image loading slowly - poor connection?" message
   - Offer: download offline package, switch to lower-quality preview
   - Log: network conditions for performance monitoring
4. **Critical finding escalation failure (SMS/page service down)**:
   - UI shows "Automated notification failed - call clinician directly"
   - Log: escalation failure for manual follow-up
   - Alert: PACS admin of notification service outage
5. **Report autosave failure (DB unreachable)**:
   - UI shows "Unsaved changes - connection lost"
   - Fallback: save draft to IndexedDB, sync when connection restored
   - Warning: do not close browser tab

---

## Workflow W2: Preliminary Report Review & Finalization (frequency: daily, criticality: high)

**User Intent**: On-site radiologist (R12) reviews teleradiologist preliminary reports and upgrades to final status.

```mermaid
sequenceDiagram
    actor SR as Staff Radiologist (R12)
    actor TR as Teleradiologist (R18)
    participant UI as Web UI
    participant API as Backend API
    participant DB as PostgreSQL
    participant Notif as Notification Service

    Note over SR: Morning shift, reviewing overnight prelim reports
    SR->>UI: Navigate to "Preliminary Reports" queue
    UI->>API: GET /api/reports?status=preliminary&assignee=me
    API->>DB: SELECT reports WHERE status='preliminary'
    DB-->>API: Preliminary report list
    API-->>UI: 200 + report list
    UI-->>SR: Table with 12 overnight reports

    SR->>UI: Click report to review
    UI->>API: GET /api/reports/{id}
    API->>DB: SELECT report + study + author
    DB-->>API: Report + metadata
    API-->>UI: 200 + report data
    
    Note over UI: Display report with "Preliminary by Dr. [TR]" badge
    UI-->>SR: Report text + author + timestamp

    SR->>UI: Open associated study viewer
    UI->>API: GET /api/studies/{id}/viewer
    API->>DB: Study metadata + instances
    DB-->>API: DICOM data
    API-->>UI: 200 + viewer config
    UI-->>SR: Side-by-side: report + images

    Note over SR: Reviews images, agrees with findings
    SR->>UI: Click "Finalize Report" button
    UI->>API: POST /api/v2/reports/{id}/finalize
    API->>DB: UPDATE report SET status='final', finalized_by='SR_id', finalized_at=NOW()
    DB-->>API: Success
    API->>Notif: Notify referring clinician (R14)
    Notif-->>API: Notification sent
    API-->>UI: 200 + finalized report
    UI-->>SR: "Report finalized"

    Note over SR: Discrepancy case: addendum needed
    SR->>UI: Add addendum to report
    UI->>API: PUT /api/reports/{id}/addendum
    API->>DB: INSERT addendum (parent_report_id, text, author)
    DB-->>API: Addendum ID
    API->>Notif: Notify teleradiologist of addendum (peer review)
    Notif->>TR: Email: "Addendum added to your preliminary report"
    API-->>UI: 201 + addendum
    UI-->>SR: "Addendum saved"

    Note over SR: Major discrepancy: QA flag
    SR->>UI: Flag for QA review (R05)
    UI->>API: POST /api/qa/discrepancies
    API->>DB: INSERT qa_event (report_id, type='discrepancy', severity='major')
    DB-->>API: QA event ID
    API->>Notif: Notify QA team + teleradiologist
    API-->>UI: 201 + QA ticket
    UI-->>SR: "QA review initiated"
```

### Friction & Cognitive Load Points
- **Report-to-image switching**: R12 must toggle between report view and viewer — lacks integrated side-by-side layout
- **Discrepancy documentation**: No structured discrepancy classification (false positive, false negative, missed finding) — free-text addendum only
- **Peer feedback loop**: Teleradiologist (R18) receives email notification but has no in-app feedback dashboard

### Error & Exception Paths
1. **Finalization conflict (report modified by R18)**:
   - UI shows "Report updated by [TR] 2min ago - reload before finalizing"
   - Fallback: reload report, re-review, finalize
2. **Addendum save failure**:
   - UI shows "Unable to save addendum - try again"
   - Fallback: copy text to clipboard, retry
3. **QA notification failure**:
   - UI shows "QA team notified (email pending)"
   - Fallback: manual email to QA coordinator

---

## Workflow W3: Multi-Site Coverage Dashboard (frequency: continuous during shift, criticality: medium)

**User Intent**: Monitor worklists across multiple hospital sites, prioritize by urgency and turnaround time.

```mermaid
sequenceDiagram
    actor TR as Teleradiologist
    participant UI as Web UI
    participant API as Backend API
    participant DB as PostgreSQL

    Note over TR: Shift start - home office, dual monitors
    TR->>UI: Login, lands on multi-site dashboard
    UI->>API: GET /api/v2/users/me/sites
    API->>DB: SELECT tenants WHERE user_id IN tenant_users
    DB-->>API: Site list with worklist counts
    API-->>UI: 200 + [Site A: 8 studies (3 STAT), Site B: 12 studies (1 STAT), Site C: 5 studies]
    UI-->>TR: Dashboard cards per site with color-coded urgency

    Note over UI: Poll every 30s for updates (WebSocket backup)
    UI->>API: GET /api/v2/worklists/teleradiology/summary
    API->>DB: Aggregate worklist counts per site
    DB-->>API: Counts + oldest STAT age
    API-->>UI: 200 + summary
    UI-->>TR: Real-time updates, STAT > 20min highlighted red

    TR->>UI: Click "Site A" card
    UI->>API: Switch tenant context (Site A)
    API->>DB: Exchange JWT token for Site A tenant
    DB-->>API: New token scoped to Site A
    API-->>UI: 200 + Site A token
    UI-->>TR: Site A worklist, sidebar context: "Site A"

    Note over TR: Works through Site A STAT queue
    TR->>UI: Complete study, return to dashboard
    UI->>API: GET /api/v2/users/me/sites (refresh counts)
    API->>DB: Updated counts
    DB-->>API: Site A: 7 studies (2 STAT)
    API-->>UI: 200
    UI-->>TR: Dashboard updated, Site A card shows 7 studies

    TR->>UI: Click "Site B" card (1 STAT aging)
    UI->>API: Switch tenant context (Site B)
    API->>DB: Exchange JWT token for Site B tenant
    DB-->>API: Site B token
    API-->>UI: 200
    UI-->>TR: Site B worklist
```

### Friction & Cognitive Load Points
- **Context switching overhead**: JWT token exchange for each site switch takes 1-2s — feels sluggish
- **Lack of unified STAT queue**: Must manually monitor multiple site cards — no "all sites STAT" view
- **Visual priority cues**: Color coding helps but lacks audio alert for new STAT arrivals across sites
- **No predictive workload**: Dashboard shows current counts but not projected inbound studies (HL7 scheduled exams)

### Error & Exception Paths
1. **Site unreachable (DB down for one tenant)**:
   - UI shows "Site C unavailable - contact Site C IT"
   - Fallback: continue working other sites, alert PACS admin
2. **Token exchange failure**:
   - UI shows "Unable to switch to Site B - session expired?"
   - Fallback: re-authenticate via SSO
3. **Stale worklist counts (WebSocket + polling both fail)**:
   - UI shows "Last updated: 5min ago" warning
   - Fallback: manual refresh button, alert user of connectivity issue

---

## Workflow W4: Offline Study Access (frequency: as-needed, criticality: medium)

**User Intent**: Download study for offline reading during connectivity outages or travel.

```mermaid
sequenceDiagram
    actor TR as Teleradiologist
    participant UI as Web UI
    participant API as Backend API
    participant BG as Background Job Queue
    participant Storage as File Storage
    participant DB as PostgreSQL

    Note over TR: Anticipating VPN instability, pre-downloads studies
    TR->>UI: Right-click study row, "Download Offline Package"
    UI->>API: POST /api/v2/studies/{id}/offline-package
    API->>DB: Check user permission, log request
    DB-->>API: Authorized
    API->>BG: Queue job: generate_offline_package(study_id, user_id)
    BG-->>API: Job ID
    API-->>UI: 202 Accepted + job_id
    UI-->>TR: "Preparing offline package (est. 30s)..."

    Note over BG: Background worker processes job
    BG->>DB: SELECT instances for study
    DB-->>BG: Instance list
    BG->>Storage: Fetch DICOM files
    Storage-->>BG: Raw DICOM files
    BG->>BG: Decompress lossless JPEG 2000 to uncompressed
    BG->>BG: Bundle: viewer HTML + DICOM + metadata JSON
    BG->>BG: Encrypt ZIP with AES-256, password = user-specific key
    BG->>Storage: Write encrypted ZIP to /offline-packages/
    Storage-->>BG: ZIP URL
    BG->>DB: UPDATE job SET status='complete', url='...'
    DB-->>BG: Success

    Note over UI: Polling for job status every 2s
    UI->>API: GET /api/v2/jobs/{job_id}
    API->>DB: SELECT job status
    DB-->>API: status='complete', url='/offline-packages/study_{id}.zip'
    API-->>UI: 200 + download URL
    UI-->>TR: "Download ready" notification + link

    TR->>UI: Click download link
    UI->>API: GET /offline-packages/study_{id}.zip
    API->>Storage: Fetch ZIP (with auth token check)
    Storage-->>API: Encrypted ZIP stream
    API-->>UI: ZIP file (2GB)
    UI-->>TR: Browser download: study_12345.zip

    Note over TR: VPN drops, opens offline package
    TR->>TR: Unzip file, open viewer.html
    Note over TR: Standalone HTML viewer (Cornerstone3D + embedded DICOM)
    TR->>TR: Read study, dictate report in separate app
    TR->>TR: Connectivity restored

    TR->>UI: Login, upload draft report
    UI->>API: POST /api/reports (sync offline draft)
    API->>DB: INSERT report
    DB-->>API: Report ID
    API-->>UI: 201
    UI-->>TR: "Draft report synced"
```

### Friction & Cognitive Load Points
- **Download time**: 30s for 500-instance study (2GB) — requires proactive planning before VPN issues
- **Password management**: User must securely store decryption password — potential friction
- **Offline report drafting**: Separate app (Word, Notes) — no integrated offline editor, must manually sync on reconnect
- **Storage cleanup**: User must manually delete downloaded ZIP files — no auto-expiry warning

### Error & Exception Paths
1. **Background job failure (disk full, DB timeout)**:
   - UI shows "Offline package generation failed - contact support"
   - Fallback: retry job, manual DICOM export via PACS admin
2. **Download interrupted (network drop mid-transfer)**:
   - Browser shows "Download failed"
   - Fallback: resume download (if server supports Range requests), or regenerate package
3. **Decryption failure (wrong password, corrupted ZIP)**:
   - Offline viewer shows "Unable to decrypt package"
   - Fallback: re-download package, verify file integrity
4. **Offline report sync conflict (study already finalized by R12)**:
   - UI shows "Study finalized while offline - save as addendum?"
   - Fallback: attach offline draft as addendum, notify R12

---

## Workflow W5: Second Opinion Consultation (frequency: daily, criticality: medium)

**User Intent**: Provide consultative second opinion to on-site radiologist without taking over primary read responsibility.

```mermaid
sequenceDiagram
    actor SR as Staff Radiologist (R12)
    actor TR as Teleradiologist (R18)
    participant UI_SR as Web UI (R12)
    participant UI_TR as Web UI (R18)
    participant API as Backend API
    participant DB as PostgreSQL
    participant Notif as Notification Service

    Note over SR: Complex case, needs subspecialty opinion
    SR->>UI_SR: Open study, click "Request Consultation"
    UI_SR->>API: POST /api/v2/consultations
    API->>DB: INSERT consultation (study_id, requesting_user='SR', priority='routine', question='')
    DB-->>API: Consultation ID
    API->>Notif: Notify teleradiologist roster (on-call subspecialist)
    Notif->>TR: Email + in-app notification: "Consultation request from Dr. [SR]"
    API-->>UI_SR: 201 + consultation ID
    UI_SR-->>SR: "Consultation requested - awaiting response"

    Note over TR: Checks in-app consultation queue
    TR->>UI_TR: Navigate to "Consultations" tab
    UI_TR->>API: GET /api/v2/consultations?assignee=me&status=pending
    API->>DB: SELECT consultations
    DB-->>API: Consultation list
    API-->>UI_TR: 200 + consultations
    UI_TR-->>TR: List: "Consultation from Dr. [SR] - chest CT question"

    TR->>UI_TR: Click consultation row
    UI_TR->>API: GET /api/v2/consultations/{id}
    API->>DB: SELECT consultation + study + messages
    DB-->>API: Consultation thread
    API-->>UI_TR: 200 + consultation data
    UI_TR-->>TR: Study link + SR's question

    TR->>UI_TR: Open study viewer
    UI_TR->>API: GET /api/studies/{id}/viewer
    API->>DB: Study metadata
    DB-->>API: DICOM data
    API-->>UI_TR: 200 + viewer
    UI_TR-->>TR: Images displayed

    Note over TR: Reviews images, formulates opinion
    TR->>UI_TR: Type consultation response
    UI_TR->>API: POST /api/v2/consultations/{id}/responses
    API->>DB: INSERT consultation_message (author='TR', text='...')
    DB-->>API: Message ID
    API->>Notif: Notify requesting radiologist (SR)
    Notif->>SR: Email: "Consultation response from Dr. [TR]"
    API-->>UI_TR: 201 + message
    UI_TR-->>TR: "Response sent"

    TR->>UI_TR: Mark consultation as "Consulted" (no report sign-off)
    UI_TR->>API: PUT /api/v2/consultations/{id}/status
    API->>DB: UPDATE consultation SET status='completed', consultant='TR'
    DB-->>API: Success
    API-->>UI_TR: 200
    UI_TR-->>TR: "Consultation closed"

    Note over SR: Receives notification, reads response
    SR->>UI_SR: Navigate to consultation thread
    UI_SR->>API: GET /api/v2/consultations/{id}
    API->>DB: SELECT consultation + messages
    DB-->>API: Thread with TR's response
    API-->>UI_SR: 200
    UI_SR-->>SR: "Dr. [TR] suggests: likely organizing pneumonia..."

    SR->>UI_SR: Incorporate opinion into final report
    UI_SR->>API: PUT /api/reports/{id} (add note: "Consultation with Dr. [TR]")
    API->>DB: UPDATE report
    DB-->>API: Success
    API-->>UI_SR: 200
    UI_SR-->>SR: "Report updated"
```

### Friction & Cognitive Load Points
- **Asynchronous communication**: Email + in-app notifications — lacks real-time chat or video for urgent consults
- **Context loss**: Teleradiologist must reconstruct clinical question from text — no voice/video context
- **Report integration**: On-site radiologist must manually copy consultation text into report — no auto-append

### Error & Exception Paths
1. **No consultant available (all teleradiologists offline)**:
   - UI shows "No consultants available - try later or escalate to attending"
   - Fallback: email to department head, manual phone call
2. **Consultation response timeout (>24h no response)**:
   - UI shows "Consultation pending >24h" warning to requesting radiologist
   - Escalation: auto-notify department coordinator
3. **Consultation assignment conflict (multiple TR respond)**:
   - First responder assigned, others notified "Already answered by Dr. [TR]"

---

## Integration Touchpoints Summary

| Workflow | External System | Integration Type | Data Flow |
|----------|-----------------|------------------|-----------|
| W1 (STAT Reading) | Hospital On-Call System | SMS/Page API (Twilio, PagerDuty) | Critical findings → clinician notification |
| W1 (STAT Reading) | Voice Dictation (Dragon Medical) | Plugin/API | Audio → report text |
| W2 (Finalization) | Referring Clinician Portal | Notification Service | Final report → R14 notification |
| W3 (Multi-Site) | Azure AD / Okta | OAuth/OIDC | SSO authentication + site access |
| W4 (Offline) | None | Standalone HTML viewer | Self-contained DICOM viewer bundle |
| W5 (Consultation) | Email Service | SMTP | Consultation notifications |

## Performance Targets by Workflow

| Workflow | Critical Metric | Target | Rationale |
|----------|-----------------|--------|-----------|
| W1 | First-image load (WAN) | ≤ 2.5s p95 | ACR teleradiology diagnostic threshold |
| W1 | STAT turnaround (assignment → prelim report) | ≤ 30min | ACR guideline + hospital SLA |
| W1 | Critical finding notification latency | ≤ 15min | ACR guideline |
| W2 | Preliminary report review queue load | ≤ 2s LCP | R12 morning workflow efficiency |
| W3 | Site-switching token exchange | ≤ 2s | Minimize context-switch overhead |
| W3 | Worklist update staleness | ≤ 5s | Real-time confidence for remote monitoring |
| W4 | Offline package generation | ≤ 30s for 500-inst study | Proactive download window |
| W5 | Consultation response time | ≤ 4h (routine), ≤ 1h (urgent) | Peer review timeliness |
