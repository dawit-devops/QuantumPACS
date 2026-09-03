# Design Spec: Radiologist Reading Workstation
### (Cornerstone — dual-pane image viewer + report editor)

Use this as a single prompt to regenerate the design. It is written so an AI or
designer with no other context could produce an equivalent, single-file HTML
mockup.

---

## 1. Brief

Design a highly ergonomic radiologist workstation UI: a **DICOM image viewer**
and a **structured report editor** side by side, so a radiologist can read a
study and dictate/type findings without moving between separate tools. Build
it as a single self-contained HTML file (inline CSS + vanilla JS, no build
step, no external frameworks) with believable placeholder imagery generated
on a `<canvas>` (not real DICOM — a procedurally drawn CT-style axial slice
is sufficient). Every interactive element should actually work in the
browser: dragging, scrolling, toggling, typing.

**Audience:** radiologists in a reading room. **Primary job:** read images
fast with minimal mouse travel, write a structured report in parallel, sign
it safely.

---

## 2. Design tokens

### Color (dark theme — reading rooms are kept dark so eyes stay calibrated
to grayscale image contrast; the UI must never compete with the image)

| Token | Hex / value | Use |
|---|---|---|
| `--bg-void` | `#08090b` | outermost app background |
| `--panel` | `#111318` | top bar, toolbars, footers |
| `--panel-2` | `#171b21` | cards, textareas, popovers |
| `--panel-3` | `#1d222a` | hovered/nested surfaces, chips |
| `--border` | `#262b34` | default hairline borders |
| `--border-soft` | `#1c2028` | subtle internal dividers |
| `--text` | `#e6e9ee` | primary text |
| `--text-dim` | `#8992a3` | secondary/meta text |
| `--text-faint` | `#565d6b` | placeholders, disabled, hints |
| `--accent` | `#4cc3c9` (teal-cyan) | active tool/state, focus rings, links |
| `--accent-dim` | `#2c8489` | accent borders, primary button base |
| `--accent-glow` | `rgba(76,195,201,0.14)` | active-state background wash |
| `--warn` | `#dba75a` (amber) | draft/unsigned/pending states |
| `--critical` | `#e2635a` (muted red) | critical flag, destructive actions |
| `--ok` | `#6bbf8a` | "ready" / success states |

Do **not** use pure black or pure white; do not use a vermilion/terracotta or
acid-green accent (common AI-generated-design tells) — the accent is a
clinical, desaturated cyan.

### Typography

- **UI/body:** `IBM Plex Sans` (400/500/600/700) — all chrome, labels, report
  prose.
- **Data/mono:** `IBM Plex Mono` (400/500/600) — DICOM overlay text, patient
  IDs, measurements, keyboard-key badges, timestamps. This pairing is
  deliberate: mono for anything that reads as *data*, sans for anything that
  reads as *prose or UI*.
- Base body size 13px. Overlay/meta text 10–11.5px. Section headings ~11px,
  uppercase-free, letter-spacing ~0.03–0.06em only on the very small mono
  labels (not on headings generally).

### Spacing / shape

- Border radius: 3px everywhere (sharp, instrument-panel feel — not
  soft-SaaS rounded cards).
- 1px hairline borders throughout; no drop shadows except on floating
  popovers/menus (`0 14px 34px rgba(0,0,0,0.45)`).
- Scrollbars: thin (9px), custom-colored to match the border palette.

---

## 3. Layout architecture

Three-row app shell (`display:grid; grid-template-rows: 40px 1fr 26px`):

```
┌───────────────────────────── topbar (40px) ─────────────────────────────┐
├───────────┬──────────────────────────────┬──────┬──────────────────────┤
│ nav-panel │        viewport-col          │resize│     report-panel     │
│  168px    │         flex:1 1 auto        │ 6px  │   380px (resizable   │
│  fixed    │                              │ drag │   300–680px)         │
├───────────┴──────────────────────────────┴──────┴──────────────────────┤
├───────────────────────────── statusbar (26px) ───────────────────────────┤
```

- Main region is a **flex row**, not a fixed grid, specifically so the
  divider between the viewport and the report panel can be dragged.
- Nav panel is fixed-width (icons/thumbnails don't need to flex).
- Viewport column is the flexible/dominant space — it should visually read
  as the hero of the screen.
- Report panel has `min-width:300px; max-width:680px` so it can't be
  resized into uselessness or swallow the whole window.

---

## 4. Component specification

### 4.1 Top bar
- Left: **← Worklist** back button (plain, icon+text, no border until hover).
- Divider, then **brand mark** (mono, small caps-free wordmark, accent color).
- Patient identity block: bold patient name, then a mono meta string (MRN,
  sex, age, DOB) separated by a middle-dot, then study description
  (modality, accession #, date) separated by a vertical rule.
- Spacer.
- **Critical flag** pill/button (amber-to-red on click, pulsing dot) — marks
  a finding for urgent callback; clicking it locks into a confirmed state
  ("✓ CRITICAL FLAGGED — CALLBACK LOGGED").
- Small icon buttons: compare-prior, patient history, **keyboard-shortcut
  help (`?`)**.

### 4.2 Left nav panel — study/series navigator
- Section label ("CURRENT STUDY") in small tracked mono.
- Scrollable list of **series cards**: each a square canvas thumbnail
  (procedurally drawn mini version of the same body-outline art) + a label
  row (series name, image count). Active card gets an accent border +
  inset glow.
- A dashed-top divider labeled "PRIOR · <date>" beneath the current list,
  signaling comparison studies exist without fully building that state out.

### 4.3 Center — viewport column
**Toolbar** (icon+label+keyboard-key buttons, all with the shortcut key
shown *on the button itself* so no memorization is required):
- Window/Level (`W`) — default/active tool.
- Zoom (`Z`), Pan (`P`), Measure (`M`).
- Divider.
- Cine play/pause (`Space`), Invert (`I`), Reset (`R`).
- Divider.
- Layout/hanging-protocol cycle button.
- Divider.
- **Key Images** button opening a popover: a "＋ Capture current image" row,
  then a 2-column grid of captured thumbnails, each with a small
  "Insert →" action that appends a figure reference into the report's
  Findings field. This is the bridge between viewing and reporting.

**Stage** (the actual image area):
- Full-bleed black canvas, centered, generated CT-style axial slice
  (radial-gradient body outline, two lung fields with subtle procedural
  reticular texture, spine/sternum/ribs as bright shapes, grain/noise pass,
  vignette). Purpose is *plausible*, not medically precise.
- Corner overlay text (mono, cyan-tinted, drop-shadowed for legibility over
  any image tone): patient/study info top-left, acquisition params
  top-right, series/slice + current W/L bottom-left, technique parameters
  bottom-right.
- Orientation letters (A/P/L/R) faint at the four edge midpoints.
- Interactions: mouse wheel or `↑/↓` pages through slices; left-drag behaves
  according to the active tool (WL adjusts brightness/contrast via CSS
  `filter`, Pan translates, Zoom scales, Measure drops two points and draws
  an SVG line + computed mm distance); double-click resets the view.

**Footer:** mono readout of current W/L/zoom values (left) + a one-line
hint of the core interaction model (right): *"Scroll to page slices · drag
= active tool · double-click to reset."*

### 4.4 Right — report panel
- **Header:** report title + a status pill (amber "DRAFT · UNSIGNED",
  updates to "DRAFT · EDITED" on any edit), template name subtitle, and a
  dictation row: a pill-shaped mic toggle (goes red/pulsing when "live")
  plus a hint that typing directly into any field also works.
- **Body:** scrollable, four numbered sections — Clinical History,
  Technique, Findings, Impression (Recommendations optional/omissible
  depending on template) — each a small mono index number + label above a
  textarea. Findings and Impression get **macro chips** below the textarea
  (small pill buttons like "+ Normal lungs", "+ No acute findings") that
  append a canned phrase on click, so common normal findings never have to
  be typed from scratch.
- **Footer:** Save draft (ghost button), Preview, an autosave status string
  that flips to "Saving…" then "Autosaved just now" ~700ms after any edit,
  a sign-readiness hint, and **Sign & Finalize** as the one true primary
  button (`--accent-dim` fill) — **disabled until the Impression field has
  content**, with the hint text explaining why ("Impression required to
  sign" → "Ready to sign", color shifts to `--ok`).

### 4.5 Status bar
Single thin mono strip: series position, slice counter, pixel
spacing/matrix size, then a right-aligned row of the most important
keyboard shortcuts rendered as `<b>` key-badges (`↑↓`, `W`, `M`, `Tab`,
`⌘⏎`, `?`).

### 4.6 Shortcut overlay
A centered modal (`?` to open, `Esc` or click-outside to close) listing
every shortcut as a two-column grid of `label — key-badge` rows. This
exists so the "no toolbar memorization" ergonomic claim is actually true.

---

## 5. Interaction & keyboard spec

| Action | Input |
|---|---|
| Change slice | `↑ / ↓`, or mouse wheel over the image |
| Window/Level tool | `W` (also default on load) |
| Zoom tool | `Z` |
| Pan tool | `P` |
| Measure tool | `M` (click two points; draws line + mm label) |
| Cine play/pause | `Space` |
| Invert grayscale | `I` |
| Reset view | `R`, or double-click the stage |
| Flag critical finding | `F` |
| All shortcuts | `?` |
| Resize report panel | drag the divider between viewport and report |
| Capture key image | click "Capture current image" in the Key Images popover |
| Insert key image into report | click "Insert →" on a captured thumbnail |
| Sign & Finalize | enabled only once Impression is non-empty; `⌘⏎` |

General rule: **any tool reachable by mouse must show its keyboard
equivalent inline on the control itself** — never a separate legend the
person has to cross-reference.

---

## 6. Content / copy conventions

- Section labels: plain nouns, sentence case, no ALL-CAPS except tiny mono
  status/meta strings (MRN line, overlay text, key-badges) where mono caps
  read as *data*, not shouting.
- Macro chips are written as literal insertable sentence fragments
  ("Normal lungs", "No acute findings"), not abstract command names.
- Status/empty states are direct and unapologetic: "No measurements",
  "Impression required to sign" — state the fact, not an apology.
- Placeholder copy in empty fields describes *what goes here*, not a
  generic "Enter text…" (e.g. "Structured findings — per template or free
  text…").

---

## 7. Technical constraints

- Single `.html` file, inline `<style>` and `<script>`, no build tooling.
- Fonts via Google Fonts CDN (`IBM Plex Sans`, `IBM Plex Mono`).
- All imagery generated at runtime on `<canvas>` using a seeded
  pseudo-random function (so slices look different but are
  deterministic per index) — no external image assets.
- No `localStorage`/`sessionStorage` — all state lives in JS variables/DOM
  for the session.
- Every described interaction (drag WL, wheel-scroll slices, measure tool,
  cine, resizer drag, key-image capture/insert, sign-state toggling) must
  be functionally wired, not just styled to look clickable.

---

## 8. Ergonomic principles (the "why" behind the choices)

1. **Zero mouse-travel for the core loop.** Slice navigation, tool
   switching, and signing are all one keypress away; the report and the
   image are never more than a glance apart.
2. **Dark by necessity, not aesthetic.** The chrome sits at low luminance so
   it never distorts perceived image contrast.
3. **The image is the hero.** It gets the flexible, largest share of
   screen space; every panel is either fixed-width or user-resizable, never
   competing for default space with the viewport.
4. **Boilerplate should never be retyped.** Macro chips and templates exist
   because "normal chest CT" language is identical across hundreds of
   reports a day.
5. **Unsafe states are visibly blocked, not just discouraged.** Signing
   without an impression isn't a validation error after the fact — the
   button is inert until the report is actually complete.
6. **Every shortcut is self-documenting.** Keys are printed on the controls
   that use them; the `?` overlay is a backup, not the primary way to learn
   the interface.
   
   
   A few directions worth considering, grouped by what they'd actually change about the workflow:

Dictation & AI draftingReal
-time voice-to-text with structured routing — not just transcription, but parsing spoken findings into the right section (Findings vs. Impression) as you talk, with a visible transcript the radiologist can correct inline before it's committed.AI-drafted
 first pass — a model reads the study and proposes Findings/Impression text the radiologist edits rather than writes from scratch. This is high-value but needs very visible provenance (e.g. AI-drafted text stays a distinct color/style until the radiologist has touched it) so nothing signed ever looks like it was verified when it wasn't.Autotext expansi
on — short typed triggers (".nlung", ".nctabd") expand into full normal-organ phrases, faster than clicking macro chips and works mid-sentence.AI-assisted image revi

ewDetection/measurement over
lays — nodule, fracture, or lesion candidates marked directly on the image with a confidence indicator, always accept/reject by the radiologist, never auto-inserted into the report.Prior comparison with registrati
on — auto-fetch the relevant prior series, align it to the current study, and highlight interval change (new/growing/resolved) rather than making the radiologist eyeball two separate viewers.Quantification tools — auto-volumetric
s for nodules, coronary calcium scoring, RECIST-style lesion tracking across timepoints, feeding numbers straight into the report instead of manual re-entry.Report intelligence & safetyPre-sign QA pass

 — flags laterality mismatches, 
an Impression that contradicts Findings, missing required fields, or a critical-sounding phrase in Findings that wasn't flagged critical.Structured/synoptic fields for applicable studies — BI
-RADS, LI-RADS, PI-RADS style discrete dropdowns alongside free text, since payers and tumor boards often need the structured value, not prose.Closed-loop critical results — flagging a finding doesn't ju
st log it; it pages the referring clinician and tracks acknowledgment, with the report showing that chain.Viewer capabilityMPR / volume rendering / MIP for CT and MR, and P

ET-CT fusion overlay 
— the current 2D-slice viewer is the common case but not the only one.Auto-loaded hanging protocols by modality/body part so the layout is right b
efore the radiologist even opens the study.Collaboration & trustAddendum and audit trail — every post-sign edit versioned and

 visible, not silently ov
erwritten.Peer review / discrepancy flagging built into the same screen, since QA usually happens in a
 separate system today.PersonalizationPer-radiologist macro libraries and template defaults, adjustable report font size,

 and a colorblind-s
afe palette option for measurement/annotation colors.If any of these are heading toward a v2, I'd flag the AI-drafting and detection-overlay ones as needing 

the most care up front — worth designing the "this is AI, not verified" visual language before building the feature itself, since that's what determines whether it's trusted or distrusted once radiologists actually use it. 

# Design Spec: AI-Assisted Reporting & Detection Overlays (v2)
### Extends: Cornerstone Reading Workstation

Two additive features for the existing viewer + report console. Both
introduce AI output into a clinical-legal document and a diagnostic image,
so the central design problem for *both* is the same: **make AI
contribution and radiologist verification visually distinct at every
stage, with no way for AI text or marks to reach a signed report or an
unreviewed screenshot without a human decision recorded against them.**

Read this alongside the base spec — tokens, layout, and typography below
extend rather than replace it.

---

## Part A — AI-Drafted Report Content

### A.1 What it does
On opening a study, an AI model proposes Findings and Impression text based
on the images. The radiologist edits, accepts, rejects, or regenerates —
the model never writes directly into a signed report, and the report can
never be signed while any AI-drafted sentence remains in its unreviewed
state.

### A.2 New tokens
| Token | Value | Use |
|---|---|---|
| `--ai` | `#9b8cf0` (muted violet) | AI-authored content, distinct from `--accent` (radiologist/system actions) so the two are never confusable |
| `--ai-glow` | `rgba(155,140,240,0.12)` | background wash behind unreviewed AI text |
| `--ai-border` | `rgba(155,140,240,0.4)` | left-rule / outline on AI blocks |

Violet is chosen deliberately: it must not read as "error" (red/amber) or
"success" (teal/green/`--ok`) — AI output is neither wrong nor verified by
default, it's *pending*.

### A.3 States (this is the core of the feature)
Every AI-authored span of text carries one of four states, and the state
is always visible, never just implied by a tooltip:

1. **Unreviewed** — violet left-rule + faint violet background wash + a
   small `✨ AI-drafted` mono tag at the start of the block. Editable but
   flagged.
2. **Accepted** — radiologist clicked "Accept" or manually edited the text.
   Violet styling is fully removed; the text becomes indistinguishable from
   anything the radiologist typed themselves. This is intentional: once
   touched, it *is* the radiologist's text, full stop, and the UI should
   stop reminding them it wasn't originally theirs.
3. **Rejected/regenerated** — block is removed and either left blank or
   replaced with a new AI proposal (still Unreviewed).
4. **Edited-in-place** — the moment a radiologist types inside an
   unreviewed block, it silently converts to Accepted on blur. No
   confirmation dialog; typing *is* the acceptance gesture.

### A.4 Layout additions
- **Draft banner**, top of the Findings section, shown only while any
  Unreviewed block exists: *"AI draft — review before signing"* with
  inline **Accept all** / **Discard all** actions and a per-section
  regenerate icon (↻).
- Each AI-drafted paragraph/sentence gets its own accept (✓) / reject (✕)
  affordance in the left gutter on hover — granular, not all-or-nothing,
  since a radiologist may agree with 4 of 5 sentences.
- **Confidence is not shown as a percentage.** Radiologists calibrate
  poorly to false-precision numbers; instead surface it qualitatively only
  where it changes behavior (see A.6).

### A.5 Sign-gate rule
Extends the existing "Sign & Finalize disabled until Impression has
content" rule:
> Sign & Finalize stays disabled while **any** block anywhere in the report
> is in the Unreviewed state — not just Impression. The sign-hint text
> becomes explicit: *"2 AI-drafted findings need review before signing."*
This is a hard gate, not a warning-and-proceed dialog — matches the
existing pattern of blocking rather than nagging.

### A.6 Edge cases to design for
- **Empty/low-confidence study** (e.g. poor technique, wrong protocol): AI
  should say so directly — *"Unable to draft — image quality insufficient"*
  — rather than fabricating generic normal findings. A qualitative
  confidence flag belongs here: this is the one place it changes what the
  radiologist does next.
- **Conflicting prior report**: if AI drafts something inconsistent with a
  prior signed report on the same patient/finding, show a small inline
  note ("Prior report (2025-11-02) described this differently") — surfaced,
  not resolved automatically.
- **Regeneration history**: keep a lightweight local log (this session
  only) of prior AI drafts per section, reachable via a small "v2 of 3"
  stepper, so a radiologist who regenerates and then prefers the original
  isn't stuck retyping it.
- **Multi-user/teaching contexts**: if a resident's accepted edit differs
  substantially from the AI draft, that's a normal accepted state — no
  special UI; provenance tracking is AI-vs-human, not resident-vs-attending.

### A.7 Audit trail
Every Accept/Reject/Regenerate/Edit-in-place action is timestamped and
attributed in a per-report changelog (accessible from "More actions" or
similar), independent of the visible document. This is what makes the
violet-fades-on-accept behavior safe — the fact that AI proposed it is
still recoverable later even though the live document no longer shows it.

---

## Part B — AI Detection Overlays on Images

### B.1 What it does
An AI model marks candidate findings directly on the image — nodules,
fractures, lesions — as an overlay layer the radiologist can toggle,
inspect, and accept/dismiss per mark. Marks never auto-populate the report;
accepting a mark is what creates a linked Findings entry (optionally via
the same Key Images bridge already in the base design).

### B.2 New tokens
Reuse `--ai` / `--ai-border` from Part A for consistency — one AI color
across the whole product, not a second competing hue. Add:

| Token | Value | Use |
|---|---|---|
| `--ai-mark-fill` | `rgba(155,140,240,0.18)` | ROI box/contour fill |
| `--ai-mark-stroke` | `#9b8cf0` | ROI box/contour outline |
| `--ai-mark-dismissed` | `rgba(86,93,107,0.5)` (uses `--text-faint`) | dismissed marks, kept visible but muted, not deleted |

Measurement/manual-annotation color stays the existing amber
(`#ffd966`) from the base spec — a radiologist's own measurement must never
share a color with an AI-generated one.

### B.3 Layout additions
- New toolbar toggle: **AI Findings** (`Shift+A`), off by default on
  study open — marks should be an opt-in overlay, not something that loads
  before the radiologist has formed their own first impression, to avoid
  anchoring bias. Toggling on reveals all marks for the current
  slice/series; a small count badge on the button shows total marks across
  the study ("AI Findings · 3").
- Each mark: a rounded rectangle or contour outline at `--ai-mark-stroke`,
  with a small numbered tag (①②③) rather than a text label directly on the
  image, to avoid cluttering the image itself. A hover/click on the tag
  opens a compact popover: mark type, the qualitative confidence flag
  (High / Uncertain — never a bare percentage), and Accept / Dismiss
  buttons.
- **Accepted marks** convert to the radiologist's own measurement/annotation
  styling (amber) and behave exactly like a manually placed
  measurement from that point on — same rule as Part A's "accept removes
  the AI styling."
- **Dismissed marks** stay visible but rendered in muted gray with a
  strikethrough tag, toggleable via a "show dismissed" checkbox in the AI
  Findings panel — dismissed is a recorded decision, not a deletion, for
  the same audit reasons as Part A.
- Slice-aware indicator: if AI marks exist on slices other than the one
  currently viewed, show small tick marks on the slice slider at those
  positions (reusing the existing right-edge slice slider from the base
  viewport) so the radiologist doesn't have to scroll blindly to find them.

### B.4 Interaction with existing tools
- AI Findings overlay respects the existing Zoom/Pan/Window-Level
  transforms — marks must move and scale with the image, not float in
  screen space.
- Measure tool (`M`) still works normally over an AI mark; drawing a manual
  measurement near a mark does not auto-link them — linking only happens
  through explicit Accept.
- Cine mode: AI Findings toggle stays respected during cine playback but
  marks should visually simplify (outline only, no popovers) during
  playback to avoid flicker/clutter at speed.

### B.5 Report linkage
Accepting a mark opens a small inline choice, not a silent auto-write:
*"Add to Findings as new line"* / *"Attach to existing line"* (with a
dropdown of current Findings sentences) / *"Just keep as image marker, don't
add text."* This keeps the same human-in-the-loop principle as Part A:
AI can propose a *link* between image and text, but the radiologist
chooses whether and how it's recorded.

### B.6 Edge cases to design for
- **High mark volume** (e.g. a screening chest CT with many small nodules):
  cap the default overlay to the N highest-confidence marks with a "Show
  N more" affordance, rather than covering the image in boxes.
- **False-positive-prone modalities**: for known-noisy detection tasks
  (e.g. lung nodule vs. vessel cross-section), the qualitative flag should
  bias toward "Uncertain" rather than "High" — better to under-claim
  confidence than to anchor the radiologist.
- **Disagreement with prior study**: if a prior signed report already
  addressed the same region and called it benign/stable, the mark's
  popover should surface that prior text inline, same pattern as A.6.

### B.7 Audit trail
Same principle as Part A: every Accept/Dismiss is timestamped and
attributed, independent of what's currently rendered, so "why did the
radiologist not act on mark ③" is always answerable later.

---

## Part C — Shared principles (apply to both)

1. **One AI color, everywhere.** Violet means "AI produced this, not yet
   verified" in text and on images alike. No other feature should ever
   reuse that hue.
2. **Acceptance is destructive to the AI styling, not the content.** Once a
   radiologist accepts (or edits, which implies acceptance), the AI
   markers disappear from the live view — the content becomes fully the
   radiologist's, visually and legally. The record of AI origin lives only
   in the audit trail, not the working document.
3. **Nothing AI-generated can reach a signed artifact unresolved.** Signing
   is blocked while unreviewed text or unresolved marks exist — this is
   the same hard-gate pattern as the existing Impression-required rule,
   just extended.
4. **Qualitative over quantitative confidence.** Two levels only (e.g.
   High / Uncertain) shown as a word, not a percentage — avoids false
   precision and anchoring on a number that wasn't validated for that
   specific case.
5. **Opt-in, not on-by-default, for anything that could anchor a first
   impression.** AI Findings overlay starts off; AI-drafted text is shown
   but never silently pre-fills a field the radiologist thinks is
   empty — it is always visually marked as a draft.
6. **Dismissal ≠ deletion.** Both dismissed marks and rejected draft text
   remain recoverable/auditable, never silently discarded, for the same
   reason clinical documentation generally doesn't allow silent edits.

---

## Part D — Open questions for a v2 build (flag before implementing)

- Where does the audit trail live — inline "changelog" panel in this same
  console, or a separate compliance/QA tool? Affects whether Part A.7/B.7
  need any UI at all in v2.1 or can stay backend-only initially.
- Should AI-drafted Impression text be held to a stricter gate than
  Findings (e.g. always require an explicit Accept, never allowed to
  silently convert via edit-in-place) given it's the legally load-bearing
  section of the report?
- Does "Uncertain" confidence ever warrant hiding a mark by default rather
  than showing it muted — i.e. is there a threshold below which showing
  the mark at all does more harm (alert fatigue) than good?
