import React from "react";
import { renderHook, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { useReaderShortcuts } from "../radiologist/useReaderShortcuts";

const STORAGE_KEY = "reading-immersive";

function fireKey(init: Partial<KeyboardEvent> & { key: string }) {
  const e = new KeyboardEvent("keydown", {
    key: init.key,
    ctrlKey: init.ctrlKey ?? false,
    metaKey: init.metaKey ?? false,
    shiftKey: init.shiftKey ?? false,
    bubbles: true,
    cancelable: true,
  });
  document.dispatchEvent(e);
  return e;
}

function makeHandlers() {
  return {
    saveDraft: vi.fn(),
    requestSign: vi.fn(),
    submitReport: vi.fn(),
    goPrevExam: vi.fn(),
    goNextExam: vi.fn(),
    goToWorklist: vi.fn(),
    showHelp: vi.fn(),
    toggleCine: vi.fn(),
    flagCritical: vi.fn(),
  };
}

describe("useReaderShortcuts (§5)", () => {
  let handlers: ReturnType<typeof makeHandlers>;

  beforeEach(() => {
    handlers = makeHandlers();
    localStorage.clear();
    document.body.classList.remove("immersive-reading");
  });

  afterEach(() => {
    document.body.classList.remove("immersive-reading");
  });

  const render = () => renderHook(() => useReaderShortcuts(handlers));

  it("starts non-immersive on a normal screen; Space triggers cine, not immersive", () => {
    const { result } = render();
    expect(result.current.immersive).toBe(false);
    // Space is rebound to cine per §5.2 — immersive stays a button-only toggle.
    act(() => {
      fireKey({ key: " " });
    });
    expect(handlers.toggleCine).toHaveBeenCalledTimes(1);
    expect(result.current.immersive).toBe(false);
    expect(localStorage.getItem(STORAGE_KEY)).toBeNull();
    // The body flag drives the global sidebar-strip CSS and stays off on Space.
    expect(document.body.classList.contains("immersive-reading")).toBe(false);
  });

  it("auto-enters immersive on dual-monitor-class widths until opted out", () => {
    Object.defineProperty(window, "innerWidth", { value: 2560, configurable: true });
    const first = render();
    expect(first.result.current.immersive).toBe(true);
    act(() => {
      first.result.current.toggleImmersive(); // explicit opt-out wins forever
    });
    expect(localStorage.getItem(STORAGE_KEY)).toBe("0");
    unmountAndRerender();
    expect(localStorage.getItem(STORAGE_KEY)).toBe("0");

    function unmountAndRerender() {
      first.unmount();
      const second = render();
      expect(second.result.current.immersive).toBe(false);
      Object.defineProperty(window, "innerWidth", { value: 1024, configurable: true });
    }
  });

  it("binds Ctrl+S save, Ctrl+Enter sign-confirm, Ctrl+Shift+S submit", () => {
    const { result } = render();
    expect(result.current.immersive).toBe(false);
    act(() => fireKey({ key: "s", ctrlKey: true }));
    expect(handlers.saveDraft).toHaveBeenCalledTimes(1);
    act(() => fireKey({ key: "Enter", ctrlKey: true }));
    expect(handlers.requestSign).toHaveBeenCalledTimes(1);
    act(() => fireKey({ key: "S", ctrlKey: true, shiftKey: true }));
    expect(handlers.submitReport).toHaveBeenCalledTimes(1);
    act(() => fireKey({ key: "F1" }));
    expect(handlers.showHelp).toHaveBeenCalledTimes(1);
    act(() => fireKey({ key: "w", ctrlKey: true, shiftKey: true }));
    expect(handlers.goToWorklist).toHaveBeenCalledTimes(1);
  });

  it("binds F to open critical flagging (§5) and Space to cine", () => {
    render();
    act(() => fireKey({ key: "f" }));
    expect(handlers.flagCritical).toHaveBeenCalledTimes(1);
    act(() => fireKey({ key: " " }));
    expect(handlers.toggleCine).toHaveBeenCalledTimes(1);
  });

  it("navigates the queue with arrows only while immersive", () => {
    const { result } = render();
    act(() => fireKey({ key: "ArrowRight" }));
    expect(handlers.goNextExam).not.toHaveBeenCalled(); // viewer paging stays intact

    act(() => {
      result.current.toggleImmersive(); // enter immersive via the header button
    });
    act(() => fireKey({ key: "ArrowRight" }));
    expect(handlers.goNextExam).toHaveBeenCalledTimes(1);
    act(() => fireKey({ key: "ArrowLeft" }));
    expect(handlers.goPrevExam).toHaveBeenCalledTimes(1);
  });

  it("ignores shortcuts typed inside inputs and content-editables", () => {
    render();
    const textarea = document.createElement("textarea");
    document.body.appendChild(textarea);
    textarea.focus();
    const evt = new KeyboardEvent("keydown", {
      key: "s",
      ctrlKey: true,
      bubbles: true,
      cancelable: true,
    });
    textarea.dispatchEvent(evt);
    expect(handlers.saveDraft).not.toHaveBeenCalled();
    expect(evt.defaultPrevented).toBe(false);
    textarea.remove();
  });
});
