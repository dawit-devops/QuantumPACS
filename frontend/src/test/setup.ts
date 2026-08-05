import "@testing-library/jest-dom";
import { beforeEach, vi } from "vitest";
import { message } from "antd";

// (T-L1) antd's static message API (message.success/error/...) spawns a
// real React root with a 3s auto-dismiss timer that outlives the test
// file. After vitest tears down jsdom the pending scheduler callback
// throws "window is not defined" — an unhandled-error flake in CI.
// Patch the shared module instance here so every file is covered
// (QAReviewForm.test.tsx etc. carry an equivalent per-file vi.mock).
Object.assign(message, {
  success: vi.fn(),
  error: vi.fn(),
  info: vi.fn(),
  warning: vi.fn(),
});

const noop = () => {};
const originalWarn = console.warn;
console.warn = (msg: unknown, ...args: unknown[]) => {
  if (
    typeof msg === "string" &&
    (msg.includes("Not implemented: Window's getComputedStyle()") ||
      msg.includes("Not implemented: HTMLCanvasElement"))
  )
    return;
  originalWarn(msg, ...args);
};

// (T-L1) Tests must not leak state between tests: auth tokens, tenant
// selection and the session tempKey all live in storage.
beforeEach(() => {
  localStorage.clear();
  sessionStorage.clear();
});

if (typeof globalThis.localStorage === "undefined") {
  const store: Record<string, string> = {};
  (globalThis as any).localStorage = {
    getItem: (k: string) => store[k] ?? null,
    setItem: (k: string, v: string) => {
      store[k] = v;
    },
    removeItem: (k: string) => {
      delete store[k];
    },
    clear: () => {
      Object.keys(store).forEach((k) => delete store[k]);
    },
    get length() {
      return Object.keys(store).length;
    },
    key: (i: number) => Object.keys(store)[i] ?? null,
  };
}

// (T-L1) Honest matchMedia: evaluate min/max-width against the real
// window.innerWidth instead of hardcoding which queries match. antd's
// useBreakpoint derives `lg` from these results (base.tsx, Sidebar.tsx).
// Widths may be fractional ("screen and (max-width: 991.98px)" from
// antd's Sider), so the number group allows decimals.
window.matchMedia = function matchMedia(query: string): MediaQueryList {
  const width = window.innerWidth;
  const minMatch = query.match(/min-width:\s*(\d+(?:\.\d+)?)px/);
  const maxMatch = query.match(/max-width:\s*(\d+(?:\.\d+)?)px/);
  let matches = true;
  if (minMatch) matches = matches && width >= Number(minMatch[1]);
  if (maxMatch) matches = matches && width <= Number(maxMatch[1]);
  const listeners = new Set<(e: MediaQueryListEvent) => void>();
  const mql: MediaQueryList = {
    media: query,
    matches,
    onchange: null,
    addListener: (cb) => {
      if (typeof cb === "function") {
        listeners.add(cb as (e: MediaQueryListEvent) => void);
      }
    },
    removeListener: (cb) => {
      if (typeof cb === "function") {
        listeners.delete(cb as (e: MediaQueryListEvent) => void);
      }
    },
    addEventListener: (
      _type: string,
      cb: EventListenerOrEventListenerObject | null,
    ) => {
      if (typeof cb === "function") {
        listeners.add(cb as (e: MediaQueryListEvent) => void);
      }
    },
    removeEventListener: (
      _type: string,
      cb: EventListenerOrEventListenerObject | null,
    ) => {
      if (typeof cb === "function") {
        listeners.delete(cb as (e: MediaQueryListEvent) => void);
      }
    },
    dispatchEvent: (e: Event) => {
      listeners.forEach((l) => l(e as MediaQueryListEvent));
      return true;
    },
  };
  return mql;
};

class ResizeObserverMock {
  observe() {}
  unobserve() {}
  disconnect() {}
}
(globalThis as any).ResizeObserver = ResizeObserverMock;

// (T-L1) Fail loudly instead of silently succeeding: a phantom 200 makes
// unmocked fetch calls look like successful API responses. Suites that
// exercise request() stub fetch explicitly (helpers.test.ts, dicomweb.test.ts).
(globalThis as any).fetch = () => {
  throw new Error(
    "fetch called without a stub — mock the api module or vi.stubGlobal('fetch', ...) in this test",
  );
};

if (typeof globalThis.requestAnimationFrame === "undefined") {
  globalThis.requestAnimationFrame = (cb: FrameRequestCallback) => {
    return setTimeout(cb, 16) as unknown as number;
  };
  globalThis.cancelAnimationFrame = (id: number) => clearTimeout(id);
}
