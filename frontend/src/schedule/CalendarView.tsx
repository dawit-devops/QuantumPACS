import { CalendarOutlined, PlusOutlined } from "@ant-design/icons";
import { App, Button, Drawer, Empty, Spin, Tag, Alert } from "antd";
import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { type Window } from "./boardSlots";
import { dayjs } from "./time";
import BookingFormModal from "./BookingFormModal";
import ScheduleDayNav from "./ScheduleDayNav";
import CancelModal from "./CancelModal";
import RescheduleModal from "./RescheduleModal";
import CalendarGrid, { statusLabel } from "./CalendarGrid";
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
import { SCHEDULE_CALENDAR_STATUS_COLORS } from "../common/statusColors";
import "./schedule.css";

const STATUS_COLORS = SCHEDULE_CALENDAR_STATUS_COLORS;

// CalendarView uses the 07:00–19:00 window (default) — out-of-window
// times return null so the row simply doesn't render.
const BOARD_WINDOW: Window = { start: 7, end: 19 };

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

  // T1: anchor the day in UTC — the backend interprets dates as UTC
  // (engine.py _slot_within_windows compares UTC wall-clock), so the
  // calendar must match. Browser-local dayjs() would point at yesterday
  // for users in UTC+8 between 00:00-08:00.
  const [day, setDay] = useState<string>(() => dayjs.utc().format("YYYY-MM-DD"));
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
    // R3: clear stale grid data on fetch start — if this fetch fails,
    // the user sees an empty grid + error, not the previous day's bookings
    // under a new date header.
    setAppointments({});
    setFreeSlots({});
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
          <ScheduleDayNav
            onDayChange={changeDay}
            onToday={() => setDay(dayjs.utc().format("YYYY-MM-DD"))}
          />
        </div>
      </div>

      {error && <Alert type="error" showIcon title={error} style={{ marginBottom: 16 }} />}

      {loading ? (
        <div style={{ padding: 40, textAlign: "center" }}>
          <Spin />
        </div>
      ) : resources.length === 0 ? (
        <Empty description="No resources configured — add them from the Resources page." />
      ) : (
        <CalendarGrid
          day={day}
          window={BOARD_WINDOW}
          resources={resources}
          appointments={appointments}
          freeSlots={freeSlots}
          canWrite={canWrite}
          onOpenBooking={openBooking}
          onSelectAppointment={(a, r) => {
            setSelected(a);
            setDetailResource(r);
          }}
        />
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
              )
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
