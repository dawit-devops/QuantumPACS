import { request } from "./client";

// §3 configurable-widget substrate: per-user preference documents.
// Backend GET/PUT /account/preferences merges top-level keys server-side,
// so this client can safely post just the section it owns.

export type Preferences = Record<string, any>;

export interface DashboardLayout {
  /** Ordered widget ids; ids absent here trail after role defaults. */
  order?: string[];
  /** Widget ids the user removed from their dashboard. */
  hidden?: string[];
}

export const getPreferences = (): Promise<Preferences> =>
  request<{ data: Preferences }>("account/preferences").then(
    (res) => (res as { data: Preferences })?.data ?? {}
  );

export const updatePreferences = (patch: Preferences): Promise<Preferences> =>
  request<Preferences>("account/preferences", { method: "PUT", data: patch });
