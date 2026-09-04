import React, { useMemo } from "react";
import { buildSlots, type Window } from "./boardSlots";
import { dayjs } from "./time";
import type { RisResource, RisAppointment, ResourceAvailabilitySlot } from "../api/scheduling";
import { statusLabel } from "./CalendarGrid";
import "./schedule.css";

const SLOT_MINUTES = 30;

interface HeatmapViewProps {
  window: Window;
  resources: RisResource[];
  appointments: Record<string, RisAppointment[]>;
  freeSlots: Record<string, ResourceAvailabilitySlot[]>;
  canWrite: boolean;
  onOpenBooking: (resource: RisResource, slot: ResourceAvailabilitySlot) => void;
  onSelectAppointment: (appointment: RisAppointment, resource: RisResource) => void;
}

type Utilization = "full" | "partial" | "free" | "closed";

// S-04: per-room utilization heatmap. Rows are resources, columns are the
// 30-min slots of the board window. A cell's color reflects how much of that
// slot a booking covers: full (≥50% covered) / partial (<50%) / free / closed
// (outside the resource's schedule). Clicking a full cell opens its first
// appointment; a free cell opens the booking form.
export default function HeatmapView({
  window,
  resources,
  appointments,
  freeSlots,
  canWrite,
  onOpenBooking,
  onSelectAppointment,
}: HeatmapViewProps) {
  const slots = useMemo(() => buildSlots(window), [window]);

  // For each resource + slot index, the appointments overlapping that slot and
  // the fraction of the slot they cover (0..1).
  const occupancy = useMemo(() => {
    const map: Record<
      string,
      { util: number; appts: RisAppointment[]; slot?: ResourceAvailabilitySlot }
    > = {};
    for (const r of resources) {
      for (const a of appointments[r.id] ?? []) {
        if (statusLabel(a.status) === "CANCELLED" || statusLabel(a.status) === "NO_SHOW") continue;
        // Compare wall-clock time-of-day only — appointments bucket by their
        // HH:mm like the day grid (the date belongs to the board being shown).
        const startMin = dayjs.utc(a.start_time).hour() * 60 + dayjs.utc(a.start_time).minute();
        const endMin = dayjs.utc(a.end_time).hour() * 60 + dayjs.utc(a.end_time).minute();
        slots.forEach((slot, si) => {
          const key = `${r.id}|${si}`;
          const [sh, sm] = slot.split(":").map(Number);
          const slotStartMin = sh * 60 + sm;
          const slotEndMin = slotStartMin + SLOT_MINUTES;
          const overlapMin = Math.max(
            0,
            Math.min(endMin, slotEndMin) - Math.max(startMin, slotStartMin)
          );
          if (overlapMin <= 0) return;
          const cell = (map[key] ??= { util: 0, appts: [] });
          cell.util += overlapMin / SLOT_MINUTES;
          cell.appts.push(a);
        });
      }
    }
    // Attach the free slot (for open-booking) and cap util at 1.
    for (const r of resources) {
      for (const s of freeSlots[r.id] ?? []) {
        const si = slots.indexOf(s.start);
        if (si < 0) continue;
        const key = `${r.id}|${si}`;
        const cell = (map[key] ??= { util: 0, appts: [] });
        cell.slot = s;
        cell.util = Math.min(cell.util, 1);
      }
    }
    return map;
  }, [resources, appointments, freeSlots, slots]);

  const utilization = (util: number, hasSlot: boolean): Utilization => {
    if (util >= 0.5) return "full";
    if (util > 0) return "partial";
    return hasSlot ? "free" : "closed";
  };

  return (
    <div className="sched-heat-scroll">
      <div
        className="sched-heat-grid"
        role="grid"
        aria-label="Room utilization heatmap"
        style={{
          gridTemplateColumns: `150px repeat(${slots.length}, minmax(56px, 1fr))`,
        }}
      >
        <div className="sched-heat-corner" role="columnheader">
          Resource
        </div>
        {slots.map((slot, si) => (
          <div key={slot} className="sched-heat-slot-head" role="columnheader">
            {si % 2 === 0 ? slot : ""}
          </div>
        ))}

        {resources.map((r) => (
          <React.Fragment key={r.id}>
            <div className="sched-heat-resource" role="rowheader">
              {r.name}
            </div>
            {slots.map((slot, si) => {
              const key = `${r.id}|${si}`;
              const cell = occupancy[key];
              const util = cell?.util ?? 0;
              const u = utilization(util, cell?.slot !== undefined);
              const appt = cell?.appts[0];
              const freeSlot = cell?.slot;
              return (
                <div
                  key={slot}
                  className={`sched-heat-cell is-${u}`}
                  role="button"
                  tabIndex={0}
                  data-testid={`heat-cell-${r.id}-${slot}`}
                  data-utilization={u}
                  aria-label={`${r.name} ${slot} — ${u}`}
                  onClick={() => {
                    if (appt) onSelectAppointment(appt, r);
                    else if (freeSlot && canWrite) onOpenBooking(r, freeSlot);
                  }}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault();
                      if (appt) onSelectAppointment(appt, r);
                      else if (freeSlot && canWrite) onOpenBooking(r, freeSlot);
                    }
                  }}
                />
              );
            })}
          </React.Fragment>
        ))}
      </div>
    </div>
  );
}
