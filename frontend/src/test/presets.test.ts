import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor, act } from "@testing-library/react";
import {
  layoutLabel,
  parseLayoutKey,
  readCurrentWL,
  applyWindowLevel,
  STANDARD_WL,
  listPresets,
  savePreset,
  updatePreset,
  deletePreset,
} from "../detail/viewer/presets";
import { useReadingPresets } from "../detail/viewer/useReadingPresets";

const { requestMock } = vi.hoisted(() => ({
  requestMock: vi.fn(),
}));

vi.mock("../helpers", () => ({
  request: requestMock,
}));

function viewportMock() {
  return {
    setProperties: vi.fn(),
    render: vi.fn(),
    voiRange: { upper: 80, lower: 0 },
    invert: false,
  };
}

describe("reading presets — pure helpers", () => {
  it("labels layouts", () => {
    expect(layoutLabel({ rows: 1, cols: 1 })).toBe("1x1");
    expect(layoutLabel({ rows: 2, cols: 2 })).toBe("2x2");
  });

  it("parses layout keys with safe default", () => {
    expect(parseLayoutKey("2x2")).toEqual({ rows: 2, cols: 2 });
    expect(parseLayoutKey("bogus")).toEqual({ rows: 1, cols: 1 });
  });

  it("reads W/L off a viewport voiRange", () => {
    const cfg = readCurrentWL(viewportMock() as any);
    expect(cfg.window_center).toBe(40);
    expect(cfg.window_width).toBe(80);
    expect(cfg.invert).toBe(false);
  });

  it("applies a W/L preset via setProperties + render", () => {
    const vp = viewportMock();
    applyWindowLevel(vp as any, { window_center: 400, window_width: 2000 });
    expect(vp.setProperties).toHaveBeenCalledWith({
      voiRange: { lower: -600, upper: 1400 },
      invert: false,
    });
    expect(vp.render).toHaveBeenCalled();
  });

  it("ships standard clinical W/L values", () => {
    expect(STANDARD_WL.Bone.window_width).toBe(2000);
    expect(STANDARD_WL.Lung.window_center).toBe(-600);
  });
});

describe("reading presets — API client", () => {
  beforeEach(() => {
    requestMock.mockReset();
  });

  it("lists with preset_type + modality query", async () => {
    requestMock.mockResolvedValue({
      data: [{ id: "a", name: "Bone", preset_type: "window_level" }],
    });
    const rows = await listPresets({
      presetType: "window_level",
      modality: "CT",
    });
    expect(requestMock).toHaveBeenCalledWith("reading-presets", {
      query: { preset_type: "window_level", modality: "CT" },
    });
    expect(rows).toHaveLength(1);
  });

  it("tolerates a missing data array", async () => {
    requestMock.mockResolvedValue({});
    expect(await listPresets()).toEqual([]);
  });

  it("saves, updates, and deletes", async () => {
    requestMock.mockResolvedValue({ data: { id: "a" } });
    await savePreset({
      preset_type: "window_level",
      modality: "CT",
      name: "Bone",
      config: { window_center: 400, window_width: 2000 },
      is_default: true,
    });
    expect(requestMock).toHaveBeenCalledWith("reading-presets", {
      method: "POST",
      data: expect.objectContaining({ name: "Bone", is_default: true }),
    });

    requestMock.mockClear();
    await updatePreset("a", { name: "Bone 2" });
    expect(requestMock).toHaveBeenCalledWith("reading-presets/a", {
      method: "PUT",
      data: { name: "Bone 2" },
    });

    requestMock.mockClear();
    await deletePreset("a");
    expect(requestMock).toHaveBeenCalledWith("reading-presets/a", {
      method: "DELETE",
    });
  });
});

describe("useReadingPresets", () => {
  const getViewport = () => viewportMock() as any;

  beforeEach(() => {
    requestMock.mockReset();
    requestMock.mockResolvedValue({ data: [] });
  });

  it("loads W/L + layout presets for the modality", async () => {
    requestMock.mockImplementation((url: string) => {
      if (url === "reading-presets") {
        return Promise.resolve({
          data: [
            {
              id: "wl1",
              preset_type: "window_level",
              modality: "CT",
              name: "Bone",
              config: { window_center: 400, window_width: 2000 },
              is_default: true,
            },
          ],
        });
      }
      return Promise.resolve({ data: [] });
    });
    const { result } = renderHook(() =>
      useReadingPresets({ modality: "CT", getViewport }),
    );
    await waitFor(() => {
      expect(result.current.wlPresets).toHaveLength(1);
    });
    expect(requestMock).toHaveBeenCalledWith("reading-presets", {
      query: { preset_type: "window_level", modality: "CT" },
    });
  });

  it("auto-applies the default W/L preset to the viewport", async () => {
    const vp = viewportMock();
    requestMock.mockImplementation((url: string) => {
      if (url === "reading-presets") {
        return Promise.resolve({
          data: [
            {
              id: "wl1",
              preset_type: "window_level",
              modality: "CT",
              name: "Bone",
              config: { window_center: 400, window_width: 2000 },
              is_default: true,
            },
          ],
        });
      }
      return Promise.resolve({ data: [] });
    });
    const onAutoApplied = vi.fn();
    const { result } = renderHook(() =>
      useReadingPresets({
        modality: "CT",
        getViewport: () => vp as any,
        onAutoApplied,
      }),
    );
    await act(async () => {
      await result.current.applyAutoDefault();
    });
    await waitFor(() => {
      expect(vp.setProperties).toHaveBeenCalled();
    });
    expect(onAutoApplied).toHaveBeenCalledWith(
      expect.objectContaining({ name: "Bone" }),
    );
  });

  it("does nothing when the modality is empty", async () => {
    const { result } = renderHook(() =>
      useReadingPresets({ modality: "", getViewport }),
    );
    await waitFor(() => {
      expect(result.current.wlPresets).toEqual([]);
    });
    expect(requestMock).not.toHaveBeenCalled();
  });

  it("removes a preset from both lists without a refetch", async () => {
    const { result } = renderHook(() =>
      useReadingPresets({ modality: "CT", getViewport }),
    );
    await act(async () => {
      await result.current.remove("abc");
    });
    expect(requestMock).toHaveBeenCalledWith("reading-presets/abc", {
      method: "DELETE",
    });
  });
});
