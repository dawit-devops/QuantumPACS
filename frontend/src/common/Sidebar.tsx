import React, { useState, useEffect } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { Layout, Menu } from 'antd';
import { FileSearchOutlined, UserOutlined, LockOutlined, DatabaseOutlined, TeamOutlined, AlignLeftOutlined, LogoutOutlined } from '@ant-design/icons';
import { useFetch } from '../hooks';
import { isAdmin } from '../helpers';
import { PAGINATION } from '../config';
import './Sidebar.css';

const { Sider } = Layout;

function getKey(loc: string) {
  return loc === '/' ? 'files' : loc.slice(1).split('/')[0];
}

function getOpenKey(key: string) {
  if (['replicas', 'users', 'logs'].includes(key)) {
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

  const { exec } = useFetch('logout', { method: 'POST' });

  const handleLogout = async (e: React.MouseEvent) => {
    e.preventDefault();
    await exec();
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
      onBreakpoint={broke => {
        if (broke) {
          PAGINATION.limit = 5;
        }
      }}
    >
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
