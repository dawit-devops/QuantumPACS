import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { ReadingPresetsPanel } from "../detail/viewer/ReadingPresetsPanel";
import type { ReadingPresetsApi } from "../detail/viewer/useReadingPresets";

function makeApi(
  overrides: Partial<ReadingPresetsApi> = {},
): ReadingPresetsApi {
  return {
    wlPresets: [],
    layoutPresets: [],
    activeWl: null,
    activeLayout: null,
    loading: false,
    error: null,
    reload: vi.fn(),
    applyAutoDefault: vi.fn(),
    applyWl: vi.fn(),
    applyLayout: vi.fn(),
    saveWl: vi.fn(),
    saveLayout: vi.fn(),
    setDefault: vi.fn(),
    remove: vi.fn(),
    ...overrides,
  } as ReadingPresetsApi;
}

describe("ReadingPresetsPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows the modality tag", () => {
    render(
      <ReadingPresetsPanel
        modality="CT"
        presets={makeApi()}
        readCurrentWl={() => ({ window_center: 40, window_width: 80 })}
      />,
    );
    expect(screen.getByText("CT")).toBeInTheDocument();
  });

  it("lists saved W/L presets with apply + delete + default actions", () => {
    const api = makeApi({
      wlPresets: [
        {
          id: "p1",
          preset_type: "window_level",
          modality: "CT",
          name: "Bone",
          config: { window_center: 400, window_width: 2000 },
          is_default: true,
          created_at: "",
          updated_at: "",
        },
      ],
    });
    render(
      <ReadingPresetsPanel
        modality="CT"
        presets={api}
        readCurrentWl={() => ({ window_center: 40, window_width: 80 })}
      />,
    );
    // The saved preset row and the standard-W/L quick button both say "Bone".
    expect(screen.getAllByText("Bone").length).toBeGreaterThanOrEqual(1);
    fireEvent.click(screen.getByLabelText("Apply Bone"));
    expect(api.applyWl).toHaveBeenCalledTimes(1);
  });

  it("saves the current viewport W/L with a name", async () => {
    const api = makeApi();
    const readCurrentWl = vi.fn(() => ({
      window_center: 400,
      window_width: 2000,
    }));
    render(
      <ReadingPresetsPanel
        modality="CT"
        presets={api}
        readCurrentWl={readCurrentWl}
      />,
    );
    fireEvent.change(screen.getByLabelText("New window/level preset name"), {
      target: { value: "My Bone" },
    });
    fireEvent.click(
      screen.getByLabelText("Save current window/level as preset"),
    );
    await waitFor(() => {
      expect(readCurrentWl).toHaveBeenCalled();
      expect(api.saveWl).toHaveBeenCalledWith("My Bone", {
        window_center: 400,
        window_width: 2000,
      });
    });
  });

  it("applies standard W/L buttons", () => {
    const api = makeApi();
    render(
      <ReadingPresetsPanel
        modality="CT"
        presets={api}
        readCurrentWl={() => ({ window_center: 40, window_width: 80 })}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Lung" }));
    expect(api.applyWl).toHaveBeenCalledWith(
      expect.objectContaining({ name: "Lung" }),
    );
  });

  it("applies a saved layout preset", () => {
    const api = makeApi({
      layoutPresets: [
        {
          id: "l1",
          preset_type: "layout",
          modality: "CT",
          name: "Quad",
          config: { rows: 2, cols: 2 },
          is_default: true,
          created_at: "",
          updated_at: "",
        },
      ],
      saveLayout: vi.fn(),
    });
    render(
      <ReadingPresetsPanel
        modality="CT"
        presets={api}
        readCurrentWl={() => ({ window_center: 40, window_width: 80 })}
      />,
    );
    fireEvent.click(screen.getByLabelText("Apply 2x2 layout"));
    expect(api.applyLayout).toHaveBeenCalledWith(
      expect.objectContaining({ name: "Quad" }),
    );
  });

  it("saves a new layout when no preset matches the grid", async () => {
    const api = makeApi({
      saveLayout: vi.fn().mockResolvedValue({ id: "new" }),
    });
    render(
      <ReadingPresetsPanel
        modality="CT"
        presets={api}
        readCurrentWl={() => ({ window_center: 40, window_width: 80 })}
      />,
    );
    fireEvent.click(screen.getByLabelText("Apply 1x2 layout"));
    await waitFor(() => {
      expect(api.saveLayout).toHaveBeenCalledWith(
        expect.any(String),
        { rows: 1, cols: 2 },
        true,
      );
      // The created preset is activated immediately so the grid changes.
      expect(api.applyLayout).toHaveBeenCalledWith({ id: "new" });
    });
  });

  it("shows the empty state when no presets exist", () => {
    render(
      <ReadingPresetsPanel
        modality="CT"
        presets={makeApi()}
        readCurrentWl={() => ({ window_center: 40, window_width: 80 })}
      />,
    );
    expect(screen.getByText(/No saved W\/L presets/)).toBeInTheDocument();
  });
});
