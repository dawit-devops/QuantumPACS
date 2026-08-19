/**
 * Canonical modality list — single source of truth for the frontend.
 *
 * History: five different files each declared their own MODALITIES array with
 * contradictory vocabularies ("MR" vs "MRI", different subsets). This module
 * replaces all of them. The backend (dicomweb.py VALID_MODALITIES) uses "MR"
 * per DICOM PS3.6; "MRI" is included here as a recognized alias for
 * backwards compatibility with ScheduleBoard's worklist data.
 */

/** All recognized modalities (DICOM standard + common aliases). */
export const MODALITIES = [
  "CT",
  "MR",
  "MRI", // alias for MR — recognized for display, normalized on create
  "PET",
  "DX",
  "US",
  "MG",
  "FL",
  "XA",
  "NM",
  "PT",
  "CR",
  "IO",
  "RF",
  "SC",
  "OT",
  "BI",
  "SR",
  "SEG",
] as const;

export type Modality = (typeof MODALITIES)[number];

/**
 * Check if a string is a recognized modality (case-sensitive).
 * Accepts both "MR" and "MRI".
 */
export const isValidModality = (m: string): m is Modality =>
  (MODALITIES as readonly string[]).includes(m);

/**
 * Normalize a modality string for backend storage.
 * - Trims and uppercases
 * - Maps "MRI" → "MR" (the canonical DICOM value the backend expects)
 *
 * Unknown values pass through unchanged (backend validates independently).
 */
export const normalizeModality = (m: string): string => {
  const upper = m.trim().toUpperCase();
  return upper === "MRI" ? "MR" : upper;
};
