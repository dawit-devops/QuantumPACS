import { API_URL } from "./config";

export {
  request,
  handleResponse,
  fetchWithRetry,
} from "./api/client";
export type { RequestOptions } from "./api/client";
export {
  getAccessToken,
  getRefreshToken,
  setTokens,
  clearTokens,
  startRefreshTimer,
  stopRefreshTimer,
  tryRefreshToken,
} from "./api/session";

export const open = async (url: string): Promise<void> => {
  // Same-site navigation; the HttpOnly token cookie authenticates it, so no
  // token needs to be appended to the URL (S1-D).
  window.open(`${API_URL}/${url}`);
};

export const parseParams = (search: string): Record<string, string> => {
  // URLSearchParams decodes percent-encoding and + (Q-21) — the old manual
  // split leaked %20 into searches and broke on values containing '='.
  const params: Record<string, string> = {};
  for (const [name, value] of new URLSearchParams(search)) {
    params[name] = value;
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

// (P-M8) Map a list through an async fn with at most `limit` in-flight
// calls. Batch UI operations (bulk cancel, bulk performed, ...) would
// otherwise fire N concurrent HTTP requests, hammering the server.
export async function mapLimit<T, R>(
  items: T[],
  limit: number,
  fn: (item: T) => Promise<R>,
): Promise<R[]> {
  const results = new Array<R>(items.length);
  let next = 0;
  const worker = async () => {
    while (true) {
      const i = next;
      next += 1;
      if (i >= items.length) return;
      results[i] = await fn(items[i]);
    }
  };
  await Promise.all(
    Array.from({ length: Math.min(limit, items.length) }, () => worker()),
  );
  return results;
}
