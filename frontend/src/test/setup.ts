import '@testing-library/jest-dom';

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

(globalThis as any).fetch = (globalThis as any).fetch || function fetch() {
  return Promise.resolve({
    ok: true,
    status: 200,
    json: () => Promise.resolve({}),
  });
};
