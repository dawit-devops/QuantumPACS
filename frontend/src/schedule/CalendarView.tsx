import { LeftOutlined, RightOutlined, CalendarOutlined, PlusOutlined } from "@ant-design/icons";
import { App, Button, Drawer, Empty, Spin, Tag, Alert } from "antd";
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { BOARD_END_HOUR, BOARD_START_HOUR, SLOT_MINUTES } from "./boardSlots";
import BookingFormModal from "./BookingFormModal";
import CancelModal from "./CancelModal";
import RescheduleModal from "./RescheduleModal";
import {
  listRisResources,
  listResourceAppointments,
  getResourceAvailability,
  type RisResource,
  type RisAppointment,
  type ResourceAvailabilitySlot,
} from "../api/scheduling";
import { useAuth } from "../auth/AuthContext";
import withSidebar from "../common/base";
import { toErrorMessage } from "../common/errors";
import { useDocumentTitle, useTenantRefetch } from "../hooks";
import "./schedule.css";

dayjs.extend(utc);

const STATUS_COLORS: Record<string, string> = {
  SCHEDULED: "blue",
  ARRIVED: "orange",
  IN_PROGRESS: "cyan",
  COMPLETED: "green",
  CANCELLED: "red",
};

function buildSlots(): string[] {
  const slots: string[] = [];
  for (let h = BOARD_START_HOUR; h < BOARD_END_HOUR; h += 1) {
    slots.push(`${String(h).padStart(2, "0")}:00`);
    slots.push(`${String(h).padStart(2, "0")}:30`);
  }
  return slots;
}

// Slot index of a start time (HH:MM) within the board window. Returns null
// for anything outside the window — the row simply does not exist in the grid.
function slotIndexFor(time: string | null | undefined): number | null {
  if (!time) return null;
  const [hStr, mStr] = time.split(":");
  const minutes = Number(hStr) * 60 + Number(mStr);
  const startMin = BOARD_START_HOUR * 60;
  if (minutes < startMin || minutes >= BOARD_END_HOUR * 60) return null;
  return Math.floor((minutes - startMin) / SLOT_MINUTES);
}

// Number of grid rows an appointment spans (30-min slots), clamped to the
// board window so a long exam never bleeds past the last rendered row.
function slotSpanFor(appt: RisAppointment): number {
  const start = dayjs.utc(appt.start_time);
  const end = dayjs.utc(appt.end_time);
  if (!start.isValid() || !end.isValid()) return 1;
  const minutes = Math.max(0, end.diff(start, "minute"));
  return Math.max(1, Math.ceil(minutes / SLOT_MINUTES));
}

/**
 * S4-14/S4-16 calendar grid — per-resource day view. Rows are 30-min slots
 * across the board window, columns are resources; booked appointments render
 * as colored blocks (status color-coded) and clicking a free cell opens the
 * booking modal for that resource+slot. Row actions (reschedule/cancel) are
 * available from each block's detail drawer.
 */
function CalendarView() {
  useDocumentTitle("QuantumPACS - Schedule");
  const { message } = App.useApp();
  const { hasPermission } = useAuth();
  const canWrite = hasPermission("SCHEDULE_WRITE");

  const [day, setDay] = useState<string>(() => dayjs().format("YYYY-MM-DD"));
  const [resources, setResources] = useState<RisResource[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // per-resource appointments for the day
  const [appointments, setAppointments] = useState<Record<string, RisAppointment[]>>({});
  // per-resource free slots for the day
  const [freeSlots, setFreeSlots] = useState<Record<string, ResourceAvailabilitySlot[]>>({});

  // modal state
  const [bookFor, setBookFor] = useState<{
    resource: RisResource;
    slot: ResourceAvailabilitySlot;
  } | null>(null);
  const [selected, setSelected] = useState<RisAppointment | null>(null);
  const [detailResource, setDetailResource] = useState<RisResource | null>(null);
  const [rescheduleFor, setRescheduleFor] = useState<RisAppointment | null>(null);
  const [cancelFor, setCancelFor] = useState<RisAppointment | null>(null);

  // A slow response for an earlier day must never paint over a newer one
  // (same pattern as Visits' detailSeq guard).
  const fetchSeq = useRef(0);
  const fetch = useCallback(() => {
    const seq = ++fetchSeq.current;
    setLoading(true);
    setError(null);
    listRisResources()
      .then(async (res) => {
        const [apptMap, freeMap] = await Promise.all([
          Promise.all(res.map((r) => listResourceAppointments(r.id, day))),
          Promise.all(res.map((r) => getResourceAvailability(r.id, day))),
        ]);
        if (seq !== fetchSeq.current) return; // stale — drop
        setResources(res);
        const a: Record<string, RisAppointment[]> = {};
        const f: Record<string, ResourceAvailabilitySlot[]> = {};
        res.forEach((r, i) => {
          a[r.id] = apptMap[i];
          f[r.id] = freeMap[i];
        });
        setAppointments(a);
        setFreeSlots(f);
      })
      .catch((e: unknown) => {
        if (seq !== fetchSeq.current) return;
        setError(toErrorMessage(e) || "Failed to load schedule");
      })
      .finally(() => {
        if (seq === fetchSeq.current) setLoading(false);
      });
  }, [day]);

  useEffect(() => {
    fetch();
  }, [fetch]);

  // Tenant switch must repaint this page with the new tenant's data.
  useTenantRefetch(fetch);

  const changeDay = (delta: number) => {
    setDay((prev) => dayjs(prev).add(delta, "day").format("YYYY-MM-DD"));
    setSelected(null);
    setBookFor(null);
    setRescheduleFor(null);
    setCancelFor(null);
  };

  const slots = useMemo(() => buildSlots(), []);

  // appointment blocks bucketed by resource|slotIndex — each appointment is
  // registered on every row it spans so covered cells read as busy.
  const blocksByResourceSlot = useMemo(() => {
    const map: Record<string, RisAppointment[]> = {};
    for (const r of resources) {
      for (const a of appointments[r.id] ?? []) {
        const si = slotIndexFor(dayjs.utc(a.start_time).format("HH:mm"));
        if (si === null) continue;
        const span = slotSpanFor(a);
        for (let k = 0; k < span; k++) {
          const key = `${r.id}|${si + k}`;
          if (!map[key]) map[key] = [];
          map[key].push(a);
        }
      }
    }
    return map;
  }, [resources, appointments]);

  // free-slot lookup by resource|slotIndex (skip slots covered by a booking)
  const slotByResourceSlot = useMemo(() => {
    const map: Record<string, ResourceAvailabilitySlot> = {};
    for (const r of resources) {
      for (const s of freeSlots[r.id] ?? []) {
        const si = slotIndexFor(s.start);
        if (si === null) continue;
        const key = `${r.id}|${si}`;
        const booked = blocksByResourceSlot[key]?.length ?? 0;
        if (booked === 0) map[key] = s;
      }
    }
    return map;
  }, [resources, freeSlots, blocksByResourceSlot]);

  const openBooking = (resource: RisResource, slot: ResourceAvailabilitySlot) =>
    setBookFor({ resource, slot });

  const refreshAfterMutation = () => {
    setSelected(null);
    fetch();
  };

  const handleBookingConflict = (msg: string) => {
    message.warning(msg);
    fetch();
  };

  const openReschedule = () => {
    if (!selected) return;
    const r = resources.find((x) => x.id === selected.resource_id);
    const slots = (r ? (freeSlots[r.id] ?? []) : []).filter(
      (s) => s.start !== dayjs.utc(selected.start_time).format("HH:mm")
    );
    if (slots.length === 0) {
      message.info("No free slots available for rescheduling");
      return;
    }
    setRescheduleFor(selected);
  };

  const statusLabel = (s?: string) => (s ? s : "SCHEDULED");

  return (
    <div style={{ padding: 24 }} role="main">
      <div className="sched-header">
        <div className="sched-header-title">
          <CalendarOutlined />
          <h2>Schedule</h2>
          <Tag>{day}</Tag>
        </div>
        <div className="sched-header-nav">
          {canWrite && (
            <Button
              type="primary"
              icon={<PlusOutlined />}
              disabled={resources.length === 0}
              onClick={() => {
                const r = resources[0];
                const s = r ? freeSlots[r.id]?.[0] : undefined;
                if (r && s) openBooking(r, s);
                else message.info("No free slot available right now");
              }}
            >
              Book Appointment
            </Button>
          )}
          <Button icon={<LeftOutlined />} onClick={() => changeDay(-1)} aria-label="Previous day" />
          <Button onClick={() => setDay(dayjs().format("YYYY-MM-DD"))}>Today</Button>
          <Button icon={<RightOutlined />} onClick={() => changeDay(1)} aria-label="Next day" />
        </div>
      </div>

      {error && <Alert type="error" showIcon message={error} style={{ marginBottom: 16 }} />}

      {loading ? (
        <div style={{ padding: 40, textAlign: "center" }}>
          <Spin />
        </div>
      ) : resources.length === 0 ? (
        <Empty description="No resources configured — add them from the Resources page." />
      ) : (
        <div className="sched-calendar-scroll">
          <div
            className="sched-grid"
            role="grid"
            aria-label={`Schedule grid for ${day}`}
            style={{
              gridTemplateColumns: `90px repeat(${resources.length}, minmax(160px, 1fr))`,
            }}
          >
            <div className="sched-corner" role="columnheader">
              Time
            </div>
            {resources.map((r) => (
              <div key={r.id} className="sched-resource-header" role="columnheader">
                {r.name}
                <span className="sched-resource-sub">
                  {r.resource_type}
                  {r.modality ? ` · ${r.modality}` : ""}
                </span>
              </div>
            ))}

            {slots.map((slot, si) => (
              <React.Fragment key={slot}>
                <div className={`sched-time-col ${si % 2 === 1 ? "is-half" : ""}`} role="rowheader">
                  {si % 2 === 0 ? slot : ""}
                </div>
                {resources.map((r) => {
                  const cellKey = `${r.id}|${si}`;
                  const blocks = blocksByResourceSlot[cellKey] ?? [];
                  const free = slotByResourceSlot[cellKey];
                  const isBooked = blocks.length > 0;
                  return (
                    <div
                      key={r.id}
                      className={`sched-cell ${isBooked ? "is-full" : ""}`}
                      role="gridcell"
                      onClick={() => {
                        if (free && canWrite) {
                          openBooking(r, free);
                        }
                      }}
                      aria-label={`${r.name} ${slot}${isBooked ? " (booked)" : free ? " (free)" : " (closed)"}`}
                    >
                      {blocks.map((a) => {
                        const startSi = slotIndexFor(dayjs.utc(a.start_time).format("HH:mm"));
                        const span = slotSpanFor(a);
                        // Render the visible block only on the appointment's
                        // start row; later rows in the span just stay "busy".
                        if (startSi !== si) return null;
                        return (
                          <div
                            key={a.id}
                            className={`sched-block ${statusLabel(a.status).toLowerCase()}`}
                            role="button"
                            tabIndex={0}
                            onClick={(e) => {
                              e.stopPropagation();
                              setSelected(a);
                              setDetailResource(r);
                            }}
                            onKeyDown={(e) => {
                              if (e.key === "Enter") {
                                e.stopPropagation();
                                setSelected(a);
                                setDetailResource(r);
                              }
                            }}
                          >
                            <span className="sched-block-title">{a.patient_id}</span>
                            <span className="sched-block-meta">
                              <span>{dayjs.utc(a.start_time).format("HH:mm")}</span>
                              <Tag color={STATUS_COLORS[statusLabel(a.status)]}>
                                {statusLabel(a.status)}
                              </Tag>
                            </span>
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
      )}

      <BookingFormModal
        open={bookFor !== null}
        resource={bookFor?.resource ?? null}
        slot={bookFor?.slot ?? null}
        day={day}
        onClose={() => setBookFor(null)}
        onDone={refreshAfterMutation}
        onConflict={handleBookingConflict}
      />

      {/* appointment detail drawer with reschedule/cancel */}
      <Drawer title="Appointment" open={!!selected} onClose={() => setSelected(null)} size={400}>
        {selected && (
          <>
            <div className="sched-form-section">
              <div className="sched-order-meta">Patient</div>
              <div style={{ fontWeight: 600, marginBottom: 4 }}>{selected.patient_id}</div>
              <div className="sched-order-meta">
                Resource: {detailResource?.name ?? selected.resource_id}
              </div>
              <div className="sched-order-meta">
                Time: {dayjs.utc(selected.start_time).format("HH:mm")}–
                {dayjs.utc(selected.end_time).format("HH:mm")}
              </div>
              <div className="sched-order-meta" style={{ marginTop: 4 }}>
                Status:{" "}
                <Tag color={STATUS_COLORS[statusLabel(selected.status)]}>
                  {statusLabel(selected.status)}
                </Tag>
              </div>
            </div>

            {canWrite && selected.status !== "CANCELLED" && (
              <div className="sched-toolbar">
                <Button type="primary" onClick={openReschedule}>
                  Reschedule
                </Button>
                <Button danger onClick={() => setCancelFor(selected)}>
                  Cancel
                </Button>
              </div>
            )}
          </>
        )}
      </Drawer>

      <RescheduleModal
        open={rescheduleFor !== null}
        appointment={rescheduleFor}
        day={day}
        slots={
          rescheduleFor
            ? (resources.find((x) => x.id === rescheduleFor.resource_id)
                ? (freeSlots[rescheduleFor.resource_id] ?? [])
                : []
              ).filter((s) => s.start !== dayjs.utc(rescheduleFor.start_time).format("HH:mm"))
            : []
        }
        onClose={() => setRescheduleFor(null)}
        onDone={refreshAfterMutation}
        onConflict={handleBookingConflict}
      />

      <CancelModal
        open={cancelFor !== null}
        appointment={cancelFor}
        onClose={() => setCancelFor(null)}
        onDone={refreshAfterMutation}
      />
    </div>
  );
}

export default withSidebar(CalendarView);
