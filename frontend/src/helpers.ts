import { API_URL } from "./config";
import { navigate } from "./navigator";

export const handleResponse = async (response: Response): Promise<any> => {
  if (!response) {
    return;
  }
  if (!response.ok && response.status !== 400) {
    const error = { error: response.status };
    throw error;
  }
  const json = await response.json();
  if (response.ok) {
    return json;
  } else {
    const error = { error: json };
    throw error;
  }
};

interface RequestOptions {
  method?: string;
  body?: string;
  headers?: Headers;
  data?: any;
  query?: Record<string, string>;
  unauthorized?: () => void;
  [key: string]: any;
}

export async function fetchWithRetry(
  url: string,
  options: RequestOptions,
  retries = 3,
): Promise<Response> {
  // Only idempotent GETs may be retried — repeating a POST/PUT/DELETE on a
  // 5xx can duplicate mutations (e.g. double-created resources in a batch).
  const method = (options.method || "GET").toUpperCase();
  const retryable = method === "GET";
  for (let i = 0; i < retries; i++) {
    const resp = await fetch(url, options);
    if (resp.ok || !retryable || resp.status < 500) {
      return resp;
    }
    if (i < retries - 1) {
      await new Promise((r) =>
        setTimeout(r, Math.min(1000 * Math.pow(2, i), 8000)),
      );
    }
  }
  return fetch(url, options);
}

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

export const request = async (
  url: string,
  options: RequestOptions = {},
): Promise<any> => {
  if (!url.startsWith("http")) {
    url = `${API_URL}/${url}`;
  }
  options.headers = new Headers({
    "Content-Type": "application/json",
    "X-CSRF-Token": "1",
  });
  const token = getAccessToken();
  if (token) {
    options.headers.set("X-Auth-Pacs", token);
  }
  if (options.data) {
    options.method = "POST";
    options.body = JSON.stringify(options.data);
    delete options.data;
  }
  if (options.query) {
    url = `${url}?${encodeQuery(options.query)}`;
    delete options.query;
  }
  const exec = async (): Promise<any> => {
    const resp = await fetchWithRetry(url, options);
    return await handleResponse(resp);
  };
  try {
    return await exec();
  } catch (error: any) {
    if (error.error === 401) {
      const tempKey = localStorage.getItem("tempKey");
      if (tempKey) {
        sessionStorage.setItem("shareKeyError", "expired");
      }
      const refreshed = await tryRefreshToken();
      if (refreshed) {
        const newToken = getAccessToken();
        if (newToken) {
          options.headers.set("X-Auth-Pacs", newToken);
        }
        try {
          return await exec();
        } catch (retryError: any) {
          // Only a second 401 means the session is really dead; any other
          // failure of the retried request must surface to the caller instead
          // of bouncing the user to the login screen.
          if (retryError.error !== 401) throw retryError;
        }
      }
      if (options.unauthorized) {
        options.unauthorized();
      } else {
        navigate("/login");
      }
    }
    if (!error.code || error.code !== 20) {
      throw Error(error.error || error.message || error);
    }
  }
};

export const open = async (url: string): Promise<void> => {
  // Same-site navigation; the HttpOnly token cookie authenticates it, so no
  // token needs to be appended to the URL (S1-D).
  window.open(`${API_URL}/${url}`);
};

export const parseParams = (search: string): Record<string, string> => {
  search = search.slice(1);
  const parts = search.split("&");
  const params: Record<string, string> = {};
  for (const part of parts) {
    const [name, value] = part.split("=");
    if (name) params[name] = value;
  }
  return params;
};

export const encodeQuery = (data: Record<string, string>): string => {
  const ret: string[] = [];
  for (const d in data) {
    ret.push(encodeURIComponent(d) + "=" + encodeURIComponent(data[d]));
  }
  return ret.join("&");
};

export const updateQuery = (
  history: any,
  data: Record<string, string>,
): void => {
  const { pathname, search } = history.location;
  const params = parseParams(search);
  for (const k in data) {
    params[k] = data[k];
  }
  history.push(`${pathname}?${encodeQuery(params)}`);
};

export const emit = (event: string, data?: any): void => {
  const e = new CustomEvent(event, { detail: data });
  document.body.dispatchEvent(e);
};

export const subscribe = (event: string, listener: EventListener): void => {
  document.body.addEventListener(event, listener);
};

export const isAdmin = (): boolean => {
  return localStorage.getItem("admin") === "true";
};
