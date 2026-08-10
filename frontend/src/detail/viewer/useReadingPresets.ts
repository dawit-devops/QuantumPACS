import { useCallback, useEffect, useRef, useState } from "react";
import type { StackViewport } from "@cornerstonejs/core";
import type { LayoutConfig, ReadingPreset, WindowLevelConfig } from "./presets";
import {
  applyWindowLevel,
  deletePreset,
  listPresets,
  savePreset,
  updatePreset,
} from "./presets";

export interface UseReadingPresetsOptions {
  modality: string;
  /** Returns the active (primary) viewport, or null before it is ready. */
  getViewport: () => StackViewport | null;
  /** Fired after the per-modality default W/L preset is auto-applied. */
  onAutoApplied?: (preset: ReadingPreset) => void;
}

/**
 * Per-user reading presets for the current modality (FR-R12-15).
 *
 * - Loads the user's W/L + layout presets for the given modality.
 * - Auto-applies the default W/L preset once the viewport is ready
 *   (AC-R12-26: preset applies before interaction).
 * - Exposes save / apply / delete / set-default actions for the panel.
 */
export function useReadingPresets({
  modality,
  getViewport,
  onAutoApplied,
}: UseReadingPresetsOptions) {
  const [wlPresets, setWlPresets] = useState<ReadingPreset[]>([]);
  const [layoutPresets, setLayoutPresets] = useState<ReadingPreset[]>([]);
  const [activeWl, setActiveWl] = useState<ReadingPreset | null>(null);
  const [activeLayout, setActiveLayout] = useState<ReadingPreset | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const autoAppliedRef = useRef(false);
  const getViewportRef = useRef(getViewport);
  getViewportRef.current = getViewport;
  const onAutoAppliedRef = useRef(onAutoApplied);
  onAutoAppliedRef.current = onAutoApplied;

  const reload = useCallback(async () => {
    if (!modality) {
      setWlPresets([]);
      setLayoutPresets([]);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const [wl, layouts] = await Promise.all([
        listPresets({ presetType: "window_level", modality }),
        listPresets({ presetType: "layout", modality }),
      ]);
      setWlPresets(wl);
      setLayoutPresets(layouts);
      return { wl, layouts };
    } catch (e: any) {
      setError(e.message || "Failed to load reading presets");
      return { wl: [], layouts: [] };
    } finally {
      setLoading(false);
    }
  }, [modality]);

  // Initial load + auto-apply the default W/L preset (AC-R12-26). The apply
  // is attempted once the viewport reports ready — the caller re-runs
  // `applyAutoDefault` from its ready-loop.
  useEffect(() => {
    autoAppliedRef.current = false;
    reload();
  }, [reload]);

  const applyPresetToViewport = useCallback(
    (preset: ReadingPreset): boolean => {
      const vp = getViewportRef.current();
      if (!vp) return false;
      applyWindowLevel(vp, preset.config as WindowLevelConfig);
      setActiveWl(preset);
      return true;
    },
    [],
  );

  const applyAutoDefault = useCallback(async () => {
    if (!modality || autoAppliedRef.current) return;
    const res = await reload();
    if (!res) return;
    const def = res.wl.find((p) => p.is_default);
    if (def) {
      if (applyPresetToViewport(def)) {
        autoAppliedRef.current = true;
        onAutoAppliedRef.current?.(def);
      }
    }
    const layoutDef =
      res.layouts.find((p) => p.is_default) || res.layouts[0] || null;
    if (layoutDef) setActiveLayout(layoutDef);
  }, [modality, reload, applyPresetToViewport]);

  // (R1-05) applyWl is synchronous — the old `async`/bare-await block never
  // had a pending promise, so callers (cycleWlPreset) treated it as fire-and-
  // forget already.
  const applyWl = useCallback(
    (preset: ReadingPreset) => {
      applyPresetToViewport(preset);
    },
    [applyPresetToViewport],
  );

  const saveWl = useCallback(
    async (name: string, config: WindowLevelConfig, isDefault = false) => {
      if (!modality) return null;
      const created = await savePreset({
        preset_type: "window_level",
        modality,
        name,
        config,
        is_default: isDefault,
      });
      await reload();
      return created;
    },
    [modality, reload],
  );

  const saveLayout = useCallback(
    async (name: string, config: LayoutConfig, isDefault = false) => {
      if (!modality) return null;
      const created = await savePreset({
        preset_type: "layout",
        modality,
        name,
        config,
        is_default: isDefault,
      });
      await reload();
      return created;
    },
    [modality, reload],
  );

  const setDefault = useCallback(
    async (id: string, presetType: "window_level" | "layout") => {
      await updatePreset(id, { is_default: true });
      await reload();
    },
    [reload],
  );

  const remove = useCallback(async (id: string) => {
    await deletePreset(id);
    setWlPresets((p) => p.filter((x) => x.id !== id));
    setLayoutPresets((p) => p.filter((x) => x.id !== id));
  }, []);

  const applyLayout = useCallback((preset: ReadingPreset) => {
    setActiveLayout(preset);
  }, []);

  return {
    wlPresets,
    layoutPresets,
    activeWl,
    activeLayout,
    loading,
    error,
    reload,
    applyAutoDefault,
    applyWl,
    applyLayout,
    saveWl,
    saveLayout,
    setDefault,
    remove,
  };
}

export type ReadingPresetsApi = ReturnType<typeof useReadingPresets>;
