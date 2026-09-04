/**
 * Shared dayjs setup for the schedule module. All schedule components import
 * dayjs from here instead of each calling dayjs.extend(utc) independently.
 * Also exports slotToIso — the repeated pattern of converting a UTC wall-clock
 * slot time ("HH:mm") into an ISO instant for the booking engine.
 */
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";

dayjs.extend(utc);

/** Convert a UTC day string + slot start time to an ISO instant. */
export function slotToIso(day: string, time: string): string {
  return dayjs.utc(`${day} ${time}`).toISOString();
}

export { dayjs };
