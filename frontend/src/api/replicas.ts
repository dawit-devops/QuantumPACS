import { request } from "./client";

export interface Replica {
  id: number;
  name?: string;
  master?: boolean;
  status?: string;
  delay?: number;
  last_sync_at?: string | null;
}

export const listReplicas = (): Promise<Replica[]> =>
  request<{ data: Replica[] }>("replicas").then((res) => res.data ?? []);

export const createReplica = (
  data: Record<string, unknown>,
): Promise<{ id: number }> =>
  request<{ id: number }>("replicas", { data }).then((res) => res ?? { id: 0 });

// ReplicaHandlers is POST-only (update delay / change master); the data
// payload defaults to POST in the client, so no explicit method is needed.
export const updateReplica = (
  id: number,
  data: Record<string, unknown>,
): Promise<void> => request(`replicas/${id}`, { data });

export const deleteReplica = (id: number): Promise<void> =>
  request(`replicas/${id}`, { method: "DELETE" });
