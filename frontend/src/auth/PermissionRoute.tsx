import React from "react";
import { Navigate } from "react-router";
import { useAuth } from "./AuthContext";
import { landingRouteFor } from "../navigator";

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

export default function PermissionRoute({
  permission,
  children,
}: {
  permission: string | string[];
  children: React.ReactNode;
}) {
  const { isAuthenticated, hasPermission, user } = useAuth();
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  const required = Array.isArray(permission) ? permission : [permission];
  const allowed = required.some((p) => hasPermission(p));
  if (!allowed) {
    // Hardcoding "/" here would loop: the Files route is itself permission-
    // gated, so a user without study/file perms would bounce forever.
    // landingRouteFor picks the highest-priority route this user can open.
    return (
      <Navigate to={landingRouteFor(user ?? { permissions: [] })} replace />
    );
  }
  return <>{children}</>;
}
