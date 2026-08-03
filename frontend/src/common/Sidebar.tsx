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

function getOpenKey(key: string) {
  if (
    [
      "replicas",
      "users",
      "roles",
      "tenants",
      "logs",
      "worklist",
      "exams",
      "reading",
      "peer-review",
      "qa-queue",
      "qa-protocols",
      "qa-incidents",
      "qa-actions",
      "service-keys",
      "routing",
      "fhir",
      "hl7",
      "dicomweb",
      "integrations",
    ].includes(key)
  ) {
    return "admin";
  }
  return key;
}

function hasAnyAdminPermission(
  hasPermission: (p: string) => boolean,
  userAdmin: boolean | undefined,
): boolean {
  if (userAdmin) return true;
  const adminPermissions = [
    "USER_READ",
    "REPLICA_READ",
    "TENANT_READ",
    "ROLE_READ",
    "LOG_READ",
    "SERVICE_KEY_READ",
    "WORKLIST_READ",
    "EXAM_READ",
    "REPORT_READ",
    "PEER_REVIEW_READ",
    "QA_READ",
    "HL7_READ",
    "ROUTING_READ",
    "DICOMWEB_READ",
    "SYSTEM_ADMIN",
  ];
  return adminPermissions.some((p) => hasPermission(p));
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
  const [selectedKey, setSelectedKey] = useState(key);
  const [openKey, setOpenKey] = useState(getOpenKey(key));

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
    setOpenKey(getOpenKey(key));
  }, [loc]);

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
        defaultOpenKeys={[openKey]}
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
          key="metrics"
          aria-current={selectedKey === "metrics" ? "page" : undefined}
        >
          <Link to="/metrics">
            <DashboardOutlined />
            <span className="nav-text">Metrics</span>
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
        {hasAnyAdminPermission(hasPermission, user?.admin) && (
          <Menu.SubMenu
            key="admin"
            title={
              <span>
                <LockOutlined />
                <span>Admin</span>
              </span>
            }
          >
            {hasPermission("REPLICA_READ") && (
              <Menu.Item key="replicas">
                <Link to="/replicas">
                  <DatabaseOutlined />
                  <span className="nav-text">Replicas</span>
                </Link>
              </Menu.Item>
            )}
            {hasPermission("USER_READ") && (
              <Menu.Item key="users">
                <Link to="/users">
                  <TeamOutlined />
                  <span className="nav-text">Users</span>
                </Link>
              </Menu.Item>
            )}
            {hasPermission("TENANT_READ") && (
              <Menu.Item key="tenants">
                <Link to="/tenants">
                  <BankOutlined />
                  <span className="nav-text">Tenants</span>
                </Link>
              </Menu.Item>
            )}
            {hasPermission("ROLE_READ") && (
              <Menu.Item key="roles">
                <Link to="/roles">
                  <SafetyCertificateOutlined />
                  <span className="nav-text">Roles</span>
                </Link>
              </Menu.Item>
            )}
            {hasPermission("LOG_READ") && (
              <Menu.Item key="logs">
                <Link to="/logs">
                  <AlignLeftOutlined />
                  <span className="nav-text">Logs</span>
                </Link>
              </Menu.Item>
            )}
            {hasPermission("WORKLIST_READ") && (
              <Menu.Item key="worklist">
                <Link to="/worklist">
                  <FileSearchOutlined />
                  <span className="nav-text">Worklist</span>
                </Link>
              </Menu.Item>
            )}
            {hasPermission("WORKLIST_READ") && (
              <Menu.Item key="schedule-board">
                <Link to="/schedule-board">
                  <CalendarOutlined />
                  <span className="nav-text">Schedule</span>
                </Link>
              </Menu.Item>
            )}
            {hasPermission("EXAM_READ") && (
              <Menu.Item key="exams">
                <Link to="/exams">
                  <MedicineBoxOutlined />
                  <span className="nav-text">Exams</span>
                </Link>
              </Menu.Item>
            )}
            {hasPermission("REPORT_READ") && (
              <Menu.Item key="reading">
                <Link to="/reading">
                  <FileDoneOutlined />
                  <span className="nav-text">Reading Worklist</span>
                </Link>
              </Menu.Item>
            )}
            {hasPermission("PEER_REVIEW_READ") && (
              <Menu.Item key="peer-review">
                <Link to="/peer-review">
                  <AuditOutlined />
                  <span className="nav-text">Peer Review</span>
                </Link>
              </Menu.Item>
            )}
            {hasPermission("QA_READ") && (
              <Menu.Item key="qa-queue">
                <Link to="/qa/queue">
                  <SafetyCertificateOutlined />
                  <span className="nav-text">QA Queue</span>
                </Link>
              </Menu.Item>
            )}
            {hasPermission("QA_READ") && (
              <Menu.Item key="qa-protocols">
                <Link to="/qa/protocols">
                  <BookOutlined />
                  <span className="nav-text">Protocols</span>
                </Link>
              </Menu.Item>
            )}
            {hasPermission("QA_READ") && (
              <Menu.Item key="qa-incidents">
                <Link to="/qa/incidents">
                  <WarningOutlined />
                  <span className="nav-text">Incidents</span>
                </Link>
              </Menu.Item>
            )}
            {hasPermission("QA_READ") && (
              <Menu.Item key="qa-actions">
                <Link to="/qa/actions">
                  <CheckCircleOutlined />
                  <span className="nav-text">Corrective Actions</span>
                </Link>
              </Menu.Item>
            )}
            {hasPermission("SERVICE_KEY_READ") && (
              <Menu.Item key="service-keys">
                <Link to="/service-keys">
                  <KeyOutlined />
                  <span className="nav-text">Service Keys</span>
                </Link>
              </Menu.Item>
            )}
            {hasPermission("ROUTING_READ") && (
              <Menu.Item key="routing">
                <Link to="/routing">
                  <ApartmentOutlined />
                  <span className="nav-text">Routing</span>
                </Link>
              </Menu.Item>
            )}
            {hasPermission("SYSTEM_ADMIN") && (
              <Menu.SubMenu
                key="fhir"
                title={
                  <span>
                    <MedicineBoxOutlined />
                    <span>FHIR</span>
                  </span>
                }
              >
                <Menu.Item key="fhir-config">
                  <Link to="/fhir/config">
                    <MedicineBoxOutlined />
                    <span className="nav-text">FHIR Config</span>
                  </Link>
                </Menu.Item>
                <Menu.Item key="fhir-monitoring">
                  <Link to="/fhir/monitoring">
                    <FundOutlined />
                    <span className="nav-text">FHIR Monitoring</span>
                  </Link>
                </Menu.Item>
                <Menu.Item key="fhir-docs">
                  <Link to="/fhir/docs">
                    <BookOutlined />
                    <span className="nav-text">FHIR Docs</span>
                  </Link>
                </Menu.Item>
              </Menu.SubMenu>
            )}
            {hasPermission("HL7_READ") && (
              <Menu.Item key="hl7">
                <Link to="/hl7">
                  <MessageOutlined />
                  <span className="nav-text">HL7</span>
                </Link>
              </Menu.Item>
            )}
            {hasPermission("DICOMWEB_READ") && (
              <Menu.Item key="dicomweb">
                <Link to="/dicomweb">
                  <CloudServerOutlined />
                  <span className="nav-text">DICOMweb</span>
                </Link>
              </Menu.Item>
            )}
            {hasPermission("SYSTEM_ADMIN") && (
              <Menu.Item key="integrations">
                <Link to="/integrations">
                  <ApiOutlined />
                  <span className="nav-text">Integrations</span>
                </Link>
              </Menu.Item>
            )}
          </Menu.SubMenu>
        )}
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
