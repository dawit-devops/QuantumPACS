import { request } from "./client";
import { API_URL } from "../config";

export interface WeasisStatus {
  enabled: boolean;
  launch_url: string;
}

/** Probe whether the Weasis connector integration is enabled (ADR-028). */
export async function getWeasisStatus(): Promise<WeasisStatus> {
  // No leading slash: request() joins API_URL + "/" + path, so a
  // leading "/" would double the slash and 404 (same convention as
  // the other api/* modules).
  return request<WeasisStatus>("weasis/status");
}

/** Launch URL — the backend 302s to the weasis-pacs-connector. */
export function weasisLaunchUrl(studyUid: string): string {
  return `${API_URL}/weasis/launch?studyUID=${encodeURIComponent(studyUid)}`;
}

export function openInWeasis(studyUid: string): void {
  window.open(weasisLaunchUrl(studyUid), "_blank", "noopener");
}
