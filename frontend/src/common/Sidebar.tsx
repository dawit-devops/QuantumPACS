import React, { useState, useEffect } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { Layout, Menu } from 'antd';
import { FileSearchOutlined, UserOutlined, LockOutlined, DatabaseOutlined, TeamOutlined, AlignLeftOutlined, SafetyCertificateOutlined, BankOutlined, LogoutOutlined, DashboardOutlined } from '@ant-design/icons';
import { useAuth } from '../auth/AuthContext';
import QuantumLogo from './QuantumLogo';
import TenantSelector from '../auth/TenantSelector';
import { request } from '../helpers';
import './Sidebar.css';

const { Sider } = Layout;

function getKey(loc: string) {
  return loc === '/' ? 'files' : loc.slice(1).split('/')[0];
}

function getOpenKey(key: string) {
  if (['replicas', 'users', 'roles', 'tenants', 'logs'].includes(key)) {
    return 'admin';
  }
  return key;
}

type PermissionCheck = { permission: string } | { adminOnly: true };

function hasAnyAdminPermission(hasPermission: (p: string) => boolean, userAdmin: boolean | undefined): boolean {
  if (userAdmin) return true;
  const adminPermissions = ['USER_READ', 'REPLICA_READ', 'TENANT_READ', 'ROLE_READ', 'LOG_READ', 'SERVICE_KEY_READ'];
  return adminPermissions.some(p => hasPermission(p));
}

function Sidebar() {
  const { hasPermission, user } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const loc = location.pathname;

  let [collapsed, setCollapsed] = useState(false);
  const key = getKey(loc);
  let [selectedKey, setSelectedKey] = useState(key);
  let [openKey, setOpenKey] = useState(getOpenKey(key));

  const onCollapse = (collapsed: boolean) => {
    setCollapsed(collapsed);
  };

  const handleLogout = async (e: React.MouseEvent) => {
    e.preventDefault();
    try {
      await request('auth/logout', { method: 'POST' });
    } catch {
    }
    localStorage.removeItem('userId');
    localStorage.removeItem('admin');
    navigate('/login');
  };

  useEffect(() => {
    const key = getKey(loc);
    setSelectedKey(key);
    setOpenKey(getOpenKey(key));
  }, [loc]);

  return (
    <Sider collapsible collapsed={collapsed} onCollapse={onCollapse} theme="dark"
      breakpoint="lg"
      collapsedWidth="0"
      onBreakpoint={() => {}}
    >
      <div style={{
        padding: collapsed ? '16px 8px' : '16px 24px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: collapsed ? 'center' : 'flex-start',
        borderBottom: '1px solid rgba(255,255,255,0.08)',
        marginBottom: 4,
      }}>
        <QuantumLogo size={32} showText={!collapsed} />
      </div>
      <TenantSelector />
      <Menu mode="inline" theme="dark"
        defaultOpenKeys={[openKey]} defaultSelectedKeys={[selectedKey]} >

        <Menu.Item key="files">
          <Link to="/">
            <FileSearchOutlined />
            <span className="nav-text">Files</span>
          </Link>
        </Menu.Item>

        <Menu.Item key="metrics">
          <Link to="/metrics">
            <DashboardOutlined />
            <span className="nav-text">Metrics</span>
          </Link>
        </Menu.Item>

        <Menu.Item key="account">
          <Link to="/account">
            <UserOutlined />
            <span className="nav-text">Account</span>
          </Link>
        </Menu.Item>
        {
          hasAnyAdminPermission(hasPermission, user?.admin) &&
          <Menu.SubMenu key="admin"
            title={
              <span>
                <LockOutlined />
                <span>Admin</span>
              </span>
            }>
            {hasPermission('REPLICA_READ') && (
              <Menu.Item key="replicas">
                <Link to="/replicas">
                  <DatabaseOutlined />
                  <span className="nav-text">Replicas</span>
                </Link>
              </Menu.Item>
            )}
            {hasPermission('USER_READ') && (
              <Menu.Item key="users">
                <Link to="/users">
                  <TeamOutlined />
                  <span className="nav-text">Users</span>
                </Link>
              </Menu.Item>
            )}
            {hasPermission('TENANT_READ') && (
              <Menu.Item key="tenants">
                <Link to="/tenants">
                  <BankOutlined />
                  <span className="nav-text">Tenants</span>
                </Link>
              </Menu.Item>
            )}
            {hasPermission('ROLE_READ') && (
              <Menu.Item key="roles">
                <Link to="/roles">
                  <SafetyCertificateOutlined />
                  <span className="nav-text">Roles</span>
                </Link>
              </Menu.Item>
            )}
            {hasPermission('LOG_READ') && (
              <Menu.Item key="logs">
                <Link to="/logs">
                  <AlignLeftOutlined />
                  <span className="nav-text">Logs</span>
                </Link>
              </Menu.Item>
            )}
          </Menu.SubMenu>
        }
        <Menu.Item key="logout">
          <Link to="/logout" onClick={handleLogout}>
            <LogoutOutlined />
            <span className="nav-text">Logout</span>
          </Link>
        </Menu.Item>
      </Menu>
    </Sider>
  );
}

export default Sidebar;
