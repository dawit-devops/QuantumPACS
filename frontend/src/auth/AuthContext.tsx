import React, { createContext, useContext, useState, useCallback, useMemo } from 'react';

export interface AuthUser {
  id: string;
  username: string;
  admin: boolean;
  role: string;
  tenant_id?: string;
}

export interface AuthContextType {
  isAuthenticated: boolean;
  user: AuthUser | null;
  signIn: (token: string, user: AuthUser) => void;
  signOut: () => void;
  hasPermission: (permission: string) => boolean;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(() => {
    const id = localStorage.getItem('userId');
    const token = localStorage.getItem('token');
    if (!id || !token) return null;
    return {
      id,
      username: localStorage.getItem('username') || '',
      admin: localStorage.getItem('admin') === 'true',
      role: localStorage.getItem('role') || (localStorage.getItem('admin') === 'true' ? 'admin' : 'user'),
      tenant_id: localStorage.getItem('tenant_id') || undefined,
    };
  });

  const isAuthenticated = user !== null && !!localStorage.getItem('token');

  const hasPermission = useCallback(
    (permission: string) => isAuthenticated && (user?.admin || user?.role === permission),
    [isAuthenticated, user],
  );

  const signIn = useCallback((token: string, userData: AuthUser) => {
    localStorage.setItem('token', token);
    localStorage.setItem('userId', userData.id);
    localStorage.setItem('username', userData.username);
    localStorage.setItem('admin', String(userData.admin));
    localStorage.setItem('role', userData.role);
    if (userData.tenant_id) {
      localStorage.setItem('tenant_id', userData.tenant_id);
    }
    setUser(userData);
  }, []);

  const signOut = useCallback(() => {
    localStorage.removeItem('token');
    localStorage.removeItem('userId');
    localStorage.removeItem('username');
    localStorage.removeItem('admin');
    localStorage.removeItem('role');
    localStorage.removeItem('tenant_id');
    setUser(null);
  }, []);

  const value = useMemo(
    () => ({ isAuthenticated, user, signIn, signOut, hasPermission }),
    [isAuthenticated, user, signIn, signOut, hasPermission],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextType {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within an AuthProvider');
  return ctx;
}
