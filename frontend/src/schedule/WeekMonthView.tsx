import { Tag } from "antd";
import React, { useMemo } from "react";
import { SCHEDULE_CALENDAR_STATUS_COLORS } from "../common/statusColors";
import type { RisAppointment, RisResource } from "../api/scheduling";
import { dayjs } from "./time";
import { statusLabel } from "./CalendarGrid";
import "./schedule.css";

const STATUS_COLORS = SCHEDULE_CALENDAR_STATUS_COLORS;

const WEEKDAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

/** Monday-start weekday index: 0=Monday .. 6=Sunday (dayjs .day() is Sun-first). */
const mondayStartDay = (d: dayjs.Dayjs): number => (d.day() + 6) % 7;

interface WeekMonthViewProps {
  mode: "week" | "month";
  anchor: string; // YYYY-MM-DD (UTC) — the day the user is browsing
  appointments: RisAppointment[];
  resources: RisResource[];
  // resource may be undefined when an appointment references a decommissioned
  // resource — the detail drawer already falls back to resource_id.
  onSelectAppointment: (appointment: RisAppointment, resource?: RisResource) => void;
  onPickDay: (day: string) => void;
}

/**
 * S-03: week + month calendar views. Week renders 7 columns (Mon–Sun) with
 * each day's appointments as compact colored blocks; month renders the
 * standard monthly grid with per-day appointment dots colored by status.
 * Both are pure functions of the already-fetched date-range appointments
 * (CalendarView owns the fetch via listAppointmentsDateRange).
 */
export default function WeekMonthView({
  mode,
  anchor,
  appointments,
  resources,
  onSelectAppointment,
  onPickDay,
}: WeekMonthViewProps) {
  // Bucket appointments by their UTC calendar day.
  const byDay = useMemo(() => {
    const map: Record<string, RisAppointment[]> = {};
    for (const a of appointments) {
      const d = dayjs.utc(a.start_time).format("YYYY-MM-DD");
      (map[d] ??= []).push(a);
    }
    for (const list of Object.values(map)) {
      list.sort((a, b) => a.start_time.localeCompare(b.start_time));
    }
    return map;
  }, [appointments]);

  const resourceFor = useMemo(() => {
    const map: Record<string, RisResource> = {};
    for (const r of resources) map[r.id] = r;
    return map;
  }, [resources]);

  const weekDays = useMemo(() => {
    const anchorDate = dayjs.utc(anchor);
    const monday = anchorDate.subtract(mondayStartDay(anchorDate), "day");
    return Array.from({ length: 7 }, (_, i) => monday.add(i, "day"));
  }, [anchor]);

  // First weekday-7-row grid for the month containing `anchor`.
  const monthGrid = useMemo(() => {
    const anchorDate = dayjs.utc(anchor);
    const first = anchorDate.startOf("month");
    const daysInMonth = anchorDate.daysInMonth();
    const leading = mondayStartDay(first);
    const total = Math.ceil((leading + daysInMonth) / 7) * 7;
    const cells: Array<dayjs.Dayjs | null> = [];
    for (let i = 0; i < total; i++) {
      const dayNum = i - leading + 1;
      cells.push(dayNum >= 1 && dayNum <= daysInMonth ? first.date(dayNum) : null);
    }
    return { first, cells };
  }, [anchor]);

  if (mode === "week") {
    return (
      <div className="sched-wm-scroll" role="grid" aria-label="Week schedule">
        <div
          className="sched-wm-week"
          style={{ gridTemplateColumns: `repeat(7, minmax(150px, 1fr))` }}
        >
          {weekDays.map((d) => {
            const key = d.format("YYYY-MM-DD");
            const list = byDay[key] ?? [];
            return (
              <div key={key} className="sched-wm-day-col" role="columnheader">
                <button
                  type="button"
                  className="sched-wm-day-head"
                  data-testid="week-day-head"
                  onClick={() => onPickDay(key)}
                  aria-label={`View ${d.format("ddd DD MMM")}`}
                >
                  <span className="sched-wm-day-name">{d.format("ddd")}</span>
                  <span className="sched-wm-day-date">{d.format("DD MMM")}</span>
                  <span className="sched-wm-day-count">
                    {list.length} appt{list.length === 1 ? "" : "s"}
                  </span>
                </button>
                <div className="sched-wm-day-list">
                  {list.length === 0 ? (
                    <div className="sched-wm-empty">No appointments</div>
                  ) : (
                    list.map((a) => (
                      <button
                        key={a.id}
                        type="button"
                        className={`sched-wm-block ${statusLabel(a.status).toLowerCase()}`}
                        onClick={() => onSelectAppointment(a, resourceFor[a.resource_id])}
                      >
                        <span className="sched-wm-block-time">
                          {dayjs.utc(a.start_time).format("HH:mm")}
                        </span>
                        <span className="sched-wm-block-title">{a.patient_id}</span>
                        <Tag
                          color={STATUS_COLORS[statusLabel(a.status)]}
                          style={{ margin: 0, fontSize: 10, lineHeight: "16px" }}
                        >
                          {statusLabel(a.status)}
                        </Tag>
                      </button>
                    ))
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    );
  }

  return (
    <div className="sched-wm-scroll" role="grid" aria-label="Month schedule">
      <div className="sched-wm-month">
        <div className="sched-wm-weekdays">
          {WEEKDAY_LABELS.map((l) => (
            <div key={l} className="sched-wm-weekday">
              {l}
            </div>
          ))}
        </div>
        <div className="sched-wm-month-body">
          {monthGrid.cells.map((cell, i) => {
            if (!cell) return <div key={i} className="sched-wm-cell is-outside" />;
            const key = cell.format("YYYY-MM-DD");
            const list = byDay[key] ?? [];
            const isToday = key === dayjs.utc().format("YYYY-MM-DD");
            const dots = list.slice(0, 4);
            const overflow = list.length - dots.length;
            return (
              <button
                key={i}
                type="button"
                className={`sched-wm-cell ${isToday ? "is-today" : ""}`}
                onClick={() => onPickDay(key)}
                aria-label={`${key} — ${list.length} appointment${list.length === 1 ? "" : "s"}`}
                data-testid="month-day-cell"
              >
                <span className="sched-wm-cell-date">{cell.date()}</span>
                {dots.length > 0 && (
                  <span className="sched-wm-dots" data-testid="appointment-dots">
                    {dots.map((a) => (
                      <span
                        key={a.id}
                        className="sched-wm-dot"
                        style={{ background: STATUS_COLORS[statusLabel(a.status)] }}
                        title={`${a.patient_id} ${dayjs.utc(a.start_time).format("HH:mm")}`}
                      />
                    ))}
                    {overflow > 0 && <span className="sched-wm-overflow">+{overflow}</span>}
                  </span>
                )}
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
