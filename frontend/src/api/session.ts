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

export async function tryRefreshToken(): Promise<boolean> {
  // Single-flight: N concurrent 401s must not fire N parallel /auth/refresh
  // requests. All callers share one in-flight refresh, then a fresh one.
  if (refreshPromise) return refreshPromise;
  refreshPromise = (async () => {
    try {
      const resp = await fetch(`${API_URL}/auth/refresh`, {
        method: "POST",
        headers: new Headers({
          "Content-Type": "application/json",
          "X-CSRF-Token": "1",
        }),
      });
      if (!resp.ok) return false;
      const data = await resp.json();
      setTokens(data.access_token, data.refresh_token);
      return true;
    } catch {
      return false;
    } finally {
      refreshPromise = null;
    }
  })();
  return refreshPromise;
}
