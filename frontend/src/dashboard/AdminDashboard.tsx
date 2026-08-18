import { useDocumentTitle, useTenantRefetch } from "../hooks";
import React, {
  useState,
  useEffect,
  useCallback,
  useRef,
  useMemo,
} from "react";
import { useNavigate } from "react-router";
import {
  App,
  Layout,
  Table,
  Tag,
  Switch,
  Typography,
  Button,
  Spin,
  Space,
} from "antd";
import {
  TeamOutlined,
  FolderOutlined,
  ExperimentOutlined,
  FileOutlined,
  HddOutlined,
  ReloadOutlined,
  DatabaseOutlined,
  CloudServerOutlined,
  FundOutlined,
  FileSearchOutlined,
  SafetyCertificateOutlined,
  BankOutlined,
  ApartmentOutlined,
  DashboardOutlined,
} from "@ant-design/icons";
import { Bar, Line } from "react-chartjs-2";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
} from "chart.js";
import withSidebar from "../common/base";
import PageHeader from "../common/PageHeader";
import StatCard from "../common/StatCard";
import { useTheme } from "../common/ThemeProvider";
import { useAuth } from "../auth/AuthContext";
import {
  getDashboardMetrics,
  getHealth,
  type HealthComponent,
  type HealthStatus,
} from "../api/metrics";
import { listUsers } from "../api/users";
import {
  getDicomwebMetrics,
  type DicomwebMetrics,
} from "../api/dicomweb-admin";
import { listReplicas, type Replica } from "../api/replicas";
import { listLogs, type LogEntry } from "../api/logs";
import "./AdminDashboard.css";

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
);

const { Text } = Typography;
const Content = Layout.Content;

const HEALTH_LABELS: Record<string, string> = {
  database: "Database",
  elasticsearch: "Elasticsearch",
  redis: "Redis",
  storage: "Storage",
  dicom_listener: "DICOM Listener",
  ingestion_service: "Ingestion Service",
  hl7: "HL7",
  fhir: "FHIR",
  auth: "Auth",
};

// Components with a dedicated area dashboard become drill-down links.
const HEALTH_LINKS: Record<string, string> = {
  storage: "/replicas",
  dicom_listener: "/dicomweb",
  hl7: "/hl7",
  fhir: "/fhir/monitoring",
};

// Permission each drill-down target requires (tenant_admin review P1-1): a
// role holding INTERFACE_MONITOR (which shows the Interfaces panel) but not
// the target's read grant must get a plain status row — never a dead "Open"
// button that bounces back to /admin. Mirrors Metrics' AREA_LINKS guard.
const HEALTH_LINK_PERMISSIONS: Record<string, string> = {
  storage: "REPLICA_READ",
  dicom_listener: "DICOMWEB_READ",
  hl7: "HL7_READ",
  fhir: "SYSTEM_ADMIN",
};

// Interface components surfaced in the Interfaces panel (INTERFACE_MONITOR).
const INTERFACE_LINKS: Record<string, string> = {
  dicom_listener: "/dicomweb",
  hl7: "/hl7",
  fhir: "/fhir/monitoring",
};

// Fixed ordering for the Interfaces panel; components without a dedicated
// page render as a plain status line (no drill-down).
const INTERFACE_COMPONENTS = [
  "dicom_listener",
  "hl7",
  "fhir",
  "ingestion_service",
];

interface DashboardTotals {
  patients?: number;
  studies?: number;
  series?: number;
  files?: number;
  storage_bytes?: number;
  users?: number;
}

function getCSSVar(name: string): string {
  return getComputedStyle(document.documentElement)
    .getPropertyValue(name)
    .trim();
}

function formatBytes(bytes: number): string {
  if (!bytes) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB"];
  let i = 0;
  let val = bytes;
  while (val >= 1024 && i < units.length - 1) {
    val /= 1024;
    i++;
  }
  return `${val.toFixed(1)} ${units[i]}`;
}

function HealthStrip({
  health,
  loading,
  hasPermission,
}: {
  health: HealthStatus | null;
  loading: boolean;
  hasPermission: (p: string) => boolean;
}) {
  const navigate = useNavigate();
  const components: Record<string, HealthComponent> = health?.components ?? {};
  if (loading) {
    return (
      <div className="dashboard-health dashboard-skeleton">
        <Spin size="small" />
        <Text type="secondary" style={{ fontSize: 12 }}>
          Checking services…
        </Text>
      </div>
    );
  }
  const entries = Object.entries(components);
  if (entries.length === 0) {
    return (
      <div className="dashboard-health">
        <Tag color="green">All services OK</Tag>
      </div>
    );
  }
  return (
    <div className="dashboard-health">
      {entries.map(([name, comp]) => {
        const link = HEALTH_LINKS[name];
        const pill = (
          <>
            <span
              className={`dashboard-health-dot dashboard-health-dot-${comp.status ?? "error"}`}
              aria-hidden="true"
            />
            <span>{HEALTH_LABELS[name] ?? name}</span>
            <span className="dashboard-health-latency">
              {comp.latency_ms != null ? `${comp.latency_ms}ms` : ""}
            </span>
          </>
        );
        const targetPerm = HEALTH_LINK_PERMISSIONS[name];
        const canOpen = link && (!targetPerm || hasPermission(targetPerm));
        return canOpen ? (
          <button
            key={name}
            type="button"
            className="dashboard-health-pill"
            onClick={() => navigate(link)}
            aria-label={`Open ${HEALTH_LABELS[name] ?? name} dashboard`}
          >
            {pill}
          </button>
        ) : (
          <span
            key={name}
            className="dashboard-health-pill dashboard-health-pill-static"
            aria-label={`${HEALTH_LABELS[name] ?? name}: ${comp.status}`}
          >
            {pill}
          </span>
        );
      })}
    </div>
  );
}

function AdminDashboard() {
  const { message } = App.useApp();
  useDocumentTitle("QuantumPACS - Admin Dashboard");
  const { hasPermission } = useAuth();
  const { isDark } = useTheme();
  const navigate = useNavigate();

  const can = useCallback((p: string) => hasPermission(p), [hasPermission]);
  const canMetrics = can("METRICS_READ") || can("ANALYTICS_READ");
  const canUsers = can("USER_READ");
  const canDicomweb = can("DICOMWEB_READ");
  const canReplicas = can("REPLICA_READ");
  const canLogs = can("LOG_READ") || can("AUDIT_READ");
  const canInterfaces = can("INTERFACE_MONITOR");

  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [healthLoading, setHealthLoading] = useState(true);
  const [metrics, setMetrics] = useState<Record<string, unknown> | null>(null);
  const [metricsLoading, setMetricsLoading] = useState(canMetrics);
  const [usersTotal, setUsersTotal] = useState<number | null>(null);
  const [dicomweb, setDicomweb] = useState<DicomwebMetrics | null>(null);
  const [replicas, setReplicas] = useState<Replica[]>([]);
  const [recentLogs, setRecentLogs] = useState<LogEntry[]>([]);
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [lastUpdate, setLastUpdate] = useState<string | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchHealth = useCallback(() => {
    setHealthLoading(true);
    getHealth()
      .then((resp) => {
        setHealth(resp);
        if (resp) setLastUpdate(new Date().toLocaleTimeString());
      })
      .catch(() => {})
      .finally(() => setHealthLoading(false));
  }, []);

  const fetchMetrics = useCallback(() => {
    if (!canMetrics) return;
    setMetricsLoading(true);
    getDashboardMetrics("30d")
      .then((resp) => {
        setMetrics(resp);
        setLastUpdate(new Date().toLocaleTimeString());
      })
      .catch((e: any) => message.error(e.message))
      .finally(() => setMetricsLoading(false));
  }, [canMetrics]);

  const fetchUsers = useCallback(() => {
    if (!canUsers) return;
    listUsers({ offset: 0, limit: 1 })
      .then((resp) => setUsersTotal(resp.total ?? null))
      .catch(() => {});
  }, [canUsers]);

  const fetchDicomweb = useCallback(() => {
    if (!canDicomweb) return;
    getDicomwebMetrics("24h")
      .then(setDicomweb)
      .catch(() => {});
  }, [canDicomweb]);

  const fetchReplicas = useCallback(() => {
    if (!canReplicas) return;
    listReplicas()
      .then(setReplicas)
      .catch(() => {});
  }, [canReplicas]);

  const fetchLogs = useCallback(() => {
    if (!canLogs) return;
    listLogs({ limit: 8 })
      .then((resp) => setRecentLogs(resp.data ?? []))
      .catch(() => {});
  }, [canLogs]);

  const refreshAll = useCallback(() => {
    fetchHealth();
    fetchMetrics();
    fetchUsers();
    fetchDicomweb();
    fetchReplicas();
    fetchLogs();
  }, [
    fetchHealth,
    fetchMetrics,
    fetchUsers,
    fetchDicomweb,
    fetchReplicas,
    fetchLogs,
  ]);

  // Tenant-scoped totals must refetch on tenant switch (mirrors Metrics).
  useTenantRefetch(refreshAll);

  useEffect(() => {
    refreshAll();
  }, [refreshAll]);

  useEffect(() => {
    if (autoRefresh) {
      intervalRef.current = setInterval(refreshAll, 30000);
    } else if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [autoRefresh, refreshAll]);

  const chartTheme = useMemo(() => {
    const primary = getCSSVar("--color-primary") || "#0891B2";
    const text = getCSSVar("--text-secondary") || "#475569";
    const gridColor = isDark ? "rgba(255,255,255,0.06)" : "rgba(0,0,0,0.06)";
    return { primary, text, gridColor };
  }, [isDark]);

  const chartOptions = useMemo(
    () => ({
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: {
          ticks: { color: chartTheme.text },
          grid: { color: chartTheme.gridColor },
        },
        y: {
          ticks: { color: chartTheme.text },
          grid: { color: chartTheme.gridColor },
        },
      },
    }),
    [chartTheme],
  );

  const totals = (metrics?.totals as DashboardTotals | undefined) ?? {};
  const modalities = metrics?.modalities ?? {};
  const ingestion30d: any[] =
    (metrics?.ingestion_30d as any[] | undefined) ?? [];

  const modalityLabels = Object.keys(modalities);
  const modalityChartData = {
    labels: modalityLabels,
    datasets: [
      {
        data: Object.values(modalities),
        backgroundColor: [
          chartTheme.primary,
          "#34D399",
          "#FBBF24",
          "#F87171",
          "#A78BFA",
          "#22D3EE",
        ],
      },
    ],
  };

  const ingestionChartData = {
    labels: ingestion30d.map((d) => d.date),
    datasets: [
      {
        data: ingestion30d.map((d) => d.count),
        borderColor: chartTheme.primary,
        backgroundColor: isDark
          ? "rgba(6, 182, 212, 0.15)"
          : "rgba(8, 145, 178, 0.1)",
        fill: true,
        tension: 0.3,
      },
    ],
  };

  const quickLinks: Array<{
    label: string;
    path: string;
    show: boolean;
    icon: React.ReactNode;
  }> = [
    { label: "Users", path: "/users", show: canUsers, icon: <TeamOutlined /> },
    {
      label: "Replicas",
      path: "/replicas",
      show: canReplicas,
      icon: <DatabaseOutlined />,
    },
    {
      label: "Metrics",
      path: "/metrics",
      show: canMetrics,
      icon: <FundOutlined />,
    },
    {
      label: "Logs",
      path: "/logs",
      show: canLogs,
      icon: <FileSearchOutlined />,
    },
    {
      label: "DICOMweb",
      path: "/dicomweb",
      show: canDicomweb,
      icon: <CloudServerOutlined />,
    },
    {
      label: "Roles",
      path: "/roles",
      show: can("ROLE_READ"),
      icon: <SafetyCertificateOutlined />,
    },
    {
      label: "Tenants",
      path: "/tenants",
      show: can("TENANT_READ"),
      icon: <BankOutlined />,
    },
    {
      label: "Routing",
      path: "/routing",
      show: can("ROUTING_READ"),
      icon: <ApartmentOutlined />,
    },
  ].filter((l) => l.show);

  return (
    <Content style={{ padding: 24 }}>
      <PageHeader
        title="Operations Dashboard"
        description="Live system health, storage totals and recent platform activity."
        extra={
          <Space size="middle">
            {lastUpdate && (
              <Text type="secondary" style={{ fontSize: 12 }}>
                Updated: {lastUpdate}
              </Text>
            )}
            <span>
              <Text style={{ fontSize: 12, marginRight: 4 }}>Auto-refresh</Text>
              <Switch
                size="small"
                checked={autoRefresh}
                onChange={setAutoRefresh}
              />
            </span>
            <Button
              size="small"
              icon={<ReloadOutlined />}
              onClick={refreshAll}
              aria-label="Refresh dashboard"
            >
              Refresh
            </Button>
          </Space>
        }
      />

      <HealthStrip
        health={health}
        loading={healthLoading}
        hasPermission={hasPermission}
      />

      {/* KPI row is assembled per-permission: the metrics cards need
          METRICS_READ/ANALYTICS_READ, the Users card only USER_READ, and
          DICOMweb only DICOMWEB_READ — a metrics-less role (e.g. pacs_admin)
          still gets its own cards instead of a blank row. */}
      {(canMetrics || canUsers || canDicomweb) && (
        <div className="dashboard-kpis">
          {canMetrics && (
            <>
              <StatCard
                label="Patients"
                value={totals.patients ?? "—"}
                icon={<TeamOutlined />}
              />
              <StatCard
                label="Studies"
                value={totals.studies ?? "—"}
                icon={<FolderOutlined />}
              />
              <StatCard
                label="Series"
                value={totals.series ?? "—"}
                icon={<ExperimentOutlined />}
              />
              <StatCard
                label="Files"
                value={totals.files ?? "—"}
                icon={<FileOutlined />}
              />
              <StatCard
                label="Storage"
                value={
                  totals.storage_bytes != null
                    ? formatBytes(totals.storage_bytes)
                    : "—"
                }
                icon={<HddOutlined />}
                hint="Archive usage"
              />
            </>
          )}
          {canUsers && (
            <StatCard
              label="Users"
              value={canUsers && usersTotal != null ? usersTotal : "—"}
              icon={<TeamOutlined />}
              hint="Active accounts"
            />
          )}
          {canDicomweb && (
            <StatCard
              label="DICOMweb Requests"
              value={dicomweb?.requests_total ?? "—"}
              icon={<CloudServerOutlined />}
              hint="Last 24h"
              tone={dicomweb && dicomweb.requests_failed > 0 ? "warn" : "ok"}
            />
          )}
        </div>
      )}

      {metricsLoading && canMetrics && (
        <div className="dashboard-skeleton" style={{ marginTop: 16 }}>
          <Spin size="small" />
          <Text type="secondary" style={{ fontSize: 12 }}>
            Loading metrics…
          </Text>
        </div>
      )}

      {canMetrics && !metricsLoading && metrics && (
        <div className="dashboard-charts">
          <section className="dashboard-panel">
            <h2 className="dashboard-panel-title">Ingestion (30 days)</h2>
            <div
              className="dashboard-chart-box"
              role="img"
              aria-label={`Ingestion trend chart: ${ingestion30d.length} days, latest: ${ingestion30d[ingestion30d.length - 1]?.count ?? 0} studies`}
            >
              <Line data={ingestionChartData} options={chartOptions} />
            </div>
          </section>
          <section className="dashboard-panel">
            <h2 className="dashboard-panel-title">Modality Distribution</h2>
            <div
              className="dashboard-chart-box"
              role="img"
              aria-label={`Modality distribution chart: ${modalityLabels.map((l, i) => `${l}: ${Object.values(modalities)[i]}`).join(", ")}`}
            >
              <Bar data={modalityChartData} options={chartOptions} />
            </div>
          </section>
        </div>
      )}

      <div className="dashboard-grid">
        {canInterfaces && (
          <section className="dashboard-panel">
            <h2 className="dashboard-panel-title">
              <ApartmentOutlined /> Interfaces
            </h2>
            {Object.keys(health?.components ?? {}).length > 0 ? (
              <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                {INTERFACE_COMPONENTS.map((name) => {
                  const comp = health?.components?.[name];
                  if (!comp) return null;
                  const target = INTERFACE_LINKS[name];
                  const targetPerm = HEALTH_LINK_PERMISSIONS[name];
                  // P1-1: only render "Open" when the caller can actually
                  // open the target route — INTERFACE_MONITOR holders without
                  // DICOMWEB_READ/HL7_READ/SYSTEM_ADMIN get a status line.
                  const canOpen =
                    target && (!targetPerm || hasPermission(targetPerm));
                  return (
                    <Space key={name}>
                      <Tag
                        color={
                          comp.status === "ok"
                            ? "green"
                            : comp.status === "degraded"
                              ? "orange"
                              : "red"
                        }
                        style={{ minWidth: 64, textAlign: "center" }}
                      >
                        {HEALTH_LABELS[name] ?? name}
                      </Tag>
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        {comp.status ?? "unknown"}
                      </Text>
                      {comp.latency_ms != null && (
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          {comp.latency_ms}ms
                        </Text>
                      )}
                      {canOpen && (
                        <Button
                          size="small"
                          type="link"
                          onClick={() => navigate(target)}
                        >
                          Open
                        </Button>
                      )}
                    </Space>
                  );
                })}
              </div>
            ) : (
              <Text type="secondary" style={{ fontSize: 12 }}>
                No interface status reported
              </Text>
            )}
          </section>
        )}

        {canReplicas && (
          <section className="dashboard-panel">
            <h2 className="dashboard-panel-title">
              <DatabaseOutlined /> Replicas
            </h2>
            {replicas.length > 0 ? (
              <Table
                dataSource={replicas}
                rowKey="id"
                size="small"
                pagination={false}
                columns={[
                  { title: "Name", dataIndex: "name", key: "name" },
                  {
                    title: "Status",
                    dataIndex: "status",
                    key: "status",
                    render: (s: string) => (
                      <Tag
                        color={
                          s === "ok" || s === "synced" ? "green" : "orange"
                        }
                      >
                        {(s ?? "unknown").toUpperCase()}
                      </Tag>
                    ),
                  },
                  {
                    title: "Delay",
                    dataIndex: "delay",
                    key: "delay",
                    render: (d: number) => (d != null ? `${d}s` : "—"),
                  },
                ]}
              />
            ) : (
              <Text type="secondary" style={{ fontSize: 12 }}>
                No replicas configured
              </Text>
            )}
          </section>
        )}

        {canLogs && (
          <section className="dashboard-panel">
            <h2 className="dashboard-panel-title">
              <FileSearchOutlined /> Recent Activity
            </h2>
            {recentLogs.length > 0 ? (
              <Table
                dataSource={recentLogs}
                rowKey="id"
                size="small"
                pagination={false}
                columns={[
                  {
                    title: "Time",
                    dataIndex: "created_at",
                    key: "created_at",
                    render: (t: string) =>
                      t ? new Date(t).toLocaleTimeString() : "—",
                  },
                  {
                    title: "Actor",
                    dataIndex: "actor",
                    key: "actor",
                    render: (a: string) => a || "system",
                  },
                  {
                    title: "Event",
                    dataIndex: "event_type",
                    key: "event_type",
                    render: (e: string) => e || "—",
                  },
                  {
                    title: "Description",
                    dataIndex: "description",
                    key: "description",
                    ellipsis: true,
                    render: (d: string) => d || "—",
                  },
                ]}
              />
            ) : (
              <Text type="secondary" style={{ fontSize: 12 }}>
                No recent events
              </Text>
            )}
          </section>
        )}

        <section className="dashboard-panel">
          <h2 className="dashboard-panel-title">
            <DashboardOutlined /> Quick Links
          </h2>
          <div className="dashboard-quick-links">
            {quickLinks.map((l) => (
              <Button
                key={l.path}
                size="small"
                icon={l.icon}
                onClick={() => navigate(l.path)}
              >
                {l.label}
              </Button>
            ))}
          </div>
        </section>
      </div>
    </Content>
  );
}

export default withSidebar(AdminDashboard);
