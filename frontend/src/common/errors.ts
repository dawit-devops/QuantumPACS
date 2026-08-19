/**
 * Narrow an unknown catch value to a displayable string. Scheduling pages
 * and mutations all surface failures via message.error/toast — keeping one
 * narrow helper in the shared tree avoids per-module copy-paste drift.
 */
export function toErrorMessage(e: unknown): string {
  if (e instanceof Error) return e.message;
  if (typeof e === "string") return e;
  return "An unexpected error occurred";
}