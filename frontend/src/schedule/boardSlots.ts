/**
 * Shared scheduling-board slot helpers. Both CalendarView and ScheduleBoard
 * render 30-min-slot grids with different day windows, so every function
 * takes explicit window bounds instead of relying on module-level constants.
 *
 * CalendarView uses { start: 7, end: 19 } (default) — out-of-window times
 * return null (the row doesn't exist in the grid).
 *
 * ScheduleBoard uses { start: 8, end: 18 } — out-of-window times clamp to
 * the nearest edge so nothing is lost from the legacy board's view.
 */

export interface Window {
  start: number; // inclusive hour, e.g. 7 or 8
  end: number; // exclusive hour, e.g. 18 or 19
}

export const DEFAULT_WINDOW: Window = { start: 7, end: 19 };
export const SLOT_MINUTES = 30;

/** Generate slot labels ("HH:00", "HH:30") for the given window. */
export function buildSlots(win: Window = DEFAULT_WINDOW): string[] {
  const slots: string[] = [];
  for (let h = win.start; h < win.end; h += 1) {
    slots.push(`${String(h).padStart(2, "0")}:00`);
    slots.push(`${String(h).padStart(2, "0")}:30`);
  }
  return slots;
}

/**
 * Slot index of a start time (HH:MM) within the window.
 * Returns null for out-of-window times (CalendarView convention — the row
 * simply doesn't exist in the grid).
 */
export function slotIndexFor(
  time: string | null | undefined,
  win: Window = DEFAULT_WINDOW,
): number | null {
  if (!time) return null;
  const [hStr, mStr] = time.split(":");
  const minutes = Number(hStr) * 60 + Number(mStr);
  const startMin = win.start * 60;
  if (minutes < startMin || minutes >= win.end * 60) return null;
  return Math.floor((minutes - startMin) / SLOT_MINUTES);
}

/**
 * Slot index with clamping (ScheduleBoard convention — out-of-window times
 * snap to the nearest edge so nothing is lost from view).
 */
export function slotIndexForClamped(
  time: string | null | undefined,
  win: Window = DEFAULT_WINDOW,
): number | null {
  if (!time) return null;
  const [hStr, mStr] = time.split(":");
  const minutes = Number(hStr) * 60 + Number(mStr);
  const startMin = win.start * 60;
  const endMin = win.end * 60;
  const slotCount = ((win.end - win.start) * 60) / SLOT_MINUTES;
  if (minutes < startMin || minutes >= endMin) {
    return minutes < startMin ? 0 : slotCount - 1;
  }
  return Math.floor((minutes - startMin) / SLOT_MINUTES);
}

/**
 * Number of grid rows an appointment spans (30-min slots), derived from
 * ISO timestamp strings. Returns at least 1.
 */
export function slotSpanFor(appt: {
  start_time: string;
  end_time: string;
}): number {
  const startMs = new Date(appt.start_time).getTime();
  const endMs = new Date(appt.end_time).getTime();
  if (Number.isNaN(startMs) || Number.isNaN(endMs)) return 1;
  const minutes = Math.max(0, (endMs - startMs) / 60_000);
  return Math.max(1, Math.ceil(minutes / SLOT_MINUTES));
}
