# Integration Spec: FHIR ImagingStudy + DICOMweb Zero-Footprint Viewer

**Team:** `pacs-ris-research` · **Compiled:** 2026-08-04 · Companion to `research/pacs-ris-architecture-deep-dive.md` (§2 DICOMweb, §3 FHIR imaging)

---

## 1. Purpose & Scope

This specification defines how a **zero-footprint HTML5 imaging viewer** (OHIF/Cornerstone-class) retrieves and displays radiology studies using:

- **FHIR** (`ImagingStudy`, `Endpoint`) to discover studies and their DICOMweb endpoints in clinical context, and
- **DICOMweb** (QIDO-RS / WADO-RS) to query metadata and stream pixels.

It is intended as the reference integration for the **EHR-launched viewer** pattern (SMART on FHIR) plus a **standalone viewer** pattern.

### Audience
Integration engineers, solution architects, and vendor implementers.

---

## 2. Architectural Overview

```
EHR / RIS
   │  SMART on FHIR launch (iss + launch)
   ▼
Zero-Footprint Viewer (OHIF)
   │  1. GET /ImagingStudy?patient=...   (FHIR)
   │  2. resolve Endpoint → DICOMweb base URL
   │  3. GET {base}/studies?...          (QIDO-RS)
   │  4. GET {base}/studies/{uid}...     (WADO-RS metadata + pixels)
   ▼
DICOMweb Server (PACS/VNA)  ── pixels from object storage
```

Two flows:
1. **SMART-on-FHIR (in-EHR):** viewer receives `iss` + `launch`, authenticates via SMART, reads `ImagingStudy`, then pulls pixels via DICOMweb with a bearer token (IHE IUA).
2. **Standalone (direct link):** viewer is launched with `StudyInstanceUIDs` and talks straight to DICOMweb.

---

## 3. FHIR Resources

### 3.1 ImagingStudy (as served to the viewer)

```json
{
  "resourceType": "ImagingStudy",
  "id": "example-imaging-study",
  "identifier": [
    {
      "system": "urn:ietf:rfc:3986",
      "value": "urn:oid:2.16.840.113883.2.4.3.11.999.123456789.df"
    }
  ],
  "status": "available",
  "modality": [
    {
      "system": "http://dicom.nema.org/resources/ontology/DCM",
      "code": "CT",
      "display": "Computed Tomography"
    }
  ],
  "subject": { "reference": "Patient/example" },
  "numberOfSeries": 1,
  "numberOfInstances": 1,
  "endpoint": [
    {
      "reference": "Endpoint/dicom-wado-rs-example",
      "display": "DICOM WADO-RS Server"
    }
  ],
  "series": [
    {
      "uid": "1.2.840.113619.2.55.3.2831193131.599.1519725508.431",
      "number": 1,
      "modality": { "system": "http://dicom.nema.org/resources/ontology/DCM", "code": "CT" },
      "endpoint": [ { "reference": "Endpoint/dicom-wado-rs-example" } ],
      "instance": [
        {
          "uid": "1.2.840.113619.2.55.3.2831193131.599.1519725508.432",
          "sopClass": {
            "system": "urn:ietf:rfc:3986",
            "code": "urn:oid:1.2.840.10008.5.1.4.1.2.2.1"
          },
          "number": 1
        }
      ]
    }
  ]
}
```

**Key fields for the viewer:**
- `series[].uid`, `series[].instance[].uid` — used to build WADO-RS URLs.
- `series[].instance[].sopClass` — lets the viewer pick rendering support.
- `endpoint` (resource + series level) — resolves the DICOMweb base URL (see 3.2).

### 3.2 Endpoint (DICOM WADO-RS)

```json
{
  "resourceType": "Endpoint",
  "id": "dicom-wado-rs-example",
  "status": "active",
  "connectionType": {
    "system": "http://terminology.hl7.org/CodeSystem/endpoint-connection-type",
    "code": "dicom-wado-rs"
  },
  "name": "Enterprise DICOM WADO-RS Server",
  "managingOrganization": { "reference": "Organization/example" },
  "payloadType": [
    {
      "coding": [
        {
          "system": "http://dicom.nema.org/medical/dicom/2019e/output/chtml/part18/sect_I.2.html",
          "code": "application/dicom"
        }
      ]
    }
  ],
  "address": "https://dicom.hospital.org/dicomweb"
}
```

**Contract:** the `address` MUST be the DICOMweb base root (no trailing slash in examples; viewer appends the `-RS` service paths below).

---

## 4. DICOMweb API Surface

Base URL: `https://dicom.hospital.org/dicomweb`

| Service | Method & Path | Purpose |
| :--- | :--- | :--- |
| **QIDO-RS** query studies | `GET /studies?PatientID={patientId}&Modality=CT&includefield=...` | Study list / worklist |
| **QIDO-RS** query series | `GET /studies/{StudyUID}/series` | Series-level metadata |
| **WADO-RS** metadata | `GET /studies/{StudyUID}/metadata` | Study metadata (JSON) |
| **WADO-RS** series metadata | `GET /studies/{StudyUID}/series/{SeriesUID}/metadata` | Series metadata |
| **WADO-RS** instance | `GET /studies/{StudyUID}/series/{SeriesUID}/instances/{SOPUID}` | Single instance pixels (Accept: image/jpeg, image/png, application/dicom) |
| **WADO-RS** frames | `GET /studies/{StudyUID}/series/{SeriesUID}/instances/{SOPUID}/frames/{frameList}` | Specific frames (progressive / partial retrieval). `{frameList}` = comma-separated values and/or ranges, e.g. `1,3,5-10` |
| **STOW-RS** store | `POST /studies` (multipart/related) | Upload (optional; e.g., AI results) |

### Example — QIDO-RS query

```http
GET /dicomweb/studies?PatientID=11235813&Modality=CT&includefield=00081030 HTTP/1.1
Host: dicom.hospital.org
Authorization: Bearer eyJhbGciOiJSUzI1NiIs...
Accept: application/dicom+json
```

Response (JSON array of DICOM attributes in the DICOM JSON Model):
```json
[
  {
    "0020000D": { "vr": "UI", "Value": ["1.3.6.1.4.1.14519.5.2.1.6279.6001.101370605276577556143013894866"] },
    "00080061": { "vr": "CS", "Value": ["CT"] },
    "00081030": { "vr": "LO", "Value": ["CT CHEST W CONTRAST"] },
    "00100020": { "vr": "LO", "Value": ["11235813"] }
  }
]
```

### Example — WADO-RS frames (progressive rendering)

```http
GET /dicomweb/studies/{StudyUID}/series/{SeriesUID}/instances/{SOPUID}/frames/1-50 HTTP/1.1
Authorization: Bearer ...
Accept: multipart/related; type=image/jpeg
```

---

## 5. Viewer Configuration (OHIF / Cornerstone)

### 5.1 DICOMweb data source config

```js
// ohifConfig / window.config dataSources entry
{
  "name": "dicomweb",
  "type": "web",
  "endpoint": "https://dicom.hospital.org/dicomweb",
  "qidoRoot": "https://dicom.hospital.org/dicomweb",
  "wadoRoot": "https://dicom.hospital.org/dicomweb",
  "wadoUriRoot": "https://dicom.hospital.org/wado",   // legacy WADO-URI, optional
  "stowRoot": "https://dicom.hospital.org/dicomweb",
  "singlepart": "bulkdata,video,pdf,thumbnail,image", // server single-part payload types
  "staticWado": false,
  "requestOptions": { "headers": [ { "name": "Authorization", "value": "Bearer ${token}" } ] }
}
```

**Notes:**

> Version caveat: `requestOptions` header/token injection at the data-source level varies across OHIF versions. Confirm the exact mechanism for your OHIF version, or handle token attachment via a custom data-source adapter/middleware.
- `qidoRoot` / `wadoRoot` point at the same base; the viewer appends the `-RS` service paths.
- `singlepart` avoids multipart parsing for servers (e.g., DCM4CHEE) that return single-part payloads; Orthanc requires multipart (leave unset).
- Bearer token injection via request headers enables IHE IUA / OAuth2 protected endpoints.

### 5.2 Direct study launch (standalone)

```
https://viewer.hospital.org/viewer?StudyInstanceUIDs=1.3.6.1.4.1.14519.5.2.1.6279.6001.101370605276577556143013894866
```

- Multiple studies (current + prior): repeat `StudyInstanceUIDs` or comma-separate.
- Series-only load: `&SeriesInstanceUIDs=...`
- Initial viewport: `&initialSeriesInstanceUID=...` and/or `&initialSopInstanceUID=...`

### 5.3 SMART on FHIR launch (in-EHR)

```
https://viewer.hospital.org/fhir-viewer?iss=https://fhir.hospital.org/R4&launch=abc123
```

**Launch flow:**
1. EHR calls the app with `iss` (FHIR server URL) + opaque `launch` token.
2. Viewer fetches `GET {iss}/.well-known/smart-configuration` to discover `token_endpoint`, `authorization_endpoint`, `capabilities`.
3. Viewer performs OAuth2 authorization-code flow with scopes `launch openid fhirUser patient/ImagingStudy.read` (standard SMART resource-scope form; `patient/*.read` also acceptable if broader read is justified).
4. On success, viewer queries `GET {iss}/ImagingStudy?patient={patientId}` (SMART context token provides `patient`).
5. For each `ImagingStudy`, resolve `endpoint` → DICOMweb base; call WADO-RS with the same bearer token (IUA-compliant servers accept it directly, or via `requestOptions` header).

---

## 6. Sequence Diagram (SMART + DICOMweb)

```
EHR                Viewer                 FHIR Server          DICOMweb
 │  launch(iss,launch) │                       │                  │
 │────────────────────▶│                       │                  │
 │                     │  GET .well-known/     │                  │
 │                     │  smart-configuration  │                  │
 │                     │──────────────────────▶│                  │
 │                     │  token (OAuth2) ◀─────│                  │
 │                     │                       │                  │
 │                     │  GET ImagingStudy?patient=...            │
 │                     │──────────────────────▶│                  │
 │                     │  ImagingStudy + Endpoint ◀───            │
 │                     │                       │                  │
 │                     │  GET /dicomweb/studies/{uid}/series/...  │
 │                     │─────────────────────────────────────────▶│
 │                     │  metadata + pixels ◀─────────────────────│
 │                     │                       │                  │
```

---

## 7. Error Handling & Edge Cases

| Case | Behavior |
| :--- | :--- |
| Missing `endpoint` on ImagingStudy | Fall back to configured default DICOMweb base; log warning |
| Token expired (401) | Refresh via SMART token endpoint; if refresh fails, re-trigger launch |
| WADO-RS multipart vs singlepart mismatch | Configure `singlepart` per server; test in integration lab |
| Large study (multi-GB) | Use frame-level WADO-RS + progressive/SSR rendering; avoid full download |
| Non-DICOM payloads (PDF, video) | WADO-RS with `Accept: application/pdf`, `video/*`; configure `singlepart` |
| Cross-origin | CORS allow-list for viewer origin; use same token; never expose tokens client-side in URLs |

---

## 8. Security & Compliance

- **Transport:** TLS 1.2+ for FHIR and DICOMweb.
- **Auth:** SMART on FHIR OAuth2/OIDC for FHIR; bearer token forwarded to DICOMweb (IHE IUA profile).
- **Scopes:** least privilege (SMART standard form `patient/ImagingStudy.read` / `user/ImagingStudy.read`); no write scopes for pure viewer.
- **Audit:** DICOMweb server logs every retrieve (HIPAA audit trail); viewer-level logging for launch/abandon.
- **No PHI in URLs:** pass tokens via headers; use `StudyInstanceUIDs` (not patient identifiers) in deep links where possible.

---

## 9. Acceptance Criteria

- [ ] Viewer launches from EHR via SMART and displays the correct patient's studies.
- [ ] QIDO-RS query returns expected studies for `PatientID` filter.
- [ ] WADO-RS metadata + frames render in the viewer for CT, MR, XR, US.
- [ ] Prior study launch (2 `StudyInstanceUIDs`) shows current + prior side-by-side.
- [ ] Token expiration triggers refresh without user disruption.
- [ ] Large study loads progressively (first frames visible < 3 s on reference bandwidth).
- [ ] Audit log entries exist for every retrieve; no PHI in URLs.

---

## 10. References

- DICOM PS3.18 — DICOMweb (QIDO-RS, WADO-RS, STOW-RS, UPS-RS).
- HL7 FHIR R4 — ImagingStudy, ImagingSelection, Endpoint; SMART App Launch; FHIRcast.
- IHE Radiology — IUA (Internet User Authorization), XDS-I.b.
- OHIF Viewer docs — data source config (`qidoRoot`, `wadoRoot`, `singlepart`), `/viewer?StudyInstanceUIDs=` launch params, `fhir-viewer` SMART mode.
