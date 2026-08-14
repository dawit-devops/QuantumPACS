import { useEffect, useRef } from "react";
import { subscribe } from "./helpers";

export { useFetch } from "./api/useFetch";

// Sets document.title from an effect (Q-4) instead of during render, which
// React 19 treats as a side effect in the render phase.
export function useDocumentTitle(title: string): void {
  useEffect(() => {
    document.title = title;
  }, [title]);
}

// Refetch whenever the active tenant changes. TenantSelector emits
// 'tenant:changed' (payload: new slug) on switch; every screen that shows
// tenant-scoped data subscribes here so results are never stale after a
// switch. The fetcher is held in a ref so callers may pass a non-memoized
// function (e.g. Files' fetch) without re-subscribing every render.
// R1-06: the subscription is torn down on unmount — the old version left a
// permanent listener per mounted screen, so every tenant switch fired N
// redundant refetches (several on unmounted components).
export function useTenantRefetch(fetcher: () => void): void {
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;
  useEffect(() => {
    return subscribe("tenant:changed", () => fetcherRef.current());
  }, []);
}

// Poll `fetcher` every `ms` while the document is visible; a hidden tab
// must not keep firing network requests (R1-04). On returning to the tab the
// data is stale, so fetch immediately before resuming the cadence.
export function useVisibilityGatedInterval(
  fetcher: () => void,
  ms: number,
): void {
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;
  useEffect(() => {
    let timer: number | undefined;
    const stop = () => {
      if (timer !== undefined) {
        window.clearInterval(timer);
        timer = undefined;
      }
    };
    const start = () => {
      stop();
      timer = window.setInterval(() => fetcherRef.current(), ms);
    };
    const onVisibility = () => {
      if (document.hidden) {
        stop();
      } else {
        fetcherRef.current();
        start();
      }
    };
    document.addEventListener("visibilitychange", onVisibility);
    start();
    return () => {
      stop();
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, [ms]);
}
