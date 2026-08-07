import { useDocumentTitle, useTenantRefetch } from "../hooks";
import React, { useState, useEffect, useCallback } from "react";
import {
  Layout,
  Table,
  Tag,
  Button,
  Select,
  Input,
  Alert,
  Spin,
  Badge,
  Checkbox,
} from "antd";
import { FileDoneOutlined, ReloadOutlined } from "@ant-design/icons";
import { useNavigate } from "react-router";
import withSidebar from "../common/base";
import { request } from "../helpers";
import "./ReadingWorklist.css";

const Content = Layout.Content;

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

const REPORT_STATUS_COLORS: Record<string, string> = {
  none: "blue",
  draft: "gold",
  preliminary: "purple",
};

// NFR-R12-04: worklist staleness (new/urgent arrivals) ≤ 30s.
const REFRESH_MS = 30000;

function ReadingWorklist() {
  useDocumentTitle("QuantumPACS - Reading Worklist");

  const navigate = useNavigate();
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string | undefined>();
  const [modalityFilter, setModalityFilter] = useState<string | undefined>();
  const [search, setSearch] = useState("");
  const [assignedToMe, setAssignedToMe] = useState(false);
  const [physicianFilter, setPhysicianFilter] = useState("");
  const [assigning, setAssigning] = useState<string | null>(null);

  const fetchList = useCallback(() => {
    setLoading(true);
    setError(null);
    const query: Record<string, string> = {};
    if (statusFilter) query.status = statusFilter;
    if (modalityFilter) query.modality = modalityFilter;
    if (search) query.search = search;
    if (assignedToMe) query.radiologist = "me";
    if (physicianFilter) query.physician = physicianFilter;
    request("reports/reading-list", { query })
      .then((res: any) => {
        setLoading(false);
        setData(Array.isArray(res.data) ? res.data : []);
      })
      .catch((e: any) => {
        setLoading(false);
        setError(e.message);
      });
  }, [statusFilter, modalityFilter, search, assignedToMe, physicianFilter]);

  useEffect(() => {
    fetchList();
    const timer = setInterval(fetchList, REFRESH_MS);
    return () => clearInterval(timer);
  }, [fetchList]);

  // Tenant switch → refetch immediately (interval may be up to 30s away).
  useTenantRefetch(fetchList);

  const modalities = [...new Set(data.map((e) => e.modality).filter(Boolean))];

  const columns = [
    {
      title: "Priority",
      dataIndex: "priority",
      key: "priority",
      width: 90,
      defaultSortOrder: "ascend" as const,
      render: (p: string) => (
        <Tag
          color={PRIORITY_COLORS[p]}
          className={p === "stat" ? "reading-stat-tag" : ""}
        >
          {PRIORITY_LABEL[p] || "Routine"}
        </Tag>
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
      title: "Report",
      dataIndex: "report_status",
      key: "report_status",
      width: 130,
      render: (s: string) => (
        <Badge
          status={s === "none" ? "processing" : "warning"}
          text={
            <Tag color={REPORT_STATUS_COLORS[s] || "default"}>
              {s || "none"}
            </Tag>
          }
        />
      ),
    },
    {
      title: "Completed",
      dataIndex: "completed_at",
      key: "completed_at",
      width: 170,
      render: (v: string) => (v ? new Date(v).toLocaleString() : "—"),
    },
    {
      title: "Assigned",
      dataIndex: "assigned_radiologist",
      key: "assigned_radiologist",
      width: 90,
      render: (v: string) => (v ? "Claimed" : "—"),
    },
    {
      title: "",
      key: "action",
      width: 210,
      render: (_: unknown, r: any) => (
        <div style={{ display: "flex", gap: 8 }}>
          <Button
            size="small"
            type="primary"
            ghost
            onClick={() => navigate(`/reading/${r.exam_id}`)}
          >
            {r.report_status && r.report_status !== "none"
              ? "Continue"
              : "Read Study"}
          </Button>
          {!r.assigned_radiologist && (
            <Button
              size="small"
              loading={assigning === r.exam_id}
              onClick={() => takeExam(r.exam_id)}
            >
              Take
            </Button>
          )}
        </div>
      ),
    },
  ];

  const takeExam = (examId: string) => {
    setAssigning(examId);
    request(`reports/reading-list/${examId}/assign`, { method: "POST" })
      .then(() => fetchList())
      .catch((e: any) => setError(e.message))
      .finally(() => setAssigning(null));
  };

  return (
    <Content style={{ padding: 24 }} role="main" id="main-content">
      <div className="reading-wl-header">
        <div>
          <h2 style={{ margin: 0 }}>
            <FileDoneOutlined /> Reading Worklist
          </h2>
          <span className="reading-wl-subtitle">
            Handed-off exams awaiting interpretation — auto-refreshes every 30s
          </span>
        </div>
        <Button icon={<ReloadOutlined />} onClick={fetchList}>
          Refresh
        </Button>
      </div>

      <div className="reading-wl-filters">
        <Select
          allowClear
          placeholder="Report status"
          style={{ width: 150 }}
          value={statusFilter}
          onChange={setStatusFilter}
          options={["draft", "preliminary"].map((s) => ({
            value: s,
            label: s,
          }))}
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
          onSearch={() => fetchList()}
        />
        <Input.Search
          placeholder="Referring physician"
          allowClear
          style={{ width: 200 }}
          value={physicianFilter}
          onChange={(e) => setPhysicianFilter(e.target.value)}
          onSearch={() => fetchList()}
        />
        <Checkbox
          checked={assignedToMe}
          onChange={(e) => setAssignedToMe(e.target.checked)}
        >
          Assigned to me
        </Checkbox>
      </div>

      {error && (
        <Alert
          type="error"
          message="Failed to load reading worklist"
          description={error}
          showIcon
          style={{ marginBottom: 16 }}
        />
      )}

      {loading && !data.length ? (
        <div className="reading-wl-loading">
          <Spin />
        </div>
      ) : (
        <Table
          rowKey="exam_id"
          columns={columns}
          dataSource={data}
          pagination={{ pageSize: 20, showSizeChanger: false }}
          onRow={(r) => ({
            onDoubleClick: () => navigate(`/reading/${r.exam_id}`),
          })}
          scroll={{ x: 900 }}
          locale={{
            emptyText:
              "No studies awaiting interpretation. Completed exams appear here.",
          }}
        />
      )}
    </Content>
  );
}

export default withSidebar(ReadingWorklist);
