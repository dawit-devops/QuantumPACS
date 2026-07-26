import React, { useState, useEffect } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { Layout, Menu } from 'antd';
import { FileSearchOutlined, UserOutlined, LockOutlined, DatabaseOutlined, TeamOutlined, AlignLeftOutlined, SafetyCertificateOutlined, LogoutOutlined } from '@ant-design/icons';
import { isAdmin } from '../helpers';
import QuantumLogo from './QuantumLogo';
import TenantSelector from '../auth/TenantSelector';
import './Sidebar.css';

const { Sider } = Layout;

function getKey(loc: string) {
  return loc === '/' ? 'files' : loc.slice(1).split('/')[0];
}

function getOpenKey(key: string) {
  if (['replicas', 'users', 'roles', 'logs'].includes(key)) {
    return 'admin';
  }
  return key;
}

function Sidebar() {
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
    localStorage.removeItem('userId');
    localStorage.removeItem('admin');
    localStorage.removeItem('token');
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

        <Menu.Item key="account">
          <Link to="/account">
            <UserOutlined />
            <span className="nav-text">Account</span>
          </Link>
        </Menu.Item>
        {
          isAdmin() &&
          <Menu.SubMenu key="admin"
            title={
              <span>
                <LockOutlined />
                <span>Admin</span>
              </span>
            }>
            <Menu.Item key="replicas">
              <Link to="/replicas">
                <DatabaseOutlined />
                <span className="nav-text">Replicas</span>
              </Link>
            </Menu.Item>
            <Menu.Item key="users">
              <Link to="/users">
                <TeamOutlined />
                <span className="nav-text">Users</span>
              </Link>
            </Menu.Item>
            <Menu.Item key="roles">
              <Link to="/roles">
                <SafetyCertificateOutlined />
                <span className="nav-text">Roles</span>
              </Link>
            </Menu.Item>
            <Menu.Item key="logs">
              <Link to="/logs">
                <AlignLeftOutlined />
                <span className="nav-text">Logs</span>
              </Link>
            </Menu.Item>
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
