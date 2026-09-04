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
const QaOverview = React.lazy(() => import("./QaOverview"));
const OrdersPipeline = React.lazy(() => import("./OrdersPipeline"));
const BillingUnbilled = React.lazy(() => import("./BillingUnbilled"));
const FrontDeskWaiting = React.lazy(() => import("./FrontDeskWaiting"));

export const WIDGETS: WidgetDef[] = [
  {
    id: "platform-totals",
    title: "Platform totals",
    defaultSize: "md",
    permissions: ["METRICS_READ"],
    component: PlatformTotals,
  },
  {
    id: "qa-overview",
    title: "QA overview",
    defaultSize: "md",
    permissions: ["QA_READ"],
    component: QaOverview,
  },
  {
    id: "orders-pipeline",
    title: "Order pipeline",
    defaultSize: "md",
    permissions: ["ORDER_READ"],
    component: OrdersPipeline,
  },
  {
    id: "billing-unbilled",
    title: "Unbilled charges",
    defaultSize: "md",
    permissions: ["BILLING_READ"],
    component: BillingUnbilled,
  },
  {
    id: "frontdesk-waiting",
    title: "Waiting room",
    defaultSize: "sm",
    permissions: ["QUEUE_READ"],
    component: FrontDeskWaiting,
  },
];

export const WIDGET_BY_ID = new Map(WIDGETS.map((w) => [w.id, w]));

/**
 * Role default layouts (§3.2). Roles without an entry fall back to
 * DEFAULT_LAYOUT_IDS; widgets the role lacks grants for are filtered at
 * render time by the grid.
 */
export const ROLE_DEFAULT_LAYOUTS: Record<string, string[]> = {
  receptionist: ["frontdesk-waiting"],
  care_coordinator: ["orders-pipeline"],
  cashier: ["billing-unbilled"],
  dept_manager: ["qa-overview", "orders-pipeline", "billing-unbilled"],
};

export const DEFAULT_LAYOUT_IDS = ["platform-totals"];
