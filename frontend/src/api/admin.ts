import { request } from "./client";
import { API_URL } from "../config";

// Platform-admin ops (super_admin review): maintenance, config, backups.
// All mutation endpoints are SYSTEM_ADMIN-gated server-side; the frontend
// additionally gates the routes/items by the same permission.

export interface MaintenanceState {
  active: boolean;
  reason?: string;
  since?: string;
}

export const getAdminStatus = (): Promise<{ maintenance: MaintenanceState }> =>
  request<{ maintenance: MaintenanceState }>("admin/status");

export const setMaintenance = (
  active: boolean,
  reason = "",
): Promise<{ maintenance: MaintenanceState }> =>
  request<{ maintenance: MaintenanceState }>("admin/maintenance", {
    method: "POST",
    data: { active, reason },
  });

export interface ConfigSetting {
  value: string | number | boolean;
  type: "int" | "str" | "bool";
  restart: boolean;
}

export const getAdminConfig = (): Promise<{
  settings: Record<string, ConfigSetting>;
}> => request<{ settings: Record<string, ConfigSetting> }>("admin/config");

export const updateAdminConfig = (
  settings: Record<string, { value: string | number | boolean }>,
): Promise<{ updated: string[] }> =>
  request<{ updated: string[] }>("admin/config", {
    method: "PUT",
    data: { settings },
  });

export interface Backup {
  id: string;
  status: "running" | "completed" | "failed";
  kind: string;
  artifact_key: string | null;
  size_bytes: number;
  files_count: number;
  bytes_count: number;
  created_by: number | null;
  created_at: string;
}

export const listBackups = (): Promise<{ data: Backup[] }> =>
  request<{ data: Backup[] }>("admin/backups");

export const createBackup = (): Promise<{ data: Backup }> =>
  request<{ data: Backup }>("admin/backups", { method: "POST" });

export const deleteBackup = (id: string): Promise<{ message: string }> =>
  request<{ message: string }>(`admin/backups/${id}`, { method: "DELETE" });

export interface BackupVerification {
  backup_id: string;
  kind?: string;
  generated_at?: string;
  files: number;
  bytes: number;
  master_replica?: number | null;
  valid: boolean;
}

export const verifyBackup = (
  id: string,
): Promise<{ verification: BackupVerification; message: string }> =>
  request<{ verification: BackupVerification; message: string }>(
    `admin/backups/${id}/restore`,
    { method: "POST" },
  );

export async function downloadBackup(id: string): Promise<void> {
  // Raw fetch (not request()): the artifact is JSON bytes with a content
  // disposition, not the JSON envelope request() unwraps.
  const resp = await fetch(`${API_URL}/admin/backups/${id}`, {
    credentials: "include",
  });
  if (!resp.ok) {
    let message = `Backup download failed (${resp.status})`;
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
  a.download = `quantumpacs-backup-${id}.json`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
