/**
 * Narrow an unknown catch value to a displayable string. Scheduling pages
 * and mutations all surface failures via message.error/toast — keeping one
 * narrow helper in the shared tree avoids per-module copy-paste drift.
 */
export function toErrorMessage(e: unknown): string {
  if (e instanceof Error) return e.message;
  if (typeof e === "string") return e;
  // Plain-object rejections (e.g. the request client's API error shape,
  // or a mocked 409 {code, status, message}) carry the backend message
  // in .message — surface it instead of the generic fallback.
  if (e && typeof e === "object" && typeof (e as any).message === "string") {
    return (e as { message: string }).message;
  }
  return "An unexpected error occurred";
}
