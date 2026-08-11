# QuantumPACS — Round 2: Refinement Package

> **Skill:** SVG Logo Designer · **Phase:** refine selected concepts → final variations
> **Date:** 2026-08-11 · **Location:** `design-system/quantumpacs/logos/round2/`
> **Basis:** Round-1 exploration recommended refining **Concept 3 (Q-Orbit)** and **Concept 5 (Aperture)** — one owns the *name*, the other owns the *promise*. Round 2 also adds **Concept C — The Orbit (refined)**, the shipped mark's variant family, so the brand has a like-for-like comparison with the alternatives.
> **Palette (live tokens):** blue-600 `#0077B6` · cyan-400 `#22D3EE` · teal-600 `#059669` · cyan-700 `#0E7490` · slate-800 `#1E293B` · white `#FFFFFF`
> **Constraint:** calm clinical precision — no purple "AI glow", no neon, no consumer cheer.

Each mark now ships a full variant family: **icon · icon monochrome dark · icon monochrome light (reversed) · favicon · horizontal lockup · vertical lockup**. All are viewBox-based, gradient defined once in `<defs>`, and accessible (`role="img"` + `<title>`/`<desc>`).

> **Orbit files live in the `orbit/` subfolder** (`orbit/orbit-icon.svg`, etc.) to keep the three concept families visually separated.

---

## Concept A — The Q-Orbit (refined) · *the monogram*

### What changed from round 1

| Aspect | Round 1 | Round 2 (refined) |
|---|---|---|
| **Bowl position** | Centered at (46,46) — optically heavy top-left | Biased to (42,42) so the tail + electron **balance the glyph** as a true Q letterform |
| **Tail** | Straight diagonal `L66,66 84,84` | **Curved orbit** — cubic Bézier exiting along the bowl's tangent, sweeping into the electron |
| **Tail joint** | Abrupt join at the ring | Curve merges at the bowl edge (round cap), seamless |
| **Electron node** | r 6 at (84,84) | r 6.5, larger presence, teal — the "study" anchor |
| **Nucleus** | Solid cyan-700 @ 35% | Gradient-filled, tied to the current Orbit's patient-focused core |
| **Favicon** | — | Simplified bowl + tail + electron (nucleus dropped below 24px) |

### Variants

| File | Use |
|---|---|
| `qorbit-icon.svg` | Primary icon — headers, signage, app tiles |
| `qorbit-icon-mono-dark.svg` | Slate-800 — light/print, B&W documents |
| `qorbit-icon-mono-light.svg` | White (reversed) — dark surfaces, splash |
| `qorbit-favicon.svg` | Browser tab / 16–24px contexts |
| `qorbit-lockup-horizontal.svg` | Web header, business cards, email |
| `qorbit-lockup-vertical.svg` | Social profiles, app-store listing |

### Design rationale (why this works)

- **Trademark strength:** a letterform is inherently more ownable than a generic geometric mark — "the Q is the brand."
- **Quantum equity preserved:** the curved tail *is* an orbit, the electron is the study, the nucleus is the patient — the same story as the current Orbit mark, in one glyph.
- **At 24px:** bowl + tail + electron remain distinct; the favicon drops the nucleus for clean small-size legibility.

---

## Concept B — The Aperture (refined) · *the frame through which you see*

### What changed from round 1

| Aspect | Round 1 | Round 2 (refined) |
|---|---|---|
| **Corner markers** | Four short "tick" lines at ring cardinal points | **True window/level corner brackets** — the L-shaped indicators radiologists use, at the actual frame corners |
| **Frame weight** | stroke 5 | stroke 5.5 — frame leads, ring supports |
| **Focus dot** | r 4 solid | r 4.5 gradient fill — the image at the center |
| **Lens ring** | stroke 3.5 cyan | Kept cyan 3.5, reads as the optics behind the frame |
| **Favicon** | — | Simplified frame + ring + dot (brackets dropped below 24px) |

### Variants

| File | Use |
|---|---|
| `aperture-icon.svg` | Primary icon — headers, signage, app tiles |
| `aperture-icon-mono-dark.svg` | Slate-800 — light/print, B&W documents |
| `aperture-icon-mono-light.svg` | White (reversed) — dark surfaces, splash |
| `aperture-favicon.svg` | Browser tab / 16–24px contexts |
| `aperture-lockup-horizontal.svg` | Web header, business cards, email |
| `aperture-lockup-vertical.svg` | Social profiles, app-store listing |

### Design rationale (why this works)

- **Promise match:** "Diagnostic Clarity, Quantum Fast" — the mark *is* the moment the image comes into focus.
- **Rad-native detail:** the corner brackets are the actual window/level affordance, so it reads instantly to a radiologist and stays "medical" to everyone else.
- **At 24px:** frame + ring + dot carry the concept; the favicon drops the brackets for clean small-size legibility.

---

## Concept C — The Orbit (refined) · *the shipped mark's variant family*

The Orbit is the QuantumPACS mark **in production** (`QuantumLogo.tsx`, favicon, login screen, sidebar header). Until now it shipped only as the legacy 40×40 canvas with no mono variants or vertical lockup — so it could not be placed at like-for-like comparison with the Round-2 Q-Orbit and Aperture families.

Concept C closes that gap: a refined, scaled-up variant family on the standard 100×100 canvas, with the same full-color / mono-dark / mono-light / favicon / lockup set the alternatives carry.

### What changed from round 1

| Aspect | Round 1 (current / shipped) | Round 2 (refined) |
|---|---|---|
| **Canvas** | `viewBox="0 0 40 40"` (legacy, used by `QuantumLogo.tsx`) | `viewBox="0 0 100 100"` — matches the Q-Orbit and Aperture round-2 canvases |
| **Outer ring** | r 18, stroke 3 | r 34, stroke 6 — leads the hierarchy, survives at small sizes |
| **Inner ring** | r 10, stroke 2, 50% opacity | r 20, stroke 3.5, 50% opacity — same role, scaled |
| **Orbit ellipse** | rx 6 / ry 2.5, stroke 1.5, 60% opacity | rx 14 / ry 5.5, stroke 2.5, 70% opacity — second axis orbit reads as motion, not a hairline |
| **Axis ticks** | Bleed to canvas edge: `(20, 2)–(20, 10)` and `(20, 30)–(20, 38)` — only 2u clearance, visually collides with the ring stroke | Contained **inside** the outer ring: `(50, 12)–(50, 22)` and `(50, 78)–(50, 88)` — the scan plane stays a contained axis |
| **Nucleus** | r 2.5 — visually lost against the ring at large sizes | r 6.5, gradient fill — the patient anchor, matches Q-Orbit's nucleus weight |
| **Favicon** | (shipped inline in `frontend/index.html`, no SVG file) | Standalone SVG: outer ring + axis ticks + nucleus (inner ring and ellipse dropped below 24px) |
| **Mono variants** | — | Slate-800 (light backgrounds) + white reversed (dark surfaces) |
| **Vertical lockup** | — | Icon centered above the wordmark |

### Variants

| File | Use |
|---|---|
| `orbit/orbit-icon.svg` | Primary icon — headers, signage, app tiles |
| `orbit/orbit-icon-mono-dark.svg` | Slate-800 — light/print, B&W documents |
| `orbit/orbit-icon-mono-light.svg` | White (reversed) — dark surfaces, splash |
| `orbit/orbit-favicon.svg` | Browser tab / 16–24px contexts |
| `orbit/orbit-lockup-horizontal.svg` | Web header, business cards, email |
| `orbit/orbit-lockup-vertical.svg` | Social profiles, app-store listing |

### Design rationale (why this works)

- **Shipped equity preserved:** the round-1 Orbit is already in production and on every login screen. Refining, not replacing, keeps brand recognition while solving the documented problems (edge-bled ticks, weak central hierarchy).
- **At 24px:** outer ring + ticks + nucleus remain distinct; the favicon drops the inner ring and ellipse so the silhouette stays clean.
- **Side-by-side evaluation:** with the same variant family as Q-Orbit and Aperture, all three concepts can be reviewed at like-for-like scales and on like-for-like surfaces.

### Migration note

The legacy `orbit-current-icon.svg` and `orbit-current-lockup.svg` at `logos/` remain the **shipped** assets (`QuantumLogo.tsx` references them directly). When this refinement is approved, those files are replaced by the round-2 family and `QuantumLogo.tsx` updates its `viewBox` rasterization. Until then, both ship in parallel.

---

## Usage Guidelines (Phase 7)

### Clear space
- **Icon:** keep the mark's **2.5u** clear on all sides — for Q-Orbit measure from the bowl edge, for Aperture from the frame edge, for Orbit from the outer-ring ink edge.

### Clear space
- **Icon:** keep the mark's **2.5u** clear on all sides — for Q-Orbit measure from the bowl edge, for Aperture from the frame edge.
- **Lockup:** keep the wordmark's x-height clear on all sides.

### Minimum sizes
| Form | Minimum | Note |
|---|---|---|
| Icon (full detail) | **24px** | Below this, switch to the favicon |
| Favicon | **12px** | Simplified ring/bowl + node |
| Horizontal lockup | **140px** wide | Wordmark becomes unreadable below |
| Vertical lockup | **120px** wide | |

### Color usage
- **Full color** on white or slate-900 — never on busy/mid-tone backgrounds.
- **Monochrome dark** on light backgrounds; **monochrome light (reversed)** on dark backgrounds — B&W printing, faxes, embossing.
- Gradient is **non-negotiable** for the full-color mark — never flatten it to a single hue.
- Keep "PACS" in cyan-700 `#0E7490` on light lockups (AA) and cyan-400 `#22D3EE` on the dark rail.

### Do / Don't
- ✓ Keep the blue→cyan→teal gradient direction (top-left → bottom-right).
- ✓ Preserve aspect ratio; scale via width with `height: auto`.
- ✓ Use the favicon for anything under 24px.
- ✗ Rotate, stretch, or add drop-shadows/glows/3D effects.
- ✗ Recolor with foreign palettes (indigo/purple "AI" gradients).
- ✗ Place on busy backgrounds without clear space.

---

## Exporting to PNG (if needed)
```bash
# Inkscape
inkscape qorbit-icon.svg --export-png=qorbit-icon.png --export-width=1000
# ImageMagick
convert -background none qorbit-icon.svg qorbit-icon.png
```

## Web implementation
```html
<!-- Inline SVG (recommended) for full control -->
<img src="round2/qorbit-icon.svg" alt="QuantumPACS" />
```
```css
.logo { width: 100%; max-width: 200px; height: auto; }
@media (max-width: 768px) { .logo { max-width: 150px; } }
```
