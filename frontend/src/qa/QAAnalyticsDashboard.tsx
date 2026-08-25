import { useDocumentTitle } from "../hooks";
import React, { useState, useEffect, useCallback } from "react";
import {
  Layout,
  Tabs,
  Table,
  Tag,
  Button,
  Statistic,
  Row,
  Col,
  Alert,
  Spin,
  Select,
  Space,
} from "antd";
import { ReloadOutlined, DownloadOutlined } from "@ant-design/icons";
import withSidebar from "../common/base";
import { PageState } from "../common/PageState";
import {
  getRejectAnalysis,
  getDoseTracking,
  getTechMetrics,
  getProtocolCompliance,
  getQATrends,
  exportQAReport,
  type QAReportType,
  type RejectAnalysisData,
  type DoseTrackingData,
  type TechMetric,
  type ProtocolCompliance,
  type TrendPoint,
} from "../api/qa-analytics";
import "./QAAnalyticsDashboard.css";

const Content = Layout.Content;

// QA-08: Reusable CSV export button
function ExportButton({ report }: { report: QAReportType }) {
  const [exporting, setExporting] = useState(false);
  const handleExport = async () => {
    setExporting(true);
    try {
      await exportQAReport(report);
    } catch {
      // error is thrown but we don't block the UI
    } finally {
      setExporting(false);
    }
  };
  return (
    <Button size="small" icon={<DownloadOutlined />} loading={exporting} onClick={handleExport}>
      Export CSV
    </Button>
  );
}

function RejectAnalysisPanel() {
  const [data, setData] = useState<RejectAnalysisData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetch = useCallback(() => {
    setLoading(true);
    setError(null);
    getRejectAnalysis()
      .then((d) => {
        setLoading(false);
        setData(d);
      })
      .catch((e: any) => {
        setLoading(false);
        setError(e.message);
      });
  }, []);

  useEffect(() => {
    fetch();
  }, [fetch]);

  const modCols = [
    { title: "Modality", dataIndex: "modality", key: "mod", render: (v: string) => <Tag>{v}</Tag> },
    { title: "Total", dataIndex: "total", key: "total" },
    { title: "Fails", dataIndex: "fails", key: "fails" },
    {
      title: "Reject Rate",
      dataIndex: "reject_rate",
      key: "rate",
      render: (v: number) => (
        <span style={{ color: v > 10 ? "#ff4d4f" : v > 5 ? "#fa8c16" : "#52c41a" }}>{v}%</span>
      ),
    },
  ];

  const techCols = [
    { title: "Technologist", dataIndex: "tech", key: "tech" },
    { title: "Total", dataIndex: "total", key: "total" },
    { title: "Fails", dataIndex: "fails", key: "fails" },
    {
      title: "Reject Rate",
      dataIndex: "reject_rate",
      key: "rate",
      render: (v: number) => (
        <span style={{ color: v > 10 ? "#ff4d4f" : v > 5 ? "#fa8c16" : "#52c41a" }}>{v}%</span>
      ),
    },
  ];

  return (
    <PageState error={error} onRetry={fetch} loading={loading}>
      {data && (
        <>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginBottom: 8,
            }}
          >
            <h3 style={{ margin: 0 }}>Reject Rate by Modality</h3>
            <ExportButton report="reject-analysis" />
          </div>
          <Table
            rowKey="modality"
            columns={modCols}
            dataSource={data.by_modality}
            pagination={false}
            size="small"
            style={{ marginBottom: 16 }}
          />
          <h3>Reject Rate by Technologist</h3>
          <Table
            rowKey="tech"
            columns={techCols}
            dataSource={data.by_technologist}
            pagination={false}
            size="small"
            style={{ marginBottom: 16 }}
          />
          <h3>Reject by Discrepancy Level</h3>
          <Row gutter={16}>
            {data.by_discrepancy.map((d) => (
              <Col span={6} key={d.discrepancy_level}>
                <Statistic title={d.discrepancy_level} value={d.n} />
              </Col>
            ))}
          </Row>
        </>
      )}
    </PageState>
  );
}

function DoseTrackingPanel() {
  const [data, setData] = useState<DoseTrackingData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetch = useCallback(() => {
    setLoading(true);
    setError(null);
    getDoseTracking()
      .then((d) => {
        setLoading(false);
        setData(d);
      })
      .catch((e: any) => {
        setLoading(false);
        setError(e.message);
      });
  }, []);

  useEffect(() => {
    fetch();
  }, [fetch]);

  const modCols = [
    { title: "Modality", dataIndex: "modality", key: "mod", render: (v: string) => <Tag>{v}</Tag> },
    { title: "Reviews", dataIndex: "n", key: "n" },
    {
      title: "Avg DLP",
      dataIndex: "avg_dlp",
      key: "avg_dlp",
      render: (v: number) => `${v} mGy·cm`,
    },
    {
      title: "Max DLP",
      dataIndex: "max_dlp",
      key: "max_dlp",
      render: (v: number) => `${v} mGy·cm`,
    },
    {
      title: "ACR DLP Limit",
      dataIndex: "acr_benchmark_dlp",
      key: "bench",
      render: (v: number | null) => (v != null ? `${v} mGy·cm` : "—"),
    },
    {
      title: "Exceedances",
      dataIndex: "dlp_exceedances",
      key: "exc",
      render: (v: number) => <Tag color={v > 0 ? "red" : "green"}>{v}</Tag>,
    },
  ];

  return (
    <PageState error={error} onRetry={fetch} loading={loading}>
      {data && (
        <>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginBottom: 8,
            }}
          >
            <h3 style={{ margin: 0 }}>Dose Metrics by Modality</h3>
            <ExportButton report="dose-tracking" />
          </div>
          <Table
            rowKey="modality"
            columns={modCols}
            dataSource={data.by_modality}
            pagination={false}
            size="small"
            style={{ marginBottom: 16 }}
          />
          {data.exceedances.length > 0 && (
            <>
              <Alert
                type="warning"
                showIcon
                style={{ marginBottom: 8 }}
                title={`${data.exceedances.length} exams exceeded ACR DLP benchmarks`}
              />
              <Table
                rowKey="accession_number"
                dataSource={data.exceedances}
                pagination={{ pageSize: 10 }}
                size="small"
                columns={[
                  { title: "Protocol", dataIndex: "protocol_name", key: "proto" },
                  {
                    title: "Modality",
                    dataIndex: "modality",
                    key: "mod",
                    render: (v: string) => <Tag>{v}</Tag>,
                  },
                  {
                    title: "DLP",
                    dataIndex: "dose_dlp",
                    key: "dlp",
                    render: (v: number) => `${v} mGy·cm`,
                  },
                  {
                    title: "ACR Limit",
                    dataIndex: "acr_benchmark_dlp",
                    key: "bench",
                    render: (v: number) => `${v} mGy·cm`,
                  },
                  { title: "Accession", dataIndex: "accession_number", key: "acc" },
                ]}
              />
            </>
          )}
        </>
      )}
    </PageState>
  );
}

function TechMetricsPanel() {
  const [data, setData] = useState<TechMetric[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetch = useCallback(() => {
    setLoading(true);
    setError(null);
    getTechMetrics()
      .then((d) => {
        setLoading(false);
        setData(d);
      })
      .catch((e: any) => {
        setLoading(false);
        setError(e.message);
      });
  }, []);

  useEffect(() => {
    fetch();
  }, [fetch]);

  const cols = [
    { title: "Technologist", dataIndex: "tech", key: "tech" },
    { title: "Reviewed", dataIndex: "total_reviewed", key: "total" },
    { title: "Passed", dataIndex: "passed", key: "passed" },
    { title: "Failed", dataIndex: "failed", key: "failed" },
    {
      title: "Reject Rate",
      dataIndex: "reject_rate",
      key: "rate",
      render: (v: number) => (
        <span style={{ color: v > 10 ? "#ff4d4f" : v > 5 ? "#fa8c16" : "#52c41a" }}>{v}%</span>
      ),
    },
    {
      title: "Avg DLP",
      dataIndex: "avg_dlp",
      key: "dlp",
      render: (v: number) => (v > 0 ? `${v}` : "—"),
    },
    {
      title: "Protocol Adherence",
      dataIndex: "protocol_adherence_pct",
      key: "adh",
      render: (v: number) => (
        <span style={{ color: v < 80 ? "#ff4d4f" : v < 90 ? "#fa8c16" : "#52c41a" }}>
          {v != null ? `${v}%` : "—"}
        </span>
      ),
    },
  ];

  return (
    <PageState error={error} onRetry={fetch} loading={loading}>
      <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 8 }}>
        <ExportButton report="tech-metrics" />
      </div>
      <Table rowKey="tech" columns={cols} dataSource={data} pagination={false} size="small" />
    </PageState>
  );
}

function ProtocolCompliancePanel() {
  const [data, setData] = useState<ProtocolCompliance[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetch = useCallback(() => {
    setLoading(true);
    setError(null);
    getProtocolCompliance()
      .then((d) => {
        setLoading(false);
        setData(d);
      })
      .catch((e: any) => {
        setLoading(false);
        setError(e.message);
      });
  }, []);

  useEffect(() => {
    fetch();
  }, [fetch]);

  const cols = [
    { title: "Protocol", dataIndex: "protocol_name", key: "name" },
    { title: "Modality", dataIndex: "modality", key: "mod", render: (v: string) => <Tag>{v}</Tag> },
    { title: "Body Part", dataIndex: "body_part", key: "bp", render: (v: string) => v || "—" },
    { title: "Reviews", dataIndex: "total_reviews", key: "total" },
    {
      title: "Compliance %",
      dataIndex: "compliance_pct",
      key: "pct",
      render: (v: number) => (
        <span style={{ color: v < 80 ? "#ff4d4f" : v < 90 ? "#fa8c16" : "#52c41a" }}>
          {v != null ? `${v}%` : "—"}
        </span>
      ),
    },
    {
      title: "Avg DLP",
      dataIndex: "avg_dlp",
      key: "dlp",
      render: (v: number) => (v > 0 ? `${v} mGy·cm` : "—"),
    },
    {
      title: "ACR DLP",
      dataIndex: "acr_benchmark_dlp",
      key: "bench",
      render: (v: number | null) => (v != null ? `${v} mGy·cm` : "—"),
    },
  ];
  return (
    <PageState error={error} onRetry={fetch} loading={loading}>
      <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 8 }}>
        <ExportButton report="protocol-compliance" />
      </div>
      <Table
        rowKey="protocol_id"
        columns={cols}
        dataSource={data}
        pagination={false}
        size="small"
      />
    </PageState>
  );
}

function TrendsPanel() {
  const [data, setData] = useState<TrendPoint[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [granularity, setGranularity] = useState<"daily" | "weekly" | "monthly">("daily");

  const fetch = useCallback(() => {
    setLoading(true);
    setError(null);
    getQATrends(granularity)
      .then((d) => {
        setLoading(false);
        setData(d.data);
      })
      .catch((e: any) => {
        setLoading(false);
        setError(e.message);
      });
  }, [granularity]);

  useEffect(() => {
    fetch();
  }, [fetch]);

  const cols = [
    {
      title: "Period",
      dataIndex: "period",
      key: "period",
      render: (v: string) => new Date(v).toLocaleDateString(),
    },
    { title: "Total", dataIndex: "total", key: "total" },
    { title: "Passed", dataIndex: "passed", key: "passed" },
    { title: "Failed", dataIndex: "failed", key: "failed" },
    {
      title: "Reject Rate",
      dataIndex: "reject_rate",
      key: "rate",
      render: (v: number) => (
        <span style={{ color: v > 10 ? "#ff4d4f" : v > 5 ? "#fa8c16" : "#52c41a" }}>{v}%</span>
      ),
    },
    {
      title: "Avg DLP",
      dataIndex: "avg_dlp",
      key: "dlp",
      render: (v: number) => (v > 0 ? `${v}` : "—"),
    },
  ];

  return (
    <PageState error={error} onRetry={fetch} loading={loading}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 12,
        }}
      >
        <Space>
          <span>Granularity:</span>
          <Select
            value={granularity}
            onChange={setGranularity}
            style={{ width: 120 }}
            options={[
              { value: "daily", label: "Daily" },
              { value: "weekly", label: "Weekly" },
              { value: "monthly", label: "Monthly" },
            ]}
          />
          <ReloadOutlined onClick={fetch} style={{ cursor: "pointer" }} />
        </Space>
        <ExportButton report="trends" />
      </div>
      <Table
        rowKey="period"
        columns={cols}
        dataSource={data}
        pagination={{ pageSize: 30 }}
        size="small"
      />
    </PageState>
  );
}

function QAAnalyticsDashboard() {
  useDocumentTitle("QuantumPACS - QA Analytics");

  return (
    <Content style={{ padding: 16 }}>
      <h2>QA Analytics Dashboard</h2>
      <Tabs
        defaultActiveKey="reject"
        items={[
          { key: "reject", label: "Reject Analysis", children: <RejectAnalysisPanel /> },
          { key: "dose", label: "Dose Tracking", children: <DoseTrackingPanel /> },
          { key: "tech", label: "Tech Metrics", children: <TechMetricsPanel /> },
          { key: "protocol", label: "Protocol Compliance", children: <ProtocolCompliancePanel /> },
          { key: "trends", label: "Trends", children: <TrendsPanel /> },
        ]}
      />
    </Content>
  );
}

export default withSidebar(QAAnalyticsDashboard);
