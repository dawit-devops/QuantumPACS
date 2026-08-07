import { request } from "./client";

export interface Tenant {
  id: string;
  slug?: string;
  name?: string;
  domain?: string;
  plan?: string;
  status?: string;
  created_at?: string;
  last_activity?: string | null;
  storage_quota_bytes?: number;
  storage_used_bytes?: number;
  user_count?: number;
  study_count?: number;
}

export interface TenantStats {
  user_count: number;
  study_count: number;
  file_count: number;
  storage_used_bytes: number;
  storage_quota_bytes: number;
  storage_pct: number;
  last_activity: string | null;
}

// Tenant ids are backend UUIDs; the provision response may carry the
// one-time admin password that is never retrievable afterwards.
export interface CreateTenantResponse {
  id: string;
  admin_password?: string;
}

export interface TenantUsageRow {
  date: string;
  api_calls: number;
}

export interface TenantHealth {
  status: string;
  [key: string]: unknown;
}

export const listTenants = (): Promise<Tenant[]> =>
  request<{ data: Tenant[] }>("tenants").then((res) => res.data ?? []);

export const createTenant = (
  data: Record<string, unknown>,
): Promise<CreateTenantResponse> =>
  request<CreateTenantResponse>("tenants", { data });

export const updateTenant = (
  id: string,
  data: Record<string, unknown>,
): Promise<void> => request(`tenants/${id}`, { method: "PUT", data });

export const deleteTenant = (id: string): Promise<void> =>
  request(`tenants/${id}`, { data: undefined, method: "DELETE" });

// Daily api_calls series for the per-tenant usage panel. The backend may
// wrap rows in {data: [...]} or return a bare array; normalize to an array.
export const getTenantUsage = async (id: string): Promise<TenantUsageRow[]> => {
  const res = (await request(`tenants/${id}/usage`)) as any;
  if (Array.isArray(res)) return res;
  if (Array.isArray(res?.data)) return res.data;
  if (Array.isArray(res?.usage)) return res.usage;
  return [];
};

// One-shot health probe for all tenants, keyed by slug (fallback: id).
// Callers must treat a failure (e.g. 404 before the endpoint exists) as
// "unknown health" and degrade — never block the tenant list on it.
export const getTenantHealth = async (): Promise<
  Record<string, TenantHealth>
> => {
  let res: any;
  try {
    res = await request("tenants/health");
  } catch {
    return {};
  }
  if (Array.isArray(res)) {
    const map: Record<string, TenantHealth> = {};
    for (const t of res) {
      if (t && (t.slug || t.id)) map[t.slug || t.id] = { status: t.status };
    }
    return map;
  }
  if (Array.isArray(res?.data)) {
    const map: Record<string, TenantHealth> = {};
    for (const t of res.data) {
      if (t && (t.slug || t.id)) map[t.slug || t.id] = { status: t.status };
    }
    return map;
  }
  return (res as Record<string, TenantHealth>) || {};
};

// v2/tenants is the session-scoped tenant list used by the login flow.
export const listSessionTenants = (): Promise<Tenant[]> =>
  request<{ data: Tenant[] }>("v2/tenants").then((res) => res.data ?? []);
