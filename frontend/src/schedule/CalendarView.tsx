import { CalendarOutlined, PlusOutlined } from "@ant-design/icons";
import { App, Button, Drawer, Empty, Popconfirm, Spin, Tag, Alert, Segmented, Select } from "antd";
import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useLocation } from "react-router";

import { type Window } from "./boardSlots";
import { dayjs } from "./time";
import BookingFormModal from "./BookingFormModal";
import ScheduleDayNav from "./ScheduleDayNav";
import CancelModal from "./CancelModal";
import RescheduleModal from "./RescheduleModal";
import CalendarGrid, { statusLabel } from "./CalendarGrid";
import WeekMonthView from "./WeekMonthView";
import GanttView from "./GanttView";
import HeatmapView from "./HeatmapView";
import BatchBookingModal from "./BatchBookingModal";
import WaitlistModal from "./WaitlistModal";
import {
  listRisResources,
  listResourceAppointments,
  getResourceAvailability,
  listAppointmentsDateRange,
  rescheduleAppointment,
  type RisResource,
  type RisAppointment,
  type ResourceAvailabilitySlot,
  markNoShow,
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

// S-03: week starts Monday; month is the whole UTC month containing the
// anchored day. Range fetch reuses the shipped date_from/date_to handler.
const weekRange = (d: string) => {
  const anchor = dayjs.utc(d);
  const monday = anchor.subtract((anchor.day() + 6) % 7, "day");
  return [monday.format("YYYY-MM-DD"), monday.add(6, "day").format("YYYY-MM-DD")];
};

const monthRange = (d: string) => {
  const first = dayjs.utc(d).startOf("month");
  return [first.format("YYYY-MM-DD"), first.endOf("month").format("YYYY-MM-DD")];
};

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
  // S-03: day/week/month toggle — week/month reuse the range appointments
  // API; the day grid keeps the per-resource availability view.
  const [view, setView] = useState<"day" | "week" | "month" | "gantt" | "heatmap">("day");
  const [resources, setResources] = useState<RisResource[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // per-resource appointments for the day
  const [appointments, setAppointments] = useState<Record<string, RisAppointment[]>>({});
  // per-resource free slots for the day
  const [freeSlots, setFreeSlots] = useState<Record<string, ResourceAvailabilitySlot[]>>({});
  // S-03: flat date-range appointments for week/month views
  const [rangeAppointments, setRangeAppointments] = useState<RisAppointment[]>([]);

  // S-09: an order to pre-fill into the booking form, carried here from the
  // Orders page via /schedule?order=<id>. Cleared after a successful booking
  // so a later free-cell click starts clean.
  const location = useLocation();
  const [orderPrefill, setOrderPrefill] = useState<string | null>(() =>
    new URLSearchParams(location.search).get("order")
  );

  // modal state
  const [bookFor, setBookFor] = useState<{
    resource: RisResource;
    slot: ResourceAvailabilitySlot;
  } | null>(null);
  const [selected, setSelected] = useState<RisAppointment | null>(null);
  const [detailResource, setDetailResource] = useState<RisResource | null>(null);
  const [rescheduleFor, setRescheduleFor] = useState<RisAppointment | null>(null);
  const [cancelFor, setCancelFor] = useState<RisAppointment | null>(null);
  // S-06: batch booking modal — book several slots on one resource at once.
  const [batchOpen, setBatchOpen] = useState(false);
  // S-08: waitlist modal — patients waiting for a cancelled slot.
  const [waitlistOpen, setWaitlistOpen] = useState(false);

  // S-11: calendar filters — narrow by resource type (room/modality/tech)
  // or modality. Passed server-side to listRisResources so appointments and
  // availability are only fetched for the shown resources.
  const [resTypeFilter, setResTypeFilter] = useState<string | undefined>();
  const [modalityFilter, setModalityFilter] = useState<string | undefined>();
  // Full unfiltered resource list — the modality dropdown must not collapse
  // to whatever the current filter happens to show.
  const [allResources, setAllResources] = useState<RisResource[]>([]);

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
    setRangeAppointments([]);
    listRisResources({
      ...(resTypeFilter ? { resource_type: resTypeFilter } : {}),
      ...(modalityFilter ? { modality: modalityFilter } : {}),
    })
      .then(async (res) => {
        if (view !== "day" && view !== "heatmap") {
          // S-03 week/month + S-14 gantt: one date-range query across all
          // resources. Gantt shows the anchored week (same range as week).
          const [from, to] = view === "month" ? monthRange(day) : weekRange(day);
          const rows = await listAppointmentsDateRange(from, to);
          if (seq !== fetchSeq.current) return; // stale — drop
          setResources(res);
          setRangeAppointments(rows);
          return;
        }
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
  }, [day, view, resTypeFilter, modalityFilter]);

  useEffect(() => {
    fetch();
  }, [fetch]);

  // Tenant switch must repaint this page with the new tenant's data.
  useTenantRefetch(fetch);

  // S-11: keep a full resource list so the modality/resource-type filter
  // options survive even when the grid itself is narrowed server-side.
  const loadAllResources = useCallback(() => {
    listRisResources()
      .then((res) => setAllResources(res))
      .catch(() => {
        /* filter options are best-effort — the grid still loads */
      });
  }, []);
  useEffect(() => {
    loadAllResources();
  }, [loadAllResources]);
  useTenantRefetch(loadAllResources);

  const modalityOptions = useMemo(
    () => [...new Set(allResources.map((r) => r.modality).filter(Boolean) as string[])].sort(),
    [allResources]
  );

  const changeDay = (delta: number) => {
    // S-03: prev/next shifts by the current view's unit (day/week/month);
    // S-14 gantt shifts by week like the week view.
    const unit = view === "month" ? "month" : view === "week" || view === "gantt" ? "week" : "day";
    setDay((prev) => dayjs(prev).add(delta, unit).format("YYYY-MM-DD"));
    setSelected(null);
    setBookFor(null);
    setRescheduleFor(null);
    setCancelFor(null);
  };

  // S-03: jump the anchored day to a specific date (week/day head clicks or
  // a month cell) and switch to the day grid.
  const pickDay = (d: string) => {
    setDay(d);
    setView("day");
    setSelected(null);
    setBookFor(null);
    setRescheduleFor(null);
    setCancelFor(null);
  };

  const openBooking = (resource: RisResource, slot: ResourceAvailabilitySlot) =>
    setBookFor({ resource, slot });

  const refreshAfterMutation = () => {
    setSelected(null);
    // S-09: one pre-filled order per visit — the next open starts clean.
    setOrderPrefill(null);
    fetch();
  };

  const handleBookingConflict = (msg: string) => {
    message.warning(msg);
    fetch();
  };

  // S-01: drop-to-rebook — drag a booked block onto a free cell and the
  // appointment moves there preserving its duration. Conflicts surface via
  // the same warning path as a modal reschedule.
  const rebookByDrag = (appointmentId: string, startIso: string, endIso: string) => {
    rescheduleAppointment(appointmentId, { new_start_time: startIso, new_end_time: endIso })
      .then(() => {
        message.success("Appointment moved");
        refreshAfterMutation();
      })
      .catch((e: unknown) => {
        handleBookingConflict(toErrorMessage(e) || "Could not move the appointment");
      });
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
          <Segmented
            value={view}
            onChange={(v) => setView(v as "day" | "week" | "month" | "gantt" | "heatmap")}
            options={[
              { label: "Day", value: "day" },
              { label: "Week", value: "week" },
              { label: "Month", value: "month" },
              { label: "Gantt", value: "gantt" },
              { label: "Heatmap", value: "heatmap" },
            ]}
            aria-label="Calendar view"
          />
          {canWrite && view === "day" && (
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
          {/* S-06: batch book several slots at once on one resource. */}
          {canWrite && view === "day" && (
            <Button
              disabled={resources.length === 0}
              onClick={() => setBatchOpen(true)}
              aria-label="Batch book"
            >
              Batch Book
            </Button>
          )}
          {/* S-08: waitlist — patients queued for cancelled slots. */}
          {canWrite && (
            <Button onClick={() => setWaitlistOpen(true)} aria-label="Waitlist">
              Waitlist
            </Button>
          )}
          <ScheduleDayNav
            onDayChange={changeDay}
            onToday={() => setDay(dayjs.utc().format("YYYY-MM-DD"))}
          />
        </div>
      </div>

      {/* S-11: filter the calendar to a resource type (room/modality/tech)
          and/or a modality. Both narrow the grid server-side. */}
      <div className="sched-toolbar" style={{ marginTop: -8 }}>
        <Select
          id="schedule-type-filter"
          aria-label="Resource type"
          allowClear
          placeholder="All resource types"
          style={{ width: 180 }}
          value={resTypeFilter}
          onChange={setResTypeFilter}
          options={[
            { value: "ROOM", label: "Rooms" },
            { value: "MODALITY", label: "Modalities" },
            { value: "TECH", label: "Technologists" },
          ]}
        />
        <Select
          id="schedule-modality-filter"
          aria-label="Modality"
          allowClear
          placeholder="All modalities"
          style={{ width: 140 }}
          value={modalityFilter}
          onChange={setModalityFilter}
          options={modalityOptions.map((m) => ({ value: m, label: m }))}
        />
      </div>

      {error && <Alert type="error" showIcon title={error} style={{ marginBottom: 16 }} />}

      {loading ? (
        <div style={{ padding: 40, textAlign: "center" }}>
          <Spin />
        </div>
      ) : resources.length === 0 ? (
        <Empty description="No resources configured — add them from the Resources page." />
      ) : view === "day" ? (
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
          onRebook={rebookByDrag}
        />
      ) : view === "heatmap" ? (
        <HeatmapView
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
      ) : view === "gantt" ? (
        <GanttView
          anchor={day}
          appointments={rangeAppointments}
          resources={resources}
          onSelectAppointment={(a, r) => {
            setSelected(a);
            setDetailResource(r ?? null);
          }}
        />
      ) : (
        <WeekMonthView
          mode={view}
          anchor={day}
          appointments={rangeAppointments}
          resources={resources}
          onSelectAppointment={(a, r) => {
            setSelected(a);
            setDetailResource(r ?? null);
          }}
          onPickDay={pickDay}
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
        orderId={orderPrefill}
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
                {/* S-13: no-show tracking — scheduled appointments the
                    patient never arrived for. */}
                {selected.status === "SCHEDULED" && (
                  <Popconfirm
                    title={`Mark ${selected.patient_id} as a no-show?`}
                    onConfirm={() => {
                      markNoShow(selected.id)
                        .then(() => {
                          message.success("Marked as no-show");
                          refreshAfterMutation();
                        })
                        .catch((e: unknown) =>
                          message.error(toErrorMessage(e) || "Failed to mark no-show")
                        );
                    }}
                  >
                    <Button danger aria-label="Mark as no-show">
                      Mark as no-show
                    </Button>
                  </Popconfirm>
                )}
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
            ? resources.find((x) => x.id === rescheduleFor.resource_id)
              ? (freeSlots[rescheduleFor.resource_id] ?? [])
              : []
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

      {/* S-06: batch booking — several slots on one resource at once. */}
      <BatchBookingModal
        open={batchOpen}
        day={day}
        resources={resources}
        onClose={() => setBatchOpen(false)}
        onDone={() => {
          setBatchOpen(false);
          refreshAfterMutation();
        }}
      />

      {/* S-08: waitlist — add/list/notify/remove patients on cancelled slots. */}
      <WaitlistModal
        open={waitlistOpen}
        resources={resources}
        onClose={() => setWaitlistOpen(false)}
        onDone={() => setWaitlistOpen(false)}
      />
    </div>
  );
}

export default withSidebar(CalendarView);
