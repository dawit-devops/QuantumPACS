import { useDocumentTitle, useTenantRefetch } from "../hooks";
import React, { useState, useEffect, useCallback, useMemo, useRef } from "react";
import {
  App,
  Layout,
  Table,
  Tag,
  Select,
  Input,
  Button,
  Tooltip,
  Popconfirm,
  Badge,
  Space,
  Modal,
  Descriptions,
  DatePicker,
} from "antd";
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  ClockCircleOutlined,
  ExclamationCircleOutlined,
  ArrowRightOutlined,
  AlertOutlined,
  CalendarOutlined,
} from "@ant-design/icons";
import withSidebar from "../common/base";
import { useAuth } from "../auth/AuthContext";
import {
  listTracking,
  getTrackingKpi,
  updateTrackingStatus,
  type TrackingEntry,
  type TrackingKpi,
} from "../api/tracking";
import { getResourceAvailability } from "../api/scheduling";
import RescheduleModal from "../schedule/RescheduleModal";
import type { ResourceAvailabilitySlot, RisAppointment } from "../api/scheduling";
import { PageState } from "../common/PageState";
import { TRACKING_STATUS_COLORS, TRACKING_PRIORITY_COLORS } from "../common/statusColors";
import KpiStrip from "./KpiStrip";
import "./TrackingBoard.css";

const { Content } = Layout;

const STATUS_COLORS = TRACKING_STATUS_COLORS;

const PRIORITY_COLORS = TRACKING_PRIORITY_COLORS;

const VALID_TRANSITIONS: Record<string, string[]> = {
  scheduled: ["arrived", "cancelled"],
  arrived: ["in_progress", "cancelled"],
  in_progress: ["completed", "cancelled"],
  completed: [],
  cancelled: [],
};

function TrackingBoard() {
  const { message } = App.useApp();
  useDocumentTitle("QuantumPACS - Tracking Board");
  const { hasPermission } = useAuth();
  const canWrite = hasPermission("WORKLIST_WRITE");

  const [data, setData] = useState<TrackingEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pagination, setPagination] = useState<any>({
    current: 1,
    pageSize: 20,
    total: 0,
  });
  const [kpi, setKpi] = useState<TrackingKpi | null>(null);
  const [kpiError, setKpiError] = useState<string | null>(null);
  const [modalityFilter, setModalityFilter] = useState<string | undefined>();
  const [statusFilter, setStatusFilter] = useState<string | undefined>();
  const [priorityFilter, setPriorityFilter] = useState<string | undefined>();
  const [roomFilter, setRoomFilter] = useState("");
  const [debouncedRoom, setDebouncedRoom] = useState("");
  const [dateRange, setDateRange] = useState<[any, any] | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [detailModal, setDetailModal] = useState<TrackingEntry | null>(null);
  // C5: reschedule straight from the board — the row's live appointment
  // plus the target resource's availability feed the shared modal.
  const [rescheduleTarget, setRescheduleTarget] = useState<{
    entry: TrackingEntry;
    appointment: RisAppointment;
    slots: ResourceAvailabilitySlot[];
    day: string;
  } | null>(null);
  const [rescheduleLoading, setRescheduleLoading] = useState(false);
  // M-1: staleness guard — last successful fetch time so operators can see
  // when the board data was actually retrieved.
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  // M-2: keep the user's page across auto-refresh (30s) so the board does not
  // silently jump back to page 1 while they review a later page.
  const pageRef = useRef(1);
  const pageSizeRef = useRef(20);

  // Debounce search
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(searchQuery), 300);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  // Debounce room filter
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedRoom(roomFilter.trim()), 300);
    return () => clearTimeout(timer);
  }, [roomFilter]);

  const buildQuery = useCallback(
    (overrides?: Record<string, string>) => {
      const query: Record<string, string> = {};
      if (modalityFilter) query.modality = modalityFilter;
      if (statusFilter) query.status = statusFilter;
      if (priorityFilter) query.priority = priorityFilter;
      if (debouncedRoom) query.station_ae_title = debouncedRoom;
      if (dateRange?.[0]) query.date_from = dateRange[0].format("YYYY-MM-DD");
      if (dateRange?.[1]) query.date_to = dateRange[1].format("YYYY-MM-DD");
      if (debouncedSearch) query.search = debouncedSearch;
      if (overrides) Object.assign(query, overrides);
      return query;
    },
    [modalityFilter, statusFilter, priorityFilter, debouncedRoom, dateRange, debouncedSearch],
  );

  const fetchKpi = useCallback(() => {
    getTrackingKpi()
      .then((res) => {
        setKpi(res);
        setKpiError(null);
      })
      .catch(() => setKpiError("KPI unavailable"));
  }, []);

  const fetch = useCallback(
    (params?: any) => {
      setLoading(true);
      setError(null);
      const query = buildQuery();
      const page = params?.page ?? pageRef.current;
      const perPage = params?.per_page ?? pageSizeRef.current;
      if (page) query.page = String(page);
      if (perPage) query.per_page = String(perPage);
      listTracking(query)
        .then((res: any) => {
          setLoading(false);
          setData(Array.isArray(res.data) ? res.data : []);
          pageRef.current = res.page || page;
          pageSizeRef.current = res.per_page || perPage;
          setPagination((prev: any) => ({
            ...prev,
            total: res.total || 0,
            current: res.page || prev.current,
            pageSize: res.per_page || prev.pageSize,
          }));
          setLastUpdated(new Date());
        })
        .catch((e: any) => {
          setLoading(false);
          setError(e.message);
          message.error(e.message);
        });
      fetchKpi();
    },
    [buildQuery, fetchKpi],
  );

  useEffect(() => {
    fetch();
  }, [fetch]);

  useTenantRefetch(() => {
    fetch({ page: 1 });
    fetchKpi();
  });

  // Auto-refresh every 30s
  useEffect(() => {
    const interval = setInterval(() => {
      fetch();
      fetchKpi();
    }, 30000);
    return () => clearInterval(interval);
  }, [fetch, fetchKpi]);

  const handleStatusUpdate = useCallback(
    async (entry: TrackingEntry, newStatus: string) => {
      try {
        await updateTrackingStatus(entry.id, newStatus);
        message.success(`Status updated to ${newStatus}`);
        fetch();
      } catch (e: any) {
        message.error(e.message || "Failed to update status");
      }
    },
    [fetch],
  );

  // C5: open the shared reschedule modal against the entry's live
  // appointment — availability comes from the scheduling engine so the
  // picked slot is guaranteed free at submit time.
  const canSchedule = hasPermission("SCHEDULE_WRITE");
  const handleReschedule = useCallback(
    async (entry: TrackingEntry) => {
      if (!entry.appointment_id || !entry.resource_id) return;
      setRescheduleLoading(true);
      const day =
        (entry.scheduled_date || new Date().toISOString().slice(0, 10));
      try {
        const slots = await getResourceAvailability(entry.resource_id, day);
        setRescheduleTarget({
          entry,
          appointment: {
            id: entry.appointment_id,
            resource_id: entry.resource_id,
            patient_id: entry.patient_id,
            status: "SCHEDULED",
            start_time: `${entry.scheduled_date}T${entry.scheduled_time || "00:00"}:00Z`,
            end_time: `${entry.scheduled_date}T${entry.scheduled_time || "00:00"}:00Z`,
          },
          slots,
          day,
        });
      } catch (e: any) {
        message.error(e.message || "Could not load availability");
      } finally {
        setRescheduleLoading(false);
      }
    },
    [message],
  );

  const columns: any[] = useMemo(
    () => [
      {
        title: "Patient",
        dataIndex: "patient_name",
        width: "14%",
        render: (v: string) => v || "-",
      },
      { title: "Patient ID", dataIndex: "patient_id", width: "8%" },
      { title: "Accession #", dataIndex: "accession_number", width: "10%" },
      {
        title: "Modality",
        dataIndex: "modality",
        width: "6%",
        render: (v: string) => (v ? <Tag>{v}</Tag> : "-"),
      },
      {
        title: "Procedure",
        dataIndex: "requested_procedure_desc",
        width: "14%",
        render: (v: string) => v || "-",
      },
      {
        title: "Scheduled",
        width: "12%",
        render: (_: any, r: TrackingEntry) =>
          r.scheduled_date
            ? `${r.scheduled_date} ${r.scheduled_time || ""}`
            : "-",
      },
      {
        title: "Room",
        dataIndex: "station_ae_title",
        width: "8%",
        render: (v: string) => (v ? <Tag style={{ margin: 0 }}>{v}</Tag> : "-"),
      },
      {
        title: "Status",
        dataIndex: "status",
        width: "10%",
        render: (s: string) => (
          <Tag color={STATUS_COLORS[s] || "default"}>{s}</Tag>
        ),
      },
      {
        title: "Priority",
        dataIndex: "requested_procedure_priority",
        width: "8%",
        render: (v: string) => {
          if (!v) return "-";
          const color =
            PRIORITY_COLORS[v] || (v === "STAT" || v === "S" ? "red" : "default");
          return <Badge count={v} style={{ backgroundColor: color === "red" ? "#ff4d4f" : color === "orange" ? "#fa8c16" : "#d9d9d9", color: "#fff" }} />;
        },
      },
      {
        // S6-21: critical-result badge — persists until the finding is
        // acknowledged (backend surfaces has_critical from ris_critical_results).
        title: "Critical",
        dataIndex: "has_critical",
        key: "has_critical",
        width: "7%",
        render: (v: boolean | undefined) =>
          v ? (
            <Tag color="red" icon={<AlertOutlined />}>
              CRITICAL
            </Tag>
          ) : null,
      },
      ...(canWrite
        ? [
            {
              title: "Actions",
              key: "actions",
              width: "12%",
              render: (_: any, record: TrackingEntry) => {
                const transitions = VALID_TRANSITIONS[record.status] || [];
                const canReschedule =
                  canSchedule &&
                  record.status === "scheduled" &&
                  !!record.appointment_id;
                if (transitions.length === 0 && !canReschedule)
                  return <span>-</span>;
                return (
                  <Space size="small">
                    {canReschedule && (
                      <Tooltip title="Reschedule">
                        <Button
                          size="small"
                          aria-label="Reschedule"
                          icon={<CalendarOutlined />}
                          loading={rescheduleLoading}
                          onClick={() => void handleReschedule(record)}
                        />
                      </Tooltip>
                    )}
                    {transitions.includes("arrived") && (
                      <Tooltip title="Check In">
                        <Button
                          size="small"
                          aria-label="Check In"
                          icon={<CheckCircleOutlined />}
                          onClick={() => handleStatusUpdate(record, "arrived")}
                        />
                      </Tooltip>
                    )}
                    {transitions.includes("in_progress") && (
                      <Tooltip title="Start Exam">
                        <Button
                          size="small"
                          type="primary"
                          aria-label="Start Exam"
                          icon={<ArrowRightOutlined />}
                          onClick={() =>
                            handleStatusUpdate(record, "in_progress")
                          }
                        />
                      </Tooltip>
                    )}
                    {transitions.includes("completed") && (
                      <Tooltip title="Complete">
                        <Button
                          size="small"
                          aria-label="Complete"
                          style={{ color: "#52c41a", borderColor: "#52c41a" }}
                          icon={<CheckCircleOutlined />}
                          onClick={() =>
                            handleStatusUpdate(record, "completed")
                          }
                        />
                      </Tooltip>
                    )}
                    {transitions.includes("cancelled") && (
                      <Popconfirm
                        title="Cancel this exam?"
                        onConfirm={() =>
                          handleStatusUpdate(record, "cancelled")
                        }
                      >
                        <Tooltip title="Cancel">
                          <Button
                            size="small"
                            aria-label="Cancel"
                            danger
                            icon={<CloseCircleOutlined />}
                          />
                        </Tooltip>
                      </Popconfirm>
                    )}
                  </Space>
                );
              },
            },
          ]
        : []),
    ],
    [canWrite, canSchedule, rescheduleLoading, handleStatusUpdate, handleReschedule],
  );

  return (
    <Content style={{ padding: 24 }} role="main">
      <KpiStrip
        kpi={kpi}
        kpiError={kpiError}
        lastUpdated={lastUpdated}
        onRefresh={() => {
          fetch();
          fetchKpi();
        }}
      />

      {/* Filters */}
      <Space style={{ marginBottom: 16 }} wrap>
        <Input.Search
          placeholder="Search patient/accession..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          onSearch={() => fetch({ page: 1 })}
          style={{ width: 220 }}
          allowClear
        />
        <Select
          allowClear
          placeholder="Modality"
          aria-label="Modality filter"
          value={modalityFilter}
          onChange={(v) => {
            setModalityFilter(v);
            pageRef.current = 1;
            setPagination((p: any) => ({ ...p, current: 1 }));
          }}
          style={{ width: 120 }}
          options={[
            { value: "CT", label: "CT" },
            { value: "MR", label: "MR" },
            { value: "MRI", label: "MRI" },
            { value: "PET", label: "PET" },
            { value: "DX", label: "DX" },
            { value: "US", label: "US" },
            { value: "MG", label: "MG" },
            { value: "XA", label: "XA" },
            { value: "NM", label: "NM" },
          ]}
        />
        <Select
          allowClear
          placeholder="Status"
          aria-label="Status filter"
          value={statusFilter}
          onChange={(v) => {
            setStatusFilter(v);
            pageRef.current = 1;
            setPagination((p: any) => ({ ...p, current: 1 }));
          }}
          style={{ width: 140 }}
          options={[
            { value: "scheduled", label: "Scheduled" },
            { value: "arrived", label: "Arrived" },
            { value: "in_progress", label: "In Progress" },
            { value: "performed", label: "Performed" },
            { value: "completed", label: "Completed" },
            { value: "cancelled", label: "Cancelled" },
          ]}
        />
        <Select
          allowClear
          placeholder="Priority"
          aria-label="Priority filter"
          value={priorityFilter}
          onChange={(v) => {
            setPriorityFilter(v);
            pageRef.current = 1;
            setPagination((p: any) => ({ ...p, current: 1 }));
          }}
          style={{ width: 120 }}
          options={[
            { value: "STAT", label: "STAT" },
            { value: "URGENT", label: "Urgent" },
            { value: "ROUTINE", label: "Routine" },
          ]}
        />
        <Input
          allowClear
          aria-label="Room filter"
          placeholder="Room / station AE"
          value={roomFilter}
          onChange={(e) => {
            setRoomFilter(e.target.value);
            pageRef.current = 1;
            setPagination((p: any) => ({ ...p, current: 1 }));
          }}
          style={{ width: 150 }}
        />
        <DatePicker.RangePicker
          aria-label="Date range filter"
          value={dateRange}
          onChange={(v) => {
            setDateRange(v as [any, any]);
            pageRef.current = 1;
            setPagination((p: any) => ({ ...p, current: 1 }));
          }}
          allowClear
          style={{ width: 240 }}
        />
      </Space>

      <PageState
        error={error}
        onRetry={() => fetch()}
        empty={!loading && !error && data.length === 0}
        emptyMessage="No exams on the tracking board"
      >
        <Table
          rowKey="id"
          columns={columns}
          dataSource={data}
          loading={loading}
          pagination={{
            ...pagination,
            showSizeChanger: true,
            showTotal: (total: number) => `${total} exams`,
          }}
          onChange={(pag: any) => {
            pageRef.current = pag.current || 1;
            pageSizeRef.current = pag.pageSize || 20;
            setPagination(pag);
            fetch({ page: pag.current, per_page: pag.pageSize });
          }}
          size="middle"
          rowClassName={(record: TrackingEntry) =>
            record.requested_procedure_priority === "STAT" ||
            record.requested_procedure_priority === "S"
              ? "tracking-stat-row"
              : ""
          }
        />
      </PageState>

      {/* Detail Modal */}
      <Modal
        title="Exam Details"
        open={!!detailModal}
        onCancel={() => setDetailModal(null)}
        footer={null}
        width={600}
      >
        {detailModal && (
          <Descriptions bordered column={1} size="small">
            <Descriptions.Item label="Patient">
              {detailModal.patient_name} ({detailModal.patient_id})
            </Descriptions.Item>
            <Descriptions.Item label="Accession #">
              {detailModal.accession_number}
            </Descriptions.Item>
            <Descriptions.Item label="Modality">
              <Tag>{detailModal.modality}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="Procedure">
              {detailModal.requested_procedure_desc || "-"}
            </Descriptions.Item>
            <Descriptions.Item label="Status">
              <Tag color={STATUS_COLORS[detailModal.status]}>
                {detailModal.status}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="Priority">
              {detailModal.requested_procedure_priority || "Routine"}
            </Descriptions.Item>
            <Descriptions.Item label="Scheduled">
              {detailModal.scheduled_date} {detailModal.scheduled_time || ""}
            </Descriptions.Item>
            <Descriptions.Item label="Room">
              {detailModal.station_ae_title || "-"}
            </Descriptions.Item>
          </Descriptions>
        )}
      </Modal>
      {rescheduleTarget && (
        <RescheduleModal
          open
          appointment={rescheduleTarget.appointment}
          slots={rescheduleTarget.slots}
          day={rescheduleTarget.day}
          onClose={() => setRescheduleTarget(null)}
          onDone={() => {
            setRescheduleTarget(null);
            fetch();
            fetchKpi();
          }}
        />
      )}
    </Content>
  );
}

export default withSidebar(TrackingBoard);
