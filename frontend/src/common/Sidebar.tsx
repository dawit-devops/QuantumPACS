import {
  MenuOutlined,
  FileSearchOutlined,
  AccountBookOutlined,
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
  HomeOutlined,
  WarningOutlined,
  AlertOutlined,
  CheckCircleOutlined,
  IdcardOutlined,
  SolutionOutlined,
  SettingOutlined,
  ScheduleOutlined,
} from "@ant-design/icons";
import { Layout, Menu, Grid, Drawer, Button } from "antd";
import React, { useState, useEffect } from "react";
import { Link, useNavigate, useLocation } from "react-router";

const { useBreakpoint } = Grid;

import QuantumLogo from "./QuantumLogo";
import { useTheme } from "./ThemeProvider";
import { logout } from "../api/auth";
import { useAuth } from "../auth/AuthContext";
import { VIEWER_ROUTE_PERMISSIONS } from "../auth/PermissionRoute";
import TenantSelector from "../auth/TenantSelector";
import { request } from "../helpers";
import {
  ADMIN_DASHBOARD_PERMISSIONS,
  workspaceFor,
  isAdminScopedRole,
  NON_ADMIN_WORKSPACES,
} from "../navigator";
import NotificationBell from "../notifications/NotificationBell";

import type { MenuProps } from "antd";

import "./Sidebar.css";

const { Sider } = Layout;

function getKey(loc: string) {
  if (loc === "/") return "files";
  const parts = loc.slice(1).split("/");
  if (parts[0] === "admin") {
    // /admin is the dashboard; /admin/{maintenance|backups|settings} are the
    // platform-ops surfaces (super_admin review).
    if (parts[1] === "maintenance") return "maintenance";
    if (parts[1] === "backups") return "backups";
    if (parts[1] === "settings") return "settings";
    return "dashboard";
  }
  if (parts[0] === "fhir" && parts[1]) return "fhir-" + parts[1];
  if (parts[0] === "reading") return parts[1] === "home" ? "resident-home" : "reading-worklist";
  if (parts[0] === "critical") return "critical-results";
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
  if (parts[0] === "schedule")
    return parts[1] === "resources" ? "schedule-resources" : "schedule-calendar";
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
  // Role allowlist: when present, the item only shows for these exact role
  // slugs (e.g. the R13 resident's educational home), regardless of grants.
  // Pure permission gating can't express role identity — every clinical role
  // holds REPORT_READ, so a resident-only surface needs the role check.
  roles?: string[];
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
        // R13 resident educational home — resident-only role surface. The
        // resident lands here (navigator.ts landingRouteFor), not the shared
        // staff worklist.
        key: "resident-home",
        path: "/reading/home",
        label: "Resident Home",
        icon: <HomeOutlined />,
        permissions: ["REPORT_READ"],
        roles: ["resident"],
      },
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
      {
        // CR-6: critical-results monitoring surface (S10). GET
        // /api/notifications/critical is REPORT_READ-gated, matching the
        // route gate; flagging inside the console needs REPORT_WRITE.
        key: "critical-results",
        path: "/critical",
        label: "Critical Results",
        icon: <AlertOutlined />,
        permissions: ["REPORT_READ"],
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
        // C10: "Exams" → "My Exams" so it reads as the technologist's own
        // R06 assignment list, distinct from the DICOM modality worklist.
        label: "My Exams",
        icon: <MedicineBoxOutlined />,
        permissions: ["EXAM_READ"],
      },
      {
        key: "worklist",
        path: "/worklist",
        // C10: "Worklist" → "Modality Worklist" (the DICOM worklist), so the
        // two Acquisition entries are distinguishable at a glance.
        label: "Modality Worklist",
        icon: <FileSearchOutlined />,
        permissions: ["WORKLIST_READ"],
      },
      {
        key: "tracking",
        path: "/tracking",
        label: "Tracking Board",
        icon: <DashboardOutlined />,
        // S6-13: live tracking board for all exams — uses worklist_entries
        // + exams tables, gated on WORKLIST_READ like the MWL.
        permissions: ["WORKLIST_READ"],
      },
      {
        key: "schedule-board",
        path: "/schedule-board",
        label: "Schedule",
        icon: <CalendarOutlined />,
        // The board loads day data from GET /api/worklist (WORKLIST_READ)
        // and supports capacity booking (SCHEDULE_READ). Accept either
        // permission so both physicians (WORKLIST_READ) and schedulers
        // (SCHEDULE_READ) see the nav item — matches the route gate.
        permissions: ["WORKLIST_READ", "SCHEDULE_READ"],
      },
      {
        key: "schedule-calendar",
        path: "/schedule",
        label: "Calendar",
        icon: <CalendarOutlined />,
        // S4-14/16 day view: RIS-native schedule over resources (rooms/
        // modalities/techs). Loads GET /ris/resources + /ris/appointments,
        // both SCHEDULE_READ-gated, so the sidebar gate matches the page.
        permissions: ["SCHEDULE_READ"],
      },
      {
        key: "schedule-resources",
        path: "/schedule/resources",
        label: "Resources",
        icon: <ApartmentOutlined />,
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
    // Care-coordinator review (P0-2): the coordination workspace. Orders is
    // the read-only ORDER_READ surface that gives the role a real home; the
    // section auto-opens for care_coordinator (workspaceFor) and appears for
    // any other ORDER_READ holder (physician).
    key: "coordination",
    title: "Coordination",
    icon: <ScheduleOutlined />,
    items: [
      {
        key: "orders",
        path: "/orders",
        label: "Orders",
        icon: <ScheduleOutlined />,
        permissions: ["ORDER_READ"],
      },
      {
        // R2-01: prior-authorization management. PRIOR_AUTH_READ matches the
        // route gate; payer-team roles and schedulers both carry it.
        key: "prior-auth",
        path: "/prior-auth",
        label: "Prior Auth",
        icon: <SafetyCertificateOutlined />,
        permissions: ["PRIOR_AUTH_READ"],
      },
    ],
  },
  {
    // S11: billing capture — coder confirms CPT suggestions, drops the
    // charge, and monitors unbilled aging. Both surfaces gate on BILLING_READ.
    key: "billing",
    title: "Billing",
    icon: <AccountBookOutlined />,
    items: [
      {
        key: "billing-queue",
        path: "/billing/queue",
        label: "Billing Queue",
        icon: <AccountBookOutlined />,
        permissions: ["BILLING_READ"],
      },
      {
        key: "billing-unbilled",
        path: "/billing/unbilled",
        label: "Unbilled Aging",
        icon: <FundOutlined />,
        permissions: ["BILLING_READ"],
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
        // S12-35: department-manager dashboard — TAT, utilization, unbilled
        // aging, volume. REPORT_READ matches the route gate; adminOnly keeps
        // the Admin section from leaking to clinical roles (radiologist etc.)
        // who have REPORT_READ but are not admin-scoped.
        key: "ris-dashboard",
        path: "/admin/ris-dashboard",
        label: "RIS Dashboard",
        icon: <FundOutlined />,
        permissions: ["REPORT_READ"],
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
        // Interface health (RIS-UI-37): the S3-16 dashboard under /admin.
        // Admin-scoped like dicomweb — clinical roles holding legacy
        // HL7_READ keep the /hl7 console, the /admin surface is ops-only.
        key: "interfaces",
        path: "/admin/interfaces",
        label: "Interface Health",
        icon: <ApiOutlined />,
        permissions: ["HL7_READ"],
        adminOnly: true,
      },
      {
        // Platform-ops surfaces (super_admin review): only the platform
        // admin holds SYSTEM_ADMIN, so these items are super_admin-only.
        key: "maintenance",
        path: "/admin/maintenance",
        label: "Maintenance",
        icon: <WarningOutlined />,
        permissions: ["SYSTEM_ADMIN"],
      },
      {
        key: "backups",
        path: "/admin/backups",
        label: "Backups",
        icon: <DatabaseOutlined />,
        permissions: ["SYSTEM_ADMIN"],
      },
      {
        key: "settings",
        path: "/admin/settings",
        label: "Settings",
        icon: <SettingOutlined />,
        permissions: ["SYSTEM_ADMIN"],
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
  maintenance: "admin",
  backups: "admin",
  settings: "admin",
  dicomweb: "admin",
  "dicomweb-server": "admin",
  "dicomweb-store": "admin",
  "dicomweb-browser": "admin",
  integrations: "admin",
  worklist: "acquisition",
  tracking: "acquisition",
  exams: "acquisition",
  "schedule-board": "acquisition",
  "schedule-calendar": "acquisition",
  "schedule-resources": "acquisition",
  "reading-worklist": "reading",
  "resident-home": "reading",
  "peer-review": "reading",
  orders: "coordination",
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
  role?: string
): boolean {
  if (item.adminOnly && !isAdminScoped) return false;
  if (item.roles && !item.roles.includes(role ?? "")) return false;
  return item.permissions.length === 0 || item.permissions.some(hasPermission);
}

function navItemToItem(
  item: NavItemDef,
  selectedKey: string
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
      hasItemPermission(item, hasPermission, isAdminScoped, user?.role)
    ),
  }))
    .filter(({ section, items }) => userWorkspace === section.key || items.length > 0)
    .filter(({ section }) => !isAdminScoped || !NON_ADMIN_WORKSPACES.has(section.key));

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
        items={[
          hasItemPermission(
            {
              key: "files",
              path: "/",
              label: "Files",
              icon: <FileSearchOutlined />,
              permissions: [...VIEWER_ROUTE_PERMISSIONS],
            },
            hasPermission,
            isAdminScoped
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
            // P2-6: the unread badge's text must not join the menu item's
            // accessible name ("49Notifications"). The count is already
            // aria-hidden inside NotificationBell; this span (pure text,
            // never focusable) is hidden so the bell button's own
            // aria-label "Notifications" is the menuitem's sole name —
            // wrapping the focusable button in aria-hidden would trip
            // axe's aria-hidden-focus rule.
            label: (
              <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <NotificationBell />
                <span className="nav-text" aria-hidden="true">
                  Notifications
                </span>
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
                <span className="nav-text">{isDark ? "Light Mode" : "Dark Mode"}</span>
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
        ].filter(Boolean)}
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
