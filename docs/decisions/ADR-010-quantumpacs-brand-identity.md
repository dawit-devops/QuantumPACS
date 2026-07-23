# ADR-010: QuantumPACS Brand Identity

## Status
Accepted

## Date
2026-07-23

## Context
The application was renamed from OpenPACS to QuantumPACS and needed a cohesive brand identity across the UI. Requirements:

- Name change reflected in all user-facing surfaces (title bar, login, sidebar, favicon)
- Professional medical-tech aesthetic — trustworthy (healthcare) + innovative (technology)
- Consistent color palette, typography, and component styling
- Minimal implementation cost — leverage existing Ant Design theme system

## Decision

### Brand DNA

| Element | Value |
|---------|-------|
| Name | QuantumPACS |
| Tagline | Diagnostic Clarity, Quantum Fast |
| Personality | Trustworthy, innovative, precise, professional |
| Domain | Medical imaging / PACS |

### Color Palette

```
Primary     #0077B6  — Deep medical blue (trust, healthcare)
Secondary   #6366F1  — Indigo (innovation, technology)
Accent      #06B6D4  — Cyan (modern, quantum feel)
Success     #10B981  — Emerald
Warning     #F59E0B  — Amber
Error       #EF4444  — Red
Background  #F8FAFC  — Light slate
Text        #1E293B  — Dark slate
```

### Typography
- **Font stack**: `Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif`
- **Weights**: 700 (headings), 600 (subheadings), 400 (body)
- **Ant Design**: default border-radius 6px, wireframe off

### Logo
An SVG atom/orbit symbol with a blue-to-indigo gradient:
- Two concentric rings (outer solid, inner semi-transparent) representing quantum orbits
- Vertical bars at top/bottom suggesting medical/pulse context
- Central dot as the focal point
- Wordmark in dark slate with indigo "PACS"

### Implementation

1. **Theme layer** (`frontend/src/common/theme.ts`) — Ant Design `ThemeConfig` exported with brand tokens
2. **Logo component** (`frontend/src/common/QuantumLogo.tsx`) — inline SVG, accepts `size` and `showText` props
3. **ConfigProvider** in `index.tsx` consumes the theme
4. **Login page** redesigned with dark gradient background, centered card, logo header
5. **Sidebar** branded with logo at top, dark theme
6. **Document titles** prefixed with "QuantumPACS — "
7. **Favicon** inline SVG matching the logo symbol

## Consequences

**Positive:**
- Consistent look across all surfaces via Ant Design theme tokens
- SVG logo is resolution-independent, no external assets
- No new dependencies — uses existing Ant Design theming
- Login page provides a more polished first impression

**Negative:**
- Ant Design themes only affect antd components; custom CSS in some legacy pages may still use old colors (migrated incrementally)
