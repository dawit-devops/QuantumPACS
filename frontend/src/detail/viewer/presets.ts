import { request } from "../../helpers";
import type { StackViewport } from "@cornerstonejs/core";

// Reading presets (FR-R12-15): per-user, per-modality window/level and
// viewport-layout presets persisted via the backend so they follow the
// radiologist across workstations.

export type PresetType = "window_level" | "layout";

export interface WindowLevelConfig {
  window_center: number;
  window_width: number;
  invert?: boolean;
}

export interface LayoutConfig {
  rows: number;
  cols: number;
}

export interface ReadingPreset {
  id: string;
  preset_type: PresetType;
  modality: string;
  name: string;
  config: WindowLevelConfig | LayoutConfig;
  is_default: boolean;
  created_at: string;
  updated_at: string;
}

export interface SavePresetPayload {
  preset_type: PresetType;
  modality: string;
  name: string;
  config: WindowLevelConfig | LayoutConfig;
  is_default?: boolean;
}

/** Standard clinical W/L values shipped as the empty-modality starting set. */
export const STANDARD_WL: Record<string, WindowLevelConfig> = {
  Brain: { window_center: 40, window_width: 80 },
  Subdural: { window_center: 80, window_width: 200 },
  Stroke: { window_center: 40, window_width: 40 },
  Temporal: { window_center: 75, window_width: 150 },
  Bone: { window_center: 400, window_width: 2000 },
  Lung: { window_center: -600, window_width: 1500 },
  Mediastinum: { window_center: 40, window_width: 400 },
  Abdomen: { window_center: 50, window_width: 400 },
  Pelvis: { window_center: 50, window_width: 400 },
};

const LAYOUTS: Record<string, LayoutConfig> = {
  "1x1": { rows: 1, cols: 1 },
  "1x2": { rows: 1, cols: 2 },
  "2x2": { rows: 2, cols: 2 },
};

export function layoutLabel(layout: LayoutConfig): string {
  return `${layout.rows}x${layout.cols}`;
}

export function parseLayoutKey(key: string): LayoutConfig {
  return LAYOUTS[key] || LAYOUTS["1x1"];
}

export async function listPresets(opts?: {
  presetType?: PresetType;
  modality?: string;
}): Promise<ReadingPreset[]> {
  const query: Record<string, string> = {};
  if (opts?.presetType) query.preset_type = opts.presetType;
  if (opts?.modality) query.modality = opts.modality;
  const res: any = await request("reading-presets", { query });
  return Array.isArray(res?.data) ? res.data : [];
}

export async function savePreset(payload: SavePresetPayload): Promise<ReadingPreset> {
  const res: any = await request("reading-presets", {
    method: "POST",
    data: payload,
  });
  return res?.data;
}

export async function updatePreset(
  id: string,
  patch: Partial<SavePresetPayload>,
): Promise<ReadingPreset> {
  const res: any = await request(`reading-presets/${id}`, {
    method: "PUT",
    data: patch,
  });
  return res?.data;
}

export async function deletePreset(id: string): Promise<void> {
  await request(`reading-presets/${id}`, { method: "DELETE" });
}

/** Read current W/L off a Cornerstone stack viewport. */
export function readCurrentWL(vp: StackViewport): WindowLevelConfig {
  const voiRange = (vp as any).voiRange;
  if (!voiRange) return { window_center: 0, window_width: 0 };
  return {
    window_center: (voiRange.upper + voiRange.lower) / 2,
    window_width: voiRange.upper - voiRange.lower,
    invert: Boolean((vp as any).invert),
  };
}

/** Apply a W/L preset to a Cornerstone stack viewport (FR-R12-15 / AC-R12-26). */
export function applyWindowLevel(
  vp: StackViewport,
  config: WindowLevelConfig,
): void {
  const { window_center: wc, window_width: ww, invert } = config;
  const lower = wc - ww / 2;
  const upper = wc + ww / 2;
  vp.setProperties({
    voiRange: { lower, upper },
    invert: Boolean(invert),
  });
  (vp as any).render?.();
}
