import { useState, useEffect, useRef } from "react";
import { LOADING_DELAY, API_URL } from "../config";
import {
  fetchWithRetry,
  handleResponse,
  ApiError,
  RequestOptions,
} from "./client";
import { getAccessToken, tryRefreshToken } from "./session";
import { navigate } from "../navigator";

export function useFetch<T = any>(url: string, options: RequestOptions = {}) {
  const [loading, setLoading] = useState(false);
  const [showLoading, setShowLoading] = useState(false);
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<any>(null);
  const controller = useRef<AbortController | null>(null);

  if (!url.startsWith("http")) {
    url = `${API_URL}/${url}`;
  }
  const exec = async (
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

    options.headers = new Headers({
      "Content-Type": "application/json",
      "X-CSRF-Token": "1",
    });
    const token = getAccessToken();
    if (token) {
      options.headers.set("X-Auth-Pacs", token);
    }
    controller.current = new AbortController();
    options.signal = controller.current.signal;

    const doFetch = async (): Promise<any> => {
      const resp = await fetchWithRetry(
        url,
        Object.assign({}, options, execOptions),
      );
      return await handleResponse(resp);
    };

    try {
      const result = await doFetch();
      setData(result);
      finish();
    } catch (error: any) {
      const is401 =
        error instanceof ApiError ? error.status === 401 : error?.error === 401;
      if (is401) {
        const refreshed = await tryRefreshToken();
        if (refreshed) {
          const newToken = getAccessToken();
          if (newToken) {
            options.headers.set("X-Auth-Pacs", newToken);
          }
          try {
            const result = await doFetch();
            setData(result);
            finish();
            return;
          } catch {}
        }
        if (options.unauthorized) {
          options.unauthorized();
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
  };
  return { exec, loading, showLoading, data, error, controller };
}
