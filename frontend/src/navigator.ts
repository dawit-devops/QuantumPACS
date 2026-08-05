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
  | "files"
  | "platform";

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
  {
    route: "/dicomweb",
    workspace: "clinical",
    permissions: ["DICOMWEB_READ"],
  },
  {
    route: "/metrics",
    workspace: "analytics",
    permissions: ["METRICS_READ", "ANALYTICS_READ"],
  },
  { route: "/users", workspace: "platform", permissions: ["USER_READ"] },
  { route: "/", workspace: "files", permissions: ["FILE_READ", "STUDY_READ"] },
];

/**
 * Canonical role slug -> workspace. PACS personas only (persona catalog
 * PAC-P01..P20 / RBAC spec §4); RIS, EMR and unknown roles fall through to
 * the generic `files` workspace below.
 */
const ROLE_WORKSPACE: Record<string, Workspace> = {
  radiologist: "reading",
  teleradiologist: "reading",
  resident: "reading",
  technologist: "acquisition",
  qa_team: "qa",
  pacs_admin: "admin",
  radiology_admin: "admin",
  imaging_informatics: "admin",
  department_manager: "analytics",
  physician: "clinical",
  referring_physician: "clinical",
  ed_physician: "clinical",
  patient: "files",
  super_admin: "platform",
  tenant_admin: "platform",
  admin: "platform",
};

// Mirrors AuthContext.hasPermission: the admin flag bypasses every gate.
function hasAnyPermission(user: WorkspaceUser, permissions: string[]): boolean {
  if (user.admin) return true;
  return permissions.some((p) => user.permissions.includes(p));
}

export function landingRouteFor(user: WorkspaceUser): string {
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
    LANDING_STEPS.find((s) => hasAnyPermission(user, s.permissions))?.route ??
    "/account"
  );
}

export function workspaceFor(user: WorkspaceUser): Workspace {
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
    LANDING_STEPS.find(
      (s) => hasAnyPermission(user, s.permissions) && s.workspace,
    )?.workspace ?? "files"
  );
}
