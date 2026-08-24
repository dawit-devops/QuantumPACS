import { useDocumentTitle, useTenantRefetch } from "../hooks";
import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Layout, Tag, Spin, Alert, Button, Segmented, DatePicker } from "antd";
import { ReloadOutlined } from "@ant-design/icons";
import withSidebar from "../common/base";
import PageHeader from "../common/PageHeader";
import {
  listRisAppointments,
} from "../api/frontdesk";
import type { RisAppointment } from "../api/scheduling";
import dayjs from "dayjs";
import "./FrontDesk.css";

const Content = Layout.Content;

// FD-06: the today-schedule response augments the appointment with joined
// display fields (patient_name, modality/room from ris_resources, priority).
interface TodayAppointment extends RisAppointment {
  patient_name?: string;
  modality?: string;
  room?: string;
  priority?: string;
}

const STATUS_COLORS: Record<string, string> = {
  SCHEDULED: "blue",
  ARRIVED: "gold",
  IN_PROGRESS: "cyan",
  COMPLETED: "green",
  CANCELLED: "default",
  NO_SHOW: "magenta",
};

const STATUS_FILTERS = [
  { label: "All", value: "" },
  { label: "Scheduled", value: "SCHEDULED" },
  { label: "Arrived", value: "ARRIVED" },
  { label: "In Progress", value: "IN_PROGRESS" },
  { label: "Completed", value: "COMPLETED" },
  { label: "Cancelled", value: "CANCELLED" },
  { label: "No Show", value: "NO_SHOW" },
];

// FD-06: chronological view of today's appointments across all resources,
// quick-filtered by modality and status.
function ScheduleToday() {
  useDocumentTitle("QuantumPACS - Today's Schedule");
  const [day, setDay] = useState<string>(() => dayjs().format("YYYY-MM-DD"));
  const [data, setData] = useState<TodayAppointment[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState("");
  const [modalityFilter, setModalityFilter] = useState("");

  const fetch = useCallback(() => {
    setLoading(true);
    setError(null);
    const query: Record<string, string> = { date: day };
    if (modalityFilter) query.modality = modalityFilter;
    if (statusFilter) query.status = statusFilter;
    listRisAppointments(query)
      .then((rows) => {
        setLoading(false);
        setData(rows);
      })
      .catch((e: any) => {
        setLoading(false);
        setError(e.message);
      });
  }, [day, modalityFilter, statusFilter]);

  useEffect(() => {
    fetch();
  }, [fetch]);

  useTenantRefetch(fetch);

  const modalities = useMemo(() => {
    const all = Array.from(
      new Set(data.map((r) => r.modality).filter(Boolean)),
    ) as string[];
    return all.sort();
  }, [data]);

  const statusOptions = useMemo(
    () =>
      STATUS_FILTERS.filter(
        (f) => !f.value || data.some((r) => r.status === f.value),
      ),
    [data],
  );

  return (
    <Content style={{ padding: 24 }} role="main">
      <PageHeader
        title="Today's Schedule"
        description="All appointments across modalities, ordered by time"
        extra={
          <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
            <DatePicker
              aria-label="Schedule date"
              value={dayjs(day)}
              onChange={(d) => d && setDay(d.format("YYYY-MM-DD"))}
              allowClear={false}
            />
            <Button icon={<ReloadOutlined />} onClick={fetch}>
              Refresh
            </Button>
          </div>
        }
      />

      <div className="fd-chips" style={{ marginBottom: 16 }}>
        <Segmented
          aria-label="Modality filter"
          value={modalityFilter}
          onChange={(v) => setModalityFilter(String(v))}
          options={[
            { label: "All", value: "" },
            ...modalities.map((m) => ({ label: m, value: m })),
          ]}
        />
        <Segmented
          aria-label="Status filter"
          value={statusFilter}
          onChange={(v) => setStatusFilter(String(v))}
          options={statusOptions.map((f) => ({
            label: f.label,
            value: f.value,
          }))}
        />
      </div>

      {error && (
        <Alert
          type="error"
          title="Failed to load schedule"
          description={error}
          showIcon
          style={{ marginBottom: 16 }}
          action={
            <Button size="small" onClick={fetch}>
              Retry
            </Button>
          }
        />
      )}

      {loading && data.length === 0 ? (
        <div className="fd-loading">
          <Spin />
        </div>
      ) : data.length === 0 ? (
        <Alert
          type="info"
          showIcon
          title={`No appointments on ${day}`}
        />
      ) : (
        <table className="fd-schedule-table">
          <thead>
            <tr>
              <th>Time</th>
              <th>Patient</th>
              <th>Modality</th>
              <th>Room</th>
              <th>Status</th>
              <th>Priority</th>
            </tr>
          </thead>
          <tbody>
            {data.map((row) => (
              <tr key={row.id}>
                <td>
                  {dayjs(row.start_time).format("HH:mm")}
                </td>
                <td>{row.patient_name || row.patient_id}</td>
                <td>{row.modality || "—"}</td>
                <td>{row.room || "—"}</td>
                <td>
                  <Tag
                    color={STATUS_COLORS[row.status] || "default"}
                  >
                    {row.status}
                  </Tag>
                </td>
                <td>
                  {row.priority && ["STAT", "S"].includes(row.priority) ? (
                    <Tag color="red">STAT</Tag>
                  ) : (
                    <span className="fd-patient-meta">
                      {row.priority || "—"}
                    </span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </Content>
  );
}

export default withSidebar(ScheduleToday);
