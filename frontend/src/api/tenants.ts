import { request } from "./client";

export interface Tenant {
  id: number;
  slug?: string;
  name?: string;
  domain?: string;
  status?: string;
  created_at?: string;
}

export const listTenants = (): Promise<Tenant[]> =>
  request<{ data: Tenant[] }>("tenants").then((res) => res.data ?? []);

export const createTenant = (
  data: Record<string, unknown>,
): Promise<Tenant> => request<Tenant>("tenants", { data });

export const updateTenant = (
  id: number,
  data: Record<string, unknown>,
): Promise<void> => request(`tenants/${id}`, { method: "PUT", data });

export const deleteTenant = (id: number): Promise<void> =>
  request(`tenants/${id}`, { data: undefined, method: "DELETE" });

// v2/tenants is the session-scoped tenant list used by the login flow.
export const listSessionTenants = (): Promise<Tenant[]> =>
  request<{ data: Tenant[] }>("v2/tenants").then((res) => res.data ?? []);
