import { useDocumentTitle, useTenantRefetch } from "../hooks";
import React, { useState, useEffect, useCallback, useRef } from "react";
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
  Tooltip,
} from "antd";
import {
  FileDoneOutlined,
  ReloadOutlined,
  AlertOutlined,
} from "@ant-design/icons";
import { useNavigate, useSearchParams } from "react-router";
import withSidebar from "../common/base";
import { request } from "../helpers";
import { useAuth } from "../auth/AuthContext";
import { patientInitials, mrnLast4 } from "./patientLabel";
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
  submitted: "cyan",
  final: "green",
};

// NFR-R12-04: worklist staleness (new/urgent arrivals) ≤ 30s.
const REFRESH_MS = 30000;

function ReadingWorklist() {
  useDocumentTitle("QuantumPACS - Reading Worklist");

  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  // The console opens exams with the current filters in the query string
  // (Sign & Next returns with them restored), so the worklist must seed its
  // filter state from the URL on mount.
  const [statusFilter, setStatusFilter] = useState<string | undefined>(
    () => searchParams.get("status") || undefined,
  );
  const [modalityFilter, setModalityFilter] = useState<string | undefined>(
    () => searchParams.get("modality") || undefined,
  );
  const [search, setSearch] = useState(() => searchParams.get("search") || "");
  const [assignedToMe, setAssignedToMe] = useState(
    () => searchParams.get("radiologist") === "me",
  );
  const [reviewFilter, setReviewFilter] = useState(
    () => searchParams.get("review") === "1",
  );
  // R-01: unread toggle — exams never opened for reading.
  const [unreadOnly, setUnreadOnly] = useState(
    () => searchParams.get("unread") === "1",
  );
  const [physicianFilter, setPhysicianFilter] = useState(
    () => searchParams.get("physician") || "",
  );
  const [data, setData] = useState<any[]>([]);
  // D1: server-side pagination state
  const [total, setTotal] = useState(0);
  const pageRef = useRef(1);
  const pageSizeRef = useRef(20);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [assigning, setAssigning] = useState<string | null>(null);

  // Claiming an exam (Take) posts to /assign, gated REPORT_WRITE on the
  // backend — readers with REPORT_READ only (referring physician, nurse,
  // care coordinator) view the queue but cannot take exams.
  const { hasPermission } = useAuth();
  const canClaim = hasPermission("REPORT_WRITE");

  const fetchList = useCallback(() => {
    setLoading(true);
    setError(null);
    const query: Record<string, string> = {};
    if (statusFilter) query.status = statusFilter;
    if (modalityFilter) query.modality = modalityFilter;
    if (search) query.search = search;
    if (assignedToMe) query.radiologist = "me";
    if (physicianFilter) query.physician = physicianFilter;
    if (reviewFilter) query.review = "1";
    if (unreadOnly) query.unread = "1";
    // D1: server-side pagination — the queue can exceed any client page.
    query.page = String(pageRef.current);
    query.per_page = String(pageSizeRef.current);
    request("reports/reading-list", { query })
      .then((res: any) => {
        setLoading(false);
        setData(Array.isArray(res.data) ? res.data : []);
        setTotal(typeof res.total === "number" ? res.total : res.data.length);
      })
      .catch((e: any) => {
        setLoading(false);
        setError(e.message);
      });
  }, [
    statusFilter,
    modalityFilter,
    search,
    assignedToMe,
    physicianFilter,
    reviewFilter,
    unreadOnly,
  ]);

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
          {p === "stat" && (
            <span className="reading-stat-dot" aria-hidden="true" />
          )}
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
      render: (_: unknown, r: any) => (
        // PHI-minimizing label: initials + MRN last-4 in the queue, full name
        // only on hover (shared with Resident Home).
        <Tooltip
          title={`${r.patient_name || ""}${r.patient_id ? ` (MRN ${r.patient_id})` : ""}`}
        >
          <span className="reading-patient-label">
            <span className="reading-patient-initials">
              {patientInitials(r.patient_name || "")}
            </span>
            {r.patient_id && (
              <span className="reading-patient-mrn">
                ·{mrnLast4(r.patient_id)}
              </span>
            )}
          </span>
        </Tooltip>
      ),
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
      // technologist review P1-1: a critical flag (set during acquisition)
      // renders as a red tag so the reading team sees it at a glance — the
      // backend already sorts flagged exams above their priority tier.
      title: "Flag",
      dataIndex: "critical_flag",
      key: "critical_flag",
      width: 90,
      render: (f: string) =>
        f ? (
          <Tag color="red" icon={<AlertOutlined />}>
            {String(f).toUpperCase()}
          </Tag>
        ) : null,
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
            onClick={() => openExam(r.exam_id)}
          >
            {r.report_status && r.report_status !== "none"
              ? "Continue"
              : "Read Study"}
          </Button>
          {!r.assigned_radiologist && canClaim && (
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

  // Serialize the active filters into the URL when opening an exam, so the
  // reading console can return the radiologist to the same queue view.
  const openExam = (examId: string) => {
    const q: Record<string, string> = {};
    if (statusFilter) q.status = statusFilter;
    if (modalityFilter) q.modality = modalityFilter;
    if (search) q.search = search;
    if (assignedToMe) q.radiologist = "me";
    if (physicianFilter) q.physician = physicianFilter;
    if (reviewFilter) q.review = "1";
    if (unreadOnly) q.unread = "1";
    const s = new URLSearchParams(q).toString();
    navigate(`/reading/${examId}${s ? `?${s}` : ""}`);
  };

  return (
    <Content style={{ padding: 24 }} role="main">
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
          id="reading-worklist-status-filter"
          aria-label="Report status"
          allowClear
          placeholder="Report status"
          style={{ width: 150 }}
          value={statusFilter}
          onChange={setStatusFilter}
          options={["draft", "preliminary", "submitted", "returned"].map(
            (s) => ({
              value: s,
              // "returned" maps server-side to draft + review_feedback set
              // (R13 resident revision loop); label reads as a revision queue.
              label: s === "returned" ? "needs revision" : s,
            }),
          )}
        />
        <Select
          id="reading-worklist-modality-filter"
          aria-label="Modality"
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
        <Checkbox
          checked={reviewFilter}
          onChange={(e) => setReviewFilter(e.target.checked)}
        >
          Awaiting review
        </Checkbox>
        <Checkbox
          checked={unreadOnly}
          onChange={(e) => setUnreadOnly(e.target.checked)}
        >
          Unread only
        </Checkbox>
      </div>

      {error && (
        <Alert
          type="error"
          title="Failed to load reading worklist"
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
          pagination={{
            current: pageRef.current,
            pageSize: pageSizeRef.current,
            total,
            showSizeChanger: false,
            onChange: (p: number, ps: number) => {
              pageRef.current = p;
              pageSizeRef.current = ps;
              fetchList();
            },
          }}
          onRow={(r) => ({
            // STAT studies get a persistent red edge + (in the priority tag) a
            // pulsing dot — visible even when the STAT row sorts below the fold.
            className: r.priority === "stat" ? "reading-stat-row" : "",
            onDoubleClick: () => openExam(r.exam_id),
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
