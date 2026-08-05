import React, {
  createContext,
  useContext,
  useState,
  useCallback,
  useMemo,
} from "react";
import {
  setTokens,
  clearTokens,
  startRefreshTimer,
  stopRefreshTimer,
} from "../helpers";
import { navigate } from "../navigator";

export interface AuthUser {
  id: string;
  username: string;
  admin: boolean;
  role: string;
  permissions: string[];
  tenant_id?: string;
}

export interface Tenant {
  id: string;
  name: string;
  slug: string;
}

export interface AuthContextType {
  isAuthenticated: boolean;
  user: AuthUser | null;
  signIn: (token: string, user: AuthUser, refreshToken?: string) => void;
  signOut: () => void;
  hasPermission: (permission: string) => boolean;
  activeTenant: Tenant | null;
  setActiveTenant: (tenant: Tenant | null) => void;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [activeTenant, setActiveTenant] = useState<Tenant | null>(() => {
    const slug = localStorage.getItem("tenant_id");
    if (!slug) return null;
    return {
      id: slug,
      name: localStorage.getItem("tenant_name") || slug,
      slug,
    };
  });
  const [user, setUser] = useState<AuthUser | null>(() => {
    const id = localStorage.getItem("userId");
    if (!id) return null;
    let permissions: string[] = [];
    try {
      const raw = localStorage.getItem("permissions");
      if (raw) permissions = JSON.parse(raw);
    } catch {}
    return {
      id,
      username: localStorage.getItem("username") || "",
      admin: localStorage.getItem("admin") === "true",
      role:
        localStorage.getItem("role") ||
        (localStorage.getItem("admin") === "true" ? "admin" : "user"),
      permissions,
      tenant_id: localStorage.getItem("tenant_id") || undefined,
    };
  });

  const isAuthenticated = user !== null;

  const signOut = useCallback(() => {
    stopRefreshTimer();
    // Single source of truth for session teardown (A-6): every key written
    // during sign-in must be cleared here so logout leaves no stale identity.
    // Keys written elsewhere (theme, tour flag) are UI prefs, not identity.
    localStorage.removeItem("userId");
    localStorage.removeItem("username");
    localStorage.removeItem("admin");
    localStorage.removeItem("role");
    localStorage.removeItem("permissions");
    localStorage.removeItem("tenant_id");
    localStorage.removeItem("tenant_name");
    localStorage.removeItem("tempKey");
    sessionStorage.removeItem("tempKey");
    sessionStorage.removeItem("shareKeyError");
    clearTokens();
    setUser(null);
    setActiveTenant(null);
  }, []);

  const hasPermission = useCallback(
    (permission: string) =>
      isAuthenticated &&
      (user?.admin || user?.permissions?.includes(permission)),
    [isAuthenticated, user],
  );

  const signIn = useCallback(
    (token: string, userData: AuthUser, refreshToken?: string) => {
      localStorage.setItem("userId", userData.id);
      localStorage.setItem("username", userData.username);
      localStorage.setItem("admin", String(userData.admin));
      localStorage.setItem("role", userData.role);
      localStorage.setItem("permissions", JSON.stringify(userData.permissions));
      if (userData.tenant_id) {
        localStorage.setItem("tenant_id", userData.tenant_id);
      }
      setTokens(token, refreshToken || token);
      setUser(userData);
      startRefreshTimer(() => {
        signOut();
        navigate("/login");
      });
    },
    [signOut],
  );

  const value = useMemo(
    () => ({
      isAuthenticated,
      user,
      signIn,
      signOut,
      hasPermission,
      activeTenant,
      setActiveTenant,
    }),
    [
      isAuthenticated,
      user,
      signIn,
      signOut,
      hasPermission,
      activeTenant,
      setActiveTenant,
    ],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextType {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
}
