import {
  useDocumentTitle,
  useTenantRefetch,
  useVisibilityGatedInterval,
} from "../hooks";
import React, { useState, useEffect, useCallback, useRef } from "react";
import {
  App,
  Layout,
  Table,
  Tag,
  Button,
  Select,
  Input,
  Alert,
  Spin,
  Space,
} from "antd";
import { ThunderboltOutlined, ReloadOutlined } from "@ant-design/icons";
import { useNavigate } from "react-router";
import withSidebar from "../common/base";
import { request } from "../helpers";
import { useAuth } from "../auth/AuthContext";
import {
  EXAM_STATUS_COLORS,
  EXAM_PRIORITY_COLORS,
  PRIORITY_LABEL,
} from "../common/statusColors";
import "./TechnologistWorklist.css";
// Status chips reuse the shared Front Desk chip styles (fd-chips/fd-chip).
import "../frontdesk/FrontDesk.css";

const Content = Layout.Content;

const STATUS_COLORS = EXAM_STATUS_COLORS;

// technologist review P1-3: the read state of an exam the tech completed
// (reports.status machine: draft -> preliminary -> submitted -> final).
const READ_STATE: Record<string, { label: string; color: string }> = {
  final: { label: "Reported", color: "green" },
  submitted: { label: "In review", color: "gold" },
  preliminary: { label: "Preliminary", color: "blue" },
  draft: { label: "In draft", color: "default" },
};

const PRIORITY_COLORS = EXAM_PRIORITY_COLORS;

// Auto-refresh cadence per NFR-R06-06 (≤30s staleness). The exam list refetches
// on this interval so new R04 assignments appear without a manual reload.
const REFRESH_MS = 30000;

const STATUS_TABS = [
  { key: "", label: "All" },
  { key: "ready", label: "Ready" },
  { key: "in_progress", label: "In Progress" },
  { key: "completed", label: "Completed" },
  { key: "cancelled", label: "Cancelled" },
];

function TechnologistWorklist() {
  const { message } = App.useApp();
  useDocumentTitle("QuantumPACS - Technologist Worklist");

  const navigate = useNavigate();
  const [data, setData] = useState<any[]>([]);
  // R1-03: loading only covers the initial load — background polls must not
  // flash the Table spinner mask every 30s. It starts true (the mount effect
  // fetches immediately) and is cleared by the first response; later polls
  // leave the previous rows in place until fresh data lands.
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string | undefined>(
    () => sessionStorage.getItem("tech-wl-status") || undefined,
  );
  const [modalityFilter, setModalityFilter] = useState<string | undefined>(
    () => sessionStorage.getItem("tech-wl-modality") || undefined,
  );
  const [search, setSearch] = useState(
    () => sessionStorage.getItem("tech-wl-search") || "",
  );
  // T-01: "My Exams" default — only exams assigned to the current user.
  // Toggle to 'pool' reveals the unassigned pool. Persisted across the
  // worklist → console → back loop like the other filters.
  const [assigned, setAssigned] = useState<string | undefined>(
    () => sessionStorage.getItem("tech-wl-assigned") || "mine",
  );

  // C7 (NFR-R06-06): the 30s poll can bring new assignments in silently, so
  // the previous id set is diffed on every poll and fresh ids are announced
  // (aria-live, by accession) and highlighted. Two scoping rules keep that
  // honest: a filter change (status/modality/search) swaps the result space,
  // so the baseline is reseeded on the fetch that follows it — otherwise the
  // same rows under a new filter would read as arrivals; and `seeded`
  // distinguishes "first load ever" from "a later poll returned empty", so
  // the first assignment to arrive after an empty worklist is announced too.
  const prevIds = useRef<Set<string>>(new Set());
  const prevFilterKey = useRef<string | null>(null);
  const seeded = useRef(false);
  const [newArrivals, setNewArrivals] = useState<any[]>([]);
  // technologist review P1-2: claiming an unassigned exam assigns it to the
  // caller; the row flips via the next poll (no separate fetch surface).
  const [claimingId, setClaimingId] = useState<string | null>(null);

  // P1-2: current user id for the "Unassigned" vs "mine" row distinction.
  // AuthContext exposes the id via user?.id.
  const { user } = useAuth();
  const myId = user?.id != null ? String(user.id) : "";

  const claimExam = async (examId: string, accession: string, release = false) => {
    setClaimingId(examId);
    try {
      await request(`exams/${examId}/claim`, { data: { release } });
      message.success(release ? "Exam released to pool" : "Exam claimed");
      fetchExams();
    } catch (e: any) {
      message.error(e.message || (release ? "Release failed" : "Claim failed"));
    } finally {
      setClaimingId(null);
    }
  };
  // C9: elapsed "time in queue" needs a ticking clock; 30s cadence matches
  // the refresh interval so the column never shows stale minutes.
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const t = window.setInterval(() => setNow(Date.now()), 30000);
    return () => window.clearInterval(t);
  }, []);

  // Persist filter state across the worklist -> exam console -> back loop
  // (R06 UI/UX: back navigation preserves scroll position and filter state).
  useEffect(() => {
    if (statusFilter) sessionStorage.setItem("tech-wl-status", statusFilter);
    else sessionStorage.removeItem("tech-wl-status");
  }, [statusFilter]);
  useEffect(() => {
    if (modalityFilter)
      sessionStorage.setItem("tech-wl-modality", modalityFilter);
    else sessionStorage.removeItem("tech-wl-modality");
  }, [modalityFilter]);
  useEffect(() => {
    if (search) sessionStorage.setItem("tech-wl-search", search);
    else sessionStorage.removeItem("tech-wl-search");
  }, [search]);
  useEffect(() => {
    if (assigned && assigned !== "mine")
      sessionStorage.setItem("tech-wl-assigned", assigned);
    else sessionStorage.removeItem("tech-wl-assigned");
  }, [assigned]);

  const fetchExams = useCallback(() => {
    setError(null);
    const query: Record<string, string> = {};
    if (statusFilter) query.status = statusFilter;
    if (modalityFilter) query.modality = modalityFilter;
    if (search) query.search = search;
    // T-01: default to my assignments; the pool is opt-in via the toggle.
    query.assigned = assigned === "pool" ? "pool" : "mine";
    request("exams", { query })
      .then((res: any) => {
        const rows = Array.isArray(res.data) ? res.data : [];
        setData(rows);
        // C7: diff against the previous poll. A filter change since the last
        // fetch makes this response a new baseline, not a poll result — the
        // reseeded set would otherwise read every row as an arrival.
        const filterKey = JSON.stringify([
          statusFilter,
          modalityFilter,
          search,
          assigned,
        ]);
        const filterChanged = filterKey !== prevFilterKey.current;
        if (filterChanged) {
          prevIds.current = new Set();
          prevFilterKey.current = filterKey;
        }
        const fresh = rows.filter((r: any) => !prevIds.current.has(r.id));
        if (seeded.current && !filterChanged && fresh.length) {
          setNewArrivals((a) => [...a, ...fresh]);
          window.setTimeout(() => {
            setNewArrivals((a) => a.filter((x: any) => !fresh.includes(x)));
          }, 8000);
        }
        seeded.current = true;
        prevIds.current = new Set(rows.map((r: any) => r.id));
        loadStatusCounts();
      })
      .catch((e: any) => {
        setError(e.message);
      })
      .finally(() => setLoading(false));
  }, [statusFilter, modalityFilter, search, assigned]);

  useEffect(() => {
    fetchExams();
  }, [fetchExams]);

  // R1-04: pause the 30s poll while the tab is hidden; refetch on return.
  useVisibilityGatedInterval(fetchExams, REFRESH_MS);

  // Tenant switch → refetch immediately (interval may be up to 30s away).
  useTenantRefetch(fetchExams);

  // Per-status counts across the whole assignment (not just the filtered
  // page): one lightweight request with a big per_page, summed client-side.
  // Refetched on every poll (via fetchExams) so the tabs stay in step with
  // the list — computing once on mount left them stale as exams arrived.
  const [statusCounts, setStatusCounts] = useState<Record<string, number>>({});
  const loadStatusCounts = useCallback(() => {
    request("exams", { query: { per_page: "500" } })
      .then((res: any) => {
        const rows = Array.isArray(res.data) ? res.data : [];
        const counts: Record<string, number> = {};
        for (const e of rows) {
          counts[e.status || "ready"] = (counts[e.status || "ready"] || 0) + 1;
        }
        setStatusCounts(counts);
      })
      .catch(() => {});
  }, []);

  const totalCount = Object.values(statusCounts).reduce((a, b) => a + b, 0);

  // P2-4: one-line queue summary — ready count and anything past the 30-minute
  // attention threshold — derived from the per_page=500 fetch (no new call).
  const overdueCount = data.filter(
    (e: any) =>
      e.status !== "completed" &&
      e.status !== "cancelled" &&
      e.created_at &&
      Date.now() - new Date(e.created_at).getTime() > 30 * 60 * 1000,
  ).length;

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
      render: (_: unknown, r: any) => (
        <span>
          {r.patient_name || r.patient_id || "—"}
          {/* P1-2: unassigned pool rows are labeled, not silently blended
              with the tech's own assignments — ownership is honest. */}
          {r.assigned_technologist && r.assigned_technologist !== myId && (
            <Tag style={{ marginLeft: 8 }}>Other tech</Tag>
          )}
          {(!r.assigned_technologist || r.assigned_technologist === "") && (
            <Tag color="default" style={{ marginLeft: 8 }}>
              Unassigned
            </Tag>
          )}
        </span>
      ),
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
      // P1-3: the read state of a completed exam — the tech sees the loop
      // close (reported / in review / awaiting read) instead of a dead end.
      title: "Read State",
      key: "read_state",
      width: 130,
      render: (_: unknown, r: any) => {
        if (r.status !== "completed") return "—";
        const st = READ_STATE[r.report_status];
        return st ? (
          <Tag color={st.color}>{st.label}</Tag>
        ) : (
          <Tag color="default">Awaiting read</Tag>
        );
      },
    },
    {
      // C9: elapsed time in queue (created_at = handoff to the worklist) or
      // since completion; color-coded once an active exam has waited long
      // enough that it needs attention.
      title: "Elapsed",
      key: "elapsed",
      width: 110,
      render: (_: unknown, r: any) => {
        const ts = r.completed_at || r.created_at;
        if (!ts) return "—";
        const mins = Math.floor((now - new Date(ts).getTime()) / 60000);
        if (mins < 0) return "—";
        const label =
          mins < 60 ? `${mins}m` : `${Math.floor(mins / 60)}h ${mins % 60}m`;
        const color =
          r.status === "completed"
            ? "default"
            : mins >= 30
              ? "orange"
              : mins >= 15
                ? "gold"
                : "default";
        return <Tag color={color}>{label}</Tag>;
      },
    },
    {
      title: "",
      key: "action",
      width: 210,
      render: (_: unknown, r: any) => (
        <Space>
          {/* P1-2: an unassigned pool row gets a one-click Claim so ownership
              is explicit (and audited) instead of implicit. */}
          {(!r.assigned_technologist || r.assigned_technologist === "") && (
            <Button
              size="small"
              loading={claimingId === r.id}
              onClick={() => claimExam(r.id, r.accession_number)}
              aria-label={`Claim exam ${r.accession_number || r.id}`}
            >
              Claim
            </Button>
          )}
          {r.assigned_technologist === myId && (
            <Button
              size="small"
              loading={claimingId === r.id}
              onClick={() => claimExam(r.id, r.accession_number, true)}
              aria-label={`Release exam ${r.accession_number || r.id}`}
            >
              Release
            </Button>
          )}
          <Button
            size="small"
            type="primary"
            ghost
            onClick={() => navigate(`/exams/${r.id}`)}
          >
            Open Exam
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <Content style={{ padding: 24 }} role="main">
      <div className="tech-wl-header">
        <div>
          <h2 style={{ margin: 0 }}>
            <ThunderboltOutlined /> Technologist Worklist
          </h2>
          <span className="tech-wl-subtitle">
            {assigned === "pool"
              ? "Unassigned pool — claim exams to take ownership"
              : "Your assigned exams — auto-refreshes every 30s"}
          </span>
        </div>
        <Button icon={<ReloadOutlined />} onClick={fetchExams}>
          Refresh
        </Button>
      </div>

      {/* T-01: "My Exams" / Unassigned Pool — default to my assignments,
          toggle to work the shared pool. */}
      <div className="fd-chips" style={{ marginBottom: 12 }}>
        <button
          type="button"
          className={`fd-chip ${assigned === "mine" ? "is-active" : ""}`}
          aria-pressed={assigned === "mine"}
          onClick={() => setAssigned("mine")}
        >
          My Exams
        </button>
        <button
          type="button"
          className={`fd-chip ${assigned === "pool" ? "is-active" : ""}`}
          aria-pressed={assigned === "pool"}
          onClick={() => setAssigned("pool")}
        >
          Unassigned Pool
        </button>
      </div>

      {/* P2-4: a headline instead of a row-count — the tech knows at a
          glance whether the queue needs attention (overdue = past the 30m
          attention threshold, same rule the Elapsed column colorizes). */}
      {data.length > 0 && (
        <div style={{ marginBottom: 12, fontSize: 13 }} aria-live="polite">
          <Tag color="blue">{statusCounts.ready || 0} ready</Tag>
          {overdueCount > 0 && (
            <Tag color="gold">{overdueCount} overdue (≥30m)</Tag>
          )}
          {overdueCount === 0 && <Tag>nothing overdue</Tag>}
        </div>
      )}

      <div className="tech-wl-filters">
        <div className="fd-chips" style={{ marginBottom: 0 }}>
          {STATUS_TABS.map((tab) => (
            <button
              key={tab.key || "all"}
              type="button"
              className={`fd-chip ${statusFilter === tab.key ? "is-active" : ""}`}
              aria-pressed={statusFilter === tab.key}
              onClick={() => setStatusFilter(tab.key || undefined)}
            >
              {tab.label} (
              {tab.key === "" ? totalCount : statusCounts[tab.key] || 0})
            </button>
          ))}
        </div>
        <Select
          id="tech-wl-modality-filter"
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
          aria-label="Search patient or accession"
          placeholder="Search patient / accession"
          allowClear
          style={{ width: 260 }}
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          onSearch={() => fetchExams()}
        />
      </div>

      {statusFilter === "completed" && data.length > 0 && (
        <Alert
          type="success"
          showIcon
          style={{ marginBottom: 16 }}
          title={`${data.length} completed exam(s) — handed off to the radiologist worklist.`}
        />
      )}

      {error && (
        <Alert
          type="error"
          title="Failed to load worklist"
          description={error}
          showIcon
          style={{ marginBottom: 16 }}
        />
      )}

      {/* C7 (NFR-R06-06): visually hidden aria-live region so newly arrived
          assignments are announced to screen-reader users by accession
          (spec §3-7: "Exam {accession} assigned") instead of rows silently
          changing under the cursor. */}
      <div aria-live="polite" role="status" className="tech-wl-live">
        {newArrivals.length === 0
          ? ""
          : newArrivals.length === 1
            ? `Exam ${
                newArrivals[0].accession_number || newArrivals[0].id
              } assigned`
            : `Exams ${newArrivals
                .map((r: any) => r.accession_number || r.id)
                .join(", ")} assigned`}
      </div>

      {loading && !data.length ? (
        <div className="tech-wl-loading">
          <Spin />
        </div>
      ) : (
        <Table
          rowKey="id"
          columns={columns}
          dataSource={data}
          rowClassName={(r: any) =>
            newArrivals.some((x: any) => x.id === r.id) ? "tech-wl-row-new" : ""
          }
          pagination={{ pageSize: 20, showSizeChanger: false }}
          onRow={(r) => ({
            onDoubleClick: () => navigate(`/exams/${r.id}`),
          })}
          scroll={{ x: 900 }}
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
