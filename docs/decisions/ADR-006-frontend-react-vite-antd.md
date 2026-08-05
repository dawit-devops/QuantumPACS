# ADR-006: Frontend Architecture — React, Vite, Ant Design, Cornerstone3D

## Status
Accepted

## Date
2026-07-22

## Context
The original frontend used Jinja2 templates per-route with minimal JavaScript. As the PACS viewer requirements grew (DICOM rendering, study browser, multi-planar reconstruction), a proper SPA became necessary. Requirements:

- DICOM image rendering in the browser
- Study/series/file browser with search
- Responsive layout for desktop reading stations
- Themeable for different hospital branding
- Fast build times during development

## Decision
Build a React SPA with:
- **Vite** for build tooling (fast HMR, TypeScript-native, esbuild bundling)
- **Ant Design v5** for UI component library (tables, forms, modals, layout)
- **Cornerstone3D** for DICOM rendering via cornerstone-wado-image-loader
- **React Router** for client-side routing
- **Manual chunk splitting** in Vite config for optimized bundles (vendor-react, vendor-antd, vendor-cornerstone)

## Alternatives Considered

### Next.js
- Pros: SSR, file-system routing, full-stack
- Cons: SSR unnecessary for a PACS viewer (all content requires auth); adds complexity
- Rejected: Simple SPA with Vite is faster and sufficient

### Material UI
- Pros: Mature, comprehensive component library
- Cons: Less suited for data-dense medical interfaces; ant Design's Table, Tree, and Upload components are better fits
- Rejected: Ant Design's medical/data-centric component set is a better match

### Cornerstone.js (legacy)
- Pros: Simpler API
- Cons: Deprecated, no longer maintained, lacks 3D MPR support
- Rejected: Cornerstone3D is the active fork with ongoing development

## Consequences
- Vite provides sub-second HMR for rapid frontend development
- Ant Design v5 provides accessible, tested components for complex data tables
- Cornerstone3D enables DICOM rendering directly in the browser
- Manual chunk splitting reduces initial load time for the viewer
- TypeScript throughout catches type errors at build time
