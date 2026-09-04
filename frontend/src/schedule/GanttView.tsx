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

/** Gantt day lane: 07:00–19:00 same as the day grid. */
const LANE_START = 7; // 07:00
const LANE_END = 19; // 19:00
const LANE_MINUTES = (LANE_END - LANE_START) * 60; // 720

interface GanttViewProps {
  anchor: string; // YYYY-MM-DD — the week containing this day is shown
  appointments: RisAppointment[];
  resources: RisResource[];
  onSelectAppointment: (appointment: RisAppointment, resource?: RisResource) => void;
}

/**
 * S-14: Gantt-style multi-day view. Rows are resources (rooms/techs),
 * columns are Mon–Sun. Each cell shows appointment bars positioned by
 * start time (07:00–19:00 lane) with height proportional to duration.
 */
export default function GanttView({
  anchor,
  appointments,
  resources,
  onSelectAppointment,
}: GanttViewProps) {
  const weekDays = useMemo(() => {
    const anchorDate = dayjs.utc(anchor);
    const monday = anchorDate.subtract(mondayStartDay(anchorDate), "day");
    return Array.from({ length: 7 }, (_, i) => monday.add(i, "day"));
  }, [anchor]);

  // Bucket appointments by resource_id + day
  const byResourceDay = useMemo(() => {
    const map: Record<string, Record<string, RisAppointment[]>> = {};
    for (const a of appointments) {
      const d = dayjs.utc(a.start_time).format("YYYY-MM-DD");
      (map[a.resource_id] ??= {})[d] ??= [];
      map[a.resource_id][d].push(a);
    }
    // Sort within each day
    for (const rmap of Object.values(map)) {
      for (const list of Object.values(rmap)) {
        list.sort((a, b) => a.start_time.localeCompare(b.start_time));
      }
    }
    return map;
  }, [appointments]);

  const resourceMap = useMemo(() => {
    const m: Record<string, RisResource> = {};
    for (const r of resources) m[r.id] = r;
    return m;
  }, [resources]);

  const weekKeys = useMemo(() => weekDays.map((d) => d.format("YYYY-MM-DD")), [weekDays]);

  /** Convert a time string to a lane percentile (0–100). */
  const laneTop = (time: string): number => {
    const m = dayjs.utc(time);
    const min = m.hour() * 60 + m.minute();
    const clamped = Math.max(LANE_START * 60, Math.min(LANE_END * 60, min));
    return ((clamped - LANE_START * 60) / LANE_MINUTES) * 100;
  };

  const barHeight = (start: string, end: string): number => {
    const s = dayjs.utc(start);
    const e = dayjs.utc(end);
    const dur = Math.max(e.diff(s, "minute"), 15); // minimum 15 min visible
    return Math.min((dur / LANE_MINUTES) * 100, 100);
  };

  return (
    <div className="sched-gantt-scroll" role="grid" aria-label="Gantt schedule">
      <div className="sched-gantt-table">
        {/* Header row */}
        <div className="sched-gantt-row is-header">
          <div className="sched-gantt-resource-head" role="columnheader">
            Resource
          </div>
          {weekDays.map((d, i) => (
            <div key={i} className="sched-gantt-day-head" role="columnheader">
              <span className="sched-gantt-day-name">{WEEKDAY_LABELS[i]}</span>
              <span className="sched-gantt-day-date">{d.format("DD MMM")}</span>
            </div>
          ))}
        </div>

        {/* Resource rows */}
        {resources.map((r) => {
          const resourceDayMap = byResourceDay[r.id] ?? {};
          return (
            <div key={r.id} className="sched-gantt-row" role="row">
              <div
                className="sched-gantt-resource"
                role="rowheader"
                aria-label={`${r.name} (${r.resource_type})`}
              >
                <span className="sched-gantt-resource-name">{r.name}</span>
                <Tag
                  color={
                    r.resource_type === "ROOM"
                      ? "blue"
                      : r.resource_type === "TECH"
                        ? "purple"
                        : "cyan"
                  }
                  style={{ fontSize: 10, lineHeight: "16px", margin: 0 }}
                >
                  {r.resource_type}
                </Tag>
              </div>
              {weekKeys.map((d) => {
                const list = resourceDayMap[d] ?? [];
                return (
                  <div
                    key={d}
                    className="sched-gantt-cell"
                    role="gridcell"
                    aria-label={`${r.name} — ${d} — ${list.length} appointment${list.length === 1 ? "" : "s"}`}
                  >
                    {list.length === 0 ? (
                      <div className="sched-gantt-empty">—</div>
                    ) : (
                      <div className="sched-gantt-lane">
                        {list.map((a) => {
                          const top = laneTop(a.start_time);
                          const height = barHeight(a.start_time, a.end_time);
                          return (
                            <button
                              key={a.id}
                              type="button"
                              className={`sched-gantt-bar ${statusLabel(a.status).toLowerCase()}`}
                              style={{ top: `${top}%`, height: `${height}%` }}
                              onClick={() => onSelectAppointment(a, resourceMap[a.resource_id])}
                              aria-label={`${a.patient_id} ${dayjs.utc(a.start_time).format("HH:mm")}–${dayjs.utc(a.end_time).format("HH:mm")} (${statusLabel(a.status)})`}
                            >
                              <span className="sched-gantt-bar-time">
                                {dayjs.utc(a.start_time).format("HH:mm")}
                              </span>
                              <span className="sched-gantt-bar-patient">{a.patient_id}</span>
                            </button>
                          );
                        })}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          );
        })}
      </div>
    </div>
  );
}
