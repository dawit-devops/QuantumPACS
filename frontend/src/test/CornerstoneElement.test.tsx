import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import CornerstoneElement from "../detail/CornerstoneElement";

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
  eventTarget: { addEventListener: vi.fn(), removeEventListener: vi.fn() },
  EVENTS: { IMAGE_RENDERED: "imageRendered", STACK_NEW_IMAGE: "stackNewImage" },
  getRenderingEngine: vi.fn(() => engineMock),
  StackViewport: vi.fn(),
}));

vi.mock("@cornerstonejs/tools", () => ({
  init: vi.fn(),
  ToolGroupManager: {
    getToolGroup: vi.fn(() => ({
      addTool: vi.fn(),
      addViewport: vi.fn(),
      removeViewports: vi.fn(),
      setToolPassive: vi.fn(),
      setToolActive: vi.fn(),
      setToolConfiguration: vi.fn(),
    })),
    createToolGroup: vi.fn(() => ({
      addTool: vi.fn(),
      addViewport: vi.fn(),
      removeViewports: vi.fn(),
      setToolPassive: vi.fn(),
      setToolActive: vi.fn(),
      setToolConfiguration: vi.fn(),
    })),
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
    const { container } = render(<CornerstoneElement {...defaultProps} />);
    const viewportEl = container.querySelector(".viewportElement");
    expect(viewportEl).toBeInTheDocument();
  });

  it("renders Zoom info", () => {
    render(<CornerstoneElement {...defaultProps} />);
    expect(screen.getByText(/Zoom/)).toBeInTheDocument();
  });

  it("renders WW/WC info", () => {
    render(<CornerstoneElement {...defaultProps} />);
    expect(screen.getByText(/WW\/WC/)).toBeInTheDocument();
  });

  it("renders collapsible metadata panel", () => {
    render(<CornerstoneElement {...defaultProps} />);
    expect(screen.getByText("Metadata")).toBeInTheDocument();
  });

  it("renders bottom touch toolbar with min 44px buttons", () => {
    render(<CornerstoneElement {...defaultProps} />);
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

  it("uses wadoRsImage when provided instead of fallback image", () => {
    const wadoRsUrl =
      "wadors:https://pacs.example.com/dicomweb/studies/1.2.3/series/4.5.6/instances/7.8.9";
    render(<CornerstoneElement {...defaultProps} wadoRsImage={wadoRsUrl} />);
    expect(screen.getByText(/Zoom/)).toBeInTheDocument();
  });

  it("enables a stack viewport on the element on mount", async () => {
    render(<CornerstoneElement {...defaultProps} />);
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
    render(<CornerstoneElement {...defaultProps} />);
    await waitFor(() =>
      expect(viewportInstance.setStack).toHaveBeenCalledWith(["wsi://test"]),
    );
  });

  it("restores persisted annotations when the viewport is ready", async () => {
    const { annotation } = await import("@cornerstonejs/tools");
    render(
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
    const { rerender } = render(<CornerstoneElement {...defaultProps} />);
    await waitFor(() => expect(engineMock.enableElement).toHaveBeenCalled());

    const newUrl = "wadors:https://pacs.example.com/dicomweb/new/instance";
    rerender(<CornerstoneElement {...defaultProps} wadoRsImage={newUrl} />);

    await waitFor(() =>
      expect(viewportInstance.setStack).toHaveBeenCalledWith([newUrl]),
    );
    expect(cache.purgeCache).toHaveBeenCalled();
  });

  it("does not purge the cache on the initial mount", async () => {
    const { cache } = await import("@cornerstonejs/core");
    render(<CornerstoneElement {...defaultProps} />);
    await waitFor(() => expect(engineMock.enableElement).toHaveBeenCalled());
    expect(cache.purgeCache).not.toHaveBeenCalled();
  });

  it("tears down the viewport, listeners, and ws handlers on unmount", async () => {
    const removeKeydown = vi.spyOn(document, "removeEventListener");
    const { unmount } = render(<CornerstoneElement {...defaultProps} />);
    await waitFor(() => expect(engineMock.enableElement).toHaveBeenCalled());

    unmount();

    expect(engineMock.disableElement).toHaveBeenCalled();
    expect(removeKeydown).toHaveBeenCalledWith("keydown", expect.any(Function));
    const { removeEventListener, removeOpenListener } = await import("../ws");
    expect(removeEventListener).toHaveBeenCalled();
    expect(removeOpenListener).toHaveBeenCalled();
  });
});
