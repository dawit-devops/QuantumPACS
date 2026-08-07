import React, { useState, useEffect } from "react";
import { Link, useNavigate, useLocation } from "react-router";
import { Layout, Menu, Grid, Drawer, Button, Space } from "antd";
import {
  MenuOutlined,
  FileSearchOutlined,
  UserOutlined,
  LockOutlined,
  DatabaseOutlined,
  TeamOutlined,
  AlignLeftOutlined,
  SafetyCertificateOutlined,
  BankOutlined,
  LogoutOutlined,
  DashboardOutlined,
  KeyOutlined,
  ApartmentOutlined,
  SunOutlined,
  MoonOutlined,
  MedicineBoxOutlined,
  FundOutlined,
  BookOutlined,
  MessageOutlined,
  CloudServerOutlined,
  UploadOutlined,
  SearchOutlined,
  ApiOutlined,
  CalendarOutlined,
  FileDoneOutlined,
  AuditOutlined,
  WarningOutlined,
  CheckCircleOutlined,
} from "@ant-design/icons";
import NotificationBell from "../notifications/NotificationBell";

const { useBreakpoint } = Grid;
import { useAuth } from "../auth/AuthContext";
import { useTheme } from "./ThemeProvider";
import QuantumLogo from "./QuantumLogo";
import TenantSelector from "../auth/TenantSelector";
import { logout } from "../api/auth";
import { request } from "../helpers";
import { workspaceFor } from "../navigator";
import "./Sidebar.css";

const { Sider } = Layout;

function getKey(loc: string) {
  if (loc === "/") return "files";
  const parts = loc.slice(1).split("/");
  if (parts[0] === "fhir" && parts[1]) return "fhir-" + parts[1];
  if (parts[0] === "qa") {
    const qaMap: Record<string, string> = {
      "qa-queue": "qa-queue",
      "qa-protocols": "qa-protocols",
      "qa-incidents": "qa-incidents",
      "qa-actions": "qa-actions",
    };
    if (parts[1] === "review") return "qa-queue";
    return qaMap[`qa-${parts[1]}`] || "qa-queue";
  }
  return parts[0];
}

export interface NavItemDef {
  key: string;
  path?: string;
  label: string;
  icon: React.ReactNode;
  // Item shows when ANY listed permission passes (or the user is admin via
  // hasPermission). An empty list means the item is never permission-gated —
  // reserved for the always-visible Files/Account entries and for children of
  // a gated submenu (FHIR), whose parent gate governs visibility.
  permissions: string[];
  children?: NavItemDef[];
}

export interface NavSectionDef {
  key: string;
  title: string;
  icon: React.ReactNode;
  items: NavItemDef[];
}

// Workspace section definitions. Every item permission gate is copied VERBATIM
// from the pre-workspace sidebar (REPORT_READ on Reading Worklist, QA_READ on
// each QA item, ...) so role scoping never weakens an existing gate. The one
// addition — METRICS_READ on Metrics — matches the /v2/dashboard/metrics
// endpoint guard (backend/api/dashboard_metrics.py) so the nav item no longer
// advertises a page the backend rejects; it only ever hides navigation.
export const NAV_SECTIONS: NavSectionDef[] = [
  {
    key: "reading",
    title: "Reading",
    icon: <FileDoneOutlined />,
    items: [
      {
        key: "reading",
        path: "/reading",
        label: "Reading Worklist",
        icon: <FileDoneOutlined />,
        permissions: ["REPORT_READ"],
      },
      {
        key: "peer-review",
        path: "/peer-review",
        label: "Peer Review",
        icon: <AuditOutlined />,
        permissions: ["PEER_REVIEW_READ"],
      },
    ],
  },
  {
    key: "acquisition",
    title: "Acquisition",
    icon: <MedicineBoxOutlined />,
    items: [
      {
        key: "exams",
        path: "/exams",
        label: "Exams",
        icon: <MedicineBoxOutlined />,
        permissions: ["EXAM_READ"],
      },
      {
        key: "worklist",
        path: "/worklist",
        label: "Worklist",
        icon: <FileSearchOutlined />,
        permissions: ["WORKLIST_READ"],
      },
      {
        key: "schedule-board",
        path: "/schedule-board",
        label: "Schedule",
        icon: <CalendarOutlined />,
        permissions: ["WORKLIST_READ"],
      },
    ],
  },
  {
    key: "qa",
    title: "QA",
    icon: <SafetyCertificateOutlined />,
    items: [
      {
        key: "qa-queue",
        path: "/qa/queue",
        label: "QA Queue",
        icon: <SafetyCertificateOutlined />,
        permissions: ["QA_READ"],
      },
      {
        key: "qa-protocols",
        path: "/qa/protocols",
        label: "Protocols",
        icon: <BookOutlined />,
        permissions: ["QA_READ"],
      },
      {
        key: "qa-incidents",
        path: "/qa/incidents",
        label: "Incidents",
        icon: <WarningOutlined />,
        permissions: ["QA_READ"],
      },
      {
        key: "qa-actions",
        path: "/qa/actions",
        label: "Corrective Actions",
        icon: <CheckCircleOutlined />,
        permissions: ["QA_READ"],
      },
    ],
  },
  {
    key: "admin",
    title: "Admin",
    icon: <LockOutlined />,
    items: [
      {
        key: "replicas",
        path: "/replicas",
        label: "Replicas",
        icon: <DatabaseOutlined />,
        permissions: ["REPLICA_READ"],
      },
      {
        key: "users",
        path: "/users",
        label: "Users",
        icon: <TeamOutlined />,
        permissions: ["USER_READ"],
      },
      {
        key: "tenants",
        path: "/tenants",
        label: "Tenants",
        icon: <BankOutlined />,
        permissions: ["TENANT_READ"],
      },
      {
        key: "roles",
        path: "/roles",
        label: "Roles",
        icon: <SafetyCertificateOutlined />,
        permissions: ["ROLE_READ"],
      },
      {
        key: "logs",
        path: "/logs",
        label: "Logs",
        icon: <AlignLeftOutlined />,
        permissions: ["LOG_READ", "AUDIT_READ"],
      },
      {
        key: "service-keys",
        path: "/service-keys",
        label: "Service Keys",
        icon: <KeyOutlined />,
        permissions: ["SERVICE_KEY_READ"],
      },
      {
        key: "routing",
        path: "/routing",
        label: "Routing",
        icon: <ApartmentOutlined />,
        permissions: ["ROUTING_READ", "INTERFACE_ADMIN"],
      },
      {
        // FHIR is a nested submenu; SYSTEM_ADMIN gates the whole group, and
        // its children inherit that gate (they carry no gates of their own).
        key: "fhir",
        label: "FHIR",
        icon: <MedicineBoxOutlined />,
        permissions: ["SYSTEM_ADMIN"],
        children: [
          {
            key: "fhir-config",
            path: "/fhir/config",
            label: "FHIR Config",
            icon: <MedicineBoxOutlined />,
            permissions: [],
          },
          {
            key: "fhir-monitoring",
            path: "/fhir/monitoring",
            label: "FHIR Monitoring",
            icon: <FundOutlined />,
            permissions: [],
          },
          {
            key: "fhir-docs",
            path: "/fhir/docs",
            label: "FHIR Docs",
            icon: <BookOutlined />,
            permissions: [],
          },
        ],
      },
      {
        key: "integrations",
        path: "/integrations",
        label: "Integrations",
        icon: <ApiOutlined />,
        permissions: ["SYSTEM_ADMIN"],
      },
      {
        key: "hl7",
        path: "/hl7",
        label: "HL7",
        icon: <MessageOutlined />,
        permissions: ["HL7_READ"],
      },
      {
        // DICOMweb is a submenu: the parent gate (DICOMWEB_READ etc.) covers
        // Server, Store (STOW-RS) and Study Browser — the backend re-checks
        // DICOMWEB_WRITE on the STOW endpoint itself.
        key: "dicomweb",
        label: "DICOMweb",
        icon: <CloudServerOutlined />,
        permissions: ["DICOMWEB_READ", "STORAGE_ADMIN", "INTERFACE_ADMIN"],
        children: [
          {
            key: "dicomweb-server",
            path: "/dicomweb",
            label: "Server",
            icon: <CloudServerOutlined />,
            permissions: [],
          },
          {
            key: "dicomweb-store",
            path: "/dicomweb/store",
            label: "Store (STOW-RS)",
            icon: <UploadOutlined />,
            permissions: [],
          },
          {
            key: "dicomweb-browser",
            path: "/dicomweb/browser",
            label: "Study Browser",
            icon: <SearchOutlined />,
            permissions: [],
          },
        ],
      },
    ],
  },
  {
    key: "analytics",
    title: "Metrics",
    icon: <DashboardOutlined />,
    items: [
      {
        key: "metrics",
        path: "/metrics",
        label: "Metrics",
        icon: <DashboardOutlined />,
        permissions: ["METRICS_READ"],
      },
    ],
  },
];

const SECTION_KEYS = NAV_SECTIONS.map((s) => s.key);

// Menu key → owning section. Used to auto-open the group that owns the current
// route, preserving the old "admin" open behavior and extending it to the new
// Reading/Acquisition/QA/Analytics groups.
const SECTION_OF_KEY: Record<string, string> = {
  replicas: "admin",
  users: "admin",
  roles: "admin",
  tenants: "admin",
  logs: "admin",
  "service-keys": "admin",
  routing: "admin",
  fhir: "admin",
  "fhir-config": "admin",
  "fhir-monitoring": "admin",
  "fhir-docs": "admin",
  hl7: "admin",
  dicomweb: "admin",
  "dicomweb-server": "admin",
  "dicomweb-store": "admin",
  "dicomweb-browser": "admin",
  integrations: "admin",
  worklist: "acquisition",
  exams: "acquisition",
  "schedule-board": "acquisition",
  reading: "reading",
  "peer-review": "reading",
  "qa-queue": "qa",
  "qa-protocols": "qa",
  "qa-incidents": "qa",
  "qa-actions": "qa",
  metrics: "analytics",
};

function getOpenKey(key: string): string | undefined {
  return SECTION_OF_KEY[key];
}

export function hasItemPermission(
  item: NavItemDef,
  hasPermission: (p: string) => boolean,
): boolean {
  return item.permissions.length === 0 || item.permissions.some(hasPermission);
}

function renderNavItem(item: NavItemDef, selectedKey: string) {
  const link = (child: NavItemDef) => (
    <Link to={child.path!}>
      {child.icon}
      <span className="nav-text">{child.label}</span>
    </Link>
  );
  if (item.children) {
    return (
      <Menu.SubMenu
        key={item.key}
        title={
          <span>
            {item.icon}
            <span>{item.label}</span>
          </span>
        }
      >
        {item.children.map((child) => (
          <Menu.Item
            key={child.key}
            aria-current={selectedKey === child.key ? "page" : undefined}
          >
            {link(child)}
          </Menu.Item>
        ))}
      </Menu.SubMenu>
    );
  }
  return (
    <Menu.Item
      key={item.key}
      aria-current={selectedKey === item.key ? "page" : undefined}
    >
      <Link to={item.path!}>
        {item.icon}
        <span className="nav-text">{item.label}</span>
      </Link>
    </Menu.Item>
  );
}

function Sidebar() {
  const { hasPermission, user, signOut } = useAuth();
  const { isDark, toggleTheme } = useTheme();
  const navigate = useNavigate();
  const location = useLocation();
  const screens = useBreakpoint();
  const isMobile = !screens.lg;
  const loc = location.pathname;

  const [collapsed, setCollapsed] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const key = getKey(loc);

  // workspaceFor() decides which section a role "lives in"; sections without a
  // role mapping (clinical, platform, files) fall back to pure permission-based
  // visibility, so e.g. a physician still sees Reading via REPORT_READ.
  const userWorkspace = user ? workspaceFor(user) : null;
  const workspaceOpenKey =
    userWorkspace && SECTION_KEYS.includes(userWorkspace)
      ? userWorkspace
      : null;

  const [selectedKey, setSelectedKey] = useState(key);
  const [openKey, setOpenKey] = useState(getOpenKey(key) ?? workspaceOpenKey);

  // Section visibility rule: a section shows when it owns the user's workspace
  // OR the user can see at least one item inside it. The workspace clause keeps
  // e.g. a role-only user's own section available; the item clause keeps
  // cross-scope access (radiologist granted LOG_READ still reaches Admin).
  const sections = NAV_SECTIONS.map((section) => ({
    section,
    items: section.items.filter((item) =>
      hasItemPermission(item, hasPermission),
    ),
  })).filter(
    ({ section, items }) => userWorkspace === section.key || items.length > 0,
  );

  const onCollapse = (collapsed: boolean) => {
    setCollapsed(collapsed);
  };

  const handleLogout = async () => {
    try {
      await logout();
    } catch {}
    // signOut clears the token pair plus all session keys (S1-B); the logout
    // endpoint blocks the cookies server-side before the navigation.
    signOut();
    navigate("/login");
  };

  useEffect(() => {
    const key = getKey(loc);
    setSelectedKey(key);
    // When the route belongs to a section, open that section; otherwise open
    // the user's workspace section (e.g. radiologist on Files → Reading open).
    setOpenKey(getOpenKey(key) ?? workspaceOpenKey);
  }, [loc, workspaceOpenKey]);

  const sidebarContent = (
    <div style={{ height: "100%", display: "flex", flexDirection: "column" }}>
      <div
        style={{
          padding: collapsed ? "16px 8px" : "16px 24px",
          display: "flex",
          alignItems: "center",
          justifyContent: collapsed ? "center" : "flex-start",
          borderBottom: "1px solid rgba(255,255,255,0.08)",
          marginBottom: 4,
        }}
      >
        <QuantumLogo size={32} showText={!collapsed && !isMobile} />
      </div>
      <TenantSelector />
      <Menu
        mode="inline"
        theme="dark"
        defaultOpenKeys={openKey ? [openKey] : []}
        defaultSelectedKeys={[selectedKey]}
        onClick={() => {
          if (isMobile) setDrawerOpen(false);
        }}
      >
        <Menu.Item
          key="files"
          aria-current={selectedKey === "files" ? "page" : undefined}
        >
          <Link to="/">
            <FileSearchOutlined />
            <span className="nav-text">Files</span>
          </Link>
        </Menu.Item>
        <Menu.Item
          key="account"
          aria-current={selectedKey === "account" ? "page" : undefined}
        >
          <Link to="/account">
            <UserOutlined />
            <span className="nav-text">Account</span>
          </Link>
        </Menu.Item>
        {sections.map(({ section, items }) => (
          <Menu.SubMenu
            key={section.key}
            title={
              <span>
                {section.icon}
                <span>{section.title}</span>
              </span>
            }
          >
            {items.map((item) => renderNavItem(item, selectedKey))}
          </Menu.SubMenu>
        ))}
        <Menu.Item
          key="notifications"
          style={{
            borderTop: "1px solid rgba(255,255,255,0.08)",
            marginTop: 8,
          }}
        >
          <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <NotificationBell />
            <span className="nav-text">Notifications</span>
          </span>
        </Menu.Item>
        <Menu.Item key="theme-toggle" onClick={toggleTheme}>
          <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
            {isDark ? <SunOutlined /> : <MoonOutlined />}
            <span className="nav-text">
              {isDark ? "Light Mode" : "Dark Mode"}
            </span>
          </span>
        </Menu.Item>
        <Menu.Item key="logout" onClick={handleLogout}>
          <LogoutOutlined />
          <span className="nav-text">Logout</span>
        </Menu.Item>
      </Menu>
    </div>
  );

  if (isMobile) {
    return (
      <>
        <Button
          type="text"
          icon={<MenuOutlined />}
          onClick={() => setDrawerOpen(true)}
          style={{
            position: "fixed",
            top: 8,
            left: 8,
            zIndex: 100,
            minWidth: 44,
            minHeight: 44,
            color: "var(--text-primary)",
            fontSize: 20,
          }}
          aria-label="Open navigation menu"
        />
        <Drawer
          open={drawerOpen}
          onClose={() => setDrawerOpen(false)}
          placement="left"
          width={280}
          styles={{ body: { padding: 0, background: "#001529" } }}
          title={null}
          closable={false}
        >
          {sidebarContent}
        </Drawer>
      </>
    );
  }

  return (
    <Sider
      collapsible
      collapsed={collapsed}
      onCollapse={onCollapse}
      theme="dark"
      breakpoint="lg"
      collapsedWidth="0"
      onBreakpoint={() => {}}
      role="navigation"
      aria-label="Main navigation"
    >
      {sidebarContent}
    </Sider>
  );
}

export default Sidebar;
