import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  App,
  Layout,
  Table,
  Tag,
  Button,
  Space,
  Select,
  Input,
  DatePicker,
  Drawer,
  Timeline,
  Statistic,
  Row,
  Col,
} from "antd";
import { ReloadOutlined } from "@ant-design/icons";
import { useDocumentTitle } from "../hooks";
import withSidebar from "../common/base";
import { PageState } from "../common/PageState";
import {
  listClaims,
  getClaimHistory,
  type ClaimRow,
  type ClaimEvent,
} from "../api/billing-ris";
import "./BillingQueue.css";

const Content = Layout.Content;

// B-06: claim status lifecycle colors (Draft → Submitted → Acknowledged →
// Paid/Denied; RESUBMITTED re-enters at Submitted).
const STATUS_COLORS: Record<string, string> = {
  DRAFT: "default",
  SUBMITTED: "blue",
  ACKNOWLEDGED: "cyan",
  PAID: "green",
  DENIED: "red",
  RESUBMITTED: "gold",
};

function ClaimsStatus() {
  const { message } = App.useApp();
  useDocumentTitle("QuantumPACS - Claims");
  const [rows, setRows] = useState<ClaimRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [payerFilter, setPayerFilter] = useState("");
  const [dateRange, setDateRange] = useState<any>(null);
  const [historyFor, setHistoryFor] = useState<ClaimRow | null>(null);
  const [history, setHistory] = useState<ClaimEvent[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);

  const fetchRows = useCallback(() => {
    setLoading(true);
    setError(null);
    const q: Record<string, string> = {};
    if (statusFilter) q.status = statusFilter;
    if (payerFilter) q.payer = payerFilter;
    if (dateRange?.[0]) q.date_from = dateRange[0].format("YYYY-MM-DD");
    if (dateRange?.[1]) q.date_to = dateRange[1].format("YYYY-MM-DD");
    listClaims(q)
      .then((data) => setRows(data))
      .catch((e: any) => {
        setError(e.message || "Failed to load claims");
        message.error(e.message || "Failed to load claims");
      })
      .finally(() => setLoading(false));
  }, [statusFilter, payerFilter, dateRange, message]);

  useEffect(() => {
    fetchRows();
  }, [fetchRows]);

  const openHistory = useCallback(async (row: ClaimRow) => {
    setHistoryFor(row);
    setHistoryLoading(true);
    try {
      setHistory(await getClaimHistory(row.id));
    } catch {
      setHistory([]);
    } finally {
      setHistoryLoading(false);
    }
  }, []);

  const counts = useMemo(() => {
    const c: Record<string, number> = {};
    for (const r of rows) c[r.status] = (c[r.status] || 0) + 1;
    return c;
  }, [rows]);

  const columns = [
    { title: "Claim #", dataIndex: "claim_number", key: "claim_number" },
    {
      title: "Status",
      dataIndex: "status",
      key: "status",
      render: (s: string) => (
        <Tag color={STATUS_COLORS[s] || "default"}>{s}</Tag>
      ),
    },
    { title: "Payer", dataIndex: "payer_name", key: "payer_name" },
    { title: "Patient", dataIndex: "patient_name", key: "patient_name" },
    {
      title: "Accession",
      dataIndex: "accession_number",
      key: "accession_number",
    },
    { title: "CPT", dataIndex: "cpt_code", key: "cpt_code" },
    {
      title: "Amount",
      dataIndex: "charge_amount",
      key: "charge_amount",
      render: (v: number) =>
        typeof v === "number" ? `$${v.toFixed(2)}` : "—",
    },
    { title: "Reworks", dataIndex: "correction_count", key: "correction_count" },
    {
      title: "",
      key: "actions",
      render: (_: any, record: ClaimRow) => (
        <Button size="small" onClick={() => openHistory(record)}>
          History
        </Button>
      ),
    },
  ];

  return (
    <Content style={{ padding: 24 }} role="main">
      <div className="billing-queue-header">
        <h2>Claims</h2>
        <Button icon={<ReloadOutlined />} onClick={fetchRows}>
          Refresh
        </Button>
      </div>

      <Row gutter={16} style={{ marginBottom: 16 }}>
        {["DRAFT", "SUBMITTED", "ACKNOWLEDGED", "PAID", "DENIED"].map((s) => (
          <Col key={s} span={4}>
            <Statistic
              title={s}
              value={counts[s] || 0}
              valueStyle={{ color: counts[s] ? undefined : "#999" }}
            />
          </Col>
        ))}
      </Row>

      <div className="billing-queue-filters" style={{ marginBottom: 16 }}>
        <Space size="small" wrap>
          <Select
            aria-label="Filter by claim status"
            allowClear
            placeholder="Status"
            style={{ width: 160 }}
            value={statusFilter || undefined}
            onChange={(v: string) => setStatusFilter(v || "")}
            options={Object.keys(STATUS_COLORS).map((s) => ({
              value: s,
              label: s,
            }))}
          />
          <Input.Search
            aria-label="Filter by payer"
            placeholder="Payer…"
            allowClear
            style={{ width: 200 }}
            onSearch={(v: string) => setPayerFilter(v)}
          />
          <DatePicker.RangePicker
            onChange={(v: any) => setDateRange(v)}
            aria-label="Date range"
          />
        </Space>
      </div>

      <PageState
        error={error}
        onRetry={fetchRows}
        empty={!loading && !error && rows.length === 0}
        emptyMessage="No claims match the filters"
      >
        <Table
          rowKey="id"
          size="small"
          loading={loading}
          dataSource={rows}
          columns={columns}
          pagination={{ pageSize: 20, showSizeChanger: true }}
        />
      </PageState>

      <Drawer
        title={`History — ${historyFor?.claim_number || ""}`}
        open={historyFor !== null}
        onClose={() => setHistoryFor(null)}
        size={420}
      >
        <PageState loading={historyLoading}>
          <Timeline
            items={history.map((ev) => ({
              children: (
                <>
                  <div>{ev.event_type}</div>
                  <div style={{ fontSize: 12 }}>{ev.note}</div>
                </>
              ),
            }))}
          />
        </PageState>
      </Drawer>
    </Content>
  );
}

export default withSidebar(ClaimsStatus);
