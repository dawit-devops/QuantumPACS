import React, { useState, useEffect } from "react";
import {
  Layout,
  Card,
  Row,
  Col,
  Tag,
  Table,
  Descriptions,
  Spin,
  Tabs,
  Empty,
  Badge,
  Statistic,
  Radio,
  Switch,
  Select,
  Button,
} from "antd";
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  ApiOutlined,
  SearchOutlined,
  DownloadOutlined,
  UploadOutlined,
  DatabaseOutlined,
  InboxOutlined,
  ReloadOutlined,
} from "@ant-design/icons";
import withSidebar from "../common/base";
import {
  getDicomwebAdmin,
  getDicomwebMetrics,
  getDicomwebRequests,
  DicomwebMetrics,
  DicomwebRequestLog,
} from "../api/dicomweb-admin";
import { PageState } from "../common/PageState";
import "./DicomWebAdmin.css";

const { Content } = Layout;

const serviceIcons: Record<string, React.ReactNode> = {
  qido: <SearchOutlined />,
  wado: <DownloadOutlined />,
  stow: <UploadOutlined />,
};

const PERIOD_OPTIONS = [
  { label: "24h", value: "24h" },
  { label: "7d", value: "7d" },
  { label: "30d", value: "30d" },
];

const KIND_OPTIONS = [
  "qido",
  "wado",
  "stow",
  "frames",
  "archive",
  "wado_uri",
].map((k) => ({ label: k.toUpperCase(), value: k }));

function formatDuration(ms: number | null): string {
  if (ms === null || ms === undefined) return "-";
  return ms >= 1000 ? `${(ms / 1000).toFixed(2)}s` : `${ms}ms`;
}

function formatTime(iso: string | null): string {
  if (!iso) return "-";
  return new Date(iso).toLocaleString();
}

function formatBytes(bytes: number): string {
  if (!bytes) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB"];
  let i = 0;
  let v = bytes;
  while (v >= 1024 && i < units.length - 1) {
    v /= 1024;
    i += 1;
  }
  const value = v.toFixed(1).replace(/\.0$/, "");
  return `${value} ${units[i]}`;
}

function DicomWebAdmin(props: any) {
  const [info, setInfo] = useState<any>(null);
  const [metrics, setMetrics] = useState<DicomwebMetrics | null>(null);
  const [period, setPeriod] = useState("24h");
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [requests, setRequests] = useState<DicomwebRequestLog[]>([]);
  const [requestsCursor, setRequestsCursor] = useState<number | null>(null);
  const [requestsHasMore, setRequestsHasMore] = useState(false);
  const [requestsLoading, setRequestsLoading] = useState(false);
  const [requestKind, setRequestKind] = useState<string | undefined>(undefined);
  const [requestPeriod, setRequestPeriod] = useState("24h");

  const fetchRequests = async (reset = false) => {
    setRequestsLoading(true);
    try {
      const res = await getDicomwebRequests({
        limit: 50,
        cursor: reset ? undefined : (requestsCursor ?? undefined),
        kind: requestKind,
        period: requestPeriod,
      });
      setRequests((prev) => (reset ? res.data : [...prev, ...res.data]));
      setRequestsCursor(res.next_cursor);
      setRequestsHasMore(res.has_more);
    } catch {
      // the page-level error state is owned by the info fetch
    } finally {
      setRequestsLoading(false);
    }
  };

  useEffect(() => {
    fetchRequests(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [requestKind, requestPeriod]);

  const fetchMetrics = async (p: string) => {
    try {
      setMetrics(await getDicomwebMetrics(p));
    } catch {
      // keep stale metrics on a failed refresh; the info fetch owns the
      // page-level error state
    }
  };

  useEffect(() => {
    fetchMetrics(period);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [period]);

  useEffect(() => {
    if (!autoRefresh) return;
    const t = setInterval(() => fetchMetrics(period), 30000);
    return () => clearInterval(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoRefresh, period]);

  useEffect(() => {
    fetchInfo();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const fetchInfo = async () => {
    setLoading(true);
    setError(null);
    try {
      const [res, m] = await Promise.all([
        getDicomwebAdmin(),
        getDicomwebMetrics(period),
      ]);
      setInfo(res);
      setMetrics(m);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <Content className="dicomweb-admin" style={{ padding: 24 }}>
        <Spin size="large" style={{ display: "block", margin: "80px auto" }} />
      </Content>
    );
  }

  if (error) {
    return (
      <Content className="dicomweb-admin" style={{ padding: 24 }}>
        <PageState error={error} onRetry={fetchInfo} />
      </Content>
    );
  }

  const endpointColumns = [
    {
      title: "Method",
      dataIndex: "method",
      key: "method",
      render: (t: string) => <Tag>{t}</Tag>,
      width: 80,
    },
    { title: "Path", dataIndex: "path", key: "path" },
    { title: "Description", dataIndex: "description", key: "description" },
  ];

  return (
    <Content className="dicomweb-admin" style={{ padding: 24 }}>
      <div style={{ fontWeight: 600, fontSize: 16, marginBottom: 16 }}>
        <ApiOutlined style={{ marginRight: 8 }} />
        DICOMweb Server
      </div>

      {/* Service Cards */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        {["qido", "wado", "stow"].map((service) => {
          const s = info?.[service];
          if (!s) return null;
          return (
            <Col span={8} key={service}>
              <Card
                title={
                  <span>
                    {serviceIcons[service]}{" "}
                    <span style={{ marginLeft: 4 }}>
                      {service.toUpperCase()}-RS
                    </span>
                  </span>
                }
                extra={
                  s.enabled ? (
                    <Tag icon={<CheckCircleOutlined />} color="green">
                      Enabled
                    </Tag>
                  ) : (
                    <Tag icon={<CloseCircleOutlined />} color="red">
                      Disabled
                    </Tag>
                  )
                }
              >
                <Descriptions column={1} size="small">
                  <Descriptions.Item label="Format">
                    <Tag>
                      {s.response_format ||
                        s.content_type ||
                        "application/dicom"}
                    </Tag>
                  </Descriptions.Item>
                  {s.pagination && (
                    <Descriptions.Item label="Pagination">
                      {s.pagination}
                    </Descriptions.Item>
                  )}
                  {s.features?.transfer_syntax && (
                    <Descriptions.Item label="Transfer Syntax">
                      {s.features.transfer_syntax}
                    </Descriptions.Item>
                  )}
                  {s.modality_validation !== undefined && (
                    <Descriptions.Item label="Valid Modalities">
                      {s.valid_modalities_count}
                    </Descriptions.Item>
                  )}
                </Descriptions>
              </Card>
            </Col>
          );
        })}
      </Row>

      <Tabs
        defaultActiveKey="endpoints"
        items={[
          {
            key: "endpoints",
            label: "Endpoints",
            children: (
              <Row gutter={16}>
                {["qido", "wado", "stow"].map((service) => {
                  const s = info?.[service];
                  if (!s?.endpoints?.length) return null;
                  return (
                    <Col span={8} key={service}>
                      <Card
                        title={`${service.toUpperCase()}-RS`}
                        size="small"
                        style={{ marginBottom: 16 }}
                      >
                        <Table
                          dataSource={s.endpoints}
                          columns={endpointColumns}
                          rowKey="path"
                          pagination={false}
                          size="small"
                        />
                      </Card>
                    </Col>
                  );
                })}
              </Row>
            ),
          },
          {
            key: "search",
            label: "Search Parameters",
            children: (
              <Card size="small">
                {info?.qido?.search_params?.length > 0 ? (
                  <Table
                    dataSource={info.qido.search_params}
                    columns={[
                      {
                        title: "Parameter",
                        dataIndex: "name",
                        key: "name",
                        render: (t: string) => <code>{t}</code>,
                      },
                      {
                        title: "Type",
                        dataIndex: "type",
                        key: "type",
                        render: (t: string) => <Tag>{t}</Tag>,
                      },
                      {
                        title: "Description",
                        dataIndex: "description",
                        key: "description",
                      },
                    ]}
                    rowKey="name"
                    pagination={false}
                    size="small"
                  />
                ) : (
                  <Empty description="No search parameters" />
                )}
              </Card>
            ),
          },
          {
            key: "modalities",
            label: "Modalities",
            children: (
              <Card size="small">
                <div
                  style={{ marginBottom: 8, color: "var(--text-secondary)" }}
                >
                  {info?.modalities?.length || 0} valid modality codes
                </div>
                {info?.modalities?.map((m: string) => (
                  <Tag key={m} style={{ marginBottom: 4 }}>
                    {m}
                  </Tag>
                ))}
              </Card>
            ),
          },
          {
            key: "metrics",
            label: "Metrics",
            children: (
              <Card size="small">
                {metrics ? (
                  <>
                    <Row
                      justify="space-between"
                      align="middle"
                      style={{ marginBottom: 16 }}
                    >
                      <Radio.Group
                        size="small"
                        options={PERIOD_OPTIONS}
                        value={period}
                        onChange={(e) => setPeriod(e.target.value)}
                      />
                      <span>
                        <Switch
                          size="small"
                          checked={autoRefresh}
                          onChange={setAutoRefresh}
                          style={{ marginRight: 8 }}
                        />
                        Auto-refresh (30s)
                      </span>
                    </Row>
                    <Row gutter={16}>
                      <Col span={6}>
                        <Statistic
                          title={`Studies stored (${metrics.period})`}
                          value={metrics.studies_stored || 0}
                          prefix={<DatabaseOutlined />}
                        />
                      </Col>
                      <Col span={6}>
                        <Statistic
                          title={`Instances stored (${metrics.period})`}
                          value={metrics.files_stored || 0}
                          prefix={<UploadOutlined />}
                        />
                      </Col>
                      <Col span={6}>
                        <Statistic
                          title={`Failed stores (${metrics.period})`}
                          value={metrics.failed_stores || 0}
                          prefix={<InboxOutlined />}
                          valueStyle={
                            metrics.failed_stores
                              ? { color: "#cf1322" }
                              : undefined
                          }
                        />
                      </Col>
                      <Col span={6}>
                        <Statistic
                          title="Storage used"
                          value={formatBytes(metrics.storage_bytes || 0)}
                          prefix={<DatabaseOutlined />}
                        />
                      </Col>
                    </Row>
                    <Row gutter={16} style={{ marginTop: 16 }}>
                      <Col span={8}>
                        <Statistic
                          title="Total studies"
                          value={metrics.totals?.studies || 0}
                        />
                      </Col>
                      <Col span={8}>
                        <Statistic
                          title="Total series"
                          value={metrics.totals?.series || 0}
                        />
                      </Col>
                      <Col span={8}>
                        <Statistic
                          title="Total instances"
                          value={metrics.totals?.files || 0}
                        />
                      </Col>
                    </Row>
                    <Row gutter={16} style={{ marginTop: 16 }}>
                      <Col span={6}>
                        <Statistic
                          title={`Requests (${metrics.period})`}
                          value={metrics.requests_total || 0}
                          prefix={<ApiOutlined />}
                        />
                      </Col>
                      <Col span={6}>
                        <Statistic
                          title={`Failed requests (${metrics.period})`}
                          value={metrics.requests_failed || 0}
                          prefix={<CloseCircleOutlined />}
                          valueStyle={
                            metrics.requests_failed
                              ? { color: "#cf1322" }
                              : undefined
                          }
                        />
                      </Col>
                    </Row>
                    {metrics.requests_by_kind?.length ? (
                      <Table
                        style={{ marginTop: 16 }}
                        size="small"
                        rowKey="kind"
                        pagination={false}
                        dataSource={metrics.requests_by_kind}
                        columns={[
                          {
                            title: "Kind",
                            dataIndex: "kind",
                            key: "kind",
                            render: (k: string) => <Tag>{k.toUpperCase()}</Tag>,
                          },
                          {
                            title: `Requests (${metrics.period})`,
                            dataIndex: "total",
                            key: "total",
                          },
                          {
                            title: "Errors",
                            dataIndex: "errors",
                            key: "errors",
                            render: (e: number) =>
                              e > 0 ? (
                                <span style={{ color: "#cf1322" }}>{e}</span>
                              ) : (
                                e
                              ),
                          },
                        ]}
                      />
                    ) : null}
                    {metrics.by_modality?.length ? (
                      <Table
                        style={{ marginTop: 16 }}
                        size="small"
                        rowKey="modality"
                        pagination={false}
                        dataSource={metrics.by_modality}
                        columns={[
                          {
                            title: "Modality",
                            dataIndex: "modality",
                            key: "modality",
                            render: (m: string) => <Tag>{m}</Tag>,
                          },
                          {
                            title: `Instances (${metrics.period})`,
                            dataIndex: "count",
                            key: "count",
                          },
                        ]}
                      />
                    ) : null}
                  </>
                ) : (
                  <Empty description="No metrics available" />
                )}
              </Card>
            ),
          },
          {
            key: "requests",
            label: "Requests",
            children: (
              <Card size="small">
                <Row
                  justify="space-between"
                  align="middle"
                  style={{ marginBottom: 16 }}
                >
                  <span>
                    <Select
                      size="small"
                      placeholder="All kinds"
                      allowClear
                      options={KIND_OPTIONS}
                      value={requestKind}
                      onChange={setRequestKind}
                      style={{ width: 140, marginRight: 8 }}
                    />
                    <Radio.Group
                      size="small"
                      options={PERIOD_OPTIONS}
                      value={requestPeriod}
                      onChange={(e) => setRequestPeriod(e.target.value)}
                    />
                  </span>
                  <Button
                    size="small"
                    onClick={() => fetchRequests(true)}
                    icon={<ReloadOutlined />}
                  >
                    Refresh
                  </Button>
                </Row>
                <Table
                  size="small"
                  rowKey="id"
                  loading={requestsLoading}
                  pagination={false}
                  dataSource={requests}
                  columns={[
                    {
                      title: "Time",
                      dataIndex: "created_at",
                      key: "created_at",
                      render: formatTime,
                      width: 180,
                    },
                    {
                      title: "Kind",
                      dataIndex: "kind",
                      key: "kind",
                      render: (k: string) => <Tag>{k?.toUpperCase()}</Tag>,
                      width: 100,
                    },
                    {
                      title: "Method",
                      dataIndex: "method",
                      key: "method",
                      width: 80,
                    },
                    {
                      title: "Path",
                      dataIndex: "path",
                      key: "path",
                      ellipsis: true,
                    },
                    {
                      title: "Status",
                      dataIndex: "status",
                      key: "status",
                      width: 80,
                      render: (s: number) =>
                        s >= 400 ? (
                          <Tag color="red">{s}</Tag>
                        ) : (
                          <Tag color="green">{s}</Tag>
                        ),
                    },
                    {
                      title: "Duration",
                      dataIndex: "duration_ms",
                      key: "duration_ms",
                      render: formatDuration,
                      width: 100,
                    },
                    {
                      title: "Actor",
                      dataIndex: "actor",
                      key: "actor",
                      render: (a: unknown) => (a == null ? "-" : String(a)),
                      width: 90,
                    },
                  ]}
                />
                {requestsHasMore && (
                  <Button
                    size="small"
                    style={{ marginTop: 12 }}
                    onClick={() => fetchRequests(false)}
                  >
                    Load more
                  </Button>
                )}
              </Card>
            ),
          },
          {
            key: "roadmap",
            label: "Missing Features",
            children: (
              <Card size="small">
                {info?.missing_features?.length > 0 ? (
                  <Table
                    dataSource={info.missing_features.map((f: string) => ({
                      feature: f,
                    }))}
                    columns={[
                      {
                        title: "Feature",
                        dataIndex: "feature",
                        key: "feature",
                      },
                    ]}
                    rowKey="feature"
                    pagination={false}
                    size="small"
                  />
                ) : (
                  <Empty description="No missing features" />
                )}
              </Card>
            ),
          },
        ]}
      />
    </Content>
  );
}

export default withSidebar(DicomWebAdmin);
