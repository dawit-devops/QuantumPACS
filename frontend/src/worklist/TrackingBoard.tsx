import { useDocumentTitle, useTenantRefetch } from "../hooks";
import React, { useState, useEffect, useCallback, useMemo } from "react";
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
  Statistic,
  Row,
  Col,
  Modal,
  Descriptions,
} from "antd";
import {
  ReloadOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ClockCircleOutlined,
  ExclamationCircleOutlined,
  ArrowRightOutlined,
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
import { PageState } from "../common/PageState";
import "./TrackingBoard.css";

const { Content } = Layout;

const STATUS_COLORS: Record<string, string> = {
  scheduled: "blue",
  arrived: "cyan",
  in_progress: "orange",
  completed: "green",
  cancelled: "red",
};

const PRIORITY_COLORS: Record<string, string> = {
  STAT: "red",
  S: "red",
  A: "orange",
  ASAP: "orange",
  U: "orange",
  URGENT: "orange",
  T: "orange",
  R: "default",
  ROUTINE: "default",
};

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
  const [modalityFilter, setModalityFilter] = useState<string | undefined>();
  const [statusFilter, setStatusFilter] = useState<string | undefined>();
  const [searchQuery, setSearchQuery] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [detailModal, setDetailModal] = useState<TrackingEntry | null>(null);

  // Debounce search
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(searchQuery), 300);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  const buildQuery = useCallback(
    (overrides?: Record<string, string>) => {
      const query: Record<string, string> = {};
      if (modalityFilter) query.modality = modalityFilter;
      if (statusFilter) query.status = statusFilter;
      if (debouncedSearch) query.search = debouncedSearch;
      if (overrides) Object.assign(query, overrides);
      return query;
    },
    [modalityFilter, statusFilter, debouncedSearch],
  );

  const fetchKpi = useCallback(() => {
    getTrackingKpi()
      .then((res) => setKpi(res))
      .catch(() => {});
  }, []);

  const fetch = useCallback(
    (params?: any) => {
      setLoading(true);
      setError(null);
      const query = buildQuery();
      if (params?.page) query.page = String(params.page);
      if (params?.per_page) query.per_page = String(params.per_page);
      listTracking(query)
        .then((res: any) => {
          setLoading(false);
          setData(Array.isArray(res.data) ? res.data : []);
          setPagination((prev: any) => ({
            ...prev,
            total: res.total || 0,
            current: res.page || prev.current,
          }));
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
      ...(canWrite
        ? [
            {
              title: "Actions",
              key: "actions",
              width: "10%",
              render: (_: any, record: TrackingEntry) => {
                const transitions = VALID_TRANSITIONS[record.status] || [];
                if (transitions.length === 0) return <span>-</span>;
                return (
                  <Space size="small">
                    {transitions.includes("arrived") && (
                      <Tooltip title="Check In">
                        <Button
                          size="small"
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
    [canWrite, handleStatusUpdate],
  );

  return (
    <Content style={{ padding: 24 }} role="main">
      {/* KPI Strip */}
      {kpi && (
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col span={4}>
            <Statistic title="Today's Volume" value={kpi.volume} />
          </Col>
          <Col span={4}>
            <Statistic
              title="In Progress"
              value={kpi.in_progress}
              valueStyle={{ color: "#fa8c16" }}
            />
          </Col>
          <Col span={4}>
            <Statistic
              title="Awaiting Read"
              value={kpi.awaiting_read}
              valueStyle={{ color: "#1890ff" }}
            />
          </Col>
          <Col span={4}>
            <Statistic
              title="Overdue"
              value={kpi.overdue}
              valueStyle={{ color: kpi.overdue > 0 ? "#ff4d4f" : undefined }}
            />
          </Col>
          <Col span={4}>
            <Statistic
              title="STAT Queue"
              value={kpi.stat_count}
              valueStyle={{ color: kpi.stat_count > 0 ? "#ff4d4f" : undefined }}
            />
          </Col>
          <Col span={4}>
            <Button
              icon={<ReloadOutlined />}
              onClick={() => {
                fetch();
                fetchKpi();
              }}
              style={{ marginTop: 24 }}
            >
              Refresh
            </Button>
          </Col>
        </Row>
      )}

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
          value={modalityFilter}
          onChange={(v) => {
            setModalityFilter(v);
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
          value={statusFilter}
          onChange={(v) => {
            setStatusFilter(v);
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
    </Content>
  );
}

export default withSidebar(TrackingBoard);
