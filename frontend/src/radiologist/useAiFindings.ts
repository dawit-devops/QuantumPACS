import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { FileNode } from "../api/files";
import { generateAiDetections } from "../detail/viewer/mockDetections";
import type { AiMarkFinding } from "../detail/viewer/aiDetectionTypes";
import {
  activeMarkCount,
  marksForFile,
} from "../detail/viewer/aiDetectionTypes";
import { nonDismissedSliceIndices } from "../detail/viewer/mockDetections";
import { reportHtmlToText, sanitizeReportHtml } from "./sanitizeReportHtml";

export type AiLinkMode = "new-line" | "existing-line" | "marker-only";

// B.6: overlay cap — only the N highest-confidence unresolved marks render by
// default; "Show N more" reveals additional ones in batches so high-volume
// screening studies never flood the image with boxes.
export const DEFAULT_MARK_CAP = 6;
export const MARK_REVEAL_STEP = 6;

export interface AiFindingsLinkState {
  open: boolean;
  mark: AiMarkFinding | null;
  mode: AiLinkMode;
  existingIndex: number | null;
  sentences: string[];
}

/**
 * Part B AI Findings state for the reading console.
 *
 * The console owns the marks array (there is no AI backend — marks come from
 * the deterministic generator seeded by the exam id). This hook:
 *  - regenerates the study's marks whenever the active stack changes, but
 *    preserves every radiologist decision (accept/dismiss + link mode) across
 *    regenerations by mark id (B.7 audit survives series/phase switches);
 *  - exposes the toggle, the "show dismissed" checkbox and the inspected-mark
 *    id driving the per-mark popover;
 *  - performs Accept (opening the B.5 inline linkage choice) and Dismiss.
 */
export function useAiFindings(
  examId: string | undefined,
  viewFiles: FileNode[],
  currentFile: FileNode | null,
  findings: string,
  onFindingsChange: (html: string) => void,
) {
  const [marks, setMarks] = useState<AiMarkFinding[]>([]);
  const [visible, setVisible] = useState(false);
  const [showDismissed, setShowDismissed] = useState(false);
  // B.6: default overlay cap — only the N highest-confidence marks are shown
  // first, with a "Show N more" affordance, so a screening study with many
  // small marks never covers the image in boxes.
  const [displayLimit, setDisplayLimit] = useState(DEFAULT_MARK_CAP);
  const [inspectedId, setInspectedId] = useState<string | null>(null);
  const [link, setLink] = useState<AiFindingsLinkState>({
    open: false,
    mark: null,
    mode: "new-line",
    existingIndex: null,
    sentences: [],
  });

  // Radiologist decisions keyed by mark id — reapplied when marks regenerate.
  const decisionsRef = useRef<
    Map<
      string,
      { status: AiMarkFinding["status"]; linkMode?: AiMarkFinding["linkMode"] }
    >
  >(new Map());

  // Stack signature: which files the marks were generated against. Regenerate
  // when the phase/series stack changes, not on every render.
  const stackSig = examId + "::" + viewFiles.map((f) => f.id).join(",");
  useEffect(() => {
    const next = generateAiDetections(viewFiles, examId ?? "unknown");
    // Reapply recorded decisions by id so accept/dismiss survive a stack switch.
    const merged = next.map((m) => {
      const d = decisionsRef.current.get(m.id);
      return d
        ? { ...m, status: d.status, linkMode: d.linkMode ?? m.linkMode }
        : m;
    });
    setMarks(merged);
    setInspectedId((cur) =>
      cur && merged.some((m) => m.id === cur) ? cur : null,
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [stackSig]);

  // Clear the popover whenever the inspected mark leaves the current file.
  useEffect(() => {
    setInspectedId((cur) => cur && marks.some((m) => m.id === cur) ? cur : null);
  }, [marks]);

  const updateMark = useCallback((id: string, patch: Partial<AiMarkFinding>) => {
    setMarks((prev) => prev.map((m) => (m.id === id ? { ...m, ...patch } : m)));
    const d = decisionsRef.current.get(id) ?? {} as Partial<{ status: AiMarkFinding["status"]; linkMode: AiMarkFinding["linkMode"] }>;
    decisionsRef.current.set(id, {
      ...d,
      ...("status" in patch ? { status: patch.status } : {}),
      ...("linkMode" in patch ? { linkMode: patch.linkMode } : {}),
    } as { status: AiMarkFinding["status"]; linkMode?: AiMarkFinding["linkMode"] });
  }, []);

  const toggleAiFindings = useCallback(() => {
    setVisible((v) => {
      // Toggling off dismisses any open popover too.
      if (v) setInspectedId(null);
      return !v;
    });
  }, []);

  const inspectMark = useCallback((mark: AiMarkFinding | null) => {
    setInspectedId(mark ? mark.id : null);
  }, []);

  const dismissMark = useCallback(
    (mark: AiMarkFinding) => {
      updateMark(mark.id, { status: "dismissed", actedAt: new Date().toISOString() });
      setInspectedId(null);
    },
    [updateMark],
  );

  // C.6 "dismissal ≠ deletion": a dismissed mark is a recorded decision, not
  // a deletion — the radiologist can reopen it as a neutral unreviewed finding
  // to re-inspect (parallel to the Part A draft-text `considerRejectedBlock`).
  // Reset clears `actedAt` too so the reopened mark no longer claims a prior
  // decision and correctly blocks signing again until re-resolved (C.3).
  const reconsiderMark = useCallback(
    (mark: AiMarkFinding) => {
      updateMark(mark.id, { status: "unreviewed", actedAt: undefined });
      setInspectedId(null);
    },
    [updateMark],
  );

  // ── Accept → B.5 inline choice modal ─────────────────────────────────────

  const sentences = useMemo(
    () =>
      reportHtmlToText(findings)
        .split("\n")
        .map((s) => s.trim())
        .filter((s) => s.length > 0),
    [findings],
  );

  const requestAccept = useCallback(
    (mark: AiMarkFinding) => {
      setLink({
        open: true,
        mark,
        mode: "new-line",
        existingIndex: sentences.length > 0 ? 0 : null,
        sentences,
      });
    },
    [sentences],
  );

  const cancelLink = useCallback(() => {
    setLink((prev) => ({ ...prev, open: false, mark: null }));
  }, []);

  const setLinkMode = useCallback((mode: AiLinkMode) => {
    setLink((prev) => ({ ...prev, mode }));
  }, []);

  const setExistingIndex = useCallback((idx: number | null) => {
    setLink((prev) => ({ ...prev, existingIndex: idx }));
  }, []);

  const applyLink = useCallback(
    (mode: AiLinkMode, existingIndex: number | null, mark: AiMarkFinding) => {
      const text = mark.label.trim();
      if (!text) return;
      if (mode === "new-line") {
        const line = `<div>• ${text}</div>`;
        onFindingsChange(
          sanitizeReportHtml(findings.length ? findings + line : line),
        );
      } else if (mode === "existing-line" && existingIndex != null) {
        const s = sentences[existingIndex];
        if (s) {
          // Append the finding to the chosen sentence, replacing that exact
          // text so the radiologist's wording owns the merged line (C.2).
          const merged = findings.replace(s, `${s} — ${text}`);
          onFindingsChange(sanitizeReportHtml(merged !== findings ? merged : findings));
        }
      }
      // marker-only: no report text; the mark stays on the image only (B.5).
    },
    [findings, sentences, onFindingsChange],
  );

  const confirmLink = useCallback(() => {
    const { mark, mode, existingIndex } = link;
    if (!mark) return;
    applyLink(mode, existingIndex, mark);
    updateMark(mark.id, {
      status: "accepted",
      linkMode: mode,
      actedAt: new Date().toISOString(),
    });
    setInspectedId(null);
    setLink((prev) => ({ ...prev, open: false, mark: null }));
  }, [link, applyLink, updateMark]);

  // B.6 display cap: Unreviewed (open) marks shown by default = the top
  // displayLimit by confidence (High sorts before Uncertain), then a "Show N
  // more" reveal grows it in steps. Accepted marks always show (they are the
  // radiologist's own now); dismissed are governed by the showDismissed toggle.
  const displayedMarks = useMemo(() => {
    const open = marks
      .filter((m) => m.status === "unreviewed")
      .sort((a, b) =>
        a.confidence === b.confidence
          ? 0
          : a.confidence === "High"
            ? -1
            : 1,
      );
    const accepted = marks.filter((m) => m.status === "accepted");
    const revealed = open.slice(0, displayLimit);
    return [...revealed, ...accepted];
  }, [marks, displayLimit]);

  const unreviewedTotal = useMemo(
    () => marks.filter((m) => m.status === "unreviewed").length,
    [marks],
  );
  const hiddenCount = unreviewedTotal - Math.min(displayLimit, unreviewedTotal);
  const revealMore = useCallback(() => {
    setDisplayLimit((prev) => prev + MARK_REVEAL_STEP);
  }, []);

  return {
    marks,
    visible,
    showDismissed,
    setShowDismissed,
    toggleAiFindings,
    inspectMark,
    inspectedId,
    dismissMark,
    requestAccept,
    reconsiderMark,
    displayedMarks,
    hiddenCount,
    revealMore,
    currentFileMarks: useMemo(
      () => (currentFile ? marksForFile(displayedMarks, currentFile.id) : []),
      [displayedMarks, currentFile],
    ),
    count: activeMarkCount(marks),
    sliceIndices: nonDismissedSliceIndices(marks),
    linkState: link,
    cancelLink,
    confirmLink,
    setLinkMode,
    setExistingIndex,
  };
}
