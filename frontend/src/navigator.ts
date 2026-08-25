import { NavigateFunction } from "react-router";

let _navigate: NavigateFunction | null = null;

export const setNavigator = (n: NavigateFunction) => {
  _navigate = n;
};

export const navigate = (to: string) => _navigate?.(to);

// ---------------------------------------------------------------------------
// Role -> workspace landing contract (PACS surfaces).
//
// A role's label describes the surface the user *should* work on, but the
// effective grant lives in `permissions` plus the legacy `admin` flag, which
// bypasses every gate exactly like AuthContext.hasPermission. Labels and
// grants can drift (custom role configs, legacy built-in accounts, partially
// provisioned users), and landing a user on a route they cannot open is a
// dead end. So both resolvers walk a fixed priority order — most specialized
// clinical surface first, most generic last — and return the first surface
// the user is actually permitted to reach. `/account` is the guaranteed
// terminal (auth-only), so every authenticated user lands somewhere usable;
// it is the fallback landing of the default `files` workspace, which is why
// a user with no accessible PACS surface still resolves to `files`.
// ---------------------------------------------------------------------------

export type Workspace =
  | "reading"
  | "acquisition"
  | "qa"
  | "admin"
  | "analytics"
  | "clinical"
  | "coordination"
  | "frontdesk"
  | "billing"
  | "portal"
  | "files"
  | "platform"
  | "dashboard";

/**
 * Roles scoped to the admin/platform workspaces. These roles operate the
 * system (users, roles, tenants, storage, interfaces) rather than perform
 * clinical work, so clinical surfaces — the Reading, Acquisition and QA
 * workspaces — are hidden for them even when their permission set still
 * contains the underlying grants (e.g. REPORT_READ on `pacs_admin`).
 */
export const ADMIN_SCOPED_ROLES: ReadonlyArray<string> = [
  "super_admin",
  "tenant_admin",
  "pacs_admin",
  "emr_admin",
  "dept_manager",
];

/**
 * Roles scoped to the clinical workspaces. These roles perform clinical work
 * (imaging, reading, EMR care) rather than operate the system, so the admin
 * console surfaces — the DICOMweb server/STOW/browser routes — are hidden for
 * them even when their legacy permission set still contains the underlying
 * grants (e.g. DICOMWEB_READ on `radiologist` and `physician`).
 */
export const CLINICAL_SCOPED_ROLES: ReadonlyArray<string> = [
  "radiologist",
  "teleradiologist",
  "resident",
  "technologist",
  "physician",
  "referring_physician",
  "care_coordinator",
];

/** Workspaces whose surfaces are clinical (queues, exams, QA review). */
export const CLINICAL_WORKSPACES: ReadonlySet<string> = new Set([
  "reading",
  "acquisition",
  "qa",
]);

/**
 * Workspaces whose surfaces belong to non-admin staff / patient roles —
 * clinical queues plus the R08 front-desk and R19 patient portal. Admin-scoped
 * roles are excluded from all of them even when their grants pass: super_admin
 * holds every permission, so REGISTRATION_READ / PORTAL_READ alone must not
 * surface the Front Desk or My Records menu items or landing steps.
 */
export const NON_ADMIN_WORKSPACES: ReadonlySet<string> = new Set([
  ...CLINICAL_WORKSPACES,
  "coordination",
  "frontdesk",
  "portal",
]);

export function isAdminScopedRole(role?: string): boolean {
  return role !== undefined && ADMIN_SCOPED_ROLES.includes(role);
}

export function isClinicalScopedRole(role?: string): boolean {
  return role !== undefined && CLINICAL_SCOPED_ROLES.includes(role);
}

/**
 * Gate for the admin dashboard route (kept here, not in PermissionRoute, to
 * avoid a navigator <-> PermissionRoute import cycle; PermissionRoute imports
 * it from navigator). No single permission is granted to every admin-scoped
 * role (super_admin, tenant_admin, pacs_admin, emr_admin), so the gate is the
 * union of the read permissions each role carries. Each listed key maps to a
 * section the dashboard surfaces; sections still render individually-gated
 * and degrade gracefully when a role lacks some.
 */
export const ADMIN_DASHBOARD_PERMISSIONS: ReadonlyArray<string> = [
  "USER_READ",
  "LOG_READ",
  "AUDIT_READ",
  "INTERFACE_MONITOR",
  "METRICS_READ",
  "REPLICA_READ",
  "DICOMWEB_READ",
];

export interface WorkspaceUser {
  role?: string;
  admin?: boolean;
  permissions: string[];
}

/**
 * Workspace -> landing route -> permission gate. Array order IS the fallback
 * priority: each step is checked in turn and the first one the user can pass
 * wins (admin bypasses every gate).
 */
interface LandingStep {
  route: string;
  workspace: Workspace;
  permissions: string[];
}

const LANDING_STEPS: LandingStep[] = [
  { route: "/reading", workspace: "reading", permissions: ["REPORT_READ"] },
  { route: "/exams", workspace: "acquisition", permissions: ["EXAM_READ"] },
  { route: "/qa/queue", workspace: "qa", permissions: ["QA_READ"] },
  { route: "/replicas", workspace: "admin", permissions: ["REPLICA_READ"] },
  // Front Desk (R08): registration is the front-office home for the
  // receptionist role; the privacy queue is reachable from there.
  // QUEUE_READ unlocks the queue step for roles that hold it without
  // REGISTRATION_READ.
  {
    route: "/frontdesk/registration",
    workspace: "frontdesk",
    permissions: ["REGISTRATION_READ"],
  },
  {
    route: "/frontdesk/queue",
    workspace: "frontdesk",
    permissions: ["QUEUE_READ"],
  },
  {
    route: "/frontdesk/schedule",
    workspace: "frontdesk",
    permissions: ["SCHEDULE_READ"],
  },
  // Patient portal (R19): the patient role lands on its own scope-gated
  // records, never on the admin/clinical surfaces.
  { route: "/portal", workspace: "portal", permissions: ["PORTAL_READ"] },
  // Care-coordinator review (P1-2): the coordination workspace lands on the
  // Orders page (ORDER_READ), not the radiologist's worklist. Positioned
  // before the clinical step so the primary lookup is unambiguous.
  {
    route: "/orders",
    workspace: "coordination",
    permissions: ["ORDER_READ"],
  },
  // Billing (§2.6): the coder/cashier persona lands on the billing queue —
  // previously unmapped, falling through to /account.
  {
    route: "/billing/queue",
    workspace: "billing",
    permissions: ["BILLING_READ"],
  },
  // The clinical workspace (physician, referring_physician) lands on the
  // reading worklist: reports are the shared clinical read surface for both
  // (REPORT_READ on Matrix A/B).
  {
    route: "/reading",
    workspace: "clinical",
    permissions: ["REPORT_READ"],
  },
  {
    // The DICOMweb console is an admin surface: it must never be a clinical
    // landing (physician previously landed here via legacy DICOMWEB_READ),
    // and non-admin roles never reach it via fallback (landingStepsFor).
    route: "/dicomweb",
    workspace: "admin",
    permissions: ["DICOMWEB_READ"],
  },
  {
    route: "/metrics",
    workspace: "analytics",
    permissions: ["METRICS_READ", "ANALYTICS_READ"],
  },
  { route: "/users", workspace: "platform", permissions: ["USER_READ"] },
  {
    route: "/logs",
    workspace: "admin",
    // AUDIT_READ is the canonical alias of LOG_READ (spec §6): the Matrix A
    // admin roles hold only AUDIT_READ, and the /logs route gate + backend
    // accept both, so a logs landing step must too.
    permissions: ["LOG_READ", "AUDIT_READ"],
  },
  { route: "/", workspace: "files", permissions: ["FILE_READ", "STUDY_READ"] },
];

// The dashboard is NOT part of LANDING_STEPS: it sits above every other step
// for admin-scoped roles, but if a non-admin role (granted USER_READ for
// example) ever resolved here the PermissionRoute adminOnly guard would bounce
// them straight back to landingRouteFor — a redirect loop. It is consulted
// explicitly only for admin-scoped roles below.
const DASHBOARD_STEP: LandingStep = {
  route: "/admin",
  workspace: "dashboard",
  permissions: [...ADMIN_DASHBOARD_PERMISSIONS],
};

/**
 * Canonical role slug -> workspace. PACS/EMR personas only (persona catalog
 * PAC-P01..P20 / RBAC spec §4); RIS, EMR support and unknown roles fall
 * through to the generic `files` workspace below.
 */
const ROLE_WORKSPACE: Record<string, Workspace> = {
  radiologist: "reading",
  teleradiologist: "reading",
  resident: "reading",
  technologist: "acquisition",
  pacs_admin: "admin",
  emr_admin: "admin",
  physician: "clinical",
  referring_physician: "clinical",
  // Care-coordinator review (P1-2): the coordinator's own workspace is the
  // coordination surface (Orders), not the shared clinical reading worklist.
  care_coordinator: "coordination",
  receptionist: "frontdesk",
  // §2.6: the cashier/biller persona's workspace is the billing queue.
  cashier: "billing",
  patient: "portal",
  super_admin: "platform",
  tenant_admin: "platform",
  dept_manager: "dashboard",
};

// Mirrors AuthContext.hasPermission: the admin flag bypasses every gate.
function hasAnyPermission(user: WorkspaceUser, permissions: string[]): boolean {
  if (user.admin) return true;
  return permissions.some((p) => user.permissions.includes(p));
}

/**
 * Fallback priority steps for landing/workspace resolution. The scan is
 * role-scope-aware and bidirectional: admin-scoped roles never land on (or
 * resolve to) clinical workspaces, clinical roles never land on admin-console
 * workspaces — even when their legacy grants would pass (e.g. DICOMWEB_READ
 * on physician) — and unmapped roles (cashier, facility custom slugs) scan
 * the full priority chain and land on the first surface their grants open.
 */
function landingStepsFor(user: WorkspaceUser): LandingStep[] {
  if (isAdminScopedRole(user.role)) {
    return LANDING_STEPS.filter(
      (s) =>
        !NON_ADMIN_WORKSPACES.has(s.workspace) && s.workspace !== "clinical",
    );
  }
  if (isClinicalScopedRole(user.role)) {
    return LANDING_STEPS.filter((s) => s.workspace !== "admin");
  }
  return LANDING_STEPS;
}

export function landingRouteFor(user: WorkspaceUser): string {
  // Admin-scoped roles land on the dashboard first: it is their operational
  // home, ahead of any single admin surface their role mapping grants
  // (platform -> /users, admin -> /replicas).
  if (
    isAdminScopedRole(user.role) &&
    hasAnyPermission(user, DASHBOARD_STEP.permissions)
  ) {
    return DASHBOARD_STEP.route;
  }
  // R13 radiology resident: land on the Resident Home instead of the shared
  // staff reading worklist. The resident workspace stays "reading" so the
  // sidebar highlights the Reading section, but the home is the educational
  // surface (queue counts, feedback, teaching library). Only routes to it
  // when REPORT_READ passes, else falls through to the generic chain.
  if (user.role === "resident" && hasAnyPermission(user, ["REPORT_READ"])) {
    return "/reading/home";
  }
  const roleWorkspace = ROLE_WORKSPACE[user.role ?? ""];
  if (roleWorkspace) {
    const primary = LANDING_STEPS.find((s) => s.workspace === roleWorkspace);
    if (primary && hasAnyPermission(user, primary.permissions)) {
      return primary.route;
    }
  }
  // Role surface blocked (or unmapped): take the first permitted route in
  // priority order, degrading to the auth-only `/account` terminal.
  return (
    landingStepsFor(user).find((s) => hasAnyPermission(user, s.permissions))
      ?.route ?? "/account"
  );
}

export function workspaceFor(user: WorkspaceUser): Workspace {
  // Mirrors landingRouteFor: admin-scoped roles with dashboard access resolve
  // to the dashboard workspace (the sidebar maps it onto the Admin section).
  if (
    isAdminScopedRole(user.role) &&
    hasAnyPermission(user, DASHBOARD_STEP.permissions)
  ) {
    return DASHBOARD_STEP.workspace;
  }
  const roleWorkspace = ROLE_WORKSPACE[user.role ?? ""];
  if (roleWorkspace) {
    const primary = LANDING_STEPS.find((s) => s.workspace === roleWorkspace);
    if (primary && hasAnyPermission(user, primary.permissions)) {
      return roleWorkspace;
    }
  }
  // First permitted workspace in priority order; `files` is the default
  // because its landing chain degrades to the always-allowed `/account`.
  return (
    landingStepsFor(user).find(
      (s) => hasAnyPermission(user, s.permissions) && s.workspace,
    )?.workspace ?? "files"
  );
}
