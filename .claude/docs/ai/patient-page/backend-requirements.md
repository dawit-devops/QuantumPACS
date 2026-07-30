# Patient Page — Backend Requirements

## Page
`GET /patients/{id}` — Radiologists, Clinicians, Technologists

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/patients/{id}` | Get patient demographics |
| `GET` | `/api/patients/{id}/studies` | Get study hierarchy tree |

## Data Model

```
Patient {
  id: uuid                  // internal DB ID
  patient_id: string        // DICOM PatientID
  name: string
  date_of_birth: string     // ISO date or partial date
  sex: string               // M, F, O, or empty
  tenant_id: uuid
}

PatientStudy {
  id: uuid
  study_uid: string         // DICOM StudyInstanceUID
  study_id: string          // DICOM StudyID
  description: string
  date: string              // ISO date
  series: PatientSeries[]
}

PatientSeries {
  id: uuid
  series_uid: string        // DICOM SeriesInstanceUID
  series_number: number
  description: string
  modality: string          // e.g. CT, MR, XR, US
  files: PatientFile[]
}

PatientFile {
  id: uuid
  sop_uid: string           // DICOM SOPInstanceUID
  name: string              // filename or instance number
  url: string               // link to detail /files/{id}
}
```

## Patient Demographics
- Patient ID (DICOM PatientID) — primary displayed identifier
- Internal DB ID (shown in UI metadata or tooltip)
- Name (formatted)
- Date of birth
- Sex

## Study/Series/File Tree
- 3-level hierarchy: Study (parent) → Series (child) → File (leaf)
- Each study is expandable/collapsible
- Study row shows: StudyID, description, date
- Series row shows: Series number, description, modality
- File row shows: file name, clickable link to detail page
- Empty studies (no series) shown with "(No series)" indicator

## States

| State | Behaviour |
|-------|-----------|
| Patient found, has studies | Show demographics + tree |
| Patient found, no studies | Show demographics + empty state message: "No studies found for this patient" |
| Patient not found | Show 404 error message: "Patient not found" |
| Loading | Show skeleton/spinner |

## Navigation
- Click study row → expand/collapse series list
- Click file row → navigate to `GET /files/{id}` detail page

## Uncertainties & Questions
1. What demographic fields are available for a patient?
2. Is the hierarchy always 3 levels (study → series → file) or can it vary?
3. Should I show study dates in the tree?
4. Can a patient have studies across multiple tenants (for merged patients)?
5. How is the patient ID displayed — internal DB ID or DICOM PatientID?
