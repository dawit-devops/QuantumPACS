import React from 'react';
import { useAuth } from './AuthContext';

export default function RequirePermission({ permission, children }: { permission: string; children: React.ReactNode }) {
  const { hasPermission } = useAuth();
  if (!hasPermission(permission)) return null;
  return <>{children}</>;
}
