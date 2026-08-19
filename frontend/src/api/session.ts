import { API_URL } from "../config";

export function getAccessToken(): string | null {
  // IAM audit H-2: the access token is no longer readable from JS. It lives
  // exclusively in the HttpOnly `token` cookie set by the backend, which the
  // browser attaches to same-site requests automatically. Returning null
  // makes any leftover header-sending code a harmless no-op.
  return null;
}

export function getRefreshToken(): string | null {
  // Refresh token is never persisted to storage (S1); it lives only in the
  // HttpOnly refresh_token cookie set by the backend.
  return null;
}

export function setTokens(access: string, _refresh?: string): void {
  // IAM audit H-2: nothing to store — the server sets the HttpOnly access
  // cookie on login/refresh. Kept as a no-op so callers keep working.
  void access;
}

export function clearTokens(): void {
  // Stale keys from pre-cookie sessions; both the access and refresh cookies
  // are cleared server-side on logout.
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
}

let refreshTimer: ReturnType<typeof setInterval> | null = null;

export function startRefreshTimer(onRefreshFailed: () => void): void {
  stopRefreshTimer();
  refreshTimer = setInterval(
    async () => {
      // IAM audit H-2: token expiry is unreadable (HttpOnly cookie), so the
      // timer just refreshes proactively on its cadence. The server rotates
      // both cookies; a denied (401) refresh means a dead session, while a
      // rate-limited (429) or failed (network) refresh is transient.
      const ok = await tryRefreshToken();
      if (!ok && wasRefreshDenied()) {
        onRefreshFailed();
      }
    },
    25 * 60 * 1000,
  );
}

export function stopRefreshTimer(): void {
  if (refreshTimer !== null) {
    clearInterval(refreshTimer);
    refreshTimer = null;
  }
}

let refreshPromise: Promise<boolean> | null = null;
let lastRefreshStatus: number | null = null;

// A rate-limited refresh (429, R2-M9) means the session is alive but
// throttled — not dead. Callers must not bounce the user to /login on it.
export function wasRefreshRateLimited(): boolean {
  return lastRefreshStatus === 429;
}

// A denied refresh (401) means the session is gone — the token was revoked,
// expired, or the account is unavailable. Only this status may trigger the
// sign-out path; network errors (status null) are transient.
export function wasRefreshDenied(): boolean {
  return lastRefreshStatus === 401;
}

export async function tryRefreshToken(): Promise<boolean> {
  // Single-flight: N concurrent 401s must not fire N parallel /auth/refresh
  // requests. All callers share one in-flight refresh, then a fresh one.
  if (refreshPromise) return refreshPromise;
  refreshPromise = (async () => {
    try {
      const resp = await fetch(`${API_URL}/auth/refresh`, {
        method: "POST",
        // The refresh token lives in an HttpOnly cookie; in dev the API is
        // cross-origin (5173 -> 8080) so the default same-origin credential
        // mode would silently drop it and every refresh would 401.
        credentials: "include",
        headers: new Headers({
          "Content-Type": "application/json",
          "X-CSRF-Token": (() => {
            const m = document.cookie.match(/(?:^|;\s*)csrf_token=([^;]+)/);
            return m?.[1] ?? "1";
          })(),
        }),
      });
      if (!resp.ok) {
        lastRefreshStatus = resp.status;
        return false;
      }
      const data = await resp.json();
      setTokens(data.access_token, data.refresh_token);
      lastRefreshStatus = null;
      return true;
    } catch {
      lastRefreshStatus = null;
      return false;
    } finally {
      refreshPromise = null;
    }
  })();
  return refreshPromise;
}
