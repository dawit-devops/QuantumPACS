import type { FileSeries } from "../api/files";

// Phase group keys ordered canonically — the group order patients see first.
export type PhaseKey =
  | "scout"
  | "noncontrast"
  | "arterial"
  | "portal"
  | "delayed"
  | "washout"
  | "contrast"
  | "reformat"
  | "dose"
  | "other";

export const PHASE_ORDER: PhaseKey[] = [
  "scout", "noncontrast", "arterial", "portal", "delayed",
  "washout", "contrast", "reformat", "dose", "other",
];

export interface PhaseGroup {
  key: PhaseKey;
  label: string;
  series: FileSeries[];
}

export const PHASE_LABELS: Record<PhaseKey, string> = {
  scout: "Scout",
  noncontrast: "Non-contrast",
  arterial: "Arterial",
  portal: "Portal venous",
  delayed: "Delayed",
  washout: "Washout",
  contrast: "Contrast",
  reformat: "Reformat",
  dose: "Dose",
  other: "Other",
};

export const PHASE_COLORS: Record<PhaseKey, string> = {
  scout: "#64748b",
  noncontrast: "#22c55e",
  arterial: "#ef4444",
  portal: "#f59e0b",
  delayed: "#8b5cf6",
  washout: "#a855f7",
  contrast: "#3b82f6",
  reformat: "#06b6d4",
  dose: "#78716c",
  other: "#94a3b8",
};

// Classify a series into a phase group from its description + modality
export function classifyPhase(series: FileSeries): { key: PhaseKey; label: string } {
  const d = (series.description ?? "").toLowerCase();
  const m = (series.modality ?? "").toUpperCase();

  // Dose / structured reports
  if (m === "SR" || /dose|dose record|dose report/i.test(d))
    return { key: "dose", label: PHASE_LABELS.dose };

  // Scout / localizer
  if (/scout|localizer|survey|topogram|planning/i.test(d))
    return { key: "scout", label: PHASE_LABELS.scout };

  // Reformats / MPR
  if (/coronal|sagittal|batch|mpr|reformat|3d|mip|vr|curved/i.test(d))
    return { key: "reformat", label: PHASE_LABELS.reformat };

  // Contrast phases — ordered by keyword strength
  if (/arterial|artery/i.test(d))
    return { key: "arterial", label: PHASE_LABELS.arterial };
  if (/pvp|portal venous|portal|pv/i.test(d))
    return { key: "portal", label: PHASE_LABELS.portal };
  if (/delay|delayed|5miute|equilib|washout|excretory|urograp|nephrograp/i.test(d))
    return { key: "delayed", label: PHASE_LABELS.delayed };
  if (/contrast|post.?contrast|enhanced|bolus|c[+]/i.test(d))
    return { key: "contrast", label: PHASE_LABELS.contrast };

  // Non-contrast / plain
  if (/non.?contrast|noncontrast|plain|unenhanced|pre.?contrast|ncct|stnd|std|standard/i.test(d))
    return { key: "noncontrast", label: PHASE_LABELS.noncontrast };

  return { key: "other", label: PHASE_LABELS.other };
}

// Group series into phase stacks, preserving acquisition order within each
// phase and ordering groups canonically.
export function groupByPhase(seriesList: FileSeries[]): PhaseGroup[] {
  const groups = new Map<PhaseKey, FileSeries[]>();
  for (const s of seriesList) {
    const { key } = classifyPhase(s);
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key)!.push(s);
  }
  return PHASE_ORDER
    .filter((k) => groups.has(k))
    .map((key) => {
      const series = groups.get(key)!;
      return { key, label: PHASE_LABELS[key], series };
    });
}
