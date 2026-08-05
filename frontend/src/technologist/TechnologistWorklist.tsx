import { useDocumentTitle } from "../hooks";
import React, { useState, useEffect, useCallback } from "react";
import { Layout, Table, Tag, Button, Select, Input, Alert, Spin } from "antd";
import { ThunderboltOutlined, ReloadOutlined } from "@ant-design/icons";
import { useNavigate } from "react-router";
import withSidebar from "../common/base";
import { request } from "../helpers";
import "./TechnologistWorklist.css";

const Content = Layout.Content;

const STATUS_COLORS: Record<string, string> = {
  ready: "blue",
  in_progress: "gold",
  completed: "green",
  cancelled: "red",
};

const PRIORITY_LABEL: Record<string, string> = {
  stat: "STAT",
  urgent: "Urgent",
  routine: "Routine",
};

const PRIORITY_COLORS: Record<string, string> = {
  stat: "red",
  urgent: "orange",
  routine: "default",
};

// Auto-refresh cadence per NFR-R06-06 (≤30s staleness). The exam list refetches
// on this interval so new R04 assignments appear without a manual reload.
const REFRESH_MS = 30000;

function TechnologistWorklist() {
  useDocumentTitle("QuantumPACS - Technologist Worklist");

  const navigate = useNavigate();
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string | undefined>();
  const [modalityFilter, setModalityFilter] = useState<string | undefined>();
  const [search, setSearch] = useState("");

  const fetchExams = useCallback(() => {
    setLoading(true);
    setError(null);
    const query: Record<string, string> = {};
    if (statusFilter) query.status = statusFilter;
    if (modalityFilter) query.modality = modalityFilter;
    if (search) query.search = search;
    request("exams", { query })
      .then((res: any) => {
        setLoading(false);
        setData(Array.isArray(res.data) ? res.data : []);
      })
      .catch((e: any) => {
        setLoading(false);
        setError(e.message);
      });
  }, [statusFilter, modalityFilter, search]);

  useEffect(() => {
    fetchExams();
    const timer = setInterval(fetchExams, REFRESH_MS);
    return () => clearInterval(timer);
  }, [fetchExams]);

  const modalities = [...new Set(data.map((e) => e.modality).filter(Boolean))];

  const columns = [
    {
      title: "Priority",
      dataIndex: "priority",
      key: "priority",
      width: 90,
      sorter: (a: any, b: any) => {
        const rank = (p: string) => (p === "stat" ? 0 : p === "urgent" ? 1 : 2);
        return rank(a.priority) - rank(b.priority);
      },
      defaultSortOrder: "ascend" as const,
      render: (p: string) =>
        p ? (
          <Tag
            color={PRIORITY_COLORS[p]}
            className={p === "stat" ? "stat-tag" : ""}
          >
            {PRIORITY_LABEL[p]}
          </Tag>
        ) : (
          <Tag>Routine</Tag>
        ),
    },
    {
      title: "Accession",
      dataIndex: "accession_number",
      key: "accession_number",
      width: 120,
      render: (v: string) => v || "—",
    },
    {
      title: "Patient",
      key: "patient",
      render: (_: unknown, r: any) => r.patient_name || r.patient_id || "—",
    },
    { title: "Modality", dataIndex: "modality", key: "modality", width: 90 },
    { title: "Protocol", dataIndex: "protocol_name", key: "protocol_name" },
    {
      title: "Status",
      dataIndex: "status",
      key: "status",
      width: 120,
      render: (s: string) => (
        <Tag color={STATUS_COLORS[s] || "default"}>{s || "ready"}</Tag>
      ),
    },
    {
      title: "",
      key: "action",
      width: 120,
      render: (_: unknown, r: any) => (
        <Button
          size="small"
          type="primary"
          ghost
          onClick={() => navigate(`/exams/${r.id}`)}
        >
          Open Exam
        </Button>
      ),
    },
  ];

  return (
    <Content style={{ padding: 24 }} role="main" id="main-content">
      <div className="tech-wl-header">
        <div>
          <h2 style={{ margin: 0 }}>
            <ThunderboltOutlined /> Technologist Worklist
          </h2>
          <span className="tech-wl-subtitle">
            Your assigned exams — auto-refreshes every 30s
          </span>
        </div>
        <Button icon={<ReloadOutlined />} onClick={fetchExams}>
          Refresh
        </Button>
      </div>

      <div className="tech-wl-filters">
        <Select
          allowClear
          placeholder="Status"
          style={{ width: 150 }}
          value={statusFilter}
          onChange={setStatusFilter}
          options={["ready", "in_progress", "completed", "cancelled"].map(
            (s) => ({
              value: s,
              label: s,
            }),
          )}
        />
        <Select
          allowClear
          placeholder="Modality"
          style={{ width: 150 }}
          value={modalityFilter}
          onChange={setModalityFilter}
          options={[
            ...new Set([
              ...modalities,
              "CT",
              "MR",
              "PET",
              "DX",
              "US",
              "MG",
              "FL",
            ]),
          ]
            .filter(Boolean)
            .map((m) => ({ value: m, label: m }))}
        />
        <Input.Search
          placeholder="Search patient / accession"
          allowClear
          style={{ width: 260 }}
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          onSearch={() => fetchExams()}
        />
      </div>

      {error && (
        <Alert
          type="error"
          message="Failed to load worklist"
          description={error}
          showIcon
          style={{ marginBottom: 16 }}
        />
      )}

      {loading && !data.length ? (
        <div className="tech-wl-loading">
          <Spin />
        </div>
      ) : (
        <Table
          rowKey="id"
          columns={columns}
          dataSource={data}
          pagination={{ pageSize: 20, showSizeChanger: false }}
          onRow={(r) => ({
            onDoubleClick: () => navigate(`/exams/${r.id}`),
          })}
          scroll={{ x: 800 }}
          locale={{
            emptyText:
              "No exams assigned. New assignments appear here automatically.",
          }}
        />
      )}
    </Content>
  );
}

export default withSidebar(TechnologistWorklist);
