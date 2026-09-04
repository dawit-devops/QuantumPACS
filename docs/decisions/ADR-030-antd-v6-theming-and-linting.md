# ADR-030: Ant Design v6 Theming, Linting, and CSS Override Policy

## Status

Accepted

## Date

2026-08-22

## Context

Following the antd v5 → v6 upgrade (ADR-006) and the `App.useApp()` migration, the
codebase needs consistent conventions for:

- Theme token usage (light + dark mode)
- Component-level styling (`classNames`/`styles` vs CSS files)
- Linting and deprecated-API detection
- `.ant-*` CSS selector policy

Without explicit rules, theme drift accumulates: some components use hardcoded colors,
others use tokens, and CSS overrides silently break when antd internals change.

## Decision

### 1. Single Root ConfigProvider

One `<ConfigProvider>` wraps the entire app in `index.tsx`. Never nest additional
`ConfigProvider` instances unless strict locale/theme isolation is required (e.g. a
preview panel with a different locale).

```tsx
// frontend/src/index.tsx
<ConfigProvider theme={isDark ? darkTheme : lightTheme} renderEmpty={renderEmpty}>
  <AntdApp>
    {/* app tree */}
  </AntdApp>
</ConfigProvider>
```

### 2. Theme Token Hierarchy

Follow antd's three-tier token system in order of precedence:

1. **Global tokens** — `colorPrimary`, `colorBgLayout`, `borderRadius`, etc.
   Set in `theme.ts` `token` block. Apply app-wide.
2. **Component tokens** — `Button: { primaryColor }`, `Table: { headerBg }`, etc.
   Set in `theme.ts` `components` block. Apply per-component.
3. **`classNames`/`styles` props** — Inline on individual component instances.
   Use for one-off overrides that shouldn't affect all instances of a component.

**Do not** set global tokens to fix a single component's appearance. Use component
tokens or `classNames`/`styles` instead.

### 3. Brand Tokens

Brand colors live in `BRAND` constant in `theme.ts` and are referenced by both
light and dark theme tokens. When adding a new semantic color:

1. Add it to `BRAND` with an accessibility note (contrast ratio, WCAG level)
2. Reference it in both `lightTheme.token` and `darkTheme.token`
3. Add component-level overrides if the derived defaults fail AA

### 4. Dark Mode

Dark mode uses `antTheme.darkAlgorithm` with full component token overrides in
`darkTheme`. The `ThemeProvider` toggles `isDark` state and swaps the theme prop.

Key dark-mode conventions:
- `colorBgLayout: "#0F172A"` (slate-900) — page background
- `colorBgContainer: "#1E293B"` (slate-800) — card/modal/container surfaces
- `colorBgElevated: "#334155"` (slate-700) — dropdowns, popovers, tooltips
- `colorBorder: "#334155"` — borders on dark surfaces
- Component tokens override every container background (Table, Card, Modal, etc.)

### 5. Static API Migration (`App.useApp()`)

All feedback APIs (`message.*`, `notification.*`, `modal.*`) **must** use
`App.useApp()` instead of static imports. Static calls bypass ConfigProvider
theme/locale context.

```tsx
// ✅ Correct
import { App } from "antd";
function MyComponent() {
  const { message } = App.useApp();
  message.success("Done");
}

// ❌ Wrong — bypasses theme
import { message } from "antd";
message.success("Done");
```

The `<AntdApp>` wrapper in `index.tsx` provides the context. Every component
that toasts must render under this wrapper (guaranteed by the single root layout).

### 6. CSS File Policy

#### Allowed `.ant-*` CSS overrides ( justified exceptions)

| Category | Example | Why CSS is required |
|----------|---------|-------------------|
| Print media queries | `@media print { .ant-table { display: none } }` | No token equivalent for media queries |
| Responsive breakpoints | `@media (max-width: 768px) { .ant-menu-horizontal { ... } }` | No token equivalent for breakpoints |
| Scoped dark-mode panels | `.detail-viewport-root .ant-menu-horizontal { ... }` | Panel-specific, not expressible via tokens |
| Tabs content-holder bg | `.ant-tabs-content-holder { background: transparent }` | No `contentHolderBg` token in antd v6 |

#### Prohibited `.ant-*` CSS overrides

| Pattern | Why | Alternative |
|---------|-----|-------------|
| `.ant-card { border-radius }` | Already in `Card.borderRadius` theme token | Remove — theme handles it |
| `.ant-btn { color }` | Already in `Button` component tokens | Use `Button` component tokens |
| `.ant-table { background }` | Already in `Table` component tokens | Use `Table` component tokens |
| Global `.ant-*` selectors in non-media-query context | Fragile across antd upgrades | Use `classNames`/`styles` props |

#### Rule of thumb

If a `.ant-*` override targets a **single component type** and has **no media
query**, it almost certainly belongs in `theme.ts` component tokens or on the
component's `classNames`/`styles` prop — not in a CSS file.

### 7. Ant Design CLI Linting

`@ant-design/cli` v6.6.1 is installed as a devDependency. Available via:

```bash
npx antd lint ./src --format json          # Full lint (deprecated + a11y + usage + perf)
npx antd lint ./src --only deprecated      # Deprecated API scan only
npx antd usage ./src --format json         # Component usage statistics
npx antd doctor --format json              # Project configuration health
```

#### Workflow

1. **Before writing antd code**: `antd info <Component> --format json` to verify API
2. **After modifying antd code**: `antd lint <changed-path> --format json` to catch
   deprecated or problematic usage
3. **In CI or manual review**: `npm run antd:lint` for full scan

The CLI is **not** in lint-staged/pre-commit (~10s per file scan is too slow for
commit-time gating). It's a manual/CI gate.

#### Current baseline (2026-08-22, post-migration)

| Category | Count | Top issues |
|----------|-------|------------|
| deprecated | 26 | `Space.direction` (8), `List` (5), `Spin.tip` (2), `Divider.type` (2), `Drawer.width` (2), `Select.optionFilterProp` (2), `AutoComplete.onSearch` (1), `Modal.maskClosable` (1), `Modal.confirm/info` static (3) |
| usage | 13 | `Select.Option` children → `options` prop (10), static `Modal.confirm` (3) |
| a11y | 0 | Clean |
| performance | 0 | Clean |

> Migrated this session: `Alert.message` → `title` (75), `Statistic.valueStyle` → `styles.content` (12).

### 8. Regression Checklist

Before merging frontend changes touching antd components:

- [ ] One root `ConfigProvider`; SSR style order/hydration verified (if applicable)
- [ ] Tokens first; no broad global `.ant-*` overrides
- [ ] `Table` has stable `rowKey`; sort/filter/pagination unified
- [ ] `Select` remote mode disables local filter when using remote search
- [ ] `Upload` controlled/uncontrolled mode is explicit with failure/retry path
- [ ] Feedback APIs use `App.useApp()`, not static imports
- [ ] `antd lint` run on changed files (manual or CI)

## Migration Examples (2026-08-22 session)

These are concrete before/after examples from the initial cleanup pass.

### Example A: Static `message.*` → `App.useApp()` (8 files)

**Before** (`src/qa/Incidents.tsx`):
```tsx
import { Layout, Table, Button, message, ... } from "antd";

function Incidents() {
  // message.success/error bypass ConfigProvider theme
  const submit = async () => {
    await request("qa/incidents", { method: "POST", data: values });
    message.success("Incident logged");
  };
}
```

**After**:
```tsx
import { App, Layout, Table, Button, ... } from "antd";

function Incidents() {
  const { message } = App.useApp();  // inherits theme/locale
  const submit = async () => {
    await request("qa/incidents", { method: "POST", data: values });
    message.success("Incident logged");
  };
}
```

**Files migrated**: `ExamConsole.tsx`, `TechnologistWorklist.tsx`, `Incidents.tsx`,
`QAReviewForm.tsx`, `ProtocolRegistry.tsx`, `CorrectiveActions.tsx`,
`ReadingConsole.tsx`, `PeerReviewInbox.tsx`.

### Example B: Redundant CSS → theme tokens (4 overrides removed)

**Before** (`src/metrics/Metrics.css`):
```css
.ant-card {
  border-radius: var(--card-radius, 8px);
  transition: background-color var(--duration-normal) var(--easing-standard);
}

[data-theme="dark"] .ant-card {
  border-color: var(--border-color);
}
```

**After**: Removed — `Card: { borderRadius: 8 }` already exists in both
`lightTheme` and `darkTheme` component tokens. Dark-mode border-color is
handled by `Card.colorBgContainer` in the dark theme.

**Files cleaned**: `Metrics.css`, `DicomWebAdmin.css`, `Fhir.css`.

### Example C: Component-scoped CSS → `styles`/`style` props (5 overrides)

**Before** (`src/radiologist/ResidentHome.css`):
```css
.rh-card .ant-card-body {
  padding-top: 16px;
}
```
```tsx
// ResidentHome.tsx
<Card className="rh-card" title="My Queue">
```

**After**:
```tsx
<Card
  className="rh-card"
  title="My Queue"
  styles={{ body: { paddingTop: 16 } }}
>
```
```css
/* .rh-card .ant-card-body rule removed */
```

**Other examples in this batch**:

| CSS before | TSX after |
|-----------|----------|
| `.sched-block-meta .ant-tag { margin: 0; font-size: 10px }` | `<Tag style={{ margin: 0, fontSize: 10, lineHeight: '16px' }} />` |
| `.series-navigator-slider .ant-slider { flex: 1 }` | `<Slider style={{ flex: 1, margin: '8px 0' }} />` |
| `.reading-presets-panel .ant-collapse-header { padding; color }` | `<Collapse styles={{ header: { padding, color } }} />` |
| `.rp-save-row .ant-input { flex: 1; background; color }` | `<Input style={{ flex: 1, background, color }} />` |

### Example D: Table `rowKey` audit (69 tables verified)

All 69 `<Table>` instances already had `rowKey` set. Audit pattern:

```bash
# Find Tables without rowKey (1500-char lookahead)
python3 -c "
import re, os
for root, dirs, files in os.walk('src'):
    for f in files:
        if not f.endswith('.tsx'): continue
        path = os.path.join(root, f)
        content = open(path).read()
        for m in re.finditer(r'<Table\\b', content):
            block = content[m.start():m.start()+1500]
            if 'rowKey' not in block:
                print(f'MISSING: {path}:{content[:m.start()].count(chr(10))+1}')
"
```

Common `rowKey` patterns:
- `rowKey="id"` — database-backed entities (34 tables)
- `rowKey={(r) => r.id}` — typed record access (8 tables)
- `rowKey="exam_id"`, `rowKey="studyInstanceUid"` — domain-specific (14 tables)
- `rowKey={(r) => \"${r.resource_type}-${r.method}\"}` — composite keys (3 tables)

## Consequences

### Positive

- Consistent theming across 118 component files
- Dark mode works reliably — every container background is token-controlled
- Deprecated API detection via `antd lint` catches issues before they reach production
- CSS override surface is minimal (22 overrides, all justified) — low breakage risk
  on antd upgrades
- `App.useApp()` migration complete — zero static feedback API calls remain in
  component files

### Negative

- ~10s per-file lint latency prevents pre-commit integration
- 26 deprecated warnings remain — mostly `Space.direction` (8), `List` (5), and
  component-specific deprecations that require individual migration strategies
- Component-scoped `classNames`/`styles` props can scatter styling logic across
  TSX files instead of co-located CSS

### Risks

- Ant Design v7 may deprecate additional APIs currently in use (e.g. `List` component,
  `Drawer.width`). `antd lint` will surface these when the time comes.
- The 22 remaining `.ant-*` CSS overrides depend on antd's internal DOM structure.
  These are all scoped to specific parent classes and unlikely to break, but should
  be audited on each major upgrade.
