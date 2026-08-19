/**
 * Shared scheduling-board constants — the calendar grid and the resources
 * board both render a fixed 30-min-slot window, so the window bounds and slot
 * size live in one module instead of being duplicated per component.
 */
export const BOARD_START_HOUR = 7; // 07:00
export const BOARD_END_HOUR = 19; // 19:00 (exclusive)
export const SLOT_MINUTES = 30;