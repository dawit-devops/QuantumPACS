// Deterministic mock AI detection generator for the AI Findings overlay (Part B).
//
// There is no real AI backend — this module produces plausible per-file marks
// from a seeded PRNG so the UI is fully interactive during development and
// demo. The seed is derived from the study/exam id so marks are stable across
// re-renders and reloads.
//
// Replace this module with a real API call when a model is available.

import type { FileNode } from "../../api/files";
import type { AiMarkFinding, AiMarkKind, AiConfidence, AiMarkStatus } from "./aiDetectionTypes";

// ── Seeded PRNG (mulberry32) ──────────────────────────────────────────────

function mulberry32(seed: number): () => number {
  return () => {
    seed |= 0;
    seed = (seed + 0x6d2b79f5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function hashStr(s: string): number {
  let h = 0;
  for (let i = 0; i < s.length; i++) {
    h = (Math.imul(31, h) + s.charCodeAt(i)) | 0;
  }
  return h;
}

// ── Pick helpers ──────────────────────────────────────────────────────────

const MARK_KINDS: AiMarkKind[] = ["nodule", "fracture", "lesion", "lymph-node", "opacity", "calcification"];

// CT chest weights: nodule & opacity are most common.
const KIND_WEIGHTS: Record<AiMarkKind, number> = {
  nodule: 0.35,
  fracture: 0.05,
  lesion: 0.15,
  "lymph-node": 0.10,
  opacity: 0.25,
  calcification: 0.10,
};

// B.6 bias: for false-positive-prone tasks (lung nodule vs vessel cross-section),
// the qualitative confidence flag should lean toward "Uncertain" rather than "High".
const UNCERTAIN_BIAS = 0.65;

const KIND_LABELS: Record<AiMarkKind, string[]> = {
  nodule: ["5 mm solid nodule", "8 mm subsolid nodule", "3 mm micronodule", "6 mm part-solid nodule"],
  fracture: ["Non-displaced cortical fracture", "Minimally displaced fracture line"],
  lesion: ["Hypodense lesion", "Ring-enhancing lesion", "Cystic lesion"],
  "lymph-node": ["Enlarged lymph node", "Calcified lymph node"],
  opacity: ["Ground-glass opacity", "Consolidation", "Hazy opacity"],
  calcification: ["Punctate calcification", "Coarse calcification"],
};

function pickWeighted<N extends string>(rng: () => number, weights: Record<N, number>): N {
  const entries = Object.entries(weights) as [N, number][];
  const total = entries.reduce((a, b) => a + b[1], 0);
  let r = rng() * total;
  for (const [k, w] of entries) {
    r -= w;
    if (r <= 0) return k;
  }
  return entries[0][0];
}

// ── Public generator ──────────────────────────────────────────────────────

const MAX_DISPLAYED_MARKS = 15; // B.6 cap: only the N highest-confidence marks

/**
 * Generate deterministic AI findings for the given reading stack.
 * @param files  ordered list of files in the active stack (phase or series).
 * @param seed   stable seed (e.g. exam id or study instance uid as string).
 * @param maxMarks  optional cap for the overlay (default 15).
 */
export function generateAiDetections(
  files: FileNode[],
  seed: string,
  maxMarks = MAX_DISPLAYED_MARKS,
): AiMarkFinding[] {
  if (files.length === 0) return [];

  const baseSeed = hashStr(seed);
  const marks: AiMarkFinding[] = [];
  let globalNumber = 0;

  // Decide which indices get marks by stepping through with a deterministic
  // stride so the result is stable across reloads and sparse across slices.
  const strideRng = mulberry32(baseSeed ^ 0xdead);
  const stride = Math.max(3, Math.round(strideRng() * 5 + 3)); // 3–8

  for (let i = 0; i < files.length; i += stride) {
    if (marks.length >= maxMarks) break;
    const file = files[i];
    if (!file) continue;
    const fileRng = mulberry32(baseSeed ^ file.id ^ (i * 0xbeef));
    // 0–2 marks per file (weighted: 0=30%, 1=50%, 2=20%)
    const count = fileRng() < 0.3 ? 0 : fileRng() < 0.8 / 0.7 ? 1 : 2;
    for (let j = 0; j < count; j++) {
      if (marks.length >= maxMarks) break;
      globalNumber += 1;
      const kind = pickWeighted(fileRng, KIND_WEIGHTS);
      const confidence: AiConfidence = fileRng() < UNCERTAIN_BIAS ? "Uncertain" : "High";
      const labels = KIND_LABELS[kind];
      const label = labels[Math.floor(fileRng() * labels.length)];

      // Position: avoid edges (10%–90% of image width/height).
      const cx = 0.1 + fileRng() * 0.8;
      const cy = 0.1 + fileRng() * 0.8;
      // Size: 2%–8% of image width, 2%–8% of height.
      const w = 0.02 + fileRng() * 0.06;
      const h = 0.02 + fileRng() * 0.06;

      marks.push({
        id: `ai-${file.id}-${j}`,
        fileId: file.id,
        stackIndex: i,
        number: globalNumber,
        kind,
        confidence,
        status: "unreviewed",
        x: Math.max(0, cx - w / 2),
        y: Math.max(0, cy - h / 2),
        w,
        h,
        label,
      });
    }
  }

  return marks;
}

/**
 * Which stack indices have at least one unreviewed / accepted mark (for slice
 * rail ticks). Dismissed marks are excluded — they are recorded decisions,
 * not active findings.
 */
export function nonDismissedSliceIndices(marks: AiMarkFinding[]): Set<number> {
  const s = new Set<number>();
  for (const m of marks) {
    if (m.status !== "dismissed") s.add(m.stackIndex);
  }
  return s;
}