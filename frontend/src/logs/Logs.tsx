import { useDocumentTitle } from "../hooks";
import React, {
  useState,
  useEffect,
  useRef,
  useCallback,
  useMemo,
} from "react";
import {
  Layout,
  Table,
  message,
  Tag,
  Button,
  Switch,
  DatePicker,
  Space,
  Typography,
  Input,
  Select,
  Badge,
} from "antd";
import {
  DownloadOutlined,
  ReloadOutlined,
  SearchOutlined,
} from "@ant-design/icons";
import withSidebar from "../common/base";
import { request } from "../helpers";
import { PageState } from "../common/PageState";

const { Text } = Typography;
const { RangePicker } = DatePicker;
const Content = Layout.Content;

const EVENT_GROUPS: Record<string, string[]> = {
  "Data Access": [
    "study.read",
    "study.download",
    "series.read",
    "instance.read",
    "instance.download",
  ],
  "Data Modification": [
    "study.updated",
    "study.anonymized",
    "study.deleted",
    "series.updated",
    "instance.annotations_changed",
    "instance.tags_edited",
  ],
  "Auth & Session": [
    "auth.login",
    "auth.login_failed",
    "auth.logout",
    "auth.token_refreshed",
    "auth.password_changed",
  ],
  "User Management": [
    "user.created",
    "user.updated",
    "user.deactivated",
    "user.reactivated",
    "user.deleted",
  ],
  "Tenant Management": [
    "tenant.created",
    "tenant.updated",
    "tenant.quarantined",
    "tenant.decommissioned",
    "tenant.storage_quota_changed",
  ],
  "Replica Management": [
    "replica.created",
    "replica.updated",
    "replica.deleted",
    "replica.master_changed",
    "replica.sync_status_changed",
  ],
  System: [
    "system.config_changed",
    "system.backup_completed",
    "system.backup_failed",
    "system.maintenance_mode",
  ],
};

const EVENT_TYPE_COLORS: Record<string, string> = {
  "study.read": "blue",
  "study.download": "cyan",
  "series.read": "geekblue",
  "instance.read": "blue",
  "instance.download": "cyan",
  "study.updated": "orange",
  "study.anonymized": "purple",
  "study.deleted": "red",
  "series.updated": "orange",
  "instance.annotations_changed": "gold",
  "instance.tags_edited": "gold",
  "auth.login": "green",
  "auth.login_failed": "red",
  "auth.logout": "default",
  "auth.token_refreshed": "green",
  "auth.password_changed": "orange",
  "user.created": "green",
  "user.updated": "blue",
  "user.deactivated": "red",
  "user.reactivated": "green",
  "user.deleted": "red",
  "tenant.created": "green",
  "tenant.updated": "blue",
  "tenant.quarantined": "red",
  "tenant.decommissioned": "red",
  "tenant.storage_quota_changed": "orange",
  "replica.created": "green",
  "replica.updated": "blue",
  "replica.deleted": "red",
  "replica.master_changed": "orange",
  "replica.sync_status_changed": "orange",
  "system.config_changed": "purple",
  "system.backup_completed": "green",
  "system.backup_failed": "red",
  "system.maintenance_mode": "orange",
};

const ALL_EVENT_TYPES = Object.values(EVENT_GROUPS).flat();

function Logs() {
  useDocumentTitle("QuantumPACS - Audit Logs");

  let [data, setData] = useState<any[]>([]);
  let [loading, setLoading] = useState(false);
  let [error, setError] = useState<string | null>(null);
  let [total, setTotal] = useState(0);
  let [hasMore, setHasMore] = useState(false);
  let [page, setPage] = useState(1);
  let [cursor, setCursor] = useState<number | null>(null);
  let [cursorMap, setCursorMap] = useState<Record<number, number | null>>({
    1: null,
  });

  let [eventTypeFilter, setEventTypeFilter] = useState<string[]>([]);
  let [dateRange, setDateRange] = useState<[string, string] | null>(null);
  let [actorFilter, setActorFilter] = useState<string>("");
  let [actors, setActors] = useState<string[]>([]);
  let [streaming, setStreaming] = useState(false);
  let [newEventIds, setNewEventIds] = useState<Set<number>>(new Set());
  let [newEventsAvailable, setNewEventsAvailable] = useState(false);

  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const latestIdRef = useRef<number | null>(null);
  const tableRef = useRef<HTMLDivElement>(null);
  const actorDebounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    setPage(1);
    setCursorMap({ 1: null });
    setCursor(null);
  }, [eventTypeFilter, dateRange, actorFilter]);

  useEffect(() => {
    fetch({ cursor: cursorMap[page] || null, page });
  }, [page, eventTypeFilter, dateRange, actorFilter]);

  useEffect(() => {
    if (streaming) {
      intervalRef.current = setInterval(() => pollNew(), 5000);
    } else {
      if (intervalRef.current) clearInterval(intervalRef.current);
      intervalRef.current = null;
      setNewEventsAvailable(false);
    }
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [streaming, eventTypeFilter, dateRange, actorFilter]);

  const buildQuery = useCallback(
    (extra: Record<string, any> = {}) => {
      const q: Record<string, any> = { limit: 50 };
      if (eventTypeFilter.length > 0) q.event_type = eventTypeFilter.join(",");
      if (dateRange) {
        q.date_from = dateRange[0];
        q.date_to = dateRange[1];
      }
      if (actorFilter) q.actor = actorFilter;
      Object.assign(q, extra);
      return q;
    },
    [eventTypeFilter, dateRange, actorFilter],
  );

  const fetch = async (extra: Record<string, any> = {}) => {
    setLoading(true);
    setError(null);
    try {
      const res = await request("logs", { query: buildQuery(extra) });
      const items = res.data || [];
      setData(items);
      setTotal(res.total || 0);
      setHasMore(res.has_more || false);
      if (items.length > 0) {
        latestIdRef.current = items[0].id;
      }
    } catch (e: any) {
      setError(e.message);
      message.error(e.message);
    } finally {
      setLoading(false);
    }
  };

  const pollNew = async () => {
    if (!latestIdRef.current) return;
    try {
      const q = buildQuery({ cursor: latestIdRef.current, limit: 200 });
      const res = await request("logs", { query: q });
      const newItems = (res.data || []).filter(
        (item: any) => item.id > (latestIdRef.current || 0),
      );
      if (newItems.length === 0) return;
      const ids = newItems.map((i: any) => i.id);
      const isAtTop = tableRef.current
        ? tableRef.current.scrollTop < 100
        : true;
      if (isAtTop) {
        setData((prev) => [...newItems, ...prev]);
        setNewEventIds((prev) => {
          const next = new Set(prev);
          ids.forEach((id: number) => next.add(id));
          setTimeout(
            () =>
              setNewEventIds((p) => {
                const n = new Set(p);
                ids.forEach((id: number) => n.delete(id));
                return n;
              }),
            2000,
          );
          return next;
        });
        latestIdRef.current = newItems[0].id;
      } else {
        setNewEventsAvailable(true);
      }
    } catch {}
  };

  const handlePageChange = (newPage: number) => {
    setCursorMap((prev) => {
      if (prev[newPage] !== undefined) return prev;
      return {
        ...prev,
        [newPage]: data.length > 0 ? data[data.length - 1].id : null,
      };
    });
    setPage(newPage);
  };

  const handleEventTypeClick = (type: string) => {
    setEventTypeFilter((prev) =>
      prev.includes(type) ? prev.filter((t) => t !== type) : [...prev, type],
    );
  };

  const handleDateRange = (dates: any) => {
    if (dates && dates[0] && dates[1]) {
      setDateRange([
        dates[0].format("YYYY-MM-DD"),
        dates[1].format("YYYY-MM-DD"),
      ]);
    } else {
      setDateRange(null);
    }
  };

  const handleActorSearch = (value: string) => {
    setActorFilter(value);
    if (actorDebounceRef.current) clearTimeout(actorDebounceRef.current);
    actorDebounceRef.current = setTimeout(async () => {
      try {
        const res = await request("logs/actors", {
          query: { search: value, limit: "10" },
        });
        setActors(res.data || []);
      } catch {}
    }, 300);
  };

  const handleShowNewEvents = () => {
    setNewEventsAvailable(false);
    pollNew();
  };

  const exportCsv = () => {
    const header =
      "Timestamp,Actor,Event Type,Resource Type,Resource ID,Description,Tenant,Payload\n";
    const rows = data
      .map((row: any) => {
        const escape = (s: any) => {
          if (s == null) return "";
          const str = typeof s === "object" ? JSON.stringify(s) : String(s);
          return str.includes(",") || str.includes('"') || str.includes("\n")
            ? `"${str.replace(/"/g, '""')}"`
            : str;
        };
        return [
          row.created_at,
          row.actor,
          row.event_type,
          row.resource_type,
          row.resource_id,
          row.description,
          row.tenant,
          escape(row.payload),
        ].join(",");
      })
      .join("\n");
    const blob = new Blob([header + rows], { type: "text/csv;charset=utf-8;" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `audit-logs-${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(a.href);
  };

  const columns: any[] = [
    {
      title: "Timestamp",
      dataIndex: "created_at",
      width: "16%",
      render: (d: string) => (d ? new Date(d).toLocaleString() : "-"),
    },
    {
      title: "Actor",
      dataIndex: "actor",
      width: "12%",
      render: (a: string) =>
        a === "system" ? <Tag color="default">system</Tag> : a,
    },
    {
      title: "Event Type",
      dataIndex: "event_type",
      width: "16%",
      render: (t: string) => {
        if (!t) return "-";
        const color = EVENT_TYPE_COLORS[t] || "default";
        const group = Object.entries(EVENT_GROUPS).find(([, types]) =>
          types.includes(t),
        )?.[0];
        return (
          <Tag color={color} title={group}>
            {t}
          </Tag>
        );
      },
    },
    {
      title: "Resource Type",
      dataIndex: "resource_type",
      width: "12%",
      render: (r: string) => r || "-",
    },
    {
      title: "Resource ID",
      dataIndex: "resource_id",
      width: "16%",
      render: (id: string) =>
        id ? (
          <Text copyable style={{ fontSize: 12 }}>
            {id}
          </Text>
        ) : (
          "-"
        ),
    },
    {
      title: "Description",
      dataIndex: "description",
      width: "28%",
      render: (d: string) => d || "-",
    },
  ];

  const activeFilters = eventTypeFilter;

  const scrollToNew = () => {
    handleShowNewEvents();
  };

  return (
    <Content
      style={{
        padding: 24,
        display: "flex",
        flexDirection: "column",
        height: "100%",
      }}
    >
      <div style={{ marginBottom: 12, flexShrink: 0 }}>
        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            gap: 4,
            alignItems: "center",
            marginBottom: 8,
          }}
        >
          <Space wrap size={[4, 4]}>
            {Object.entries(EVENT_GROUPS).map(([group, types]) =>
              types.map((type) => (
                <Tag
                  key={type}
                  color={
                    activeFilters.includes(type)
                      ? EVENT_TYPE_COLORS[type] || "blue"
                      : "default"
                  }
                  style={{ cursor: "pointer", fontSize: 11 }}
                  onClick={() => handleEventTypeClick(type)}
                  title={group}
                >
                  {type}
                </Tag>
              )),
            )}
          </Space>
          <Button
            size="small"
            type="link"
            onClick={() => setEventTypeFilter([])}
            style={{ fontSize: 11 }}
          >
            Clear
          </Button>
        </div>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            flexWrap: "wrap",
          }}
        >
          <RangePicker size="small" onChange={handleDateRange} allowClear />
          <Input
            size="small"
            placeholder="Filter by actor..."
            prefix={<SearchOutlined />}
            value={actorFilter}
            onChange={(e) => handleActorSearch(e.target.value)}
            style={{ width: 180 }}
            allowClear
            onClear={() => {
              setActorFilter("");
              setActors([]);
            }}
          />
          <div
            style={{
              marginLeft: "auto",
              display: "flex",
              gap: 8,
              alignItems: "center",
            }}
          >
            {streaming && (
              <Badge
                status="processing"
                text={
                  <Text style={{ fontSize: 12, color: "#52c41a" }}>Live</Text>
                }
              />
            )}
            <span style={{ fontSize: 12 }}>Live</span>
            <Switch size="small" checked={streaming} onChange={setStreaming} />
            <Button
              size="small"
              icon={<DownloadOutlined />}
              onClick={exportCsv}
              disabled={data.length === 0}
            >
              CSV
            </Button>
            <Button
              size="small"
              icon={<ReloadOutlined />}
              onClick={() => fetch({ cursor: cursorMap[page] || null })}
            >
              Refresh
            </Button>
          </div>
        </div>
        <div style={{ fontSize: 12, color: "#888", marginTop: 4 }}>
          {total > 0 ? `${total} total events` : ""}
        </div>
      </div>

      {newEventsAvailable && (
        <div style={{ textAlign: "center", marginBottom: 8 }}>
          <Button type="link" onClick={scrollToNew} style={{ fontSize: 12 }}>
            New events available — click to view
          </Button>
        </div>
      )}

      <div ref={tableRef} style={{ flex: 1, overflow: "auto" }}>
        <PageState
          error={error}
          onRetry={() => fetch({ cursor: cursorMap[page] || null })}
          empty={!loading && !error && data.length === 0}
          emptyMessage="No audit events found"
        >
          <Table
            columns={columns}
            rowKey="id"
            dataSource={data}
            loading={loading}
            size="middle"
            pagination={{
              current: page,
              pageSize: 50,
              total: Math.max(total, data.length),
              showSizeChanger: false,
              onChange: handlePageChange,
              showTotal: (t) => `${t} events`,
            }}
            expandedRowRender={(record: any) => (
              <pre
                style={{
                  margin: 0,
                  fontSize: 11,
                  whiteSpace: "pre-wrap",
                  maxHeight: 300,
                  overflow: "auto",
                }}
              >
                {JSON.stringify(record.payload, null, 2)}
              </pre>
            )}
            onRow={(record: any) => ({
              style: newEventIds.has(record.id)
                ? { animation: "fadeHighlight 2s ease-out" }
                : undefined,
            })}
          />
        </PageState>
      </div>

      <style>{`
        @keyframes fadeHighlight {
          0% { background-color: #fff7e6; }
          100% { background-color: transparent; }
        }
      `}</style>
    </Content>
  );
}

export default withSidebar(Logs);
