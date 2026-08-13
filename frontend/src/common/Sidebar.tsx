import React, { useState, useEffect } from "react";
import { Link, useNavigate, useLocation } from "react-router";
import { Layout, Menu, Grid, Drawer, Button, Space } from "antd";
import type { MenuProps } from "antd";
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
  IdcardOutlined,
  SolutionOutlined,
} from "@ant-design/icons";
import NotificationBell from "../notifications/NotificationBell";

const { useBreakpoint } = Grid;
import { useAuth } from "../auth/AuthContext";
import { useTheme } from "./ThemeProvider";
import QuantumLogo from "./QuantumLogo";
import TenantSelector from "../auth/TenantSelector";
import { logout } from "../api/auth";
import { request } from "../helpers";
import {
  ADMIN_DASHBOARD_PERMISSIONS,
  workspaceFor,
  isAdminScopedRole,
  NON_ADMIN_WORKSPACES,
} from "../navigator";
import { VIEWER_ROUTE_PERMISSIONS } from "../auth/PermissionRoute";
import "./Sidebar.css";

const { Sider } = Layout;

function getKey(loc: string) {
  if (loc === "/") return "files";
  const parts = loc.slice(1).split("/");
  if (parts[0] === "admin") return "dashboard";
  if (parts[0] === "fhir" && parts[1]) return "fhir-" + parts[1];
  if (parts[0] === "reading") return "reading-worklist";
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
  if (parts[0] === "frontdesk") {
    const fdMap: Record<string, string> = {
      registration: "fd-registration",
      visits: "fd-visits",
      queue: "fd-queue",
    };
    return fdMap[parts[1]] || "fd-registration";
  }
  if (parts[0] === "portal") return "portal-records";
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
  // Role-scope gate: the item only shows for admin-scoped roles (the
  // dashboard's operational home), mirroring the route's adminOnly guard.
  adminOnly?: boolean;
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
// each QA item, ...) so role scoping never weakens an existing gate. Gates that
// drifted from the route/backend guards were re-aligned to the guard sets:
// Metrics accepts METRICS_READ|ANALYTICS_READ (route + backend alias), Routing
// is ROUTING_READ only, DICOMweb is DICOMWEB_READ only — a nav item must never
// advertise a page the backend rejects; it only ever hides navigation.
export const NAV_SECTIONS: NavSectionDef[] = [
  {
    key: "reading",
    title: "Reading",
    icon: <FileDoneOutlined />,
    items: [
      {
        // Distinct from the section key: antd Menu rejects duplicate keys
        // (warns "Duplicated key 'reading' used in Menu by path [reading]"
        // and breaks item selection/open-state tracking).
        key: "reading-worklist",
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
        // Schedule surface (R08): SCHEDULE_READ matches the route gate; the
        // board's write actions (book/cancel) need SCHEDULE_WRITE inside.
        permissions: ["SCHEDULE_READ"],
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
        // The dashboard is the landing home of every admin-scoped role; it
        // sits at the top of the Admin section and is role-scoped (adminOnly)
        // so a clinical role granted one of its permissions never sees it.
        key: "dashboard",
        path: "/admin",
        label: "Dashboard",
        icon: <DashboardOutlined />,
        permissions: [...ADMIN_DASHBOARD_PERMISSIONS],
        adminOnly: true,
      },
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
        // Matches the /api/routing backend guard (ROUTING_READ/ROUTING_WRITE).
        // INTERFACE_ADMIN was dropped from the gate: tenant_admin and
        // emr_admin hold it but the route and backend both reject them.
        permissions: ["ROUTING_READ"],
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
        // DICOMweb is a submenu: the parent gate (DICOMWEB_READ) covers
        // Server, Store (STOW-RS) and Study Browser — the backend re-checks
        // DICOMWEB_WRITE on the STOW endpoint itself. STORAGE_ADMIN and
        // INTERFACE_ADMIN were dropped from the gate: tenant_admin and
        // pacs_admin hold them but the route and the
        // /api/dicomweb* backend guards all require DICOMWEB_READ.
        // adminOnly: the console is admin-scoped; clinical roles (radiologist,
        // physician) carry legacy DICOMWEB_READ but must not see it — the
        // same scope the AdminConsoleRoute and navigator.ts apply.
        key: "dicomweb",
        label: "DICOMweb",
        icon: <CloudServerOutlined />,
        permissions: ["DICOMWEB_READ"],
        adminOnly: true,
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
    key: "frontdesk",
    title: "Front Desk",
    icon: <IdcardOutlined />,
    items: [
      {
        key: "fd-registration",
        path: "/frontdesk/registration",
        label: "Registration",
        icon: <IdcardOutlined />,
        permissions: ["REGISTRATION_READ"],
      },
      {
        key: "fd-visits",
        path: "/frontdesk/visits",
        label: "Visits & Check-In",
        icon: <MedicineBoxOutlined />,
        permissions: ["REGISTRATION_READ"],
      },
      {
        key: "fd-queue",
        path: "/frontdesk/queue",
        label: "Waiting Queue",
        icon: <TeamOutlined />,
        permissions: ["QUEUE_READ"],
      },
    ],
  },
  {
    key: "portal",
    title: "My Records",
    icon: <SolutionOutlined />,
    items: [
      {
        key: "portal-records",
        path: "/portal",
        label: "My Records",
        icon: <SolutionOutlined />,
        // Own-data patient portal (R19): scope-gated server-side via
        // patient_staff_scope, never a navigation target for non-holders.
        permissions: ["PORTAL_READ"],
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
        // METRICS_READ or ANALYTICS_READ — mirrors the /metrics route gate
        // (METRICS_ROUTE_PERMISSIONS) and the backend alias resolution
        // (ANALYTICS_READ ⇄ METRICS_READ) so a custom role holding only
        // ANALYTICS_READ gets the nav item its landing route promises.
        permissions: ["METRICS_READ", "ANALYTICS_READ"],
      },
    ],
  },
];

const SECTION_KEYS = NAV_SECTIONS.map((s) => s.key);

// Menu key → owning section. Used to auto-open the group that owns the current
// route, preserving the old "admin" open behavior and extending it to the new
// Reading/Acquisition/QA/Analytics groups.
const SECTION_OF_KEY: Record<string, string> = {
  dashboard: "admin",
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
  "reading-worklist": "reading",
  "peer-review": "reading",
  "qa-queue": "qa",
  "qa-protocols": "qa",
  "qa-incidents": "qa",
  "qa-actions": "qa",
  "fd-registration": "frontdesk",
  "fd-visits": "frontdesk",
  "fd-queue": "frontdesk",
  "portal-records": "portal",
  metrics: "analytics",
};

function getOpenKey(key: string): string | undefined {
  return SECTION_OF_KEY[key];
}

export function hasItemPermission(
  item: NavItemDef,
  hasPermission: (p: string) => boolean,
  isAdminScoped = false,
): boolean {
  if (item.adminOnly && !isAdminScoped) return false;
  return item.permissions.length === 0 || item.permissions.some(hasPermission);
}

function navItemToItem(
  item: NavItemDef,
  selectedKey: string,
): NonNullable<MenuProps["items"]>[number] {
  const link = (child: NavItemDef) => (
    <Link to={child.path!}>
      {child.icon}
      <span className="nav-text">{child.label}</span>
    </Link>
  );
  if (item.children) {
    return {
      key: item.key,
      icon: item.icon,
      label: item.label,
      children: item.children.map((child) => navItemToItem(child, selectedKey)),
    };
  }
  return {
    key: item.key,
    label: link(item),
  };
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

  // workspaceFor() decides which section a role "lives in"; sections without a
  // role mapping (clinical, platform, files) fall back to pure permission-based
  // visibility, so e.g. a physician still sees Reading via REPORT_READ.
  // Admin-scoped roles resolve to the "dashboard" workspace, which has no nav
  // section of its own — the dashboard lives at the top of the Admin section,
  // so auto-open that section for them.
  const userWorkspace = user ? workspaceFor(user) : null;
  const workspaceOpenKey =
    userWorkspace === "dashboard"
      ? "admin"
      : userWorkspace && SECTION_KEYS.includes(userWorkspace)
        ? userWorkspace
        : null;

  // Navigation state derives from the location during render (R1-01/R1-23):
  // defaultSelectedKeys/defaultOpenKeys are read only on first mount and
  // froze the highlight at the landing route for the whole session. The
  // controlled props below stay in sync on every navigation; manual section
  // collapse is honored via onOpenChange, and the route re-opens the owning
  // section on navigation (manual overrides are cleared then).
  const selectedKey = getKey(loc);
  const routeOpenKey = getOpenKey(selectedKey) ?? workspaceOpenKey;
  const [manualOpenKeys, setManualOpenKeys] = useState<string[] | null>(null);
  useEffect(() => {
    setManualOpenKeys(null);
  }, [selectedKey]);
  const openKeys = manualOpenKeys ?? (routeOpenKey ? [routeOpenKey] : []);

  // Section visibility rule: a section shows when it owns the user's workspace
  // OR the user can see at least one item inside it. The workspace clause keeps
  // e.g. a role-only user's own section available; the item clause keeps
  // cross-scope access (radiologist granted LOG_READ still reaches Admin).
  // Admin-scoped roles (admin, super_admin, tenant_admin, pacs_admin, ...)
  // manage the platform rather than perform clinical work, so the clinical
  // sections (Reading / Acquisition / QA) are always hidden for them — even
  // when their grants would pass — mirroring navigator.ts landing rules.
  const isAdminScoped = isAdminScopedRole(user?.role);
  const sections = NAV_SECTIONS.map((section) => ({
    section,
    items: section.items.filter((item) =>
      hasItemPermission(item, hasPermission, isAdminScoped),
    ),
  }))
    .filter(
      ({ section, items }) => userWorkspace === section.key || items.length > 0,
    )
    .filter(
      ({ section }) => !isAdminScoped || !NON_ADMIN_WORKSPACES.has(section.key),
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
        openKeys={openKeys}
        selectedKeys={[selectedKey]}
        onOpenChange={(keys) => setManualOpenKeys(keys)}
        onClick={() => {
          if (isMobile) setDrawerOpen(false);
        }}
        items={
          [
            hasItemPermission(
              {
                key: "files",
                path: "/",
                label: "Files",
                icon: <FileSearchOutlined />,
                permissions: [...VIEWER_ROUTE_PERMISSIONS],
              },
              hasPermission,
              isAdminScoped,
            )
              ? {
                  key: "files",
                  label: (
                    <Link to="/">
                      <FileSearchOutlined />
                      <span className="nav-text">Files</span>
                    </Link>
                  ),
                }
              : null,
            {
              key: "account",
              label: (
                <Link to="/account">
                  <UserOutlined />
                  <span className="nav-text">Account</span>
                </Link>
              ),
            },
            ...sections.map(({ section, items }) => ({
              key: section.key,
              icon: section.icon,
              label: section.title,
              children: items.map((item) => navItemToItem(item, selectedKey)),
            })),
            {
              key: "notifications",
              label: (
                <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <NotificationBell />
                  <span className="nav-text">Notifications</span>
                </span>
              ),
              style: {
                borderTop: "1px solid rgba(255,255,255,0.08)",
                marginTop: 8,
              },
            },
            {
              key: "theme-toggle",
              onClick: toggleTheme,
              label: (
                <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  {isDark ? <SunOutlined /> : <MoonOutlined />}
                  <span className="nav-text">
                    {isDark ? "Light Mode" : "Dark Mode"}
                  </span>
                </span>
              ),
            },
            {
              key: "logout",
              onClick: handleLogout,
              label: (
                <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <LogoutOutlined />
                  <span className="nav-text">Logout</span>
                </span>
              ),
            },
          ].filter(Boolean) as MenuProps["items"]
        }
      />
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
          size={280}
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
