// Deterministic mock AI report draft generator (Part A).
// No AI backend exists — produce plausible per-exam draft blocks from a
// seeded PRNG so the accept/reject/regenerate UI is fully interactive. The
// seed comes from the exam id, so drafts are stable across reloads.
//
// Replace with a real model call when available; the hook only consumes the
// AiDraftBlock shape below.

import type { AiDraftBlock, AiDraftSection } from "./aiDraftTypes";

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

// Versions per section — "regenerate" cycles these (A.6 v2 of 3 stepper).
// Each top-level array is one version; the first entry is that version's
// proposal, the remainder are alternative phrasings the mock may vary by.
export const AI_DRAFT_VERSIONS: Record<AiDraftSection, string[][]> = {
  findings: [
    [
      "The brain demonstrates age-appropriate grey-white matter differentiation. No acute intracranial hemorrhage is identified.",
      "Ventricles and sulci are normal in size and configuration for age. No mass effect or midline shift.",
      "Cerebellar tonsils are in normal position. No acute intra-axial or extra-axial collection.",
    ],
    [
      "Age-appropriate grey-white matter differentiation. No acute intracranial hemorrhage, mass effect, or midline shift.",
      "No hydrocephalus. Basal cisterns are patent. Dural venous sinuses appear patent.",
    ],
    [
      "No acute intracranial abnormality identified. The brain demonstrates normal age-appropriate maturation.",
    ],
  ],
  impression: [
    [
      "No acute intracranial abnormality. Findings otherwise as above.",
      "Normal CT brain for age. No acute pathology.",
      "Unremarkable non-contrast CT of the brain.",
    ],
    [
      "No acute intracranial hemorrhage or mass effect. Stable compared to prior if available.",
    ],
    [
      "Normal study. No acute findings.",
    ],
  ],
  recommendations: [
    [
      "No immediate follow-up imaging required. Clinical correlation advised.",
      "Follow-up imaging only if clinically indicated.",
    ],
    [
      "If symptoms persist, consider MRI brain for further evaluation.",
    ],
    [
      "No routine follow-up indicated at this time.",
    ],
  ],
};

// A.6 bias: one study in ~6 gets a qualitative "uncertain" quality flag on a
// block, shown as a word, never a percentage.
const UNCERTAIN_RATE = 0.18;
// A.6: a minority of findings blocks carry an inline prior-report conflict note,
// and some impression blocks admit low confidence instead of fabricating.
const PRIOR_NOTE_RATE = 0.2;
const LOW_CONFIDENCE_RATE = 0.15;

export interface GeneratedAiDraft {
  blocks: AiDraftBlock[];
}

export function generateAiReportDraft(examId: string | undefined): GeneratedAiDraft {
  const seed = hashStr(examId ?? "unknown");
  const rng = mulberry32(seed);
  const now = new Date().toISOString();
  const blocks: AiDraftBlock[] = [];
  let n = 0;

  (Object.keys(AI_DRAFT_VERSIONS) as AiDraftSection[]).forEach((section) => {
    const pool = AI_DRAFT_VERSIONS[section];
    // Start at version 1 of N, so "regenerate" has somewhere to go.
    const startIdx = 0;
    const text = pool[startIdx][0];
    const totalVersions = pool.length;
    n += 1;
    const quality = rng() < UNCERTAIN_RATE ? ("uncertain" as const) : undefined;
    const block: AiDraftBlock = {
      id: `ai-draft-${section}-${n}`,
      section,
      text,
      status: "unreviewed",
      version: 1,
      totalVersions,
      quality,
      proposedAt: now,
    };
    // A.6 conflicting-prior-report note: a deterministic minority of findings
    // blocks surface an inline prior-study disagreement so the radiologist
    // sees provenance before trusting the draft — surfaced, never resolved.
    if (section === "findings" && rng() < PRIOR_NOTE_RATE) {
      block.priorNote =
        "Prior report (2026-01-14) described a stable 6 mm right lower lobe nodule; this draft does not mention interval change.";
    }
    // A.6 empty / low-confidence study: on a small fraction of impression
    // blocks the model says so directly rather than fabricating generic
    // normal findings.
    if (section === "impression" && rng() < LOW_CONFIDENCE_RATE) {
      block.text = "Unable to draft — image quality insufficient for a confident impression.";
      block.quality = "uncertain";
    }
    blocks.push(block);
  });

  return { blocks };
}