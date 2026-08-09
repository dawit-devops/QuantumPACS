import { useDocumentTitle, useTenantRefetch } from "../hooks";
import React, {
  useState,
  useEffect,
  useMemo,
  useCallback,
  useRef,
} from "react";
import { useNavigate } from "react-router";
import {
  App,
  Layout,
  Card,
  Col,
  Row,
  Statistic,
  Table,
  Tag,
  Select,
  Switch,
  Radio,
  Typography,
  Space,
  Spin,
  Button,
} from "antd";
import {
  DatabaseOutlined,
  TeamOutlined,
  FileOutlined,
  HddOutlined,
  FolderOutlined,
  ExperimentOutlined,
  CheckCircleOutlined,
  WarningOutlined,
  CloseCircleOutlined,
  ReloadOutlined,
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
import { useTheme } from "../common/ThemeProvider";
import { useAuth } from "../auth/AuthContext";
import {
  getDashboardMetrics,
  getHealth,
  type HealthComponent,
  type HealthStatus,
} from "../api/metrics";
import { PageState } from "../common/PageState";
import "./Metrics.css";

function AnimatedStat({
  value,
  title,
  prefix,
}: {
  value: number;
  title: string;
  prefix: React.ReactNode;
}) {
  const [display, setDisplay] = useState(0);
  const prevValue = useRef(0);

  useEffect(() => {
    if (value === undefined || value === null) return;
    const from = prevValue.current || 0;
    const to = value;
    if (from === to) {
      setDisplay(to);
      return;
    }
    const duration = 800;
    const start = performance.now();
    prevValue.current = to;
    let raf = requestAnimationFrame(function tick(now) {
      const elapsed = now - start;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 2);
      setDisplay(Math.round(from + (to - from) * eased));
      if (progress < 1) raf = requestAnimationFrame(tick);
    });
    return () => cancelAnimationFrame(raf);
  }, [value]);

  return <Statistic title={title} value={display} prefix={prefix} />;
}

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

const TIME_RANGES = [
  { label: "24h", value: "24h" },
  { label: "7d", value: "7d" },
  { label: "30d", value: "30d" },
  { label: "90d", value: "90d" },
];

function healthColor(status: string): string {
  if (status === "ok") return "green";
  if (status === "degraded") return "orange";
  return "red";
}

function healthIcon(status: string) {
  if (status === "ok") return <CheckCircleOutlined />;
  if (status === "degraded") return <WarningOutlined />;
  return <CloseCircleOutlined />;
}

// Components with a dedicated area dashboard become drill-down links from
// the System Health card; everything else (database, elasticsearch, redis,
// auth, ingestion_service) stays a plain status row. hl7/fhir mirror the
// current /metrics time scope via a period query param. Each link carries
// the target route's permission so a user never clicks into a dead end.
const AREA_LINKS: Record<string, { path: string; period?: boolean; permission: string }> = {
  storage: { path: "/replicas", permission: "REPLICA_READ" },
  dicom_listener: { path: "/dicomweb", permission: "DICOMWEB_READ" },
  hl7: { path: "/hl7", period: true, permission: "HL7_READ" },
  fhir: { path: "/fhir/monitoring", period: true, permission: "SYSTEM_ADMIN" },
};

// Target dashboards cap their period at 30d, so the 90d scope clamps to 30d.
function scopeToPeriod(range: string): string {
  if (range === "24h") return "24h";
  if (range === "7d") return "7d";
  return "30d";
}

function HealthRow({
  name,
  comp,
  timeRange,
}: {
  name: string;
  comp: HealthComponent;
  timeRange: string;
}) {
  const navigate = useNavigate();
  const { hasPermission } = useAuth();
  const label = labelName(name);
  const area = AREA_LINKS[name];

  const rowStyle: React.CSSProperties = {
    marginBottom: 8,
    display: "flex",
    alignItems: "center",
    gap: 8,
  };
  const content = (
    <>
      {healthIcon(comp.status)}
      <span style={{ flex: 1, fontWeight: 500 }}>{label}</span>
      <Tag color={healthColor(comp.status)}>
        {String(comp.status).toUpperCase()}
      </Tag>
    </>
  );

  // Without the target dashboard's permission the row renders as a plain
  // status line instead of a link that would bounce off the route guard.
  if (!area || !hasPermission(area.permission)) {
    return <div style={rowStyle}>{content}</div>;
  }

  const href = area.period
    ? `${area.path}?period=${scopeToPeriod(timeRange)}`
    : area.path;
  return (
    <a
      href={href}
      className="metrics-health-link"
      aria-label={`View ${label.toLowerCase()} health dashboard`}
      onClick={(e) => {
        e.preventDefault();
        navigate(href);
      }}
      style={rowStyle}
    >
      {content}
    </a>
  );
}

function getCSSVar(name: string): string {
  return getComputedStyle(document.documentElement)
    .getPropertyValue(name)
    .trim();
}

function Metrics() {
  const { message } = App.useApp();
  useDocumentTitle("QuantumPACS - Metrics");
  const { isDark } = useTheme();
  const { activeTenant } = useAuth();

  // Dashboard metrics and system health are fetched independently so one
  // panel's failure never blocks the other (AC-R01-19).
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [healthLoading, setHealthLoading] = useState(true);
  const [healthError, setHealthError] = useState<string | null>(null);
  const [timeRange, setTimeRange] = useState("30d");
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [lastUpdate, setLastUpdate] = useState<string | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchMetrics = useCallback(() => {
    setLoading(true);
    setError(null);
    getDashboardMetrics(timeRange)
      .then((resp) => {
        setData(resp);
        setLastUpdate(new Date().toLocaleTimeString());
      })
      .catch((e: any) => {
        setError(e.message);
        message.error(e.message);
      })
      .finally(() => setLoading(false));
  }, [timeRange]);

  const fetchHealth = useCallback(() => {
    setHealthLoading(true);
    setHealthError(null);
    getHealth()
      .then((resp) => {
        setHealth(resp);
        if (resp) setLastUpdate(new Date().toLocaleTimeString());
      })
      .catch((e: any) => {
        setHealthError(e.message);
      })
      .finally(() => setHealthLoading(false));
  }, []);

  const refreshAll = useCallback(() => {
    fetchMetrics();
    fetchHealth();
  }, [fetchMetrics, fetchHealth]);

  // Totals are scoped server-side via the X-Tenant-ID header (client.ts);
  // a tenant switch must refetch so the cards never show the old tenant's
  // numbers.
  useTenantRefetch(refreshAll);

  useEffect(() => {
    fetchMetrics();
    fetchHealth();
  }, [fetchMetrics, fetchHealth]);

  useEffect(() => {
    if (autoRefresh) {
      intervalRef.current = setInterval(refreshAll, 30000);
    } else {
      if (intervalRef.current) clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [autoRefresh, refreshAll]);

  const chartTheme = useMemo(() => {
    const primary = getCSSVar("--color-primary") || "#0891B2";
    const surface = getCSSVar("--bg-surface") || "#FFFFFF";
    const text = getCSSVar("--text-secondary") || "#475569";
    const gridColor = isDark ? "rgba(255,255,255,0.06)" : "rgba(0,0,0,0.06)";
    return { primary, surface, text, gridColor };
  }, [isDark]);

  const CHART_OPTIONS = useMemo(
    () => ({
      responsive: true,
      plugins: {
        legend: { display: false },
      },
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

  const totals = data?.totals || {};
  const modalities = data?.modalities || {};
  const ingestion30d = data?.ingestion_30d || [];
  const latestFiles = data?.latest_files || [];

  const modalityLabels = Object.keys(modalities);
  const modalityValues = Object.values(modalities) as number[];

  const modalityColors = [
    chartTheme.primary,
    "#34D399",
    "#FBBF24",
    "#F87171",
    "#A78BFA",
    "#22D3EE",
  ];

  const modalityChartData = {
    labels: modalityLabels,
    datasets: [{ data: modalityValues, backgroundColor: modalityColors }],
  };

  const ingestionLabels = ingestion30d.map((d: any) => d.date);
  const ingestionValues = ingestion30d.map((d: any) => d.count);

  const ingestionChartData = {
    labels: ingestionLabels,
    datasets: [
      {
        data: ingestionValues,
        borderColor: chartTheme.primary,
        backgroundColor: isDark
          ? `rgba(6, 182, 212, 0.15)`
          : `rgba(8, 145, 178, 0.1)`,
        fill: true,
        tension: 0.3,
      },
    ],
  };

  const components = health?.components || {};

  const latencyColors = Object.values(components).map((c: any) => {
    if (c.status === "ok") return "#34D399";
    if (c.status === "degraded") return "#FBBF24";
    return "#F87171";
  });

  return (
    <Content style={{ padding: 24 }}>
      <Card
        title="System Health"
        className="animate-fade-in-up"
        style={{ animationDelay: "0ms", marginBottom: 16 }}
      >
        {healthLoading ? (
          <div
            style={{
              display: "flex",
              justifyContent: "center",
              padding: "24px 0",
            }}
          >
            <Spin size="small" />
          </div>
        ) : healthError ? (
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              gap: 8,
              padding: "12px 0",
            }}
          >
            <Text type="secondary">
              <CloseCircleOutlined style={{ marginRight: 6 }} />
              Metrics unavailable
            </Text>
            <Button
              size="small"
              icon={<ReloadOutlined />}
              onClick={fetchHealth}
            >
              Retry
            </Button>
          </div>
        ) : Object.entries(components).length > 0 ? (
          Object.entries(components).map(([name, comp]: [string, any]) => (
            <HealthRow
              key={name}
              name={name}
              comp={comp}
              timeRange={timeRange}
            />
          ))
        ) : (
          <Tag color="green">OK</Tag>
        )}
      </Card>
      <PageState loading={loading} error={error} onRetry={refreshAll}>
        <Row
          justify="space-between"
          align="middle"
          style={{ marginBottom: 16 }}
        >
          <Col>
            <Space>
              {activeTenant && (
                <Tag color="blue" style={{ fontSize: 12 }}>
                  Tenant: {activeTenant.name}
                </Tag>
              )}
              <Radio.Group
                value={timeRange}
                onChange={(e) => setTimeRange(e.target.value)}
                buttonStyle="solid"
                size="small"
              >
                {TIME_RANGES.map((r) => (
                  <Radio.Button key={r.value} value={r.value}>
                    {r.label}
                  </Radio.Button>
                ))}
              </Radio.Group>
            </Space>
          </Col>
          <Col>
            <Space size="middle">
              {lastUpdate && (
                <Text type="secondary" style={{ fontSize: 12 }}>
                  Updated: {lastUpdate}
                </Text>
              )}
              <span>
                <Text style={{ fontSize: 12, marginRight: 4 }}>
                  Auto-refresh
                </Text>
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
              >
                Refresh
              </Button>
            </Space>
          </Col>
        </Row>
        <Row gutter={[16, 16]}>
          <Col xs={12} sm={8} lg={4}>
            <Card
              className="animate-fade-in-up"
              style={{ animationDelay: "0ms" }}
            >
              <AnimatedStat
                title="Patients"
                value={totals.patients}
                prefix={<TeamOutlined />}
              />
            </Card>
          </Col>
          <Col xs={12} sm={8} lg={4}>
            <Card
              className="animate-fade-in-up"
              style={{ animationDelay: "50ms" }}
            >
              <AnimatedStat
                title="Studies"
                value={totals.studies}
                prefix={<FolderOutlined />}
              />
            </Card>
          </Col>
          <Col xs={12} sm={8} lg={4}>
            <Card
              className="animate-fade-in-up"
              style={{ animationDelay: "100ms" }}
            >
              <AnimatedStat
                title="Series"
                value={totals.series}
                prefix={<ExperimentOutlined />}
              />
            </Card>
          </Col>
          <Col xs={12} sm={8} lg={4}>
            <Card
              className="animate-fade-in-up"
              style={{ animationDelay: "150ms" }}
            >
              <AnimatedStat
                title="Files"
                value={totals.files}
                prefix={<FileOutlined />}
              />
            </Card>
          </Col>
          <Col xs={12} sm={8} lg={4}>
            <Card
              className="animate-fade-in-up"
              style={{ animationDelay: "200ms" }}
            >
              <AnimatedStat
                title="Users"
                value={totals.users}
                prefix={<TeamOutlined />}
              />
            </Card>
          </Col>
          <Col xs={12} sm={8} lg={4}>
            <Card
              className="animate-fade-in-up"
              style={{ animationDelay: "250ms" }}
            >
              <Statistic
                title="Storage"
                value={formatBytes(totals.storage_bytes)}
                prefix={<HddOutlined />}
              />
            </Card>
          </Col>
        </Row>

        <Row gutter={[16, 16]} style={{ marginTop: 24 }}>
          <Col xs={24}>
            <Card
              title="Modality Distribution"
              className="animate-fade-in-up"
              style={{ animationDelay: "200ms" }}
            >
              <div
                role="img"
                aria-label={`Modality distribution chart: ${modalityLabels.map((l, i) => `${l}: ${modalityValues[i]}`).join(", ")}`}
              >
                <Bar data={modalityChartData} options={CHART_OPTIONS} />
              </div>
            </Card>
            <Card title="Component Latency" style={{ marginTop: 16 }}>
              {Object.entries(components).length > 0 ? (
                <Bar
                  data={{
                    labels: Object.keys(components).map(labelName),
                    datasets: [
                      {
                        label: "Latency (ms)",
                        data: Object.values(components).map(
                          (c: any) => c.latency_ms || 0,
                        ),
                        backgroundColor: latencyColors,
                      },
                    ],
                  }}
                  options={{
                    ...CHART_OPTIONS,
                    indexAxis: "y",
                    scales: {
                      x: Object.assign(
                        { title: { display: true, text: "ms" } },
                        CHART_OPTIONS.scales?.x,
                      ),
                      y: CHART_OPTIONS.scales?.y,
                    },
                  }}
                />
              ) : (
                <Tag color="green">OK</Tag>
              )}
            </Card>
          </Col>
        </Row>

        <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
          <Col xs={24} md={12}>
            <Card
              title="Ingestion (30 days)"
              className="animate-fade-in-up"
              style={{ animationDelay: "100ms" }}
            >
              <div
                role="img"
                aria-label={`Ingestion trend chart: ${ingestionLabels.length} days, latest: ${ingestionValues[ingestionValues.length - 1] || 0} studies`}
              >
                <Line data={ingestionChartData} options={CHART_OPTIONS} />
              </div>
            </Card>
          </Col>
          <Col xs={24} md={12}>
            <Card
              title="Latest Files"
              className="animate-fade-in-up"
              style={{ animationDelay: "200ms" }}
            >
              <Table
                dataSource={latestFiles}
                columns={[
                  { title: "ID", dataIndex: "id", key: "id" },
                  { title: "Name", dataIndex: "name", key: "name" },
                  { title: "Created", dataIndex: "created", key: "created" },
                ]}
                pagination={false}
                size="small"
              />
            </Card>
          </Col>
        </Row>
      </PageState>
    </Content>
  );
}

function labelName(key: string): string {
  const map: Record<string, string> = {
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
  return map[key] || key;
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

export default withSidebar(Metrics);
