// Part A data model for AI-drafted report content.
// These types hold the draft state for each report section; the radiologist
// accepts/rejects/edits before anything reaches the signed document (A.5
// hard gate: no unreviewed block may survive into a signed report).

export type AiDraftSection = "findings" | "impression" | "recommendations";

export const AI_DRAFT_SECTION_LABELS: Record<AiDraftSection, string> = {
  findings: "Findings",
  impression: "Impression",
  recommendations: "Recommendations",
};

export type AiDraftStatus = "unreviewed" | "accepted" | "rejected";

export type AiDraftActionType =
  | "accept"
  | "reject"
  | "accept-all"
  | "reject-all"
  | "regenerate"
  | "edit-in-place";

export interface AiDraftBlock {
  id: string;
  section: AiDraftSection;
  /** The draft text proposed by the AI model. */
  text: string;
  status: AiDraftStatus;
  version: number;
  totalVersions: number;
  /** A.6 qualitative confidence — never a percentage. Only shown when it
   *  changes behavior (e.g. "Unable to draft — image quality insufficient"). */
  quality?: "ok" | "uncertain";
  /** A.6 prior report conflict note, surfaced inline. */
  priorNote?: string;
  proposedAt: string;
  actedAt?: string;
}

export interface AiDraftChangelogEntry {
  id: string;
  timestamp: string;
  action: AiDraftActionType;
  section: AiDraftSection;
  blockId: string;
  detail?: string;
}