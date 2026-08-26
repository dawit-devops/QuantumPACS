import React from "react";

// §3.1 widget registry: every persona's dashboard composes from this list.
// Widgets are self-contained (own fetching + states) and lazy-loaded so
// the dashboard adds no eager bundle weight.

export type WidgetSize = "sm" | "md" | "lg";

export interface WidgetDef {
  id: string;
  title: string;
  defaultSize: WidgetSize;
  /** All-of grants required to see the widget; omitted = all users. */
  permissions?: string[];
  component: React.LazyExoticComponent<React.ComponentType>;
}

const PlatformTotals = React.lazy(() => import("./PlatformTotals"));

export const WIDGETS: WidgetDef[] = [
  {
    id: "platform-totals",
    title: "Platform totals",
    defaultSize: "md",
    permissions: ["METRICS_READ"],
    component: PlatformTotals,
  },
];

export const WIDGET_BY_ID = new Map(WIDGETS.map((w) => [w.id, w]));

/**
 * Role default layouts (§3.2). Roles without an entry fall back to
 * DEFAULT_LAYOUT_IDS; widgets the role lacks grants for are filtered at
 * render time by the grid.
 */
export const ROLE_DEFAULT_LAYOUTS: Record<string, string[]> = {};

export const DEFAULT_LAYOUT_IDS = ["platform-totals"];
