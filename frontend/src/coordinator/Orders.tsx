import { useDocumentTitle } from "../hooks";
import React, { useState, useEffect, useCallback, useMemo } from "react";
import {
  Layout,
  Table,
  Tag,
  Button,
  Select,
  Input,
  Alert,
  Spin,
  Typography,
} from "antd";
import { CalendarOutlined, ReloadOutlined } from "@ant-design/icons";
import { useNavigate } from "react-router";
import withSidebar from "../common/base";
import { request } from "../helpers";
import { mrnLast4 } from "../radiologist/patientLabel";
import "../radiologist/ReadingWorklist.css";

const { Text } = Typography;
const Content = Layout.Content;

export interface OrderRow {
  id: string;
  visit_id: string;
  patient_id: string;
  patient_db_id?: number | string | null;
  patient_name?: string;
  requested_procedure: string;
  indication?: string;
  urgency: string;
  order_status: string;
  referring_physician?: string;
  created_at?: string;
  wl_status?: string | null;
  scheduled_date?: string | null;
  modality?: string | null;
  exam_status?: string | null;
  exam_id?: string | null;
  report_status?: string | null;
  report_id?: string | null;
}

// Lifecycle derivation (care-coordinator review P0-2): visit_orders carries no
// FK to the imaging side, so the page joins the patient's latest schedule/exam/
// report (best-effort) and derives the coordination state from it.
export function derivedOrderStatus(o: OrderRow): string {
  if (o.order_status === "cancelled") return "cancelled";
  if (o.report_status && o.report_status !== "draft") return "reported";
  if (o.report_status === "draft") return "in progress";
  if (o.exam_status === "completed") return "performed";
  if (o.exam_status === "in_progress" || o.exam_status === "ready") {
    return "in progress";
  }
  if (o.wl_status === "scheduled") return "scheduled";
  return "requested";
}

const STATUS_COLORS: Record<string, string> = {
  requested: "blue",
  scheduled: "cyan",
  "in progress": "gold",
  performed: "default",
  reported: "green",
  cancelled: "red",
};

// Stuck-work signal: >24h amber, >72h red (design 04 P0-2).
export function ageDays(o: OrderRow): number | null {
  if (!o.created_at) return null;
  const created = new Date(o.created_at).getTime();
  if (Number.isNaN(created)) return null;
  return (Date.now() - created) / 86_400_000;
}

function ageTag(o: OrderRow) {
  const days = ageDays(o);
  if (days === null) return <Text type="secondary">—</Text>;
  const color = days > 3 ? "red" : days > 1 ? "orange" : undefined;
  const label =
    days < 1 ? `${Math.round(days * 24)}h` : `${Math.round(days)}d`;
  return <Tag color={color}>{label}</Tag>;
}

function Orders() {
  useDocumentTitle("QuantumPACS - Orders");

  const navigate = useNavigate();
  const [rows, setRows] = useState<OrderRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string | undefined>();
  const [modalityFilter, setModalityFilter] = useState<string | undefined>();
  const [patientFilter, setPatientFilter] = useState("");

  const load = useCallback(async () => {
    setError(null);
    try {
      const res = await request<{ data: OrderRow[] }>("orders");
      setRows(Array.isArray(res.data) ? res.data : []);
    } catch (e: any) {
      setError(e.message);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const modals = useMemo(() => {
    const s = new Set<string>();
    (rows ?? []).forEach((r) => r.modality && s.add(r.modality));
    return [...s].sort();
  }, [rows]);

  const summary = useMemo(() => {
    const open = (rows ?? []).filter(
      (r) => derivedOrderStatus(r) !== "reported" && derivedOrderStatus(r) !== "cancelled",
    );
    const waiting = open.filter((r) => (ageDays(r) ?? 0) > 1);
    const reportedToday = (rows ?? []).filter((r) => {
      if (derivedOrderStatus(r) !== "reported" || !r.created_at) return false;
      const d = new Date(r.created_at);
      const today = new Date();
      return (
        d.getDate() === today.getDate() &&
        d.getMonth() === today.getMonth() &&
        d.getFullYear() === today.getFullYear()
      );
    }).length;
    return { open: open.length, waiting: waiting.length, reportedToday };
  }, [rows]);

  const filtered = useMemo(() => {
    const q = patientFilter.trim().toLowerCase();
    return (rows ?? []).filter((r) => {
      if (statusFilter && derivedOrderStatus(r) !== statusFilter) return false;
      if (modalityFilter && r.modality !== modalityFilter) return false;
      if (q) {
        const hay = `${r.patient_name ?? ""} ${r.patient_id} ${r.requested_procedure}`.toLowerCase();
        if (!hay.includes(q)) return false;
      }
      return true;
    });
  }, [rows, statusFilter, modalityFilter, patientFilter]);

  return (
    <Content className="reading-wl" style={{ padding: 24 }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          marginBottom: 16,
        }}
      >
        <div>
          <h2 style={{ margin: 0 }}>Orders</h2>
          <Text type="secondary">
            Imaging requests across the facility — from request to report.
          </Text>
        </div>
        <Button icon={<ReloadOutlined />} onClick={load}>
          Refresh
        </Button>
      </div>

      {rows && (
        <Alert
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
          title={
            <span>
              <Text strong>{summary.open}</Text> open ·{" "}
              <Text strong>{summary.waiting}</Text> waiting &gt;24h ·{" "}
              <Text strong>{summary.reportedToday}</Text> reported today
            </span>
          }
        />
      )}

      <div className="reading-wl-filters">
        <Select
          id="orders-status-filter"
          aria-label="Order status"
          allowClear
          placeholder="Status"
          style={{ width: 150 }}
          value={statusFilter}
          onChange={setStatusFilter}
          options={[
            "requested",
            "scheduled",
            "in progress",
            "performed",
            "reported",
            "cancelled",
          ].map((s) => ({ value: s, label: s }))}
        />
        <Select
          id="orders-modality-filter"
          aria-label="Modality"
          allowClear
          placeholder="Modality"
          style={{ width: 140 }}
          value={modalityFilter}
          onChange={setModalityFilter}
          options={modals.map((m) => ({ value: m, label: m }))}
        />
        <Input.Search
          id="orders-patient-filter"
          aria-label="Search patient"
          placeholder="Search patient or procedure"
          allowClear
          style={{ width: 260 }}
          onChange={(e) => setPatientFilter(e.target.value)}
        />
      </div>

      <Spin spinning={rows === null}>
        {error && (
          <Alert
            type="error"
            showIcon
            style={{ marginBottom: 16 }}
            title="Failed to load orders"
            description={error}
          />
        )}
        <Table<OrderRow>
          rowKey="id"
          loading={rows === null}
          dataSource={filtered}
          pagination={{ pageSize: 20 }}
          onRow={(r) => ({
            // The patient route key is the patients table id, not the MRN.
            onClick: () => navigate(`/patients/${r.patient_db_id ?? r.patient_id}`),
            style: { cursor: "pointer" },
          })}
          locale={{
            emptyText: rows?.length === 0 ? (
              <div style={{ padding: 24 }}>
                <p style={{ marginBottom: 8 }}>No orders yet.</p>
                <Text type="secondary" style={{ fontSize: 13 }}>
                  New imaging requests will appear here. Book one from the
                  Schedule Board.
                </Text>
                <div style={{ marginTop: 12 }}>
                  <Button
                    icon={<CalendarOutlined />}
                    onClick={() => navigate("/schedule-board")}
                  >
                    Open Schedule Board
                  </Button>
                </div>
              </div>
            ) : (
              "No orders match your filters"
            ),
          }}
          columns={[
            {
              title: "Status",
              dataIndex: "status",
              width: 130,
              render: (_v, r) => {
                const s = derivedOrderStatus(r);
                return <Tag color={STATUS_COLORS[s] ?? "default"}>{s}</Tag>;
              },
            },
            {
              title: "Patient",
              dataIndex: "patient_name",
              render: (_v, r) => (
                <span>
                  <Text>{r.patient_name || r.patient_id}</Text>{" "}
                  <Text type="secondary" style={{ fontSize: 11 }}>
                    {r.patient_name ? mrnLast4(r.patient_id) : ""}
                  </Text>
                </span>
              ),
            },
            {
              title: "Procedure",
              dataIndex: "requested_procedure",
              render: (v: string) => v || "—",
            },
            {
              title: "Modality",
              dataIndex: "modality",
              width: 90,
              render: (v?: string) =>
                v ? <Tag>{v}</Tag> : <Text type="secondary">—</Text>,
            },
            {
              title: "Requested",
              dataIndex: "created_at",
              width: 110,
              render: (v?: string) =>
                v ? (
                  <Text style={{ fontSize: 12 }}>
                    {new Date(v).toLocaleDateString()}
                  </Text>
                ) : (
                  <Text type="secondary">—</Text>
                ),
            },
            {
              title: "Age",
              dataIndex: "age",
              width: 70,
              render: (_v, r) => ageTag(r),
            },
            {
              title: "Report",
              dataIndex: "report_status",
              width: 110,
              render: (_v, r) =>
                r.report_id ? (
                  <Button
                    type="link"
                    size="small"
                    onClick={(e) => {
                      e.stopPropagation();
                      navigate(`/reading/${r.exam_id}`);
                    }}
                  >
                    {r.report_status}
                  </Button>
                ) : (
                  <Text type="secondary">—</Text>
                ),
            },
          ]}
        />
      </Spin>
    </Content>
  );
}

export default withSidebar(Orders);
