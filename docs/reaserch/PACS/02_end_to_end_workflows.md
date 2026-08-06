# PACS — End-to-End Workflow Maps

**Document:** 02 of 06 · **Version:** 1.0 · **Date:** 2026-08-04

Every workflow is drawn as a **swimlane map** showing actors (human, institution, machine), system steps, and touchpoints to RIS/EMR. Priorities: `M` mandatory, `D` desired, `O` optional.

---

## PAC-WF1 · Order → Acquisition → Archive (the "hot path")

> **Actors:** Referring MD (EMR) · RIS · Technologist · Modality · PACS ingestion · Storage tiers
> **Priority:** M — this is the core clinical loop, shared with RIS (see `RIS/02` RIS-WF1).

```
Referring MD      RIS / EMR           Technologist        Modality          PACS Ingestion      Archive
     │ Order exam        │                 │                 │                 │                 │
     │──────────────────▶│ HL7 ORM / FHIR  │                 │                 │                 │
     │                   │ assign accession│                 │                 │                 │
     │                   │ set status=SCHED│                 │                 │                 │
     │                   │ push to MWL     │                 │                 │                 │
     │                   │─────────────────┼────────────────▶│ C-FIND (MWL)    │                 │
     │                   │                 │  auto-fill demo │◀────────────────│                 │
     │                   │                 │  verify patient │                 │                 │
     │                   │                 │  acquire images │                 │                 │
     │                   │                 │  MPPS IN_PROG   │────────────────▶│                 │
     │                   │                 │                 │ C-STORE/STOW-RS │                 │
     │                   │                 │                 │────────────────▶│ parse & index   │
     │                   │                 │                 │                 │── metadata ───▶│
     │                   │                 │                 │◀────── Storage Commitment ────────│
     │                   │                 │◀── verify; purge cache if committed ──│                 │
     │                   │                 │  MPPS COMPLETED │────────────────▶│ verify complete │
     │                   │◀── status COMPLETED ───────────────│                 │                 │
```

**Steps & requirements**
1. **Order intake (RIS)** — accession number assigned, unique per tenant (`RIS-WF1`). Status `SCHEDULED`.
2. **MWL query (technologist)** — patient/accession/requested procedure auto-populated at the console. *(PAC-US-P02-01)*
3. **Acquisition & MPPS** — modality reports `IN PROGRESS` → `COMPLETED`/`DISCONTINUED`. PACS/RIS echo status.
4. **Transfer & Storage Commitment (PACS)** — modality C-STORE/STOW-RS to PACS; PACS validates (patient ID, accession, SOP class), indexes metadata, commits pixels to tiered storage, returns **Storage Commitment** so the scanner may purge its cache. *(PAC-US-P02-02)*
5. **Orphan/quarantine handling** — studies failing validation (no accession, mismatched patient) go to an **exception worklist**, never silently dropped. *(PAC-US-P04-05)*

**Exit criteria:** image verified archived before scanner purges; status visible in RIS; retrieval succeeds.

---

## PAC-WF2 · Radiologist Reading Workflow

> **Actors:** Radiologist · PACS worklist · Viewer · Prior store · Dictation/SR · RIS · Referring MD
> **Priority:** M

```
Radiologist       PACS Worklist       Viewer             Prior Store        Dictation/SR     RIS / EMR
    │ open worklist    │                 │                 │                 │                │
    │─────────────────▶│ prioritized list│                 │                 │                │
    │ select study     │────────────────▶│ prefetch priors │                 │                │
    │                  │                 │────────────────▶│                 │                │
    │                  │                 │◀─ priors ready ─│                 │                │
    │                  │                 │ hanging protocol│                 │                │
    │                  │                 │ load < 3 s      │                 │                │
    │ read & measure   │                 │ tools: MPR/3D/  │                 │                │
    │                  │                 │ cine/fusion/AI  │                 │                │
    │ bookmark key img │                 │                 │                 │                │
    │ start dictation  │                 │                 │────────────────▶│ SR/dictation    │
    │ critical finding │                 │                 │                 │ flag CRITICAL   │
    │                  │                 │                 │                 │──► notify MD ──▶│
    │ sign report      │                 │                 │◀─ transcript ───│                │
    │                  │                 │                 │                 │ finalize + ORU ─▶│
```

**Key requirements**
- **Worklist prioritization:** STAT > Inpatient > Outpatient; modality & site filters; unread backlog visible. *(PAC-US-P01-01)*
- **Hanging protocols:** per anatomy/modality/priority; persisted per radiologist. *(PAC-US-P01-02)*
- **Priors:** auto-prefetched or one-click; cross-tenant priors (health system / teleradiology) via audited XDS-I.b read-across. *(PAC-US-P01-03)*
- **Reading tools:** window/level, zoom, pan, cine, MPR, MIP/MinIP, 3D volume, PET/CT fusion, measurements, AI overlay. *(PAC-US-P01-04)*
- **Critical results:** one-action flag → documented notification (call task / message / page) with acknowledgment tracking — a HIPAA-critical workflow. *(PAC-US-P01-06)*

**Exit criteria:** signed report routed to RIS/EMR; critical results acknowledged; audit trail complete.

---

## PAC-WF3 · Prior-Study Prefetching

> **Actors:** RIS scheduler · PACS prefetch engine · Edge cache · Radiologist
> **Priority:** D

```
RIS Scheduler        PACS Prefetch        Edge Cache         Radiologist
  scheduled exam ──▶  resolve patient │
                      history/MPI     │
                      locate priors   │
                      (may be another │
                       facility/XDS-I)│
                      queue prefetch  │──▶ pull to local edge (warm) ──▶ ready at read time
```

**Requirements:** prefetch triggered on schedule (and on ED arrival for known patients); priors staged to the reading site's edge cache within SLA; skip/prioritize rules (same modality/anatomy first); don't degrade active-traffic bandwidth. *(PAC-US-P01-03, PAC-SL-24)*

---

## PAC-WF4 · Teleradiology / Remote Reading

> **Actors:** Teleradiologist · IdP/OAuth · Cloud PACS · On-site staff · RIS
> **Priority:** D

```
Teleradiologist      IdP (OIDC)         Cloud PACS/VNA      On-site staff        RIS
   launch viewer ──▶ token (IUA/OAuth2) ──▶ session with      │                    │
                    grant read scope       facility consent   │                    │
   pull study (WADO-RS progressive) ◀─────────────────────────│                    │
   read with full tools + cross-tenant priors (audited)       │                    │
   STAT finding ──▶ critical alert ──────────────────────────▶│── acknowledge ────▶│
   sign report ──▶ ORU to each facility's RIS/EMR ────────────▶                    │
```

**Requirements:** single tokenized session across client tenants (no VPN); per-tenant audit of every access; progressive streaming for bandwidth; critical-results callback to on-site staff; report delivered to the ordering tenant. *(PAC-US-P03-01, PAC-US-P03-02)*

---

## PAC-WF5 · Image Lifecycle Management (ILM) & Storage

> **Actors:** PACS Admin · Storage tiers (hot/warm/cold) · Retention policy · Audit
> **Priority:** M

```
PACS Admin                    Storage Tiers                    Retention / Audit
 define tier policies ──▶  Tier1 hot  (0–30 d, edge/SSD)  ──▶ purge only on policy
 (retention clocks,       Tier2 warm (1–12 mo, cloud)     │  + legal hold override
  legal hold, tiering)    Tier3 deep (5–30+ yr, cold)     │  + WORM/immutable
                          object keys immutable,         │  + per-tenant quota
                          tenant-prefixed                ▼  + audited every delete
```

**Requirements:** automated lifecycle transitions; retention 5–30+ yr configurable per tenant with legal-hold override; immutable (WORM) archive for ransomware resilience; per-tenant quota monitoring → alert at 75/90%; deletions audited. *(PAC-US-P04-03, PAC-US-P04-04)*

---

## PAC-WF6 · AI Service Integration

> **Actors:** AI service · UPS-RS queue · PACS · Radiologist
> **Priority:** O (roadmap, `E19` in RFP)

```
AI Service            UPS-RS (PACS)         PACS Archive         Radiologist
 subscribe ──────────▶ study-arrived event
 pull via WADO-RS ◀───────────────────────── pixels
 run inference
 store result ──────▶ DICOM SR/GSPS or FHIR Observation/DiagnosticReport/ImagingSelection
                     └──► visible as overlay/key-image flag in viewer worklist
```

**Requirements:** event-driven dispatch (UPS-RS/webhook); pull with token; results stored in standard formats; radiologist sees AI flags with confidence & can accept/reject; every AI access audited. *(PAC-US-P05-01, PAC-US-P01-05)*

---

## PAC-WF7 · EMR-Launched Web Viewer (SMART on FHIR)

> **Actors:** Referring MD · EMR · FHIR server · Viewer (OHIF) · DICOMweb
> **Priority:** D (`E16`)

```
Referring MD        EMR                FHIR Server         Viewer              DICOMweb
  open study ──▶ launch (iss+launch) ──▶ token (SMART) ───▶ GET ImagingStudy?patient=...
                                                           resolve Endpoint ──▶ QIDO-RS studies
                                                           WADO-RS metadata+pixels ◀──
  view images & key images (no PHI in URLs; bearer tokens)
```

Full contract in `research/pacs-ris-viewer-integration-spec.md` §5–§6. **Acceptance:** viewer opens correct patient's studies; token refresh transparent; first frame < 3 s. *(PAC-US-P06-01)*

---

## PAC-WF8 · Export & Sharing (CD/DVD, XDS-I.b, Anonymized)

> **Actors:** PACS Admin / Technologist · Print/export service · External facility
> **Priority:** D (XDS-I.b O)

```
Requestor            PACS Export          External Facility        Audit
 select study ──▶ anonymize option ──▶ XDS-I.b push / PDI media ──▶ export logged (who/what/why)
                  format: DICOM/PDF/video                          + retention of export record
```

**Requirements:** IHE PDI conformant media; XDS-I.b cross-enterprise push/query/retrieve; anonymization profile toggle; every export audited with reason code. *(PAC-US-P04-06)*

---

## PAC-WF9 · Disaster Recovery & Failover

> **Actors:** PACS Admin · Ops/Super Admin · Cloud DR · Users
> **Priority:** M

```
Incident detected ──▶ failover to DR site (RTO ≤ 4 h) ──▶ data replay from RPO ≤ 60 min
                     ├── active reads continue from edge cache
                     ├── ingestion queue buffers modality sends
                     └── DR drill executed quarterly, documented
```

**Requirements:** defined RPO/RTO; edge caches keep recent studies readable during cloud outage; ingestion buffering prevents data loss; quarterly DR drill with evidence. *(PAC-US-P04-07, PAC-SL-03/04)*

---

## PAC-WF10 · Tenant Provisioning (PACS onboarding)

> **Actors:** Super Admin · Tenant Admin · Provisioning service
> **Priority:** M (platform)

```
Super Admin        Provisioning (atomic)         Tenant Admin
 create tenant ──▶ validate plan/billing/admin
                   insert facility + subscription (TRIAL)
                   seed: modalities, rooms, retention, defaults
                   scope RLS to new facility
                   stage PROVISIONING→SEEDING→READY ──▶ admin login, provision users/modalities/AE
```

Atomic `provision_tenant()` per `pacs-ris-schema.sql` §16; rollback on any failure. *(PLT-…)*

---

## Workflow Traceability

| Workflow | Personas | Primary stories | Acceptance |
| :--- | :--- | :--- | :--- |
| PAC-WF1 | P02, M01, M02 | PAC-US-P02-01/02, PAC-US-P04-05 | PAC-AC-P02-*, PAC-AC-P04-* |
| PAC-WF2 | P01, P06, P07 | PAC-US-P01-01…06 | PAC-AC-P01-* |
| PAC-WF3 | P01, P04 | PAC-US-P01-03 | PAC-AC-P01-03 |
| PAC-WF4 | P03 | PAC-US-P03-01/02 | PAC-AC-P03-* |
| PAC-WF5 | P04 | PAC-US-P04-03/04 | PAC-AC-P04-03/04 |
| PAC-WF6 | P01, P05 | PAC-US-P05-01, PAC-US-P01-05 | PAC-AC-P05-01 |
| PAC-WF7 | P06, P07 | PAC-US-P06-01 | PAC-AC-P06-01 |
| PAC-WF8 | P04 | PAC-US-P04-06 | PAC-AC-P04-06 |
| PAC-WF9 | P04, P20 | PAC-US-P04-07 | PAC-AC-P04-07 |
| PAC-WF10 | P19, P20 | (PLT) | PAC-AC-P19-* |
