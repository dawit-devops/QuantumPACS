import { useState, useEffect, useRef, useCallback } from "react";
import { LOADING_DELAY, API_URL } from "../config";
import {
  fetchWithRetry,
  handleResponse,
  ApiError,
  RequestOptions,
} from "./client";
import { tryRefreshToken, wasRefreshRateLimited } from "./session";
import { navigate } from "../navigator";

export function useFetch<T = any>(url: string, options: RequestOptions = {}) {
  const [loading, setLoading] = useState(false);
  const [showLoading, setShowLoading] = useState(false);
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<any>(null);
  const controller = useRef<AbortController | null>(null);
  // (L4) Keep the latest caller options in a ref so exec can be memoized on
  // [url] alone: a caller that builds a fresh options object per render no
  // longer forces exec to be recreated (and children to re-render) each time.
  const optionsRef = useRef(options);
  optionsRef.current = options;

  if (!url.startsWith("http")) {
    url = `${API_URL}/${url}`;
  }
  const exec = useCallback(
    async (
      doShowLoading = true,
      execOptions: RequestOptions = {},
    ): Promise<void> => {
      if (controller.current) {
        controller.current.abort();
      }
      setLoading(true);
      let loaderTimeout: ReturnType<typeof setTimeout> | undefined;
      if (doShowLoading) {
        loaderTimeout = setTimeout(() => setShowLoading(true), LOADING_DELAY);
      }
      const finish = () => {
        if (doShowLoading) {
          clearTimeout(loaderTimeout);
          setShowLoading(false);
        }
        setLoading(false);
      };

      // (L4) Merge caller-supplied headers with the auth/csrf headers instead
      // of replacing them: callers may set their own (Accept, Content-Type
      // for multipart, ...) and those must survive. Content-Type is only
      // defaulted when the caller did not already pick one.
      const merged: RequestOptions = {
        ...optionsRef.current,
        ...execOptions,
      };
      const headers = new Headers(merged.headers);
      if (!headers.has("Content-Type")) {
        headers.set("Content-Type", "application/json");
      }
      headers.set("X-CSRF-Token", "1");
      // IAM audit H-2: auth rides the HttpOnly access cookie.
      merged.credentials = "include";
      merged.headers = headers;
      controller.current = new AbortController();
      merged.signal = controller.current.signal;

      const doFetch = async (): Promise<any> => {
        const resp = await fetchWithRetry(url, merged);
        return await handleResponse(resp);
      };

      try {
        const result = await doFetch();
        setData(result);
        finish();
      } catch (error: any) {
        const is401 =
          error instanceof ApiError
            ? error.status === 401
            : error?.error === 401;
        if (is401) {
          const refreshed = await tryRefreshToken();
          if (refreshed) {
            try {
              const result = await doFetch();
              setData(result);
              finish();
              return;
            } catch {}
          }
          // A rate-limited refresh (429) is a transient throttle on the
          // unauthenticated grant endpoint, not a dead session — stay put and
          // surface the error instead of bouncing to /login.
          if (wasRefreshRateLimited()) return;
          if (optionsRef.current.unauthorized) {
            optionsRef.current.unauthorized();
          } else {
            navigate("/login");
          }
        }
        // AbortError (DOMException code 20 / name AbortError) is the caller
        // signalling cancellation — swallow it.
        const aborted = error?.name === "AbortError" || error?.code === 20;
        if (!aborted) {
          setError(
            error instanceof ApiError
              ? error
              : Error(String(error?.message || error)),
          );
        }
        finish();
      }
    },
    [url],
  );
  return { exec, loading, showLoading, data, error, controller };
}
