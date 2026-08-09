import { useDocumentTitle } from "../hooks";
import React, { useState, useEffect, useCallback, useMemo } from "react";
import {
  App,
  Layout,
  Button,
  Tag,
  Drawer,
  Descriptions,
  Spin,
  Empty,
  Alert,
  Popconfirm,
} from "antd";
import {
  LeftOutlined,
  RightOutlined,
  CalendarOutlined,
  PlusOutlined,
  DeleteOutlined,
} from "@ant-design/icons";
import withSidebar from "../common/base";
import { request } from "../helpers";
import { useAuth } from "../auth/AuthContext";
import {
  listAppointments,
  cancelAppointment,
  type Appointment,
} from "../api/frontdesk";
import AppointmentBooking from "../frontdesk/AppointmentBooking";
import dayjs from "dayjs";
import "./ScheduleBoard.css";

const Content = Layout.Content;

// Standard radiology modalities per the R04 spec (FR-R04-01). Custom station AE
// titles seen in the worklist data are appended dynamically.
const DEFAULT_MODALITIES = ["CT", "MRI", "PET", "DX", "MG", "US", "FL"];

// Board day window 08:00–18:00 in 30-min slots per FR-R04-01.
const BOARD_START_HOUR = 8;
const BOARD_END_HOUR = 18;
const SLOT_MINUTES = 30;

const STATUS_COLORS: Record<string, string> = {
  scheduled: "blue",
  performed: "green",
  cancelled: "red",
};

const BOARD_STATUS_COLORS: Record<string, string> = {
  scheduled: "var(--color-primary)",
  performed: "var(--color-success)",
  cancelled: "var(--color-error)",
};

function buildSlots(): string[] {
  const slots: string[] = [];
  for (let h = BOARD_START_HOUR; h < BOARD_END_HOUR; h += 1) {
    slots.push(`${String(h).padStart(2, "0")}:00`);
    slots.push(`${String(h).padStart(2, "0")}:30`);
  }
  return slots;
}

// Slot index of an exam's scheduled_time ("HH:mm") within the board window.
// Clamps out-of-window times to the nearest edge so nothing is lost from view.
function slotIndexFor(time: string | null | undefined): number | null {
  if (!time) return null;
  const [hStr, mStr] = time.split(":");
  const minutes = Number(hStr) * 60 + Number(mStr);
  const startMin = BOARD_START_HOUR * 60;
  const endMin = BOARD_END_HOUR * 60;
  const slotCount = ((BOARD_END_HOUR - BOARD_START_HOUR) * 60) / SLOT_MINUTES;
  if (minutes < startMin || minutes >= endMin) {
    return minutes < startMin ? 0 : slotCount - 1;
  }
  return Math.floor((minutes - startMin) / SLOT_MINUTES);
}

function ScheduleBoard() {
  useDocumentTitle("QuantumPACS - Schedule Board");
  const { message } = App.useApp();
  const { hasPermission } = useAuth();
  const canBook = hasPermission("SCHEDULE_WRITE");

  const [day, setDay] = useState<string>(() => dayjs().format("YYYY-MM-DD"));
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedEntry, setSelectedEntry] = useState<any | null>(null);
  const [bookingOpen, setBookingOpen] = useState(false);
  const [appointments, setAppointments] = useState<Appointment[]>([]);

  const fetch = useCallback(() => {
    setLoading(true);
    setError(null);
    request("worklist", {
      query: { date_from: day, date_to: day, per_page: "500" },
    })
      .then((res: any) => {
        setLoading(false);
        setData(Array.isArray(res.data) ? res.data : []);
      })
      .catch((e: any) => {
        setLoading(false);
        setError(e.message);
      });
  }, [day]);

  // Appointments feed the same day: list them so the board shows booked
  // capacity and the drawer can cancel them (SCHEDULE_WRITE).
  const fetchAppointments = useCallback(() => {
    listAppointments({ date: day })
      .then(setAppointments)
      .catch(() => {});
  }, [day]);

  useEffect(() => {
    fetch();
    fetchAppointments();
  }, [fetch, fetchAppointments]);

  const modalities = useMemo(() => {
    const fromData = new Set(
      data.map((e) => e.modality).filter(Boolean) as string[],
    );
    return [...new Set([...DEFAULT_MODALITIES, ...fromData])];
  }, [data]);

  const slots = useMemo(() => buildSlots(), []);

  const entriesByModality = useMemo(() => {
    const map: Record<string, any[]> = {};
    for (const entry of data) {
      const mod = entry.modality || "—";
      if (!map[mod]) map[mod] = [];
      map[mod].push(entry);
    }
    return map;
  }, [data]);

  // Pre-group entries by `${modality}|${slotIndex}` once per data change so the
  // per-cell render is a plain map lookup instead of filtering every render.
  const entriesByModalitySlot = useMemo(() => {
    const map: Record<string, any[]> = {};
    for (const entry of data) {
      const mod = entry.modality || "—";
      const si = slotIndexFor(entry.scheduled_time);
      if (si === null) continue;
      const key = `${mod}|${si}`;
      if (!map[key]) map[key] = [];
      map[key].push(entry);
    }
    return map;
  }, [data]);

  const stats = useMemo(() => {
    const byStatus: Record<string, number> = {};
    for (const entry of data) {
      byStatus[entry.status] = (byStatus[entry.status] || 0) + 1;
    }
    return {
      total: data.length,
      scheduled: byStatus.scheduled || 0,
      performed: byStatus.performed || 0,
      cancelled: byStatus.cancelled || 0,
    };
  }, [data]);

  const changeDay = (delta: number) => {
    setDay((prev) => dayjs(prev).add(delta, "day").format("YYYY-MM-DD"));
    setSelectedEntry(null);
  };

  const doCancelAppointment = async (id: string) => {
    try {
      await cancelAppointment(id);
      message.success("Appointment cancelled");
      fetch();
      fetchAppointments();
      setSelectedEntry(null);
    } catch (e: any) {
      message.error(e.message || "Cancel failed");
    }
  };

  const statusLabel = (s: string) => (s ? s : "scheduled");

  return (
    <Content style={{ padding: 24 }} role="main" id="main-content">
      <div className="schedule-header">
        <div className="schedule-header-title">
          <CalendarOutlined />
          <h2>Schedule Board</h2>
          <Tag>{day}</Tag>
          {appointments.length > 0 && (
            <Tag color="cyan">{appointments.length} booked</Tag>
          )}
        </div>
        <div className="schedule-header-nav">
          {canBook && (
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => setBookingOpen(true)}
            >
              Book Appointment
            </Button>
          )}
          <Button
            icon={<LeftOutlined />}
            onClick={() => changeDay(-1)}
            aria-label="Previous day"
          />
          <Button onClick={() => setDay(dayjs().format("YYYY-MM-DD"))}>
            Today
          </Button>
          <Button
            icon={<RightOutlined />}
            onClick={() => changeDay(1)}
            aria-label="Next day"
          />
        </div>
      </div>

      <div className="schedule-stats">
        <span>
          Total <b>{stats.total}</b>
        </span>
        <span>
          Scheduled{" "}
          <b style={{ color: "var(--color-primary)" }}>{stats.scheduled}</b>
        </span>
        <span>
          Performed{" "}
          <b style={{ color: "var(--color-success)" }}>{stats.performed}</b>
        </span>
        <span>
          Cancelled{" "}
          <b style={{ color: "var(--color-error)" }}>{stats.cancelled}</b>
        </span>
      </div>

      {appointments.length > 0 && (
        <div className="schedule-appointments">
          <div className="schedule-appointments-title">
            Booked appointments — {day}
          </div>
          {appointments.map((appt) => (
            <div key={appt.id} className="schedule-appointment">
              <span className="schedule-appointment-time">
                {appt.scheduled_time || "—"}
              </span>
              <span className="schedule-appointment-patient">
                {appt.patient_id}
              </span>
              <Tag color="cyan" style={{ margin: 0 }}>
                {appt.modality || "—"}
              </Tag>
              {canBook && appt.status !== "cancelled" && (
                <Popconfirm
                  title="Cancel this appointment?"
                  onConfirm={() => doCancelAppointment(appt.id)}
                >
                  <Button
                    size="small"
                    type="text"
                    danger
                    icon={<DeleteOutlined />}
                    aria-label={`Cancel appointment for ${appt.patient_id}`}
                  />
                </Popconfirm>
              )}
            </div>
          ))}
        </div>
      )}

      {error && (
        <Alert
          type="error"
          message="Failed to load schedule"
          description={error}
          showIcon
          style={{ marginBottom: 16 }}
          action={
            <Button size="small" onClick={() => fetch()}>
              Retry
            </Button>
          }
        />
      )}

      {loading ? (
        <div className="schedule-loading">
          <Spin />
        </div>
      ) : (
        <>
          {data.length === 0 && (
            <Empty
              description={`No worklist entries for ${day}`}
              style={{ marginBottom: 16 }}
            />
          )}
          {data.length >= 500 && (
            <Alert
              type="warning"
              showIcon
              style={{ marginBottom: 16 }}
              message="Showing the first 500 exams for this day — refine the date or use the worklist for more."
            />
          )}
          <div
            className="schedule-board"
            role="grid"
            aria-label="Schedule board"
          >
            <div className="schedule-grid">
              <div className="schedule-corner" role="columnheader">
                Time / Modality
              </div>
              {modalities.map((mod) => (
                <div
                  key={mod}
                  className="schedule-modality-header"
                  role="columnheader"
                >
                  {mod}
                </div>
              ))}

              {slots.map((slot, si) => (
                <React.Fragment key={slot}>
                  <div
                    className={`schedule-time ${si % 2 === 1 ? "is-half" : ""}`}
                    role="rowheader"
                  >
                    {si % 2 === 0 ? slot : ""}
                  </div>
                  {modalities.map((mod) => {
                    const inSlot = entriesByModalitySlot[`${mod}|${si}`] || [];
                    return (
                      <div key={mod} className="schedule-cell">
                        {inSlot.map((entry) => {
                          const st = statusLabel(entry.status);
                          return (
                            <div
                              key={entry.id}
                              className={`schedule-block ${st}`}
                              style={{
                                borderLeftColor: BOARD_STATUS_COLORS[st],
                              }}
                              role="button"
                              tabIndex={0}
                              onClick={() => setSelectedEntry(entry)}
                              onKeyDown={(e) => {
                                if (e.key === "Enter") setSelectedEntry(entry);
                              }}
                              aria-label={`${entry.patient_name || entry.patient_id} ${st} at ${entry.scheduled_time || slot}`}
                            >
                              <span className="schedule-block-time">
                                {entry.scheduled_time || slot}
                              </span>
                              <span className="schedule-block-patient">
                                {entry.patient_name || entry.patient_id}
                              </span>
                              {entry.status !== "scheduled" && (
                                <Tag
                                  color={STATUS_COLORS[entry.status]}
                                  style={{ margin: 0, fontSize: 10 }}
                                >
                                  {entry.status}
                                </Tag>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    );
                  })}
                </React.Fragment>
              ))}
            </div>
          </div>
        </>
      )}

      <Drawer
        title="Exam Details"
        open={!!selectedEntry}
        onClose={() => setSelectedEntry(null)}
        width={380}
      >
        {selectedEntry && (
          <Descriptions column={1} size="small" bordered>
            <Descriptions.Item label="Patient">
              {selectedEntry.patient_name || "—"}
            </Descriptions.Item>
            <Descriptions.Item label="Patient ID">
              {selectedEntry.patient_id || "—"}
            </Descriptions.Item>
            <Descriptions.Item label="Accession #">
              {selectedEntry.accession_number || "—"}
            </Descriptions.Item>
            <Descriptions.Item label="Modality">
              {selectedEntry.modality || "—"}
            </Descriptions.Item>
            <Descriptions.Item label="Station AE">
              {selectedEntry.station_ae_title || "—"}
            </Descriptions.Item>
            <Descriptions.Item label="Scheduled">
              {selectedEntry.scheduled_date || "—"}{" "}
              {selectedEntry.scheduled_time || ""}
            </Descriptions.Item>
            <Descriptions.Item label="Requested Procedure">
              {selectedEntry.requested_procedure_desc ||
                selectedEntry.requested_procedure_id ||
                "—"}
            </Descriptions.Item>
            <Descriptions.Item label="Status">
              <Tag color={STATUS_COLORS[selectedEntry.status] || "default"}>
                {selectedEntry.status || "scheduled"}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="Study UID">
              {selectedEntry.study_uid || "—"}
            </Descriptions.Item>
            <Descriptions.Item label="Performed">
              {selectedEntry.performed_at
                ? new Date(selectedEntry.performed_at).toLocaleString()
                : "—"}
            </Descriptions.Item>
          </Descriptions>
        )}
      </Drawer>

      <AppointmentBooking
        open={bookingOpen}
        onClose={() => setBookingOpen(false)}
        onBooked={() => {
          fetch();
          fetchAppointments();
        }}
        patientId=""
        patientName="New patient"
      />
    </Content>
  );
}

export default withSidebar(ScheduleBoard);
