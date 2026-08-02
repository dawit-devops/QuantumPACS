import React from "react";
import { Navigate } from "react-router";
import { useAuth } from "./AuthContext";

/**
 * Route-level permission gate.
 *
 * Closes the deep-link gap: routes were previously gated only on authentication
 * (ProtectedRoute), so a user without e.g. USER_READ could still navigate
 * directly to /users even though the sidebar hid the item. PermissionRoute
 * enforces the same permission at the URL boundary:
 *
 *   - unauthenticated      -> redirect to /login
 *   - authenticated but no permission -> redirect to / (Files, always visible)
 *   - authenticated + permission      -> render children
 *
 * Matches the sidebar gating matrix in common/Sidebar.tsx.
 */
export default function PermissionRoute({
  permission,
  children,
}: {
  permission: string;
  children: React.ReactNode;
}) {
  const { isAuthenticated, hasPermission } = useAuth();
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  if (!hasPermission(permission)) return <Navigate to="/" replace />;
  return <>{children}</>;
}
