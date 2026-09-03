import { useCallback, useEffect, useRef, useState } from "react";
import type { AiDraftBlock, AiDraftSection } from "./aiDraftTypes";
import { generateAiReportDraft, AI_DRAFT_VERSIONS } from "./mockReportDraft";
import type { AiDraftChangelogEntry } from "./aiDraftTypes";

export interface AiReportDraftApi {
  /** All blocks (unreviewed + resolved) for the whole report. */
  blocks: AiDraftBlock[];
  /** Blocks still awaiting a radiologist decision (A.3 state 1). */
  unreviewedBlocks: AiDraftBlock[];
  /** Blocks awaiting review in a specific section. */
  blocksForSection: (section: AiDraftSection) => AiDraftBlock[];
  /** Rejected blocks in a section (C.6: dismissal ≠ deletion — recoverable). */
  rejectedBlocksForSection: (section: AiDraftSection) => AiDraftBlock[];
  /** A.5: sign is blocked while this is non-empty. */
  unreviewedCount: number;
  hasUnreviewed: boolean;
  acceptBlock: (id: string) => void;
  rejectBlock: (id: string) => void;
  /** C.6: restore a rejected block to the unreviewed pool to re-decide it. */
  considerRejectedBlock: (id: string) => void;
  acceptAll: () => void;
  rejectAll: () => void;
  /** A.6 regeneration history: cycles the block to its next draft version
   *  ("v2 of 3" stepper), replacing the current proposal text in place. */
  regenerateBlock: (id: string) => void;
  /** A.3.4 edit-in-place: once the radiologist types inside a draft block it
   *  is treated as accepted on blur — typing IS the acceptance gesture. */
  editInPlace: (id: string, text: string) => void;
  /** A.7 per-report changelog of every accept/reject/regenerate/edit. */
  changelog: AiDraftChangelogEntry[];
}

function nextId(): string {
  return `log-${Math.random().toString(36).slice(2, 9)}-${Date.now()}`;
}

/**
 * Part A AI-drafted report content state (design spec).
 *
 * Drafts are generated once per exam (deterministic mock). The radiologist
 * resolves each block; the console appends accepted text into the report
 * fields via the supplied applyText callback, and signs only when
 * unreviewedCount === 0 (A.5 hard gate).
 */
export function useAiReportDraft(
  examId: string | undefined,
  applyText: (section: AiDraftSection, text: string) => void
): AiReportDraftApi {
  const [blocks, setBlocks] = useState<AiDraftBlock[]>(() => {
    const { blocks: generated } = generateAiReportDraft(examId);
    return generated;
  });
  const [changelog, setChangelog] = useState<AiDraftChangelogEntry[]>([]);

  // Regenerate on exam switch (new study → new draft), but preserve resolved
  // decisions by id only within a single exam.
  const prevExamRef = useRef(examId);
  useEffect(() => {
    if (prevExamRef.current === examId) return;
    prevExamRef.current = examId;
    setBlocks(generateAiReportDraft(examId).blocks);
    setChangelog([]);
  }, [examId]);

  const log = useCallback((entry: Omit<AiDraftChangelogEntry, "id" | "timestamp">) => {
    setChangelog((prev) => [
      { ...entry, id: nextId(), timestamp: new Date().toISOString() },
      ...prev,
    ]);
  }, []);

  const patchBlock = useCallback((id: string, patch: Partial<AiDraftBlock>) => {
    setBlocks((prev) => prev.map((b) => (b.id === id ? { ...b, ...patch } : b)));
  }, []);

  const acceptBlock = useCallback(
    (id: string) => {
      const block = blocks.find((b) => b.id === id);
      if (!block || block.status !== "unreviewed") return;
      applyText(block.section, block.text);
      patchBlock(id, { status: "accepted", actedAt: new Date().toISOString() });
      log({ action: "accept", section: block.section, blockId: id, detail: block.text });
    },
    [blocks, applyText, patchBlock, log]
  );

  const rejectBlock = useCallback(
    (id: string) => {
      const block = blocks.find((b) => b.id === id);
      if (!block || block.status !== "unreviewed") return;
      patchBlock(id, { status: "rejected", actedAt: new Date().toISOString() });
      // C.6: log the rejected text, not just that a rejection happened, so the
      // audit trail always records what was declined.
      log({
        action: "reject",
        section: block.section,
        blockId: id,
        detail: block.text,
      });
    },
    [blocks, patchBlock, log]
  );

  // C.6 recovery: a rejected block is never deleted — restore it to the
  // unreviewed pool so the radiologist can re-decide it (edit-in-place or a
  // fresh accept).
  const considerRejectedBlock = useCallback(
    (id: string) => {
      const block = blocks.find((b) => b.id === id);
      if (!block || block.status !== "rejected") return;
      patchBlock(id, { status: "unreviewed", actedAt: undefined });
    },
    [blocks, patchBlock]
  );

  const acceptAll = useCallback(() => {
    const pending = blocks.filter((b) => b.status === "unreviewed");
    for (const b of pending) {
      applyText(b.section, b.text);
      patchBlock(b.id, { status: "accepted", actedAt: new Date().toISOString() });
    }
    if (pending.length) {
      log({ action: "accept-all", section: "findings", blockId: pending[0].id });
    }
  }, [blocks, applyText, patchBlock, log]);

  const rejectAll = useCallback(() => {
    const pending = blocks.filter((b) => b.status === "unreviewed");
    for (const b of pending) {
      patchBlock(b.id, { status: "rejected", actedAt: new Date().toISOString() });
    }
    if (pending.length) {
      log({ action: "reject-all", section: "findings", blockId: pending[0].id });
    }
  }, [blocks, patchBlock, log]);

  const regenerateBlock = useCallback(
    (id: string) => {
      const block = blocks.find((b) => b.id === id);
      if (!block || block.status !== "unreviewed") return;
      const nextVersion = (block.version % block.totalVersions) + 1;
      const nextPoolIdx = block.version % block.totalVersions; // 0-based index of the next version
      const sectionPool = AI_DRAFT_VERSIONS[block.section];
      const text = sectionPool?.[nextPoolIdx]?.[0] ?? block.text;
      patchBlock(id, { version: nextVersion, text });
      log({
        action: "regenerate",
        section: block.section,
        blockId: id,
        detail: `v${nextVersion} of ${block.totalVersions}`,
      });
    },
    [blocks, patchBlock, log]
  );

  const editInPlace = useCallback(
    (id: string, text: string) => {
      const block = blocks.find((b) => b.id === id);
      if (!block || block.status !== "unreviewed") return;
      applyText(block.section, text);
      patchBlock(id, { status: "accepted", text, actedAt: new Date().toISOString() });
      log({ action: "edit-in-place", section: block.section, blockId: id, detail: text });
    },
    [blocks, applyText, patchBlock, log]
  );

  const unreviewedBlocks = blocks.filter((b) => b.status === "unreviewed");
  const unreviewedCount = unreviewedBlocks.length;

  const blocksForSection = useCallback(
    (section: AiDraftSection) =>
      blocks.filter((b) => b.section === section && b.status === "unreviewed"),
    [blocks]
  );

  const rejectedBlocksForSection = useCallback(
    (section: AiDraftSection) =>
      blocks.filter((b) => b.section === section && b.status === "rejected"),
    [blocks]
  );

  return {
    blocks,
    unreviewedBlocks,
    blocksForSection,
    rejectedBlocksForSection,
    unreviewedCount,
    hasUnreviewed: unreviewedCount > 0,
    acceptBlock,
    rejectBlock,
    considerRejectedBlock,
    acceptAll,
    rejectAll,
    regenerateBlock,
    editInPlace,
    changelog,
  };
}
