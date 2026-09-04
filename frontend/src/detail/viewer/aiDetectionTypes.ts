// AI Detection overlay data model (design spec Part B).
//
// B.2 / C.1: one AI color across the whole product. These types carry NO
// rendering decisions; the consumer (CornerstoneElement overlay) is the only
// place violet means "AI produced this, not yet verified". Radiologist-owned
// marks (accepted) must never share a hue with AI marks, so status is a first-
// class field here rather than derived from color later.

export type AiMarkStatus = "unreviewed" | "accepted" | "dismissed";

// C.4 qualitative confidence only — never a bare percentage. Two levels,
// shown as words, because radiologists calibrate poorly to false-precision
// numbers and a percentage was never validated against a specific case.
export type AiConfidence = "High" | "Uncertain";

export type AiMarkKind =
  | "nodule"
  | "fracture"
  | "lesion"
  | "lymph-node"
  | "opacity"
  | "calcification";

export interface AiMarkFinding {
  /** Stable id (also the audit-trail key). */
  id: string;
  /** File id (image) the mark sits on — one mark belongs to exactly one slice. */
  fileId: number;
  /** Position in the reading stack (for tick marks on the slice rail). */
  stackIndex: number;
  /** Sequential display number across the study (①②③…). */
  number: number;
  kind: AiMarkKind;
  confidence: AiConfidence;
  status: AiMarkStatus;
  /**
   * Normalized bounds in image space (fractions of image width/height).
   * Stored relative to the image so marks survive re-decodes and are mapped
   * to canvas space per-frame from the viewport transform (B.4: zoom/pan/
   * rotation must move them with the anatomy, never float in screen space).
   */
  x: number;
  y: number;
  w: number;
  h: number;
  /** Human-readable proposal, e.g. "7 mm pulmonary nodule". */
  label: string;
  /** When the radiologist decided. Filled on accept/dismiss (B.7 audit). */
  actedAt?: string;
  /** B.5: how an accepted mark was recorded against the report. */
  linkMode?: "new-line" | "existing-line" | "marker-only";
}

/** A single stacked viewport can display many marks; only the current file's
 *  subset is ever rendered, but the console keeps the whole array so slice
 *  rail ticks and the count badge know about marks on other slices. */
export function marksForFile(marks: AiMarkFinding[], fileId: number): AiMarkFinding[] {
  return marks.filter((m) => m.fileId === fileId);
}

export function activeMarkCount(marks: AiMarkFinding[]): number {
  // B.3 count badge = unresolved marks that still need a decision; dismissed
  // marks are recorded decisions, not open findings.
  return marks.filter((m) => m.status === "unreviewed").length;
}

export const AI_MARK_LABELS: Record<AiMarkKind, string> = {
  nodule: "Nodule",
  fracture: "Fracture",
  lesion: "Lesion",
  "lymph-node": "Lymph node",
  opacity: "Opacity",
  calcification: "Calcification",
};

export function describeMark(m: AiMarkFinding): string {
  const kind = AI_MARK_LABELS[m.kind] ?? m.kind;
  return m.label ? `${kind} — ${m.label}` : kind;
}
