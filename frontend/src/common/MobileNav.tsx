import {
  FileSearchOutlined,
  UserOutlined,
  MenuOutlined,
  SolutionOutlined,
} from "@ant-design/icons";
import { Badge, Drawer, Menu } from "antd";
import React, { useState } from "react";
import { Link, useLocation } from "react-router";

import { useAuth } from "../auth/AuthContext";
import { workspaceFor, isAdminScopedRole, NON_ADMIN_WORKSPACES } from "../navigator";
import { NAV_SECTIONS, hasItemPermission, type NavItemDef } from "./Sidebar";
import "./MobileNav.css";

interface MobileNavItem {
  path: string;
  label: string;
  icon: React.ReactNode;
  badge?: number;
  permission?: string;
}

const navItems: MobileNavItem[] = [
  {
    path: "/",
    label: "Files",
    icon: <FileSearchOutlined />,
  },
  {
    // Own-data patient portal: only rendered for PORTAL_READ holders (the
    // patient role); everyone else keeps a two-item bar (Files, Account).
    path: "/portal",
    label: "My Records",
    icon: <SolutionOutlined />,
    permission: "PORTAL_READ",
  },
  {
    path: "/account",
    label: "Account",
    icon: <UserOutlined />,
  },
];

export default function MobileNav() {
  const location = useLocation();
  const currentPath = location.pathname;
  const { hasPermission, user } = useAuth();
  const [drawerOpen, setDrawerOpen] = useState(false);

  // Same section visibility rule as the desktop sidebar: the user's own
  // workspace section always shows, plus any section with a visible item.
  // Admin-scoped roles never see the clinical sections (see Sidebar).
  const userWorkspace = user ? workspaceFor(user) : null;
  const isAdminScoped = isAdminScopedRole(user?.role);
  const sections = NAV_SECTIONS.map((section) => ({
    section,
    items: section.items.filter((item) => hasItemPermission(item, hasPermission, isAdminScoped)),
  }))
    .filter(({ section, items }) => userWorkspace === section.key || items.length > 0)
    .filter(({ section }) => !isAdminScoped || !NON_ADMIN_WORKSPACES.has(section.key));

  const isActive = (path: string) =>
    path === "/"
      ? currentPath === "/" ||
        currentPath.startsWith("/files") ||
        currentPath.startsWith("/detail") ||
        currentPath.startsWith("/patients")
      : currentPath.startsWith(path);

  const closeDrawer = () => setDrawerOpen(false);

  // Leaf drawer entries are Links so the drawer closes on navigation; submenu
  // headers (e.g. FHIR inside Admin) stay plain titles like on desktop.
  const toMenuNode = (item: NavItemDef) =>
    item.children
      ? { key: item.key, icon: item.icon, label: item.label }
      : {
          key: item.key,
          icon: item.icon,
          label: (
            <Link to={item.path!} onClick={closeDrawer}>
              {item.label}
            </Link>
          ),
        };

  return (
    <>
      <nav className="mobile-nav" aria-label="Bottom navigation">
        {navItems
          .filter(
            (item) =>
              !item.permission ||
              // R4-01: admin-scoped roles never see the patient portal in
              // the bar — /portal is closed to them (ClinicalRoute), so the
              // item would be a dead link, mirroring the sidebar's
              // NON_ADMIN_WORKSPACES filter.
              (!isAdminScoped && hasPermission(item.permission))
          )
          .map((item) => {
            const active = isActive(item.path);
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`mobile-nav-item ${active ? "active" : ""}`}
                aria-current={active ? "page" : undefined}
              >
                {item.badge !== undefined ? (
                  <Badge count={item.badge} size="small">
                    {item.icon}
                  </Badge>
                ) : (
                  item.icon
                )}
                <span className="mobile-nav-label">{item.label}</span>
              </Link>
            );
          })}
        {sections.length > 0 && (
          <button
            className={`mobile-nav-item ${drawerOpen ? "active" : ""}`}
            onClick={() => setDrawerOpen(true)}
            aria-label="Menu"
            style={{
              background: "none",
              border: "none",
              cursor: "pointer",
              fontFamily: "inherit",
            }}
          >
            <MenuOutlined />
            <span className="mobile-nav-label">Menu</span>
          </button>
        )}
      </nav>
      <Drawer
        open={drawerOpen}
        onClose={closeDrawer}
        placement="bottom"
        size="auto"
        title="Menu"
        styles={{ body: { padding: 0 } }}
      >
        <Menu
          mode="inline"
          onClick={closeDrawer}
          items={sections.map(({ section, items }) => ({
            key: section.key,
            icon: section.icon,
            label: section.title,
            children: items.map((item) => ({
              ...toMenuNode(item),
              children: item.children?.map((child) => toMenuNode(child)),
            })),
          }))}
        />
      </Drawer>
    </>
  );
}
