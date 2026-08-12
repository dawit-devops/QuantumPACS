import { useDocumentTitle } from "../hooks";
import React, { useState, useEffect, useCallback } from "react";
import {
  Layout,
  Table,
  Tag,
  Button,
  Select,
  Input,
  Alert,
  Badge,
  Space,
} from "antd";
import { ReloadOutlined, FileSearchOutlined } from "@ant-design/icons";
import { useNavigate } from "react-router";
import withSidebar from "../common/base";
import { request } from "../helpers";
import "./QAQueue.css";

const Content = Layout.Content;

const PRIORITY_COLORS: Record<string, string> = {
  stat: "red",
  urgent: "orange",
  routine: "default",
};

const QA_STATUS_COLORS: Record<string, string> = {
  pending: "default",
  pass: "green",
  fail: "red",
  skipped: "gold",
};

// NFR-R05-01: queue auto-refresh ≤ 1 min.
const REFRESH_MS = 30000;

function QAQueue() {
  useDocumentTitle("QuantumPACS - QA Review Queue");
  const navigate = useNavigate();
  const [data, setData] = useState<any[]>([]);
  const [meta, setMeta] = useState<any>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [modalityFilter, setModalityFilter] = useState<string | undefined>();
  const [statusFilter, setStatusFilter] = useState<string | undefined>();
  const [priorityFilter, setPriorityFilter] = useState<string | undefined>();
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);

  const fetchQueue = useCallback(() => {
    setLoading(true);
    setError(null);
    const query: Record<string, string> = { page: String(page) };
    if (modalityFilter) query.modality = modalityFilter;
    if (statusFilter) query.status = statusFilter;
    if (priorityFilter) query.priority = priorityFilter;
    if (search) query.search = search;
    request("qa/queue", { query })
      .then((res: any) => {
        setLoading(false);
        setData(Array.isArray(res.data) ? res.data : []);
        setMeta(res.meta || {});
      })
      .catch((e: any) => {
        setLoading(false);
        setError(e.message);
      });
  }, [page, modalityFilter, statusFilter, priorityFilter, search]);

  useEffect(() => {
    fetchQueue();
    const t = setInterval(fetchQueue, REFRESH_MS);
    return () => clearInterval(t);
  }, [fetchQueue]);

  const modalities = Array.from(
    new Set(data.map((d) => d.modality).filter(Boolean)),
  ).sort();

  const columns = [
    {
      title: "Accession",
      dataIndex: "accession_number",
      key: "accession",
      render: (v: string, row: any) => (
        <a
          onClick={(e) => {
            e.preventDefault();
            navigate(`/qa/review/${row.exam_id}`);
          }}
        >
          {v || "-"}
        </a>
      ),
    },
    {
      title: "Patient",
      key: "patient",
      render: (_: any, row: any) => (
        <span title={row.patient_id}>
          {row.patient_name || row.patient_id || "-"}
        </span>
      ),
    },
    {
      title: "Modality",
      dataIndex: "modality",
      key: "modality",
      render: (v: string) => (v ? <Tag>{v}</Tag> : "-"),
    },
    {
      title: "Protocol",
      dataIndex: "protocol_name",
      key: "protocol",
      render: (v: string) => v || "-",
    },
    {
      title: "Priority",
      dataIndex: "priority",
      key: "priority",
      render: (v: string) =>
        v ? (
          <Tag color={PRIORITY_COLORS[v] || "default"}>{v.toUpperCase()}</Tag>
        ) : (
          "-"
        ),
    },
    {
      title: "QA Status",
      key: "qa_status",
      render: (_: any, row: any) => {
        const st = row.qa_status || "pending";
        return (
          <Badge
            status={
              st === "pass" ? "success" : st === "fail" ? "error" : "default"
            }
            text={st}
          />
        );
      },
    },
    {
      title: "Completed",
      dataIndex: "completed_at",
      key: "completed_at",
      render: (v: string) => (v ? new Date(v).toLocaleString() : "-"),
    },
    {
      title: "",
      key: "actions",
      render: (_: any, row: any) => (
        <Button
          size="small"
          type={row.qa_status ? "default" : "primary"}
          onClick={() => navigate(`/qa/review/${row.exam_id}`)}
        >
          {row.qa_status ? "Re-review" : "Review"}
        </Button>
      ),
    },
  ];

  return (
    <Content style={{ padding: "16px" }}>
      <div className="qa-header">
        <h2>QA Review Queue</h2>
        <Space>
          <Select
            allowClear
            placeholder="Modality"
            style={{ width: 120 }}
            value={modalityFilter}
            onChange={setModalityFilter}
            options={modalities.map((m) => ({ value: m, label: m }))}
          />
          <Select
            allowClear
            placeholder="QA status"
            style={{ width: 130 }}
            value={statusFilter}
            onChange={setStatusFilter}
            options={["pending", "pass", "fail", "skipped"].map((s) => ({
              value: s,
              label: s,
            }))}
          />
          <Select
            allowClear
            placeholder="Priority"
            style={{ width: 120 }}
            value={priorityFilter}
            onChange={setPriorityFilter}
            options={["routine", "urgent", "stat"].map((s) => ({
              value: s,
              label: s,
            }))}
          />
          <Input
            allowClear
            placeholder="Search patient / MRN / accession"
            style={{ width: 220 }}
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
          />
          <Button
            icon={<ReloadOutlined />}
            onClick={fetchQueue}
            aria-label="Refresh queue"
          />
        </Space>
      </div>
      {error && (
        <Alert
          type="error"
          showIcon
          message={error}
          style={{ margin: "8px 0" }}
        />
      )}
      <Table
        rowKey="exam_id"
        loading={loading}
        columns={columns}
        dataSource={data}
        pagination={{
          current: page,
          pageSize: meta.page_size || 50,
          total: meta.total || 0,
          onChange: setPage,
          showSizeChanger: false,
        }}
        locale={{
          emptyText: (
            <Space
              orientation="vertical"
              align="center"
              style={{ padding: 24 }}
            >
              <FileSearchOutlined style={{ fontSize: 32, color: "#8b8fa3" }} />
              <span>No exams pending QA review</span>
            </Space>
          ),
        }}
      />
    </Content>
  );
}

export default withSidebar(QAQueue);
