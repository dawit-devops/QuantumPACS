import React from "react";
import { Navigate, useLocation } from "react-router";
import { useAuth } from "./AuthContext";

// Layout-route guard (A-7): wraps the protected subtree in one place instead
// of 19 per-route wrappers, and records the attempted URL so Login can
// redirect back after a successful sign-in.
export default function ProtectedRoute({
  children,
}: {
  children?: React.ReactNode;
}) {
  const { isAuthenticated } = useAuth();
  const location = useLocation();
  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }
  return <>{children}</>;
}
