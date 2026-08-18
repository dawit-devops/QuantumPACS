# Token Audit: Hardcoded Color Values

> Findings from scanning `frontend/src/` for raw hex colors that should use CSS variable tokens.

**Scan date:** 2026-07-23  **Files scanned:** 63 (tsx, ts, css, js)  
**Excluded:** `theme.ts`, `tokens.css`, `design-tokens.json`, `types.d.ts`, test files

---

## Finding 1 — Linear gradient in Login.tsx

| Property | Value | Token |
|----------|-------|-------|
| File | `frontend/src/login/Login.tsx:46` | |
| Hardcoded | `linear-gradient(135deg, #0F172A 0%, #1E293B 50%, #0F172A 100%)` | |
| Replace with | `linear-gradient(135deg, var(--login-gradient-start) 0%, var(--login-gradient-mid) 50%, var(--login-gradient-end) 100%)` | `--login-gradient-start`, `--login-gradient-mid`, `--login-gradient-end` |
| Token defined in | `frontend/src/common/tokens.css` | |

## Finding 2 — Sidebar trigger colors in Sidebar.css

| Property | Value | Token |
|----------|-------|-------|
| File | `frontend/src/common/Sidebar.css:3-4` | |
| Hardcoded | `background: #fff`, `color: #001529` | |
| Replace with | `background: var(--sidebar-trigger-bg)`, `color: var(--sidebar-trigger-text)` | `--sidebar-trigger-bg`, `--sidebar-trigger-text` |
| Token defined in | `frontend/src/common/tokens.css` | |

## Finding 3 — Link colors in index.css

| Property | Value | Token |
|----------|-------|-------|
| File | `frontend/src/index.css:19` | |
| Hardcoded | `color: #0077B6` (link) | |
| Replace with | `color: var(--text-link)` | `--text-link` |
| File | `frontend/src/index.css:23` | |
| Hardcoded | `color: #6366F1` (link hover) | |
| Replace with | `color: var(--text-link-hover)` | `--text-link-hover` |
| Token defined in | `frontend/src/common/tokens.css` | |

## Finding 4 — Logo SVG fill colors in QuantumLogo.tsx

| Property | Value | Token |
|----------|-------|-------|
| File | `frontend/src/common/QuantumLogo.tsx:15-28` | |
| Hardcoded | `#0077B6`, `#6366F1`, `#06B6D4`, `#1E293B` | |
| Replace with | CSS variable references in `<stop stopColor="...">` | SVG gradient stops cannot reference CSS variables directly — needs to use currentColor or inline `<style>` override. |
| Token defined in | `frontend/src/common/tokens.css` | |

**Workaround for SVG:** Define gradient colors via `<style>` rules using CSS vars, then reference `var(--color-primary)` in the SVG element's `style` or use `currentColor` with wrapper elements.

## Finding 5 — Search icon active color in Files.tsx

| Property | Value | Token |
|----------|-------|-------|
| File | `frontend/src/files/Files.tsx:186` | |
| Hardcoded | `filtered ? '#1890ff' : undefined` | |
| Replace with | `filtered ? 'var(--color-blue-500)' : undefined` | `--color-blue-500` |
| Token defined in | `frontend/src/common/tokens.css` | |

## Finding 6 — Search highlight background in Files.tsx

| Property | Value | Token |
|----------|-------|-------|
| File | `frontend/src/files/Files.tsx:203` | |
| Hardcoded | `highlightStyle: { backgroundColor: '#ffc069', padding: 0 }` | |
| Replace with | `backgroundColor: 'var(--table-highlight-bg)'` | `--table-highlight-bg` |
| Token defined in | `frontend/src/common/tokens.css` | |

---

## Summary

| Severity | File | Line | Value | Token Available? |
|----------|------|------|-------|-----------------|
| High | `Login.tsx` | 46 | `#0F172A`, `#1E293B` | ✅ Yes |
| High | `Sidebar.css` | 3-4 | `#fff`, `#001529` | ✅ Yes |
| High | `index.css` | 19,23 | `#0077B6`, `#6366F1` | ✅ Yes |
| Medium | `Files.tsx` | 186 | `#1890ff` | ✅ Yes |
| Medium | `Files.tsx` | 203 | `#ffc069` | ✅ Yes |
| Low | `QuantumLogo.tsx` | 15-28 | 4 raw hex values | ⚠️ Needs SVG CSS var technique |

**Total: 11 raw hex values across 5 files. 10 can be replaced immediately.**  
**Estimated time to fix:** 15 minutes.
