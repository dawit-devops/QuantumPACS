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
// Note: subscribe() has no unsubscribe — the bus lives for the app session,
// so the listener stays registered after unmount (matches the existing
// event-bus design in helpers.ts).
export function useTenantRefetch(fetcher: () => void): void {
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;
  useEffect(() => {
    subscribe("tenant:changed", () => fetcherRef.current());
  }, []);
}
