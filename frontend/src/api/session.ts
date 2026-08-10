import { API_URL } from "../config";

export function getAccessToken(): string | null {
  return localStorage.getItem("access_token");
}

export function getRefreshToken(): string | null {
  // Refresh token is never persisted to storage (S1); it lives only in the
  // HttpOnly refresh_token cookie set by the backend.
  return null;
}

export function setTokens(access: string, _refresh?: string): void {
  // Only the short-lived access token is stored; the refresh token travels
  // via HttpOnly cookie so XSS cannot exfiltrate a long-lived credential.
  localStorage.setItem("access_token", access);
}

export function clearTokens(): void {
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
}

let refreshTimer: ReturnType<typeof setInterval> | null = null;

export function startRefreshTimer(onRefreshFailed: () => void): void {
  stopRefreshTimer();
  refreshTimer = setInterval(
    async () => {
      const token = getAccessToken();
      if (!token) return;
      const ok = await tryRefreshToken();
      if (!ok) {
        // Refresh token expiry is unreadable (HttpOnly); approximate with the
        // access token's own expiry to avoid logging out on transient errors.
        const payload = token.split(".")[1];
        try {
          const decoded = JSON.parse(atob(payload));
          if (decoded.exp * 1000 < Date.now() + 60000) {
            onRefreshFailed();
          }
        } catch {}
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
          "X-CSRF-Token": "1",
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
