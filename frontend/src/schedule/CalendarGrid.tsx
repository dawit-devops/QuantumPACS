import React, { useMemo } from "react";
import { Tag } from "antd";
import {
  buildSlots,
  slotIndexFor,
  slotSpanFor,
  type Window,
} from "./boardSlots";
import { dayjs } from "./time";
import { SCHEDULE_CALENDAR_STATUS_COLORS } from "../common/statusColors";
import type {
  RisResource,
  RisAppointment,
  ResourceAvailabilitySlot,
} from "../api/scheduling";
import "./schedule.css";

const STATUS_COLORS = SCHEDULE_CALENDAR_STATUS_COLORS;

export function statusLabel(s?: string): string {
  return s ? s : "SCHEDULED";
}

interface CalendarGridProps {
  day: string;
  window: Window;
  resources: RisResource[];
  appointments: Record<string, RisAppointment[]>;
  freeSlots: Record<string, ResourceAvailabilitySlot[]>;
  canWrite: boolean;
  onOpenBooking: (resource: RisResource, slot: ResourceAvailabilitySlot) => void;
  onSelectAppointment: (appointment: RisAppointment, resource: RisResource) => void;
}

// S4-14/S4-16 grid extracted from CalendarView (M-10): owns the busy/free
// derivation and the 30-min slot render. The parent keeps fetch, modal and
// drawer state; the grid stays a pure function of its props.
export default function CalendarGrid({
  day,
  window,
  resources,
  appointments,
  freeSlots,
  canWrite,
  onOpenBooking,
  onSelectAppointment,
}: CalendarGridProps) {
  const slots = useMemo(() => buildSlots(window), [window]);

  // appointment blocks bucketed by resource|slotIndex — each appointment is
  // registered on every row it spans so covered cells read as busy.
  const blocksByResourceSlot = useMemo(() => {
    const map: Record<string, RisAppointment[]> = {};
    for (const r of resources) {
      for (const a of appointments[r.id] ?? []) {
        const si = slotIndexFor(dayjs.utc(a.start_time).format("HH:mm"), window);
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
  }, [resources, appointments, window]);

  // free-slot lookup by resource|slotIndex (skip slots covered by a booking)
  const slotByResourceSlot = useMemo(() => {
    const map: Record<string, ResourceAvailabilitySlot> = {};
    for (const r of resources) {
      for (const s of freeSlots[r.id] ?? []) {
        const si = slotIndexFor(s.start, window);
        if (si === null) continue;
        const key = `${r.id}|${si}`;
        const booked = blocksByResourceSlot[key]?.length ?? 0;
        if (booked === 0) map[key] = s;
      }
    }
    return map;
  }, [resources, freeSlots, blocksByResourceSlot, window]);

  return (
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
                  role={free && canWrite ? "button" : "gridcell"}
                  tabIndex={free && canWrite ? 0 : undefined}
                  onClick={() => {
                    if (free && canWrite) {
                      onOpenBooking(r, free);
                    }
                  }}
                  onKeyDown={(e) => {
                    if ((e.key === "Enter" || e.key === " ") && free && canWrite) {
                      e.preventDefault();
                      onOpenBooking(r, free);
                    }
                  }}
                  aria-label={`${r.name} ${slot}${isBooked ? " (booked)" : free ? " (free)" : " (closed)"}`}
                >
                  {blocks.map((a) => {
                    const startSi = slotIndexFor(
                      dayjs.utc(a.start_time).format("HH:mm"),
                      window,
                    );
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
                          onSelectAppointment(a, r);
                        }}
                        onKeyDown={(e) => {
                          if (e.key === "Enter" || e.key === " ") {
                            e.preventDefault();
                            e.stopPropagation();
                            onSelectAppointment(a, r);
                          }
                        }}
                      >
                        <span className="sched-block-title">{a.patient_id}</span>
                        <span className="sched-block-meta">
                          <span>{dayjs.utc(a.start_time).format("HH:mm")}</span>
                          {(a as { priority?: string }).priority === "STAT" ||
                            (a as { priority?: string }).priority ===
                              "URGENT" ? (
                            <Tag
                              color={
                                (a as { priority?: string }).priority === "STAT"
                                  ? "red"
                                  : "orange"
                              }
                              style={{ margin: 0, fontSize: 10, lineHeight: '16px' }}
                            >
                              {(a as { priority?: string }).priority}
                            </Tag>
                          ) : null}
                          <Tag
                            color={STATUS_COLORS[statusLabel(a.status)]}
                            style={{ margin: 0, fontSize: 10, lineHeight: '16px' }}
                          >
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
  );
}