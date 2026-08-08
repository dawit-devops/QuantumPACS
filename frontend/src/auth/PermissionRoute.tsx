import React from "react";
import { Navigate } from "react-router";
import { useAuth } from "./AuthContext";
import {
  ADMIN_DASHBOARD_PERMISSIONS,
  landingRouteFor,
  isAdminScopedRole,
} from "../navigator";

/**
 * Route-level permission gate.
 *
 * Closes the deep-link gap: routes were previously gated only on authentication
 * (ProtectedRoute), so a user without e.g. USER_READ could still navigate
 * directly to /users even though the sidebar hid the item. PermissionRoute
 * enforces the same permission at the URL boundary:
 *
 *   - unauthenticated      -> redirect to /login
 *   - authenticated but no permission -> redirect to landingRouteFor(user),
 *     the best route the user is actually allowed to open
 *   - authenticated + permission      -> render children
 *
 * `permission` may be a single key or a list; a list passes when the user has
 * ANY of the keys (admin bypasses, matching AuthContext.hasPermission).
 *
 * `excludedRoles` optionally closes a route to specific role slugs even when
 * the permission passes — used for clinical surfaces, which admin-scoped
 * roles never work despite holding the underlying grants.
 *
 * The gate sets for the PACS workspace routes live here so index.tsx (the
 * route table) and the route-gates tests share one source of truth.
 */
export const VIEWER_ROUTE_PERMISSIONS: string[] = [
  "FILE_READ",
  "STUDY_READ",
  "VIEWER_READ",
];

export const PATIENT_ROUTE_PERMISSIONS: string[] = ["PATIENT_READ"];

export const METRICS_ROUTE_PERMISSIONS: string[] = [
  "METRICS_READ",
  "ANALYTICS_READ",
];

// Defined in navigator.ts (avoids a navigator <-> PermissionRoute import
// cycle); re-exported here so index.tsx and the route-gates tests can import
// both gate sets from the same module.
export { ADMIN_DASHBOARD_PERMISSIONS };

export default function PermissionRoute({
  permission,
  excludedRoles,
  adminOnly,
  children,
}: {
  permission: string | readonly string[];
  excludedRoles?: string[];
  adminOnly?: boolean;
  children: React.ReactNode;
}) {
  const { isAuthenticated, hasPermission, user } = useAuth();
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  const required = Array.isArray(permission) ? permission : [permission];
  const allowed = required.some((p) => hasPermission(p));
  const roleExcluded =
    user !== null &&
    excludedRoles !== undefined &&
    excludedRoles.includes(user.role);
  // adminOnly is the landing complement: a user with dashboard permissions but
  // a clinical role (granted LOG_READ for instance) must not open the admin
  // console — only admin-scoped roles run the platform.
  const notAdmin = adminOnly === true && !isAdminScopedRole(user?.role);
  if (!allowed || roleExcluded || notAdmin) {
    // Hardcoding "/" here would loop: the Files route is itself permission-
    // gated, so a user without study/file perms would bounce forever.
    // landingRouteFor picks the highest-priority route this user can open.
    return (
      <Navigate to={landingRouteFor(user ?? { permissions: [] })} replace />
    );
  }
  return <>{children}</>;
}
