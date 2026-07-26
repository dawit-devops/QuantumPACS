import React from 'react';
import { Select, Typography } from 'antd';
import { useAuth } from './AuthContext';

const { Text } = Typography;

export default function TenantSelector() {
  const { isAuthenticated, activeTenant } = useAuth();
  if (!isAuthenticated || !activeTenant) return null;

  return (
    <div style={{ padding: '8px 16px', borderBottom: '1px solid rgba(255,255,255,0.08)' }}>
      <Text type="secondary" style={{ fontSize: 11, display: 'block', marginBottom: 4, color: 'rgba(255,255,255,0.45)' }}>
        Tenant
      </Text>
      <Text style={{ color: '#fff', fontSize: 13 }}>{activeTenant.name}</Text>
    </div>
  );
}
