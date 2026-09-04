import React, { useCallback, useEffect, useState } from "react";
import {
  Card,
  Layout,
  Select,
  Space,
  Table,
  Tabs,
  Tag,
  Typography,
} from "antd";
import {
  ApiOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ClockCircleOutlined,
} from "@ant-design/icons";
import withSidebar from "../common/base";
import { useDocumentTitle } from "../hooks";
import PageHeader from "../common/PageHeader";
import { PageState } from "../common/PageState";
import StatCard from "../common/StatCard";
import ExceptionQueue from "./ExceptionQueue";
import {
  getRisInterfaceMetrics,
  listRisInterfaceMessages,
  listRisInterfaces,
  type RisHl7MessageRow,
  type RisInterface,
  type RisMetrics,
} from "../api/ris";
import "./InterfaceDashboard.css";

const { Content } = Layout;
const { Text } = Typography;

const PERIODS = [
  { value: "1h", label: "Last hour" },
  { value: "24h", label: "Last 24 hours" },
  { value: "7d", label: "Last 7 days" },
  { value: "30d", label: "Last 30 days" },
];

const TYPE_COLORS: Record<string, string> = {
  HL7_ADT: "blue",
  HL7_ORM: "geekblue",
  HL7_ORU: "cyan",
  DICOM_MWL: "purple",
  DICOM_MPPS: "purple",
  FHIR: "green",
};

// S3-16 Interface health dashboard (RIS-UI-37) — per-interface message
// counts, error rates, latency and last-message times from the S3-15 API,
// plus the exception queue with the retry action. Reads ris_* tables.
function InterfaceDashboard() {
  useDocumentTitle("QuantumPACS - Interface Health");
  const [interfaces, setInterfaces] = useState<RisInterface[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<RisInterface | null>(null);
  const [period, setPeriod] = useState("24h");
  const [metrics, setMetrics] = useState<RisMetrics | null>(null);
  const [messages, setMessages] = useState<RisHl7MessageRow[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [msgLoading, setMsgLoading] = useState(false);

  const fetchInterfaces = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const list = await listRisInterfaces();
      setInterfaces(list);
      setSelected((prev) => {
        if (prev && list.some((i) => i.id === prev.id)) return prev;
        return list[0] ?? null;
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load interfaces");
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchMetrics = useCallback(async (id: string, p: string) => {
    try {
      setMetrics(await getRisInterfaceMetrics(id, p));
    } catch {
      setMetrics(null);
    }
  }, []);

  const fetchMessages = useCallback(async (id: string, pg: number) => {
    setMsgLoading(true);
    try {
      const data = await listRisInterfaceMessages(id, {
        limit: 20,
        offset: (pg - 1) * 20,
      });
      setMessages(data.messages);
      setTotal(data.total);
    } catch {
      setMessages([]);
      setTotal(0);
    } finally {
      setMsgLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchInterfaces();
  }, [fetchInterfaces]);

  useEffect(() => {
    if (selected) {
      void fetchMetrics(selected.id, period);
      void fetchMessages(selected.id, 1);
    }
  }, [selected, period, fetchMetrics, fetchMessages]);

  const statusSummary = (iface: RisInterface) => {
    const counts = iface.status_counts ?? {};
    const failed = counts.FAILED ?? 0;
    const processed = counts.PROCESSED ?? 0;
    return {
      failed,
      processed,
      total: iface.message_count ?? 0,
    };
  };

  const interfaceColumns = [
    {
      title: "Interface",
      dataIndex: "name",
      render: (v: string, row: RisInterface) => (
        <Space>
          <ApiOutlined />
          <Text strong>{v}</Text>
          <Tag color={TYPE_COLORS[row.interface_type] ?? "default"}>
            {row.interface_type}
          </Tag>
        </Space>
      ),
    },
    {
      title: "Protocol",
      dataIndex: "protocol",
      width: 110,
      render: (v: string) => <Tag>{v}</Tag>,
    },
    {
      title: "Status",
      key: "status",
      width: 110,
      render: (_: unknown, row: RisInterface) =>
        row.is_active ? (
          <Tag color="green">Active</Tag>
        ) : (
          <Tag color="default">Inactive</Tag>
        ),
    },
    {
      title: "Messages",
      key: "total",
      width: 100,
      render: (_: unknown, row: RisInterface) => statusSummary(row).total,
    },
    {
      title: "Processed",
      key: "processed",
      width: 110,
      render: (_: unknown, row: RisInterface) => statusSummary(row).processed,
    },
    {
      title: "Failed",
      key: "failed",
      width: 90,
      render: (_: unknown, row: RisInterface) =>
        statusSummary(row).failed > 0 ? (
          <Text type="danger">{statusSummary(row).failed}</Text>
        ) : (
          statusSummary(row).failed
        ),
    },
    {
      title: "Last message",
      dataIndex: "last_message_at",
      width: 180,
      render: (v: string | null) => (v ? new Date(v).toLocaleString() : "—"),
    },
  ];

  const messageColumns = [
    {
      title: "Received",
      dataIndex: "created_at",
      width: 180,
      render: (v: string | null) => (v ? new Date(v).toLocaleString() : "—"),
    },
    {
      title: "Type",
      key: "type",
      render: (_: unknown, row: RisHl7MessageRow) =>
        `${row.message_type}^${row.trigger_event}`,
    },
    { title: "Control ID", dataIndex: "control_id" },
    {
      title: "Status",
      dataIndex: "status",
      width: 110,
      render: (v: string) => (
        <Tag
          color={
            v === "PROCESSED"
              ? "green"
              : v === "FAILED"
                ? "red"
                : v === "RETRYING"
                  ? "orange"
                  : "default"
          }
        >
          {v}
        </Tag>
      ),
    },
    {
      title: "Error",
      dataIndex: "error_message",
      render: (v: string | null) =>
        v ? (
          <Text type="danger" ellipsis={{ tooltip: v }}>
            {v}
          </Text>
        ) : (
          "—"
        ),
    },
  ];

  if (error) {
    return <PageState error={error} />;
  }

  const summary = selected ? statusSummary(selected) : null;
  const failedRate =
    summary && summary.total > 0
      ? Math.round((summary.failed / summary.total) * 1000) / 10
      : 0;

  const interfacesTab = (
    <Space vertical size="large" style={{ width: "100%" }}>
      <Table
        rowKey="id"
        loading={loading}
        columns={interfaceColumns}
        dataSource={interfaces}
        pagination={false}
        size="small"
        onRow={(row) => ({
          onClick: () => setSelected(row),
          className: "qp-interface-row",
          style: { cursor: "pointer" },
        })}
      />
      {selected && (
        <>
          <Space size="large" wrap>
            <StatCard
              label="Total messages"
              value={summary?.total ?? 0}
              icon={<ClockCircleOutlined />}
            />
            <StatCard
              label="Processed"
              value={summary?.processed ?? 0}
              icon={<CheckCircleOutlined />}
              tone="ok"
            />
            <StatCard
              label="Failed"
              value={summary?.failed ?? 0}
              icon={<CloseCircleOutlined />}
              tone={failedRate > 0 ? "error" : "ok"}
              hint={
                failedRate > 0 ? `${failedRate}% of all messages` : undefined
              }
            />
            <StatCard
              label="Last message"
              value={
                selected.last_message_at
                  ? new Date(selected.last_message_at).toLocaleString()
                  : "—"
              }
              icon={<ClockCircleOutlined />}
            />
          </Space>
          <Card
            size="small"
            title={`${selected.name} — metrics`}
            extra={
              <Select
                size="small"
                value={period}
                options={PERIODS}
                onChange={(v) => {
                  setPeriod(v);
                  setPage(1);
                }}
              />
            }
          >
            <Space size="large" wrap>
              <StatCard
                label="Period total"
                value={Number(metrics?.total ?? 0)}
              />
              <StatCard
                label="Failed"
                value={Number(metrics?.failed ?? 0)}
                tone={Number(metrics?.failed ?? 0) > 0 ? "error" : "ok"}
              />
              <StatCard
                label="Avg latency"
                value={
                  metrics?.avg_latency_ms !== undefined
                    ? `${metrics.avg_latency_ms} ms`
                    : "—"
                }
              />
            </Space>
            <Table
              rowKey="id"
              size="small"
              loading={msgLoading}
              columns={messageColumns}
              dataSource={messages}
              pagination={{
                current: page,
                pageSize: 20,
                total,
                onChange: (p) => {
                  setPage(p);
                  void fetchMessages(selected.id, p);
                },
                showSizeChanger: false,
              }}
            />
          </Card>
        </>
      )}
    </Space>
  );

  return (
    <Layout>
      <Content style={{ padding: 24 }}>
        <PageHeader
          title="Interface Health"
          description="Per-interface message counts, failures, latency and the exception queue"
        />
        <Tabs
          items={[
            { key: "interfaces", label: "Interfaces", children: interfacesTab },
            {
              key: "exceptions",
              label: "Exception Queue",
              children: <ExceptionQueue />,
            },
          ]}
        />
      </Content>
    </Layout>
  );
}

export default withSidebar(InterfaceDashboard);
