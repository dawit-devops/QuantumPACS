import { request } from "./client";
import { API_URL } from "../config";

export interface Study {
  studyInstanceUid: string;
  studyId: string;
  studyDescription?: string;
  patientId?: string;
  patientName?: string;
  accessionNumber?: string;
  modalities?: string;
  numberOfSeries?: number;
  numberOfInstances?: number;
  studyDate?: string;
}

function dicomValue(raw: any, tag: string, col?: string): any {
  const v = raw[tag]?.Value;
  if (v && v.length > 0) return v[0];
  if (col) return raw[col];
  return undefined;
}

function pnValue(raw: any, tag: string, col?: string): string {
  const v = raw[tag]?.Value;
  if (v && v.length > 0 && v[0].Alphabetic) return v[0].Alphabetic;
  if (col) return raw[col] || "";
  return "";
}

function mapStudy(raw: any): Study {
  return {
    studyInstanceUid: dicomValue(raw, "0020000D", "study_instance_uid") || "",
    studyId: dicomValue(raw, "00200010", "study_id") || "",
    studyDescription: dicomValue(raw, "00081030", "study_description") || "",
    patientId: dicomValue(raw, "00100020", "patient_id") || "",
    patientName: pnValue(raw, "00100010", "patient_name"),
    accessionNumber: dicomValue(raw, "00080050", "accession_number") || "",
    modalities: dicomValue(raw, "00080061", "modalities") || "",
    numberOfSeries: raw["00201206"]?.Value?.[0] || raw.number_of_series || 0,
    numberOfInstances:
      raw["00201208"]?.Value?.[0] || raw.number_of_instances || 0,
    studyDate: dicomValue(raw, "00080020", "study_date") || "",
  };
}

export interface Series {
  seriesInstanceUid: string;
  seriesNumber?: string;
  modality?: string;
  seriesDescription?: string;
  numberOfInstances?: number;
}

function mapSeries(raw: any): Series {
  return {
    seriesInstanceUid:
      raw["0020000E"]?.Value?.[0] || raw.series_instance_uid || "",
    seriesNumber: raw["00200011"]?.Value?.[0] || raw.series_number || "",
    modality: raw["00080060"]?.Value?.[0] || raw.modality || "",
    seriesDescription:
      raw["0008103E"]?.Value?.[0] || raw.series_description || "",
    numberOfInstances:
      raw["00201209"]?.Value?.[0] || raw.number_of_instances || 0,
  };
}

export interface Instance {
  sopInstanceUid: string;
  instanceNumber?: string;
}

function mapInstance(raw: any): Instance {
  return {
    sopInstanceUid: raw["00080018"]?.Value?.[0] || raw.sop_instance_uid || "",
    instanceNumber: raw["00200013"]?.Value?.[0] || raw.instance_number || "",
  };
}

export async function searchStudies(
  query?: Record<string, string>,
): Promise<Study[]> {
  const qs = query ? "?" + new URLSearchParams(query).toString() : "";
  const data = await request<Study[]>(`/dicomweb/studies${qs}`);
  return (data || []).map(mapStudy);
}

export async function getSeries(studyUid: string): Promise<Series[]> {
  const data = await request<Series[]>(`/dicomweb/studies/${studyUid}/series`);
  return (data || []).map(mapSeries);
}

export async function getInstances(
  studyUid: string,
  seriesUid: string,
): Promise<Instance[]> {
  const data = await request<Instance[]>(
    `/dicomweb/studies/${studyUid}/series/${seriesUid}/instances`,
  );
  return (data || []).map(mapInstance);
}

export function wadoRsUrl(
  studyUid: string,
  seriesUid: string,
  instanceUid: string,
): string {
  return `wadors:${API_URL}/dicomweb/studies/${studyUid}/series/${seriesUid}/instances/${instanceUid}`;
}

function authHeaders(): Record<string, string> {
  const headers: Record<string, string> = {
    "X-CSRF-Token": "1",
  };
  const token = localStorage.getItem("access_token");
  if (token) headers["X-Auth-Pacs"] = token;
  const tenantId = localStorage.getItem("tenant_id");
  if (tenantId) headers["X-Tenant-ID"] = tenantId;
  return headers;
}

export interface StowResult {
  referenced?: unknown[];
  failed?: unknown[];
  [key: string]: unknown;
}

/**
 * STOW-RS upload of raw DICOM files. The backend parses multipart parts
 * directly from the request stream, so the boundary is assembled by hand
 * (FormData would force multipart/form-data and re-encode the files).
 */
export async function storeInstances(files: File[]): Promise<StowResult> {
  const boundary = `stow-${Date.now().toString(36)}-${Math.random()
    .toString(36)
    .slice(2)}`;
  const parts: BlobPart[] = [];
  for (const file of files) {
    parts.push(
      new Blob([
        `--${boundary}\r\nContent-Type: application/dicom\r\nContent-Length: ${file.size}\r\n\r\n`,
      ]),
    );
    parts.push(file);
    parts.push(new Blob(["\r\n"]));
  }
  parts.push(new Blob([`--${boundary}--\r\n`]));
  const resp = await fetch(`${API_URL}/dicomweb/studies`, {
    method: "POST",
    headers: {
      ...authHeaders(),
      "Content-Type": `multipart/related; type=application/dicom; boundary=${boundary}`,
    },
    body: new Blob(parts),
  });
  if (!resp.ok) {
    let message = `STOW-RS failed (${resp.status})`;
    try {
      const err = await resp.json();
      message = err?.error?.message || message;
    } catch {
      // non-JSON error body; keep the status-based message
    }
    throw new Error(message);
  }
  return resp.json();
}

/** Archive download URL for a study (GET with auth headers via fetch). */
export function archiveStudyUrl(studyUid: string): string {
  return `${API_URL}/dicomweb/studies/${studyUid}/archive`;
}

export async function downloadStudyArchive(studyUid: string): Promise<void> {
  const resp = await fetch(archiveStudyUrl(studyUid), {
    headers: authHeaders(),
  });
  if (!resp.ok) {
    let message = `Archive download failed (${resp.status})`;
    try {
      const err = await resp.json();
      message = err?.error?.message || message;
    } catch {
      // keep status-based message
    }
    throw new Error(message);
  }
  const blob = await resp.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `study-${studyUid}.zip`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
