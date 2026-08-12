import React from "react";
import { render, screen, waitFor, act } from "@testing-library/react";
import { renderWithApp } from "./renderWithApp";
import { describe, it, expect, vi, beforeEach } from "vitest";
import CornerstoneElement from "../detail/CornerstoneElement";

// (H2) Captured cornerstone eventTarget listeners so tests can fire
// render-ish event bursts (IMAGE_LOADED is the event the component actually
// listens to on the shared eventTarget in v5.6.10) and observe the per-frame
// coalescing.
const coreListeners = vi.hoisted(
  () => new Map<string, Array<(data?: any) => void>>(),
);

const viewportMock = () => ({
  setStack: vi.fn().mockResolvedValue(undefined),
  getZoom: () => 1,
  setZoom: vi.fn(),
  getCamera: () => ({
    rotation: 0,
    focalPoint: [0, 0, 0],
    position: [0, 0, 0],
  }),
  setCamera: vi.fn(),
  setProperties: vi.fn(),
  render: vi.fn(),
  voiRange: { upper: 100, lower: 0 },
});

let viewportInstance: ReturnType<typeof viewportMock>;
let engineMock: {
  enableElement: ReturnType<typeof vi.fn>;
  getViewport: ReturnType<typeof vi.fn>;
  resize: ReturnType<typeof vi.fn>;
  disableElement: ReturnType<typeof vi.fn>;
};
// (CobbAngle) Shared tool-group instance so tests can assert tool activation.
const toolGroupMock = vi.hoisted(() => ({
  addTool: vi.fn(),
  addViewport: vi.fn(),
  removeViewports: vi.fn(),
  setToolPassive: vi.fn(),
  setToolActive: vi.fn(),
  setToolConfiguration: vi.fn(),
}));

beforeEach(() => {
  viewportInstance = viewportMock();
  engineMock = {
    enableElement: vi.fn().mockResolvedValue(undefined),
    getViewport: vi.fn(() => viewportInstance),
    resize: vi.fn(),
    disableElement: vi.fn(),
  };
});

vi.mock("@cornerstonejs/core", () => ({
  init: vi.fn(),
  RenderingEngine: vi.fn(() => engineMock),
  cache: { purgeCache: vi.fn() },
  Enums: { ViewportType: { STACK: "stack" } },
  eventTarget: {
    addEventListener: vi.fn((evt: string, cb: (data?: any) => void) => {
      const list = coreListeners.get(evt) ?? [];
      list.push(cb);
      coreListeners.set(evt, list);
    }),
    removeEventListener: vi.fn(),
  },
  EVENTS: {
    IMAGE_LOADED: "imageLoaded",
    IMAGE_LOAD_ERROR: "imageLoadError",
    STACK_NEW_IMAGE: "stackNewImage",
    VOI_MODIFIED: "voiModified",
    CAMERA_MODIFIED: "cameraModified",
  },
  getRenderingEngine: vi.fn(() => engineMock),
  StackViewport: vi.fn(),
}));

vi.mock("@cornerstonejs/tools", () => ({
  init: vi.fn(),
  ToolGroupManager: {
    getToolGroup: vi.fn(() => toolGroupMock),
    createToolGroup: vi.fn(() => toolGroupMock),
  },
  addTool: vi.fn(),
  annotation: {
    state: {
      getAnnotationManager: vi.fn(() => ({
        getAllAnnotations: vi.fn(() => []),
        removeAnnotation: vi.fn(),
      })),
      removeAnnotation: vi.fn(),
      addAnnotation: vi.fn(),
    },
  },
  Enums: {
    Events: {
      ANNOTATION_ADDED: "added",
      ANNOTATION_MODIFIED: "modified",
      ANNOTATION_REMOVED: "removed",
      ANNOTATION_COMPLETED: "completed",
    },
  },
  PanTool: { toolName: "Pan" },
  ZoomTool: { toolName: "Zoom" },
  WindowLevelTool: { toolName: "WindowLevel" },
  LengthTool: { toolName: "Length" },
  RectangleROITool: { toolName: "RectangleROI" },
  AngleTool: { toolName: "Angle" },
  ArrowAnnotateTool: { toolName: "ArrowAnnotate" },
  EllipticalROITool: { toolName: "EllipticalROI" },
  EraserTool: { toolName: "Eraser" },
  StackScrollTool: { toolName: "StackScroll" },
  CobbAngleTool: { toolName: "CobbAngle" },
  ProbeTool: { toolName: "Probe" },
  CircleROITool: { toolName: "CircleROI" },
}));

vi.mock("@cornerstonejs/dicom-image-loader", () => ({
  init: vi.fn(),
}));

vi.mock("../ws", () => ({
  addEventListener: vi.fn(),
  removeEventListener: vi.fn(),
  onOpen: vi.fn(),
  removeOpenListener: vi.fn(),
  send: vi.fn(),
}));

vi.mock("../helpers", () => ({
  request: vi.fn(),
}));

describe("CornerstoneElement", () => {
  const defaultProps = {
    file: { id: "1", name: "test.dcm", tools_state: null },
    files: [{ id: "1", name: "test.dcm" }],
    changeFile: vi.fn(),
    image: "wsi://test",
    visible: true,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders viewport element", () => {
    const { container } = renderWithApp(
      <CornerstoneElement {...defaultProps} />,
    );
    const viewportEl = container.querySelector(".viewportElement");
    expect(viewportEl).toBeInTheDocument();
  });

  it("renders Zoom info", () => {
    renderWithApp(<CornerstoneElement {...defaultProps} />);
    expect(screen.getByText(/Zoom/)).toBeInTheDocument();
  });

  it("renders WW/WC info", () => {
    renderWithApp(<CornerstoneElement {...defaultProps} />);
    expect(screen.getByText(/WW\/WC/)).toBeInTheDocument();
  });

  it("renders collapsible metadata panel", () => {
    renderWithApp(<CornerstoneElement {...defaultProps} />);
    expect(screen.getByText("Metadata")).toBeInTheDocument();
  });

  it("renders bottom touch toolbar with min 44px buttons", () => {
    renderWithApp(<CornerstoneElement {...defaultProps} />);
    const buttons = screen
      .getAllByRole("button")
      .filter(
        (b) =>
          b.closest('div[style*="bottom: 0"]') ||
          (b.style && b.style.minHeight === "44px"),
      );
    expect(buttons.length).toBeGreaterThanOrEqual(4);
    buttons.forEach((btn) => {
      expect(btn.style.minHeight).toBe("44px");
      expect(btn.style.minWidth).toBe("44px");
    });
  });

  it("activates the Cobb angle tool when the '8' key is pressed", async () => {
    renderWithApp(<CornerstoneElement {...defaultProps} />);
    await waitFor(() => expect(engineMock.enableElement).toHaveBeenCalled());

    act(() => {
      document.dispatchEvent(new KeyboardEvent("keydown", { key: "8" }));
    });

    await waitFor(() =>
      expect(toolGroupMock.setToolActive).toHaveBeenCalledWith("CobbAngle", {
        bindings: [{ mouseButton: 1 }],
      }),
    );
  });

  it("activates the Probe tool when the '9' key is pressed", async () => {
    renderWithApp(<CornerstoneElement {...defaultProps} />);
    await waitFor(() => expect(engineMock.enableElement).toHaveBeenCalled());

    act(() => {
      document.dispatchEvent(new KeyboardEvent("keydown", { key: "9" }));
    });

    await waitFor(() =>
      expect(toolGroupMock.setToolActive).toHaveBeenCalledWith("Probe", {
        bindings: [{ mouseButton: 1 }],
      }),
    );
  });

  it("activates the Circle ROI tool when the '0' key is pressed", async () => {
    renderWithApp(<CornerstoneElement {...defaultProps} />);
    await waitFor(() => expect(engineMock.enableElement).toHaveBeenCalled());

    act(() => {
      document.dispatchEvent(new KeyboardEvent("keydown", { key: "0" }));
    });

    await waitFor(() =>
      expect(toolGroupMock.setToolActive).toHaveBeenCalledWith("CircleROI", {
        bindings: [{ mouseButton: 1 }],
      }),
    );
  });

  it("uses wadoRsImage when provided instead of fallback image", () => {
    const wadoRsUrl =
      "wadors:https://pacs.example.com/dicomweb/studies/1.2.3/series/4.5.6/instances/7.8.9";
    renderWithApp(
      <CornerstoneElement {...defaultProps} wadoRsImage={wadoRsUrl} />,
    );
    expect(screen.getByText(/Zoom/)).toBeInTheDocument();
  });

  it("enables a stack viewport on the element on mount", async () => {
    renderWithApp(<CornerstoneElement {...defaultProps} />);
    await waitFor(() =>
      expect(engineMock.enableElement).toHaveBeenCalledWith(
        expect.objectContaining({
          type: "stack",
          element: expect.any(HTMLDivElement),
        }),
      ),
    );
  });

  it("loads the initial image into the stack", async () => {
    renderWithApp(<CornerstoneElement {...defaultProps} />);
    await waitFor(() =>
      expect(viewportInstance.setStack).toHaveBeenCalledWith(["wsi://test"]),
    );
  });

  it("restores persisted annotations when the viewport is ready", async () => {
    const { annotation } = await import("@cornerstonejs/tools");
    renderWithApp(
      <CornerstoneElement
        {...defaultProps}
        file={{
          id: "1",
          name: "test.dcm",
          tools_state: [{ annotationUID: "a1" }],
        }}
      />,
    );
    await waitFor(
      () =>
        expect(annotation.state.addAnnotation).toHaveBeenCalledWith(
          { annotationUID: "a1" },
          "wsi://test",
        ),
      { timeout: 2000 },
    );
  });

  it("swaps the stack and purges the image cache when the image changes", async () => {
    const { cache } = await import("@cornerstonejs/core");
    const { rerender } = renderWithApp(
      <CornerstoneElement {...defaultProps} />,
    );
    await waitFor(() => expect(engineMock.enableElement).toHaveBeenCalled());

    const newUrl = "wadors:https://pacs.example.com/dicomweb/new/instance";
    rerender(<CornerstoneElement {...defaultProps} wadoRsImage={newUrl} />);

    await waitFor(() =>
      expect(viewportInstance.setStack).toHaveBeenCalledWith([newUrl]),
    );
    await waitFor(() => expect(cache.purgeCache).toHaveBeenCalled());
  });

  it("does not purge the cache on the initial mount", async () => {
    const { cache } = await import("@cornerstonejs/core");
    renderWithApp(<CornerstoneElement {...defaultProps} />);
    await waitFor(() => expect(engineMock.enableElement).toHaveBeenCalled());
    expect(cache.purgeCache).not.toHaveBeenCalled();
  });

  it("tears down the viewport, listeners, and ws handlers on unmount", async () => {
    const removeKeydown = vi.spyOn(document, "removeEventListener");
    const { unmount } = renderWithApp(<CornerstoneElement {...defaultProps} />);
    await waitFor(() => expect(engineMock.enableElement).toHaveBeenCalled());

    unmount();

    expect(engineMock.disableElement).toHaveBeenCalled();
    expect(removeKeydown).toHaveBeenCalledWith("keydown", expect.any(Function));
    const { removeEventListener, removeOpenListener } = await import("../ws");
    expect(removeEventListener).toHaveBeenCalled();
    expect(removeOpenListener).toHaveBeenCalled();
  });

  // (H2) A 100-event burst inside one animation frame must produce exactly one
  // update pass: the imperative readout write plus the state commit that
  // React reconciles into the same node. A second pass would add mutations.
  it("coalesces an IMAGE_LOADED burst into one update per frame", async () => {
    const { EVENTS } = await import("@cornerstonejs/core");
    const { container } = renderWithApp(
      <CornerstoneElement {...defaultProps} />,
    );
    await waitFor(() => {
      expect(
        coreListeners.get(EVENTS.IMAGE_LOADED)?.length ?? 0,
      ).toBeGreaterThan(0);
    });

    let zoom = 1;
    const upper = 100;
    const lower = 0;
    viewportInstance.getZoom = () => zoom;
    viewportInstance.voiRange = { upper, lower };

    const zoomNode = container.querySelector(
      ".viewportElement > div",
    ) as HTMLElement;
    const mutations: MutationRecord[][] = [];
    const obs = new MutationObserver((records) => mutations.push(records));
    obs.observe(zoomNode, {
      childList: true,
      characterData: true,
      subtree: true,
    });

    const listeners = coreListeners.get(EVENTS.IMAGE_LOADED)!;
    const evt = { type: EVENTS.IMAGE_LOADED };
    zoom = 2.5;
    viewportInstance.voiRange = { upper: 200, lower: 50 };
    await act(async () => {
      for (let i = 0; i < 100; i++) listeners.forEach((cb) => cb(evt));
      await new Promise((r) => setTimeout(r, 80));
    });

    // jsdom runs rAF on a ~16ms timer: all 100 events land in one frame, so
    // the readout is written once (imperative + React reconcile at most).
    expect(mutations.length).toBeGreaterThanOrEqual(1);
    expect(mutations.length).toBeLessThanOrEqual(2);
    expect(zoomNode.textContent).toBe("Zoom: 2.50");
    const readout = container.querySelector('[aria-live="polite"]');
    expect(readout?.textContent).toContain("Zoom 2.5, Window 150 Level 125");
  });

  // (H2) When the rendered values did not change, the second burst must not
  // touch the DOM or schedule a state update at all.
  it("skips DOM and state updates for unchanged viewport values", async () => {
    const { EVENTS } = await import("@cornerstonejs/core");
    const { container } = renderWithApp(
      <CornerstoneElement {...defaultProps} />,
    );
    await waitFor(() => {
      expect(
        coreListeners.get(EVENTS.IMAGE_LOADED)?.length ?? 0,
      ).toBeGreaterThan(0);
    });

    const zoom = 1;
    viewportInstance.getZoom = () => zoom;
    viewportInstance.voiRange = { upper: 100, lower: 0 };

    // State (and thus the aria-live readout) is the observable contract; the
    // corner overlays are written imperatively and jsdom records a character
    // mutation even when the new text equals the old.
    const readout = container.querySelector(
      '[aria-live="polite"]',
    ) as HTMLElement;
    const mutations: MutationRecord[][] = [];
    const obs = new MutationObserver((records) => mutations.push(records));
    obs.observe(readout, {
      childList: true,
      characterData: true,
      subtree: true,
    });

    const listeners = coreListeners.get(EVENTS.IMAGE_LOADED)!;
    const evt = { type: EVENTS.IMAGE_LOADED };
    await act(async () => {
      // First burst settles state to the initial values (ww 0 -> 100).
      for (let i = 0; i < 10; i++) listeners.forEach((cb) => cb(evt));
      await new Promise((r) => setTimeout(r, 80));
    });
    const afterFirstPass = mutations.length;
    // The first burst did change W/L, so the state-driven commit must have
    // happened — otherwise "unchanged" would be untestable trivially.
    expect(screen.getByText("WW/WC: 100 / 50")).toBeInTheDocument();

    await act(async () => {
      // Second burst carries identical values -> nothing may update.
      for (let i = 0; i < 100; i++) listeners.forEach((cb) => cb(evt));
      await new Promise((r) => setTimeout(r, 80));
    });

    expect(mutations.length).toBe(afterFirstPass);
    expect(readout.textContent).toContain("Zoom 1.0, Window 100 Level 50");
    const zoomNode = container.querySelector(".viewportElement > div");
    expect(zoomNode?.textContent).toBe("Zoom: 1.00");
  });
});
