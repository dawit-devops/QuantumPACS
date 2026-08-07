# ADR-003: DICOMweb Gateway + DIMSE Dual-Path Interoperability

## Status
Accepted

## Date
2026-08-04

## Context
The platform must interoperate with (a) legacy imaging modalities and workstations that speak DIMSE (C-STORE/C-FIND/C-MOVE), and (b) modern zero-footprint web viewers and EHRs that speak DICOMweb (QIDO-RS/WADO-RS/STOW-RS/UPS-RS) and FHIR. Single-protocol-only designs either exclude legacy scanners or lock out web/EHR integration. The viewer integration spec (`research/pacs-ris-viewer-integration-spec.md`) defines the retrieval contract.

## Decision
Implement a **dual-path interoperability model**: DIMSE for ingestion from legacy modalities, DICOMweb as the primary retrieval/distribution surface, unified behind one metadata index:

- **Ingestion (in):**
  - DIMSE C-STORE from legacy modalities (AE-title + IP allow-list, per-facility).
  - DICOMweb STOW-RS for DICOMweb-native scanners and external systems.
  - Both land in the same ingestion pipeline → duplicate detection → metadata index → tiered archive (ADR-002).
- **Retrieval/distribution (out):**
  - DICOMweb QIDO-RS (study/series/instance queries, server-side `total`, < 500 ms p95), WADO-RS (metadata + full-frame, < 1 s p95), and **frame-level WADO-RS** for progressive streaming of multi-GB studies (first frame < 3 s, PAC-SL-11).
  - UPS-RS for worklist/MPPS-style orchestration over web; DIMSE C-FIND (MWL) / MPPS retained for modality consoles.
- **FHIR R4 (read-only, MVP):** `ImagingStudy` read to feed EHR context; SMART-on-FHIR launch deferred to v2.0 (ADR-009).
- **Auth:** all DICOMweb endpoints behind IHE IUA/OAuth2 token gate; links are UID-based with no PHI in URLs.
- **Viewer:** zero-footprint web viewer consumes only DICOMweb — it never speaks DIMSE.

## Alternatives Considered

### DIMSE-only
- Pros: universal modality compatibility; no web auth complexity
- Cons: no zero-footprint web viewing, no EHR/SMART integration, firewall-hostile (TCP, ephemeral ports), harder multi-tenant metering per call
- Rejected: cannot serve the web/EHR surface the product requires

### DICOMweb-only
- Pros: clean REST surface; full metering; web-friendly
- Cons: legacy modalities (many installed scanners) do not support STOW-RS/C-FIND-RS reliably; would force upgrades on every site
- Rejected as sole path: keeps DIMSE C-STORE/MPPS as a compatibility surface (sprint2/3)

### Two siloed systems
- Pros: none
- Cons: double metadata, reconciliation drift, duplicate storage
- Rejected: one shared metadata index is required for priors, MPI, and analytics

## Consequences
- Modalities keep their existing workflow (C-STORE + MWL/MPPS) while all new consumers use DICOMweb — no forced upgrades.
- QIDO/WADO/frame-level SLAs (PAC-SL-16/17/11) become gate G3 acceptance criteria.
- IUA/OAuth2 gating is mandatory on every DICOMweb route; the auth model is shared with ADR-004.
- Integration engineers need DICOM + DICOMweb conformance expertise; the S2-27/S3-21 conformance lab is a critical-path dependency (sprint2/3).
- WADO egress is metered (`WADO_BYTES`) — cost model per ADR-006.

## Sources
`research/pacs-ris-viewer-integration-spec.md` §4–§6, §8 (QIDO/WADO/IUA conventions) · `research/pacs-ris-architecture-deep-dive.md` · `requrements/PACS/05_metrics_and_slas.md` PAC-SL-10/11/16/17 · sprint2 (E-PAC-02) · sprint3 (E-PAC-03) · sprint4 (E-PAC-05/06)
