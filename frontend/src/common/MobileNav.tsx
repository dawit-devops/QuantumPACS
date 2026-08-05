import React, { useState } from "react";
import { Link, useLocation } from "react-router";
import { Badge, Drawer, Menu } from "antd";
import {
  FileSearchOutlined,
  UserOutlined,
  MenuOutlined,
} from "@ant-design/icons";
import { useAuth } from "../auth/AuthContext";
import { workspaceFor } from "../navigator";
import { NAV_SECTIONS, hasItemPermission, type NavItemDef } from "./Sidebar";
import "./MobileNav.css";

const navItems = [
  {
    path: "/",
    label: "Files",
    icon: <FileSearchOutlined />,
    badge: undefined as number | undefined,
  },
  {
    path: "/account",
    label: "Account",
    icon: <UserOutlined />,
    badge: undefined,
  },
];

export default function MobileNav() {
  const location = useLocation();
  const currentPath = location.pathname;
  const { hasPermission, user } = useAuth();
  const [drawerOpen, setDrawerOpen] = useState(false);

  // Same section visibility rule as the desktop sidebar: the user's own
  // workspace section always shows, plus any section with a visible item.
  const userWorkspace = user ? workspaceFor(user) : null;
  const sections = NAV_SECTIONS.map((section) => ({
    section,
    items: section.items.filter((item) =>
      hasItemPermission(item, hasPermission),
    ),
  })).filter(
    ({ section, items }) => userWorkspace === section.key || items.length > 0,
  );

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
        {navItems.map((item) => {
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
        height="auto"
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
