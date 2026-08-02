import { request } from "./client";

export interface Role {
  id: number;
  name: string;
  slug: string;
  description?: string;
  permissions: string[];
  built_in: boolean;
  user_count?: number;
}

export type PermissionGroups = Record<string, string[]>;

export interface RoleInput {
  name?: string;
  slug?: string;
  description?: string;
  permissions: string[];
}

export interface RoleUser {
  id: number;
  username: string;
}

export const listRoles = (): Promise<Role[]> =>
  request<{ data: Role[] }>("roles").then((res) => res.data ?? []);

export const listPermissions = (): Promise<PermissionGroups> =>
  request<{ data: PermissionGroups }>("permissions").then(
    (res) => res.data ?? {},
  );

export const createRole = (input: RoleInput): Promise<void> =>
  request("roles", { data: input });

export const updateRole = (id: number, input: RoleInput): Promise<void> =>
  request(`roles/${id}`, { data: input });

export const deleteRole = (id: number): Promise<void> =>
  request(`roles/${id}`, { data: undefined, method: "DELETE" });

export const listRoleUsers = (id: number): Promise<RoleUser[]> =>
  request<{ data: RoleUser[] }>(`roles/${id}/users`).then(
    (res) => res.data ?? [],
  );
