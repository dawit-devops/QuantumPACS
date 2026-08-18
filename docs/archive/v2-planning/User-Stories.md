# QuantumPACS — Comprehensive User Story Catalog

**Version**: 2.0.0
**Status**: Final
**Date**: 2026-07-23

---

## Organization

- **Epics**: Major capability areas (numbered E1–E8)
- **User Stories**: Numbered per epic (e.g., E1-S1)
- **Acceptance Criteria**: Gherkin-style `Given/When/Then` for automated testing
- **Priority**: P0 (critical), P1 (important), P2 (nice-to-have)

---

## Epic E1: Study Acquisition & Ingestion

### E1-S1: DICOM C-STORE Receiving

> As a technologist, I want to send DICOM studies from any modality to QuantumPACS so that images are available for reading immediately.

**Priority**: P0

**Acceptance Criteria**:
```
Given a DICOM modality is configured to send to QuantumPACS on port 11112
When the modality sends a C-STORE request with a valid DICOM dataset
Then the server responds with status 0x0000 (Success)
And the file is stored in the master storage backend
And the patient, study, and series metadata are upserted into PostgreSQL
And the file hash (SHA-256) prevents duplicate storage if re-sent

Given a C-STORE request with a malformed or non-DICOM payload
When the server receives the request
Then the server responds with status 0x0001 (Failure)
And no file is written to storage
And no database records are created

Given a C-STORE request for a study that already exists (duplicate)
When the server receives the request
Then the server responds with status 0x0000 (Success)
And the file is NOT duplicated in storage (SHA-256 dedup)
And the database returns the existing file record

Given the database connection pool is exhausted
When a C-STORE request arrives
Then the server responds with status 0x0001 (Failure)
And the error is logged to the logs table
```

### E1-S2: Manual File Upload

> As a technologist, I want to upload DICOM files through the web interface so that I can manually add studies from offline modalities or removable media.

**Priority**: P1

**Acceptance Criteria**:
```
Given I am an authenticated user on the Files page
When I click "Upload" and select one or more DICOM files
Then the files are uploaded via POST /api/files/upload
And files are processed identically to C-STORE reception
And successfully uploaded files disappear from the upload list
And I see a confirmation that uploads completed

Given I am an authenticated user on the Files page
When I click "Upload" and select a directory
Then all DICOM files in the directory are uploaded
And non-DICOM files in the directory are silently skipped

Given the uploaded file is not a valid DICOM
When the upload is processed
Then I see an error message for that file
And no database records are created
```

### E1-S3: Upload Progress Feedback

> As a technologist, I want to see upload progress so that I know when large studies have finished.

**Priority**: P2

**Acceptance Criteria**:
```
Given I am uploading one or more large DICOM files
When the upload is in progress
Then I see a progress bar or percentage indicator per file
And the overall upload completion percentage

Given an upload fails mid-transfer
When the error occurs
Then I see which file failed
And the other files continue uploading
```

---

## Epic E2: Study Search & Discovery

### E2-S1: Global Full-Text Search

> As a radiologist, I want to search all studies by any text so that I can quickly find relevant exams without knowing exact DICOM tags.

**Priority**: P0

**Acceptance Criteria**:
```
Given I am on the Files page
When I type a query in the search box and press Enter
Then the search is executed against Elasticsearch with multi_match across all indexed fields
And results are returned within 500ms for a 10k-study dataset
And search terms are highlighted in yellow in the results
And the URL updates to encode the search query (bookmarkable)
And the table shows matching studies with patient ID, name, study description, modality

Given I type a partial name (e.g., "Smi" for "Smith")
When I press Enter
Then the search returns studies where any field starts with or contains "Smi"
And results are sorted by relevance

Given I clear the search box and press Enter
When the search executes
Then all studies are returned (most recent first)
```

### E2-S2: Column-Specific Filter Search

> As a PACS administrator, I want to filter results by a specific DICOM field so that I can narrow down large result sets.

**Priority**: P1

**Acceptance Criteria**:
```
Given I am on the Files page with search results displayed
When I open a column filter (e.g., "Modality") and enter "CT"
Then the table filters to only show CT studies
And the URL updates to encode the filter
And the global search box is cleared

Given I have an active column filter
When I click "Reset" on that filter
Then the filter is removed
And the table returns to the previous unfiltered state

Given I have both a global search active and a column filter
When I add a new column filter
Then the global search is cleared
And only the column filter applies
```

### E2-S3: Advanced DICOM Tag Search

> As a radiologist, I want to search by specific DICOM tags (e.g., Referring Physician, SOP Class UID) so that I can find studies matching precise clinical criteria.

**Priority**: P1

**Acceptance Criteria**:
```
Given I am on the Files page
When I click "Advanced Search"
Then a modal appears with 12 predefined fields: Patient ID, Patient's Name, Patient's Age, Patient's Gender, Study ID, Study Description, Series Number, Series Modality, Series Description, Referring Physician, Performing Physician, SOP Class UID

Given the advanced search modal is open
When I fill in one or more fields and click "Search"
Then the table filters to studies matching ALL specified criteria
And the URL updates to encode the advanced search parameters

Given I need a field not in the predefined list
When I click "Add" in the advanced search modal
Then a new empty row appears with editable label and value inputs

Given I have added a custom field
When I click the remove button on that row
Then the custom field is removed
And the remaining fields are unaffected
```

### E2-S4: Study List Pagination & Sorting

> As a radiologist, I want to paginate and sort search results so that I can efficiently scan through large result sets.

**Priority**: P1

**Acceptance Criteria**:
```
Given I have search results with more than 10 studies
When I view the table
Then I see pagination controls at the bottom
And the page size is configurable (default 10)

Given I click a column header (e.g., "Patient Name")
When the table sorts
Then the results are sorted ascending on that column
And clicking again reverses to descending
And the sort order is encoded in the URL

Given I navigate to page 3 of results
When I perform a new search
Then the pagination resets to page 1
```

### E2-S5: Search When Elasticsearch Is Unavailable

> As a PACS administrator, I want the search to degrade gracefully when Elasticsearch is down so that the system remains usable during ES maintenance.

**Priority**: P1

**Acceptance Criteria**:
```
Given Elasticsearch is unavailable (connection refused or timeout)
When any user performs a search
Then the search returns an empty results array with status 200
And the application does not crash or show an error toast
And all other functionality (viewing, uploading, management) continues working

Given Elasticsearch returns to health
When the next search is executed
Then the search returns results normally
No application restart is required
```

---

## Epic E3: Image Viewing & Interpretation

### E3-S1: DICOM Image Rendering

> As a radiologist, I want to open a DICOM study in my browser and see the images rendered without any plugins or downloads so that I can start reading immediately.

**Priority**: P0

**Acceptance Criteria**:
```
Given I click on a file result in the search table
When the Detail page loads
Then the Image tab is active by default
And the DICOM image is rendered in a Cornerstone3D viewport within 2 seconds (LAN)
And the viewport shows the image with default window/level settings

Given the DICOM file has multiple frames
When the viewport renders
Then all frames are available for scrolling

Given I navigate directly to a /files/:id URL with a temp share key
When the page loads
Then the viewer renders identically (no login required)
And only the Image tab is available (other tabs hidden)
```

### E3-S2: Stack Scrolling

> As a radiologist, I want to scroll through image stacks so that I can review multi-slice studies efficiently.

**Priority**: P0

**Acceptance Criteria**:
```
Given I am viewing a multi-slice study (e.g., CT with 500 slices)
When I use the mouse wheel
Then the viewport scrolls through slices
And the scroll is smooth (no perceptible loading between slices)

Given I am viewing a single-image study (e.g., CR)
When I use the mouse wheel
Then no scrolling occurs
And no scroll indicator is shown
```

### E3-S3: Window/Level Adjustment

> As a radiologist, I want to adjust window width and center so that I can optimize image contrast for different tissue types.

**Priority**: P0

**Acceptance Criteria**:
```
Given I am viewing a DICOM image
When I right-click and drag on the viewport
Then the window width and center adjust in real-time
And the current WW/WC values are displayed in the bottom-right overlay

Given I have adjusted window/level
When I load another image in the same series
Then the window/level settings persist for the session

Given I have adjusted window/level
When I reload the page
Then the default window/level is restored
```

### E3-S4: Pan & Zoom

> As a radiologist, I want to pan and zoom images so that I can examine regions of interest in detail.

**Priority**: P0

**Acceptance Criteria**:
```
Given I am viewing a DICOM image
When I left-click and drag
Then the image pans in the direction of the drag
And the zoom level is displayed in the bottom-left overlay

Given I have zoomed in
When I middle-click and drag (or use scroll wheel while zoom tool is active)
Then the zoom level changes in real-time

Given I have panned or zoomed
When I scroll to a different slice
Then the pan/zoom position is maintained
```

### E3-S5: Measurement Tools

> As a radiologist, I want to measure distances, angles, and regions of interest so that I can take clinical measurements.

**Priority**: P0

**Acceptance Criteria**:
```
Given I click the Length tool button
When I click and drag on the image
Then a line is drawn with the length in millimeters displayed
And the measurement is visible on all collaborators' viewers (WebSocket sync)

Given I click the Angle tool button
When I click three points on the image
Then an angle is drawn with the degrees displayed

Given I click the Rectangle ROI tool button
When I click and drag on the image
Then a rectangle is drawn with area displayed
And mean/standard deviation of pixel values within the ROI are displayed

Given I click the Ellipse ROI tool button
When I click and drag on the image
Then an ellipse is drawn with area displayed
And mean/standard deviation of pixel values within the ROI are displayed

Given I click the Arrow annotation button
When I click and then click again on the image
Then an arrow annotation with associated text label is placed
```

### E3-S6: Annotation Persistence

> As a radiologist, I want my annotations to be saved so that I can close the study and return to my measurements later.

**Priority**: P1

**Acceptance Criteria**:
```
Given I have placed annotations on an image
When I click the Save button
Then the annotations are persisted to the server via PATCH /api/files/:id
And the tools_state is updated in the database

Given I reopen a study with saved annotations
When the viewer loads
Then all previously saved annotations are restored on the image

Given a collaborator has saved annotations
When I have the study open in another browser
Then I see the collaborator's annotations in real-time via WebSocket
```

### E3-S7: Annotation Sync via WebSocket

> As a radiologist, I want to see annotations made by colleagues in real-time so that we can collaborate on cases.

**Priority**: P1

**Acceptance Criteria**:
```
Given two users have the same study open in their browsers
When User A adds or modifies an annotation
Then User B sees the annotation appear within 500ms

Given the WebSocket connection drops
When the connection is re-established
Then the current annotation state is sent to the reconnecting client
And all annotations are present

Given User A deletes an annotation
When the deletion occurs
Then User B sees the annotation disappear within 500ms
```

### E3-S8: Image Orientation Controls

> As a radiologist, I want to rotate and flip images so that I can view anatomy in the correct orientation.

**Priority**: P1

**Acceptance Criteria**:
```
Given I am viewing a DICOM image
When I click the Rotate button
Then the image rotates 90 degrees clockwise
And each subsequent click rotates another 90 degrees

Given I click the Horizontal Flip button
When the action executes
Then the image is mirrored horizontally

Given I click the Vertical Flip button
When the action executes
Then the image is mirrored vertically

Given I click the Invert button
When the action executes
Then the image colors are inverted (white → black, black → white)
And clicking again restores original colors
```

### E3-S9: Series Navigation

> As a radiologist, I want to navigate between files in a series so that I can review all images sequentially.

**Priority**: P0

**Acceptance Criteria**:
```
Given I am viewing a series with multiple files (instances)
When the viewer loads
Then a slider appears at the bottom showing the current position

Given I drag the slider
When I release
Then the viewport loads the corresponding file
And any unsaved annotations on the previous file are NOT lost

Given the series has only one file
When the viewer loads
Then no slider is shown

Given I am viewing a file in a series
When I use the breadcrumb dropdown to switch to another series
Then the viewer loads the first file of the new series
```

### E3-S10: Study-to-Study Navigation

> As a radiologist, I want to navigate between studies of the same patient so that I can compare current and prior exams.

**Priority**: P1

**Acceptance Criteria**:
```
Given I am viewing a study in the Detail page
When I click the study dropdown in the breadcrumb
Then I see a list of all studies for this patient
When I select a different study
Then the viewer loads the first series and first file of that study

Given I navigate between studies
When the target study loads
Then the Image tab is active
```

---

## Epic E4: Patient Browsing

### E4-S1: Patient Information Display

> As a radiologist, I want to see patient demographics so that I can confirm patient identity before interpretation.

**Priority**: P1

**Acceptance Criteria**:
```
Given I click a Patient ID link from the search results
When the Patient page loads
Then I see patient information: ID, Name, Sex, Birth Date
And the data is displayed in a loading-aware table

Given the patient ID does not exist
When the page loads
Then a 404 error toast appears
And I am redirected to the search page
```

### E4-S2: Study/Series/File Tree

> As a radiologist, I want to browse studies, series, and files in a hierarchical tree so that I can understand the patient's imaging history at a glance.

**Priority**: P1

**Acceptance Criteria**:
```
Given I am on the Patient page with data loaded
When I view the page
Then I see a three-level tree: Study → Series → File
And the tree defaults to expanded state

Given a study has a description
When I view the tree
Then the study node shows "<StudyID> (<description>)"
And series nodes show "<SeriesNumber> (<Modality>) <description>"

Given a study has no description
When I view the tree
Then the study node shows "<StudyID>" only

Given I click a file (leaf) node
When the selection occurs
Then I am navigated to /files/<fileId>

Given I click a study or series (non-leaf) node
When the selection occurs
Then nothing happens (the node expands/collapses instead)
```

---

## Epic E5: File Sharing & Collaboration

### E5-S1: Expiring Share Links

> As a radiologist, I want to generate expiring share links so that referring physicians can view studies without creating accounts.

**Priority**: P1

**Acceptance Criteria**:
```
Given I am on the Share tab of a file
When I enter a duration (hours) and click "Share"
Then a share link is generated via POST /api/files/:id/share
And the link is displayed in a modal with a copy button

Given I click "Copy" on the share link modal
When the copy executes
Then the share link is copied to my clipboard

Given a referring physician opens the share link
When the page loads
Then the viewer opens directly (no login screen)
And only the Image tab is visible
And the sidebar is hidden

Given a referring physician opens an expired share link
When the page loads
Then they see a 401 error
And they are redirected to the login page

Given the original file is deleted
When someone opens a share link for that file
Then they see a 404 error
```

### E5-S2: Bulk Download

> As a radiologist, I want to download multiple studies as a ZIP archive so that I can share them with colleagues outside the PACS.

**Priority**: P2

**Acceptance Criteria**:
```
Given I select multiple files in the search results table
When I click "Download files"
Then a ZIP archive is generated containing the selected DICOM files
And the archive is named using patient/study/series information
And the download begins automatically

Given I select multiple files
When I click "Download data (CSV)"
Then a CSV file is generated containing metadata of selected files
And the CSV has all unique metadata keys as columns
And the download begins automatically

Given I select no files and click download
When the action is attempted
Then nothing happens (button is disabled or no-op)

Given a download fails due to a network error
When the error occurs
Then I see an error toast
```

---

## Epic E6: File Management

### E6-S1: DICOM Metadata Viewing

> As a radiologist, I want to view full DICOM metadata so that I can verify acquisition parameters and protocol details.

**Priority**: P1

**Acceptance Criteria**:
```
Given I am on the Data tab of a file
When the tab loads
Then I see a table of all DICOM metadata key-value pairs, sorted alphabetically

Given I have many metadata fields
When I type in the search box above the table
Then the table filters to only show keys matching the search text

Given I click a metadata value
If the field is marked editable
Then the value becomes an inline input for editing
If the field is not editable
Then nothing happens (value is read-only)
```

### E6-S2: Metadata Change Audit Trail

> As a PACS administrator, I want to see a history of all metadata changes so that I can audit who changed what and when.

**Priority**: P1

**Acceptance Criteria**:
```
Given I am on the Changes tab of a file
When the tab loads
Then I see a paginated table of all changes with: time (UTC), username, change type

Given a metadata field is edited or an annotation is saved
When the change is logged
Then a new entry appears in the Changes table
And the entry includes: timestamp, user who made the change, type of change, old value, new value
```

### E6-S3: File Deletion

> As a PACS administrator, I want to delete files so that I can remove incorrectly uploaded studies or manage storage.

**Priority**: P1

**Acceptance Criteria**:
```
Given I am an admin user on the Admin tab of a file
When I click the "Delete" button
Then the file is soft-deleted (deleted=true in database)
And the file is removed from all replica storage backends
And the file is removed from the Elasticsearch index
And I am navigated to the search page after 1 second

Given I delete a file that is the only copy across all replicas
When the deletion occurs
Then the file record is physically removed from the database
And all associated replica_files records are removed
And the file_change log is preserved

Given a non-admin user accesses the Admin tab
When they view the page
Then no delete button is shown (tab is hidden entirely)
```

**Known Issue**: No confirmation dialog before deletion.

---

## Epic E7: Administration

### E7-S1: User Lifecycle Management

> As a PACS administrator, I want to create, view, and deactivate user accounts so that only authorized personnel can access the system.

**Priority**: P0

**Acceptance Criteria**:
```
Given I am an admin user on the Users page
When the page loads
Then I see a table of all users with: ID, Username, Role (ADMIN/USER), Status (ACTIVE/DEACTIVATED)

Given I click "Add user"
When the modal opens
Then I can enter a username and toggle admin privileges
When I click Create
Then a new user is created with a randomly generated password
And the password is displayed in a modal (shown once)

Given I click "Reset password" on a user row
When the action executes
Then a new random password is generated for that user
And the password is displayed in a modal

Given I click "Deactivate" on an active user
When the confirmation popup is accepted
Then the user's status changes to DEACTIVATED
And the user cannot log in even with valid credentials
And the table refreshes to show the updated status

Given a deactivated user attempts to log in
When they submit credentials
Then they receive a 401 error
And the audit log records the failed attempt
```

### E7-S2: Replica Configuration

> As a PACS administrator, I want to configure and monitor storage replicas so that I can manage data redundancy and disaster recovery.

**Priority**: P1

**Acceptance Criteria**:
```
Given I am an admin user on the Replicas page
When the page loads
Then I see a table of all configured replicas with: ID, Type, Master/Replica, Location, Delay, Status, Files count
And the table auto-refreshes every 2 seconds

Given I click "Add replica"
When the modal opens
Then I can select from three types: Local (file path), S3 (region + key/secret), B2 (app key ID + key)
And I can configure sync delay in minutes

Given I add a new replica
When the configuration is saved
Then the sync daemon begins copying all existing files to the new replica
And the status transitions from "indexing" to "ok" as files are copied

Given I click "Set master" on a replica
When the action executes
Then that replica becomes the new source of truth
And other replicas begin syncing from it

Given I click "Delete" on a replica
When the confirmation popup is accepted
Then the replica is removed from the configuration
And the associated replica_files records are cleaned up
```

### E7-S3: System Log Viewer

> As a PACS administrator, I want to view system logs so that I can troubleshoot errors and monitor system health.

**Priority**: P1

**Acceptance Criteria**:
```
Given I am an admin user on the Logs page
When the page loads
Then I see a paginated table of log entries with: Time (UTC), Log (last 2 lines preview)

Given I click "Expand" on a log row
When the action executes
Then I see the full log text

Given the logs grow large
When I navigate through pages
Then logs are loaded server-side (not all at once)
```

### E7-S4: File Upload (Admin)

> As a PACS administrator, I want to manually upload DICOM files to test the system or recover from backup.

**Priority**: P1

**Acceptance Criteria**:
```
Given I am an admin user on the Files page
When I click "Upload"
Then a modal appears with two upload options: files (multiple) and directory

Given I select files via the "Upload files" button
When the upload completes
Then the files appear in the search results on next refresh

Given I select a directory via the "Upload directory" button
When the upload completes
Then all DICOM files in the directory are ingested
```

---

## Epic E8: Authentication & Security

### E8-S1: User Login

> As any user, I want to log in with my username and password so that I can access the system securely.

**Priority**: P0

**Acceptance Criteria**:
```
Given I am not logged in
When I navigate to any protected page
Then I am redirected to /login

Given I am on the login page
When I enter valid credentials and click "Sign In"
Then a JWT token is issued (14-day default expiry)
And I am redirected to the Files page
And my user ID, admin status, and token are stored in localStorage

Given I enter invalid credentials
When I click "Sign In"
Then I see an error toast
And I remain on the login page

Given I am a deactivated user
When I enter valid credentials
Then I receive a 401 error
And the login fails
```

### E8-S2: Token-Based API Authentication

> As a developer integrating with QuantumPACS, I want to authenticate API requests using JWT tokens so that I can build integrations.

**Priority**: P0

**Acceptance Criteria**:
```
Given a valid JWT token
When I make an API request with X-Auth-Pacs header
Then the request is authenticated
And the response includes the requested data

Given an expired JWT token
When I make an API request
Then I receive a 401 response

Given no token is provided
When I make an API request to /api/health or /api/login
Then the request succeeds (public endpoints)
When I make an API request to any other endpoint
Then I receive a 401 response
```

### E8-S3: Password Change

> As any user, I want to change my password so that I can maintain account security.

**Priority**: P1

**Acceptance Criteria**:
```
Given I am logged in
When I navigate to /account
Then I see a form to enter a new password (two fields for confirmation)

Given I enter matching passwords
When I click "Change password"
Then my password is updated
And I see a success toast

Given I enter mismatched passwords
When I click "Change password"
Then I see a validation error
And the password is not updated
```

### E8-S4: Audit Logging

> As a PACS administrator, I want all authentication events and file changes to be logged so that I can maintain an audit trail for HIPAA compliance.

**Priority**: P1

**Acceptance Criteria**:
```
Given any user action (login, file view, annotation save, share link creation)
When the action occurs
Then the event is logged to the file_changes or logs table
And the log entry includes: timestamp, user ID, action type

Given a failed authentication attempt
When the failure occurs
Then the attempt is logged (without storing the password)
```

---

## Non-Functional Stories

### NF-1: Concurrent Viewer Sessions

> As a PACS administrator, I want the system to support at least 50 concurrent viewer sessions so that the entire radiology department can use it simultaneously.

**Acceptance Criteria**:
```
Given 50 radiology workstations simultaneously viewing different studies
When all viewers are actively scrolling and measuring
Then each viewer's first-image latency is ≤ 2 seconds
And the API response time for P95 requests is ≤ 500ms
And no viewer experiences disconnection or timeout
```

### NF-2: Large Study Loading

> As a radiologist, I want to load large studies (10,000+ instances) without browser crashes so that I can review CTAs and other volumetric studies.

**Acceptance Criteria**:
```
Given a study with 10,000 DICOM instances
When I open the first file
Then the first image renders within 5 seconds
And scrolling to subsequent images loads progressively
And memory usage stays below 2 GB in the browser tab
```

### NF-3: Storage Failover

> As a PACS administrator, I want the system to continue serving files when the primary storage backend fails so that radiologists can keep reading.

**Acceptance Criteria**:
```
Given a replica storage backend is configured and in sync
When the master storage backend fails
And the replica is promoted to master
Then file access continues uninterrupted
And the promotion takes effect within the sync delay window
```

### NF-4: Zero-Downtime Schema Migration

> As a PACS administrator, I want to apply database schema changes without requiring system downtime so that I can keep the PACS available during updates.

**Acceptance Criteria**:
```
Given a new Alembic migration is available
When I run the migration
Then new columns have nullable defaults or are added via ALTER TABLE ADD COLUMN IF NOT EXISTS
And existing database connections are not interrupted
And the application handles both old and new schema versions during the migration window
```

---

## Story Mapping: Epic-to-Release Matrix

| Story | Priority | v2.0 | v2.1 | v2.2 | v3.0 |
|-------|----------|------|------|------|------|
| E1-S1: C-STORE receiving | P0 | ✅ | | | |
| E1-S2: Manual upload | P1 | ✅ | | | |
| E1-S3: Upload progress | P2 | | ✅ | | |
| E2-S1: Full-text search | P0 | ✅ | | | |
| E2-S2: Column filter | P1 | ✅ | | | |
| E2-S3: Advanced tag search | P1 | ✅ | | | |
| E2-S4: Pagination/sorting | P1 | ✅ | | | |
| E2-S5: ES fallback | P1 | ✅ | | | |
| E3-S1: DICOM rendering | P0 | ✅ | | | |
| E3-S2: Stack scroll | P0 | ✅ | | | |
| E3-S3: Window/level | P0 | ✅ | | | |
| E3-S4: Pan/zoom | P0 | ✅ | | | |
| E3-S5: Measurement tools | P0 | ✅ | | | |
| E3-S6: Annotation persistence | P1 | ✅ | | | |
| E3-S7: WebSocket annotation sync | P1 | ✅ | | | |
| E3-S8: Orientation controls | P1 | ✅ | | | |
| E3-S9: Series navigation | P0 | ✅ | | | |
| E3-S10: Study navigation | P1 | ✅ | | | |
| E4-S1: Patient info | P1 | ✅ | | | |
| E4-S2: Study tree | P1 | ✅ | | | |
| E5-S1: Share links | P1 | ✅ | | | |
| E5-S2: Bulk download | P2 | ✅ | | | |
| E6-S1: Metadata viewing | P1 | ✅ | | | |
| E6-S2: Audit trail | P1 | ✅ | | | |
| E6-S3: File deletion | P1 | ✅ | | | |
| E7-S1: User management | P0 | ✅ | | | |
| E7-S2: Replica management | P1 | ✅ | | | |
| E7-S3: System logs | P1 | ✅ | | | |
| E7-S4: File upload UI | P1 | ✅ | | | |
| E8-S1: Login | P0 | ✅ | | | |
| E8-S2: Token auth | P0 | ✅ | | | |
| E8-S3: Password change | P1 | ✅ | | | |
| E8-S4: Audit logging | P1 | ✅ | | | |
| MWL SCP | P1 | | ✅ | | |
| DICOM Print SCP | P2 | | ✅ | | |
| HL7 ADT/ORM | P1 | | ✅ | | |
| Study routing rules | P2 | | ✅ | | |
| Prometheus metrics | P2 | | ✅ | | |
| FHIR R4 API | P1 | | | ✅ | |
| Multi-tenancy | P1 | | | ✅ | |
| OAuth 2.0 / OIDC | P1 | | | ✅ | |
| AI inference pipeline | P2 | | | ✅ | |
| Structured report viewer | P2 | | | ✅ | |
| Microservices | P1 | | | | ✅ |
| DICOMweb API | P1 | | | | ✅ |
| C-MOVE / C-GET | P1 | | | | ✅ |
| Mobile viewer | P2 | | | | ✅ |
| Role delegation | P2 | | | | ✅ |
