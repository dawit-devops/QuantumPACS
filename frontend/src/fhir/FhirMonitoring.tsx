import React, { useState, useEffect, useRef } from "react";
import {
  Layout,
  Card,
  Row,
  Col,
  Statistic,
  Table,
  Tag,
  Button,
  DatePicker,
  Select,
  Space,
  Spin,
  Tabs,
  message,
} from "antd";
import { ReloadOutlined, DownloadOutlined } from "@ant-design/icons";
import withRouter from "../withRouter";
import withSidebar from "../common/base";
import { open } from "../helpers";
import { getFhirMetrics, getFhirRecentRequests } from "../api/fhir";
import { PageState } from "../common/PageState";
import "./Fhir.css";

const { Content } = Layout;
const { RangePicker } = DatePicker;

function FhirMonitoring(props: any) {
  let [metrics, setMetrics] = useState<any>(null);
  let [loading, setLoading] = useState(true);
  let [error, setError] = useState<string | null>(null);
  let [period, setPeriod] = useState("24h");
  let [requests, setRequests] = useState<any[]>([]);
  let [requestsLoading, setRequestsLoading] = useState(false);
  let [requestsTotal, setRequestsTotal] = useState(0);
  let [resourceFilter, setResourceFilter] = useState("");
  let [statusFilter, setStatusFilter] = useState("");
  let [limit, setLimit] = useState(50);
  let [offset, setOffset] = useState(0);
  let [autoRefresh, setAutoRefresh] = useState(true);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchMetrics = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getFhirMetrics(period);
      setMetrics(res);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const fetchRequests = async () => {
    setRequestsLoading(true);
    try {
      const res = await getFhirRecentRequests({
        limit,
        offset,
        ...(resourceFilter ? { resource_type: resourceFilter } : {}),
        ...(statusFilter ? { status_min: statusFilter } : {}),
      });
      setRequests(res.requests || []);
      setRequestsTotal(res.total || 0);
    } catch {
    } finally {
      setRequestsLoading(false);
    }
  };

  useEffect(() => {
    fetchMetrics();
    fetchRequests();
  }, [period, offset, resourceFilter, statusFilter]);

  useEffect(() => {
    if (autoRefresh) {
      intervalRef.current = setInterval(() => {
        fetchMetrics();
        fetchRequests();
      }, 30000);
    }
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [autoRefresh, period]);

  const handleExport = () => {
    let q = `fhir/admin/requests?limit=${requestsTotal}&offset=0`;
    if (resourceFilter) q += `&resource_type=${resourceFilter}`;
    if (statusFilter) q += `&status_min=${statusFilter}`;
    open(q)
      .then(() => message.success("CSV export triggered"))
      .catch(() => {});
  };

  const reqColumns = [
    {
      title: "Time",
      dataIndex: "created_at",
      key: "created_at",
      render: (t: string) => new Date(t).toLocaleString(),
    },
    {
      title: "Method",
      dataIndex: "method",
      key: "method",
      render: (t: string) => <Tag>{t}</Tag>,
    },
    { title: "Path", dataIndex: "path", key: "path", ellipsis: true },
    {
      title: "Status",
      dataIndex: "status_code",
      key: "status_code",
      render: (t: number) => {
        const color = t < 300 ? "green" : t < 500 ? "orange" : "red";
        return <Tag color={color}>{t}</Tag>;
      },
    },
    {
      title: "Duration",
      dataIndex: "duration_ms",
      key: "duration_ms",
      render: (t: number) => `${t}ms`,
    },
    { title: "Resource", dataIndex: "resource_type", key: "resource_type" },
    { title: "Caller", dataIndex: "caller", key: "caller" },
  ];

  if (loading && !metrics) {
    return (
      <Content className="fhir-monitoring" style={{ padding: 24 }}>
        <Spin size="large" style={{ display: "block", margin: "80px auto" }} />
      </Content>
    );
  }

  if (error && !metrics) {
    return (
      <Content className="fhir-monitoring" style={{ padding: 24 }}>
        <PageState error={error} onRetry={fetchMetrics} />
      </Content>
    );
  }

  return (
    <Content className="fhir-monitoring" style={{ padding: 24 }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 16,
        }}
      >
        <Space>
          <span style={{ fontWeight: 600, fontSize: 16 }}>FHIR Monitoring</span>
          <Select
            value={period}
            onChange={(v) => {
              setPeriod(v);
              setOffset(0);
            }}
            style={{ width: 120 }}
            options={[
              { value: "1h", label: "Last Hour" },
              { value: "24h", label: "Last 24 Hours" },
              { value: "7d", label: "Last 7 Days" },
              { value: "30d", label: "Last 30 Days" },
            ]}
          />
        </Space>
        <Space>
          <Button
            icon={<ReloadOutlined />}
            onClick={() => {
              fetchMetrics();
              fetchRequests();
            }}
          >
            Refresh
          </Button>
          <Button icon={<DownloadOutlined />} onClick={handleExport}>
            Export CSV
          </Button>
        </Space>
      </div>

      {/* Summary Cards */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="Total Requests"
              value={metrics?.total_requests || 0}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="Error Rate"
              value={metrics?.error_rate || 0}
              suffix="%"
              precision={2}
              valueStyle={{
                color: (metrics?.error_rate || 0) > 5 ? "red" : "green",
              }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="p50 Latency"
              value={metrics?.latency?.p50 || 0}
              suffix="ms"
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="p99 Latency"
              value={metrics?.latency?.p99 || 0}
              suffix="ms"
              valueStyle={{
                color: (metrics?.latency?.p99 || 0) > 1000 ? "red" : undefined,
              }}
            />
          </Card>
        </Col>
      </Row>

      {/* Volume by Resource */}
      <Card title="Request Volume" size="small" style={{ marginBottom: 16 }}>
        {metrics?.volume?.length > 0 ? (
          <Table<{ resource_type: string; method: string; count: number }>
            dataSource={metrics.volume}
            columns={[
              {
                title: "Resource Type",
                dataIndex: "resource_type",
                key: "resource_type",
                render: (t: string) => t || "Unknown",
              },
              { title: "Method", dataIndex: "method", key: "method" },
              { title: "Count", dataIndex: "count", key: "count" },
            ]}
            rowKey={(r, i) => `${r.resource_type}-${r.method}-${i}`}
            pagination={false}
            size="small"
          />
        ) : (
          <div
            style={{
              color: "var(--text-secondary)",
              padding: 24,
              textAlign: "center",
            }}
          >
            No FHIR requests in this period. Advertise your FHIR endpoint to EHR
            systems to get started.
          </div>
        )}
      </Card>

      {/* Status Codes */}
      <Card title="Status Codes" size="small" style={{ marginBottom: 16 }}>
        {metrics?.status_codes?.length > 0 ? (
          <Table
            dataSource={metrics.status_codes}
            columns={[
              {
                title: "Status Family",
                dataIndex: "status_family",
                key: "status_family",
                render: (t: number) => {
                  const color = t < 300 ? "green" : t < 500 ? "orange" : "red";
                  return <Tag color={color}>{t}xx</Tag>;
                },
              },
              { title: "Count", dataIndex: "count", key: "count" },
            ]}
            rowKey="status_family"
            pagination={false}
            size="small"
          />
        ) : (
          <div
            style={{
              color: "var(--text-secondary)",
              padding: 24,
              textAlign: "center",
            }}
          >
            No data
          </div>
        )}
      </Card>

      {/* Recent Requests */}
      <Card
        title="Recent Requests"
        size="small"
        extra={
          <Space>
            <Select
              value={resourceFilter}
              onChange={setResourceFilter}
              allowClear
              placeholder="Resource Type"
              style={{ width: 150 }}
              options={[
                { value: "", label: "All" },
                { value: "Patient", label: "Patient" },
                { value: "ImagingStudy", label: "ImagingStudy" },
                { value: "DocumentReference", label: "DocumentReference" },
              ]}
            />
            <Select
              value={statusFilter}
              onChange={setStatusFilter}
              allowClear
              placeholder="Status"
              style={{ width: 120 }}
              options={[
                { value: "", label: "All" },
                { value: "400", label: "4xx Errors" },
                { value: "500", label: "5xx Errors" },
              ]}
            />
            <span style={{ color: "var(--text-secondary)", fontSize: 12 }}>
              {requestsTotal} total
            </span>
          </Space>
        }
      >
        <Table
          dataSource={requests}
          columns={reqColumns}
          rowKey="id"
          loading={requestsLoading}
          size="small"
          pagination={{
            current: offset / limit + 1,
            pageSize: limit,
            total: requestsTotal,
            onChange: (page) => setOffset((page - 1) * limit),
            showSizeChanger: false,
          }}
          locale={{ emptyText: "No FHIR requests yet." }}
        />
      </Card>
    </Content>
  );
}

export default withRouter(withSidebar(FhirMonitoring));
