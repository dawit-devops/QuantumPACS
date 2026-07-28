import '@testing-library/jest-dom';

const noop = () => {};
const originalWarn = console.warn;
console.warn = (msg: unknown, ...args: unknown[]) => {
  if (typeof msg === 'string' && (
    msg.includes('Not implemented: Window\'s getComputedStyle()') ||
    msg.includes('Not implemented: HTMLCanvasElement')
  )) return;
  originalWarn(msg, ...args);
};

if (typeof globalThis.localStorage === 'undefined') {
  const store: Record<string, string> = {};
  (globalThis as any).localStorage = {
    getItem: (k: string) => store[k] ?? null,
    setItem: (k: string, v: string) => { store[k] = v; },
    removeItem: (k: string) => { delete store[k]; },
    clear: () => { Object.keys(store).forEach(k => delete store[k]); },
    get length() { return Object.keys(store).length; },
    key: (i: number) => Object.keys(store)[i] ?? null,
  };
}

window.matchMedia = window.matchMedia || function matchMedia(this: any) {
  return {
    matches: false,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => {},
  };
};

class ResizeObserverMock {
  observe() {}
  unobserve() {}
  disconnect() {}
}
(globalThis as any).ResizeObserver = ResizeObserverMock;

(globalThis as any).fetch = (globalThis as any).fetch || function fetch() {
  return Promise.resolve({
    ok: true,
    status: 200,
    json: () => Promise.resolve({}),
  });
};
