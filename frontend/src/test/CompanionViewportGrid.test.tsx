import React from "react";
import { render, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { CompanionViewportGrid } from "../detail/viewer/CompanionViewportGrid";

const viewportMock = () => ({
  setStack: vi.fn().mockResolvedValue(undefined),
  setProperties: vi.fn(),
});

let viewportInstances: any[];
let primaryMock: any;
const engineMock = {
  enableElement: vi.fn().mockResolvedValue(undefined),
  getViewport: vi.fn((id: string) => {
    if (id === "primary") return primaryMock;
    const vp = viewportInstances.find((v) => v.id === id)?.vp;
    return vp || undefined;
  }),
  resize: vi.fn(),
  disableElement: vi.fn(),
};

const eventHandlers: Record<string, (e: any) => void> = {};

vi.mock("@cornerstonejs/core", () => ({
  init: vi.fn(),
  RenderingEngine: vi.fn(() => engineMock),
  cache: { purgeCache: vi.fn() },
  Enums: { ViewportType: { STACK: "stack" } },
  eventTarget: {
    addEventListener: (evt: string, cb: any) => {
      eventHandlers[evt] = cb;
    },
    removeEventListener: vi.fn(),
  },
  EVENTS: { IMAGE_RENDERED: "imageRendered", STACK_NEW_IMAGE: "stackNewImage" },
  getRenderingEngine: vi.fn(() => engineMock),
  StackViewport: vi.fn(),
}));

vi.mock("../detail/viewer/setup", () => ({
  ENGINE_ID: "TEST_ENGINE",
  ensureGlobalInit: vi.fn().mockResolvedValue(undefined),
}));

describe("CompanionViewportGrid", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    viewportInstances = [];
    primaryMock = undefined;
    for (const key of Object.keys(eventHandlers)) {
      delete eventHandlers[key];
    }
    engineMock.enableElement.mockImplementation(async (opts: any) => {
      viewportInstances.push({ id: opts.viewportId, vp: viewportMock() });
    });
  });

  it("renders nothing for a 1x1 layout", () => {
    const { container } = render(
      <CompanionViewportGrid
        layout={{ rows: 1, cols: 1 }}
        imageUrl="wadouri://test"
        primaryViewportId="primary"
      />,
    );
    expect(container.querySelector(".ce-companion-cell")).toBeNull();
  });

  it("creates N-1 companion viewports for a 2x2 layout", async () => {
    render(
      <CompanionViewportGrid
        layout={{ rows: 2, cols: 2 }}
        imageUrl="wadouri://test"
        primaryViewportId="primary"
      />,
    );
    await waitFor(() => {
      expect(engineMock.enableElement).toHaveBeenCalledTimes(3);
    });
    const loaded = viewportInstances.filter(
      (v) => v.id.startsWith("companion-"),
    );
    expect(loaded.length).toBe(3);
  });

  it("loads the current image into every companion stack", async () => {
    render(
      <CompanionViewportGrid
        layout={{ rows: 1, cols: 2 }}
        imageUrl="wadouri://ct-1"
        primaryViewportId="primary"
      />,
    );
    await waitFor(() => {
      expect(viewportInstances.length).toBe(1);
    });
    expect(viewportInstances[0].vp.setStack).toHaveBeenCalledWith([
      "wadouri://ct-1",
    ]);
  });

  it("mirrors the primary viewport's W/L on IMAGE_RENDERED", async () => {
    render(
      <CompanionViewportGrid
        layout={{ rows: 1, cols: 2 }}
        imageUrl="wadouri://test"
        primaryViewportId="primary"
      />,
    );
    await waitFor(() => {
      expect(viewportInstances.length).toBe(1);
    });
    primaryMock = {
      voiRange: { lower: 40, upper: 120 },
      invert: false,
    };
    const handler = eventHandlers.imageRendered;
    expect(handler).toBeDefined();
    handler({ detail: { viewportId: "primary" } });
    const comp = viewportInstances[0].vp;
    expect(comp.setProperties).toHaveBeenCalledWith({
      voiRange: { lower: 40, upper: 120 },
      invert: false,
    });
  });

  it("ignores renders from non-primary viewports", async () => {
    render(
      <CompanionViewportGrid
        layout={{ rows: 1, cols: 2 }}
        imageUrl="wadouri://test"
        primaryViewportId="primary"
      />,
    );
    await waitFor(() => {
      expect(viewportInstances.length).toBe(1);
    });
    const handler = eventHandlers.imageRendered;
    handler({ detail: { viewportId: "companion-some-id" } });
    const comp = viewportInstances[0].vp;
    expect(comp.setProperties).not.toHaveBeenCalled();
  });
});
