import { API_URL } from "../config";
import { navigate } from "../navigator";
import { getAccessToken, setTokens, tryRefreshToken } from "./session";

export interface RequestOptions {
  method?: string;
  body?: string;
  headers?: Headers;
  data?: unknown;
  query?: Record<string, string>;
  unauthorized?: () => void;
  signal?: AbortSignal;
  [key: string]: unknown;
}

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

export const request = async <T = any>(
  url: string,
  options: RequestOptions = {},
): Promise<T> => {
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
    url = `${url}?${new URLSearchParams(options.query).toString()}`;
    delete options.query;
  }
  const exec = async (): Promise<any> => {
    const resp = await fetchWithRetry(url, options);
    return await handleResponse(resp);
  };
  try {
    return (await exec()) as T;
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
          return (await exec()) as T;
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
    return undefined as T;
  }
};
