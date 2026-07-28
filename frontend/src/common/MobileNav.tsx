import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { FileSearchOutlined, DashboardOutlined, UserOutlined } from '@ant-design/icons';
import './MobileNav.css';

const navItems = [
  { path: '/', label: 'Files', icon: <FileSearchOutlined /> },
  { path: '/metrics', label: 'Metrics', icon: <DashboardOutlined /> },
  { path: '/account', label: 'Account', icon: <UserOutlined /> },
];

export default function MobileNav() {
  const location = useLocation();
  const currentPath = location.pathname;

  return (
    <nav className="mobile-nav">
      {navItems.map((item) => {
        const isActive = item.path === '/'
          ? currentPath === '/' || currentPath.startsWith('/files') || currentPath.startsWith('/detail') || currentPath.startsWith('/patients')
          : currentPath.startsWith(item.path);
        return (
          <Link
            key={item.path}
            to={item.path}
            className={`mobile-nav-item ${isActive ? 'active' : ''}`}
          >
            {item.icon}
            <span className="mobile-nav-label">{item.label}</span>
          </Link>
        );
      })}
    </nav>
  );
}
