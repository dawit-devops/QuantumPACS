# QuantumPACS — Logo Concept Exploration

> **Skill:** SVG Logo Designer · **Scope:** fresh directions beyond the shipped Orbit mark
> **Date:** 2026-08-11 · **Location:** `design-system/quantumpacs/logos/`
> **Palette (live tokens):** blue-600 `#0077B6` · cyan-400 `#22D3EE` · teal-600 `#059669` · cyan-700 `#0E7490` · slate-800 `#1E293B`
> **Constraint:** calm clinical precision — no purple "AI glow", no neon, no consumer cheer.

Each concept includes an **icon-only** and a **horizontal lockup** SVG. All marks scale from favicon to signage (viewBox-based, gradient defined once in `<defs>`).

---

## Concept 1 — The Slice · *the scan plane*

### Design Rationale
Radiology reads are about *planes*: the axial slice is the fundamental unit of a study. This mark is a rounded detector plate with a crosshair and a focus nucleus — the exact point being imaged. It says "we see precisely where it matters."

- **Metaphor:** the axial imaging plane; targeting.
- **Symbol logic:** plate (aperture) + crosshair (precision) + nucleus (patient focus).
- **Differentiation from Orbit:** rectangular, planar, clinical — less "physics", more "imaging".
- **Avoids:** floating icons, random shapes — everything is anchored to the plate.

**Icon:** `concept1-slice-icon.svg` · **Lockup:** `concept1-slice-lockup.svg`

```xml
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" role="img" aria-labelledby="t1 d1">
  <title id="t1">QuantumPACS — The Slice concept</title>
  <desc id="d1">Rounded scan-plane aperture with crosshair and focus nucleus.</desc>
  <defs>
    <linearGradient id="g1" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#0077B6"/>
      <stop offset="0.5" stop-color="#22D3EE"/>
      <stop offset="1" stop-color="#059669"/>
    </linearGradient>
  </defs>
  <rect x="16" y="16" width="68" height="68" rx="14" fill="none" stroke="url(#g1)" stroke-width="5"/>
  <line x1="50" y1="30" x2="50" y2="70" stroke="#64748B" stroke-width="2.5" stroke-linecap="round"/>
  <line x1="30" y1="50" x2="70" y2="50" stroke="#64748B" stroke-width="2.5" stroke-linecap="round"/>
  <line x1="42" y1="16" x2="42" y2="23" stroke="#94A3B8" stroke-width="2" stroke-linecap="round"/>
  <line x1="58" y1="16" x2="58" y2="23" stroke="#94A3B8" stroke-width="2" stroke-linecap="round"/>
  <circle cx="50" cy="50" r="6" fill="url(#g1)"/>
</svg>
```

---

## Concept 2 — The Signal · *the study in motion*

### Design Rationale
A PACS is a pipeline: modality → archive → reading room. The calm medical pulse captures that flow — a heartbeat waveform that reads as *life and motion without chaos*. It echoes the monitor rhythms clinicians already trust.

- **Metaphor:** the pulse of the imaging workflow; signal integrity.
- **Symbol logic:** baseline (stability) + pulse (life/flow) + peak node (the study).
- **Differentiation from Orbit:** linear, sequential, dynamic — "the journey" rather than "the atom".
- **Avoids:** jagged, alarming ECG spikes — the pulse is rounded and calm.

**Icon:** `concept2-signal-icon.svg` · **Lockup:** `concept2-signal-lockup.svg`

```xml
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" role="img" aria-labelledby="t2 d2">
  <title id="t2">QuantumPACS — The Signal concept</title>
  <desc id="d2">Calm medical pulse waveform on a baseline.</desc>
  <defs>
    <linearGradient id="g2" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="#0077B6"/>
      <stop offset="0.55" stop-color="#22D3EE"/>
      <stop offset="1" stop-color="#059669"/>
    </linearGradient>
  </defs>
  <line x1="10" y1="64" x2="90" y2="64" stroke="#CBD5E1" stroke-width="3" stroke-linecap="round"/>
  <path d="M14,64 H32 L39,50 L45,74 L52,28 L60,64 H86" fill="none" stroke="url(#g2)" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/>
  <circle cx="52" cy="28" r="5" fill="#059669"/>
</svg>
```

---

## Concept 3 — The Q-Orbit · *the monogram*

### Design Rationale
The brand initial fused with the existing quantum metaphor: the **Q** letterform whose tail becomes an orbital path carrying an electron node. It keeps the atom/quantum equity from the current mark while becoming a cleaner, more ownable letterform.

- **Metaphor:** quantum orbit inside the brand initial.
- **Symbol logic:** Q ring (name) + tail-as-orbit (quantum) + electron (the study) + soft nucleus.
- **Differentiation from Orbit:** typographic, trademark-strong, lettermark family (works as app icon and favicon).
- **Avoids:** a generic "letter in a circle" — the tail *is* the orbit, not decoration.

**Icon:** `concept3-qorbit-icon.svg` · **Lockup:** `concept3-qorbit-lockup.svg`

```xml
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" role="img" aria-labelledby="t3 d3">
  <title id="t3">QuantumPACS — The Q-Orbit concept</title>
  <desc id="d3">Q letterform whose tail doubles as an orbital path with an electron node.</desc>
  <defs>
    <linearGradient id="g3" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#0077B6"/>
      <stop offset="0.5" stop-color="#22D3EE"/>
      <stop offset="1" stop-color="#059669"/>
    </linearGradient>
  </defs>
  <circle cx="46" cy="46" r="28" fill="none" stroke="url(#g3)" stroke-width="8"/>
  <path d="M66,66 L84,84" stroke="url(#g3)" stroke-width="8" stroke-linecap="round"/>
  <circle cx="84" cy="84" r="6" fill="#059669"/>
  <circle cx="46" cy="46" r="7" fill="#0E7490" opacity="0.35"/>
</svg>
```

---

## Concept 4 — The Stack · *volume & archive*

### Design Rationale
CT/MRI *are* stacks — dozens of axial slices read as a volume. Three descending slices with a scan line say "depth, data, completeness": the whole study, not just one image. It is the most *radiology-native* symbol of the set.

- **Metaphor:** volumetric imaging; the archive; serial slices.
- **Symbol logic:** three layers (depth) + scan line (the read head).
- **Differentiation from Orbit:** dimensional, data-rich — "the whole study in one mark".
- **Avoids:** floating sheets of paper — slices are aligned and scanned, not scattered.

**Icon:** `concept4-stack-icon.svg` · **Lockup:** `concept4-stack-lockup.svg`

```xml
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" role="img" aria-labelledby="t4 d4">
  <title id="t4">QuantumPACS — The Stack concept</title>
  <desc id="d4">Three stacked axial slices with a scan line — volume and archive.</desc>
  <defs>
    <linearGradient id="g4" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="#0077B6"/>
      <stop offset="0.55" stop-color="#22D3EE"/>
      <stop offset="1" stop-color="#059669"/>
    </linearGradient>
  </defs>
  <rect x="28" y="14" width="52" height="20" rx="6" fill="none" stroke="#94A3B8" stroke-width="4" opacity="0.6"/>
  <rect x="25" y="40" width="52" height="20" rx="6" fill="none" stroke="#22D3EE" stroke-width="4"/>
  <rect x="22" y="66" width="52" height="20" rx="6" fill="none" stroke="url(#g4)" stroke-width="5"/>
  <line x1="50" y1="10" x2="50" y2="90" stroke="#64748B" stroke-width="2" stroke-dasharray="4 5" opacity="0.7"/>
</svg>
```

---

## Concept 5 — The Aperture · *the frame through which you see*

### Design Rationale
The reading experience is a *viewport*: window/level, zoom, the frame that brings an image into diagnostic clarity. A square aperture with a lens ring and window/level corner markers says "clarity on demand" — the closest to the brand promise ("Diagnostic Clarity, Quantum Fast").

- **Metaphor:** the imaging viewport; window/level; focus.
- **Symbol logic:** frame (aperture) + lens ring (optics) + corner markers (window/level controls) + focus dot.
- **Differentiation from Orbit:** viewer-centric, interactive-feeling — "the screen where the answer appears".
- **Avoids:** browser-chrome clichés — markers are the actual W/L controls radiologists use.

**Icon:** `concept5-aperture-icon.svg` · **Lockup:** `concept5-aperture-lockup.svg`

```xml
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" role="img" aria-labelledby="t5 d5">
  <title id="t5">QuantumPACS — The Aperture concept</title>
  <desc id="d5">Imaging viewport: frame, lens ring, window/level corner markers.</desc>
  <defs>
    <linearGradient id="g5" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#0077B6"/>
      <stop offset="0.5" stop-color="#22D3EE"/>
      <stop offset="1" stop-color="#059669"/>
    </linearGradient>
  </defs>
  <rect x="14" y="14" width="72" height="72" rx="10" fill="none" stroke="url(#g5)" stroke-width="5"/>
  <circle cx="50" cy="50" r="24" fill="none" stroke="#22D3EE" stroke-width="3.5"/>
  <path d="M50,32 V26 M50,74 V68 M32,50 H26 M74,50 H68" stroke="#059669" stroke-width="3" stroke-linecap="round"/>
  <circle cx="50" cy="50" r="4" fill="url(#g5)"/>
</svg>
```

---

## Comparison & Next Step

| Concept | Core idea | Most "QuantumPACS" | Best for |
|---|---|---|---|
| 1 · Slice | Scan plane & precision | Clinical, precise | Detection/imaging identity |
| 2 · Signal | Study in motion | Fast, calm, alive | Pipeline/workflow story |
| 3 · Q-Orbit | Monogram + quantum | Ownable, trademark | App icon, favicon, signage |
| 4 · Stack | Volume & archive | Rad-natively obvious | Depth/data story |
| 5 · Aperture | Clarity on demand | Matches the tagline | Viewer-centric story |

**Recommendation:** refine **Concept 3 (Q-Orbit)** and **Concept 5 (Aperture)** — one owns the *name* (Q), the other owns the *promise* (clarity). Both keep gradient/wordmark equity from the current Orbit mark. Pick one to carry into vertical, monochrome, and favicon variants.
