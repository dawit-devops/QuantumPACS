import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Badge, Drawer, Menu } from 'antd';
import { FileSearchOutlined, DashboardOutlined, UserOutlined, LockOutlined, DatabaseOutlined, TeamOutlined, AlignLeftOutlined, SafetyCertificateOutlined, BankOutlined, KeyOutlined, ApartmentOutlined, PlusOutlined } from '@ant-design/icons';
import { useAuth } from '../auth/AuthContext';
import './MobileNav.css';

const navItems = [
  { path: '/', label: 'Files', icon: <FileSearchOutlined />, badge: undefined as number | undefined },
  { path: '/metrics', label: 'Metrics', icon: <DashboardOutlined />, badge: undefined },
  { path: '/account', label: 'Account', icon: <UserOutlined />, badge: undefined },
];

const adminItems = [
  { path: '/worklist', label: 'Worklist', icon: <PlusOutlined />, permission: 'WORKLIST_READ' },
  { path: '/replicas', label: 'Replicas', icon: <DatabaseOutlined />, permission: 'REPLICA_READ' },
  { path: '/users', label: 'Users', icon: <TeamOutlined />, permission: 'USER_READ' },
  { path: '/tenants', label: 'Tenants', icon: <BankOutlined />, permission: 'TENANT_READ' },
  { path: '/roles', label: 'Roles', icon: <SafetyCertificateOutlined />, permission: 'ROLE_READ' },
  { path: '/logs', label: 'Logs', icon: <AlignLeftOutlined />, permission: 'LOG_READ' },
  { path: '/service-keys', label: 'Keys', icon: <KeyOutlined />, permission: 'SERVICE_KEY_READ' },
  { path: '/routing', label: 'Routing', icon: <ApartmentOutlined />, permission: 'ROUTING_READ' },
];

export default function MobileNav() {
  const location = useLocation();
  const currentPath = location.pathname;
  const { hasPermission, user } = useAuth();
  const [adminOpen, setAdminOpen] = useState(false);

  const hasAdminAccess = user?.admin || adminItems.some((item) => hasPermission(item.permission));

  const isActive = (path: string) => path === '/'
    ? currentPath === '/' || currentPath.startsWith('/files') || currentPath.startsWith('/detail') || currentPath.startsWith('/patients')
    : currentPath.startsWith(path);

  return (
    <>
      <nav className="mobile-nav" aria-label="Bottom navigation">
        {navItems.map((item) => {
          const active = isActive(item.path);
          return (
            <Link
              key={item.path}
              to={item.path}
              className={`mobile-nav-item ${active ? 'active' : ''}`}
              aria-current={active ? 'page' : undefined}
            >
              {item.badge !== undefined ? (
                <Badge count={item.badge} size="small">
                  {item.icon}
                </Badge>
              ) : item.icon}
              <span className="mobile-nav-label">{item.label}</span>
            </Link>
          );
        })}
        {hasAdminAccess && (
          <button
            className={`mobile-nav-item ${adminOpen ? 'active' : ''}`}
            onClick={() => setAdminOpen(true)}
            aria-label="Admin menu"
            style={{ background: 'none', border: 'none', cursor: 'pointer', fontFamily: 'inherit' }}
          >
            <LockOutlined />
            <span className="mobile-nav-label">Admin</span>
          </button>
        )}
      </nav>
      <Drawer
        open={adminOpen}
        onClose={() => setAdminOpen(false)}
        placement="bottom"
        height="auto"
        title="Admin"
        styles={{ body: { padding: 0 } }}
      >
        <Menu
          mode="inline"
          onClick={() => setAdminOpen(false)}
          items={adminItems
            .filter((item) => hasAdminAccess || hasPermission(item.permission))
            .map((item) => ({
              key: item.path,
              icon: item.icon,
              label: <Link to={item.path} onClick={() => setAdminOpen(false)}>{item.label}</Link>,
            }))}
        />
      </Drawer>
    </>
  );
}
