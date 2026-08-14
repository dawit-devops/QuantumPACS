# Design System Master — QuantumPACS Resident Console

> **LOGIC:** When building a specific page, first check `pages/[page-name].md`. If it exists, its rules override this Master. Otherwise use Master.
>
> **NOTE:** This Master mirrors the project's **live** design system — `frontend/src/common/tokens.css` (primitive+semantic, light/dark) and `frontend/src/common/theme.ts` (Ant Design v6 seed). Do NOT introduce a parallel palette; extend tokens in `tokens.css` and mirror them in `theme.ts`.

**Project:** QuantumPACS Resident Console
**Generated:** 2026-08-14
**Category:** Clinical data-dense workstation (medical imaging, PACS)

---

## Global Rules

### Color Palette (semantic layer — light mode)

| Role | Hex | CSS Variable | AntD Seed |
|------|-----|--------------|-----------|
| Primary | `#0E7490` (cyan-700, ≈5.1:1 AA) | `--color-primary` | `colorPrimary` |
| Secondary | `#22D3EE` (cyan-400) | `--color-secondary` | — |
| Accent / CTA | `#059669` (teal-600) | `--color-accent` | `colorSuccess` (#10B981 teal-500) |
| Success | `#10B981` (teal-500) | `--color-success` | `colorSuccess` |
| Warning | `#F59E0B` (amber-500) | `--color-warning` | `colorWarning` |
| Destructive | `#DC2626` (red-600) | `--color-error` | `colorError` |
| Info | `#0E7490` (cyan-700) | `--color-info` | `colorInfo` |
| Page bg | `#F8FAFC` (slate-50) | `--bg-page` | `colorBgLayout` |
| Surface bg | `#FFFFFF` | `--bg-surface` | `colorBgContainer` |
| Foreground | `#0F172A` (slate-900) | `--text-strong` | `colorText` |
| Border | `#E2E8F0` (slate-200) | `--border-default` | `colorBorder` |

**Dark mode** (`[data-theme='dark']`): primary `#22D3EE` (cyan-400), success `#34D399` (teal-400), warning `#FBBF24` (amber-400), error `#F87171` (red-400). Tinted `*-bg` tokens use higher alpha (0.15) on dark.

### Typography

- **Headings:** Figtree (`--font-heading`)
- **Body:** Inter (`--font-sans`) — 14px base, line-height 1.5
- **Mono (numbers/timestamps/accession):** `--font-mono`
- Body text never below 12px (`--font-size-xs` min for captions, 13px for table cells)
- Focus ring: 3px `--color-primary` (`--focus-ring-color`, tokens.css:300)

### Spacing (existing scale)

`--space-1` 4px · `--space-2` 8px · `--space-3` 12px · `--space-4` 16px · `--space-5` 20px · `--space-6` 24px · `--space-8` 32px · `--space-10` 40px · `--space-12` 48px · `--space-16` 64px

### Radius / Shadow / Motion (existing)

Radius: sm 4 / md 6 / lg 8 / xl 12. Shadow sm→xl as defined. Motion: fast 150ms, normal 250ms, slow 400ms; easing `cubic-bezier(0.4,0,0.2,1)`; `prefers-reduced-motion` respected.

---

## Component Specs

Use Ant Design v6 components (already themed via `theme.ts`): `Table`, `Tag`, `Badge`, `Steps`, `Modal`, `Drawer`, `Select`, `Input.TextArea`, `Alert`, `Spin`, `Skeleton`, `Progress`, `Card`, `Descriptions`, `Button`, `Tooltip`. Cornerstone3D for imaging via `CornerstoneElement.tsx` (don't rebuild the viewer).

### Status Badges (resident supervision states) — always color + icon/text, never color alone

| State | Token | Badge color | Icon / text |
|-------|-------|-------------|-------------|
| Draft | cyan | `blue` | `EditOutlined` + "DRAFT" |
| Awaiting review (submitted) | amber | `gold` | `SendOutlined` + "AWAITING REVIEW" |
| In review | purple (`--color-primary` alt) | `purple` | `AuditOutlined` + "IN REVIEW" |
| Returned for revision | amber | `warning` | `RollbackOutlined` + "RETURNED" |
| Co-signed / Final | teal | `green` | `CheckCircleOutlined` + "CO-SIGNED" |

### STAT priority row

4px left border `--color-error`, pulsing red dot + "STAT" text + optional sound toggle. Never border-only.

---

## Style Guidelines

**Style:** Data-Dense clinical workstation — maximum data visibility, minimal chrome, high scannability; existing Reading Worklist / Reading Console are the baseline.

**Page Pattern:** Real-time / operations landing for the Resident Home (queue counts + feedback + teaching library). Primary CTA in the console header (Submit / Co-sign), not a marketing CTA.

---

## Anti-Patterns (Do NOT Use)

- ❌ Emojis as icons — Ant Design SVG icons only (`@ant-design/icons`)
- ❌ Missing `cursor:pointer` / hover transitions (150–300ms)
- ❌ Layout-shifting hovers, low-contrast text (<4.5:1), instant state changes
- ❌ Invisible focus states
- ❌ New parallel palette — extend `tokens.css` / `theme.ts` only
- ❌ Color alone to convey report/priority status

---

## Pre-Delivery Checklist

- [ ] No emojis as icons; consistent icon set (`@ant-design/icons`)
- [ ] `cursor-pointer` + 150–300ms hover transitions on clickables
- [ ] Contrast ≥4.5:1 (light) and dark-mode tuned `*-bg` alphas
- [ ] Visible focus rings for keyboard nav
- [ ] `prefers-reduced-motion` respected
- [ ] Responsive: 375 / 768 / 1024 / 1440
- [ ] No horizontal scroll on mobile; tables scroll internally or card-ify
- [ ] Touch targets ≥44×44px on touch devices
