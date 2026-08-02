import { request } from "./client";

export interface ApiKey {
  id: number;
  name?: string;
  created_at?: string;
  last_used_at?: string | null;
  active?: boolean;
}

export interface CreatedApiKey {
  id: number;
  raw_key: string;
}

export const listApiKeys = (): Promise<ApiKey[]> =>
  request<{ data: ApiKey[] }>("api-keys").then((res) => res.data ?? []);

export const createApiKey = (
  data: Record<string, unknown>,
): Promise<CreatedApiKey> =>
  request<{ data: CreatedApiKey }>("api-keys", { data }).then(
    (res) => res.data,
  );

export const deleteApiKey = (id: number | string): Promise<void> =>
  request(`api-keys/${id}`, { data: undefined, method: "DELETE" });
