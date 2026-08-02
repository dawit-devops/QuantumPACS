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

export interface ApiErrorEnvelopeError {
  code?: string;
  message?: string;
  details?: unknown;
  request_id?: string;
}

export interface ApiErrorEnvelope {
  error?: string | ApiErrorEnvelopeError;
}

const STATUS_MESSAGES: Record<number, string> = {
  400: "Bad request",
  401: "Session expired — please sign in again",
  403: "You don't have permission to do that",
  404: "Not found",
  405: "Method not allowed",
  409: "Conflict",
  422: "Request validation failed",
  429: "Too many requests",
  500: "Server error",
  502: "Bad gateway",
  503: "Service unavailable",
};

// Backend messages are plain text but may embed upstream text (OAuth
// provider responses, validation details, proxied FHIR errors). Strip
// control characters and cap length so nothing hostile or huge reaches
// message.error()/alert surfaces.
export const sanitizeMessage = (text: string): string => {
  const cleaned = text
    .replace(/[\u0000-\u001f\u007f]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
  return cleaned.length > 240 ? `${cleaned.slice(0, 240)}…` : cleaned;
};

export class ApiError extends Error {
  status: number;
  code?: string;
  details?: unknown;
  requestId?: string;

  constructor(
    status: number,
    message: string,
    code?: string,
    details?: unknown,
    requestId?: string,
  ) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
    this.requestId = requestId;
  }
}

export const handleResponse = async (response: Response): Promise<any> => {
  if (!response) {
    return;
  }
  let body: any;
  try {
    body = await response.json();
  } catch {
    body = undefined;
  }
  if (response.ok) {
    return body;
  }
  const status = response.status;
  let message = STATUS_MESSAGES[status] ?? "Request failed";
  let code: string | undefined;
  let details: unknown;
  let requestId: string | undefined;
  const err = body?.error;
  if (typeof err === "string") {
    const cleaned = sanitizeMessage(err);
    if (cleaned) message = cleaned;
  } else if (err && typeof err === "object") {
    if (typeof err.code === "string") code = err.code;
    if (typeof err.message === "string") {
      const cleaned = sanitizeMessage(err.message);
      if (cleaned) message = cleaned;
    }
    details = err.details;
    if (typeof err.request_id === "string") requestId = err.request_id;
  }
  throw new ApiError(status, message, code, details, requestId);
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
    // Default to POST for payloads, but honor an explicit method — the
    // legacy helper overwrote PUT/DELETE with POST whenever data was
    // present, silently 405-ing every PUT endpoint (users/role, tenants,
    // worklist, replicas, fhir admin, ...).
    options.method = options.method || "POST";
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
    const is401 =
      error instanceof ApiError
        ? error.status === 401
        : error?.error === 401;
    if (is401) {
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
          const retry401 =
            retryError instanceof ApiError
              ? retryError.status === 401
              : retryError?.error === 401;
          if (!retry401) throw retryError;
        }
      }
      if (options.unauthorized) {
        options.unauthorized();
      } else {
        navigate("/login");
      }
    }
    // AbortError (DOMException code 20 / name AbortError) is the caller
    // signalling cancellation — swallow it like the legacy hook did.
    const aborted =
      error?.name === "AbortError" || error?.code === 20;
    if (!aborted) {
      throw error instanceof ApiError ? error : Error(String(error?.message || error));
    }
    return undefined as T;
  }
};
