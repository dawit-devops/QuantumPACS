import { request } from "./client";
import { listRoles, type Role } from "./roles";

export interface User {
  id: number;
  username: string;
  admin: boolean;
  created?: string;
  status: string;
  role_id?: number | null;
  role_name?: string | null;
  role_slug?: string | null;
  // P2-2 (tenant_admin review): users carry their tenant so the directory
  // can show a tenant column; tenant-scoped admins only ever see their own.
  tenant?: string | null;
}

export interface ListUsersParams {
  q?: string;
  offset?: number;
  limit?: number;
}

export interface UsersPage {
  data: User[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

interface UsersResponse {
  data: User[];
  meta: {
    total: number;
    page: number;
    per_page: number;
    total_pages: number;
  };
}

// Backend paginates via offset/limit query params (users.py UsersHandler.get);
// the response meta carries the true total so the client never infers it from
// the length of the current page.
export const listUsers = (params: ListUsersParams = {}): Promise<UsersPage> => {
  const query: Record<string, string> = {
    offset: String(params.offset ?? 0),
    limit: String(params.limit ?? 20),
  };
  if (params.q) query.q = params.q;
  return request<UsersResponse>("users", { query }).then((res) => ({
    data: res.data ?? [],
    total: res.meta?.total ?? 0,
    page: res.meta?.page ?? 1,
    per_page: res.meta?.per_page ?? 20,
    total_pages: res.meta?.total_pages ?? 1,
  }));
};

export const assignRole = (userId: number, roleId: number): Promise<void> =>
  // Backend route is PUT /api/users/role (UserRoleUpdate); the bare request()
  // helper defaulted to POST, so role assignment never reached the server.
  request("users/role", {
    method: "PUT",
    data: { user_id: userId, role_id: roleId },
  });

export const deactivateUser = (id: number): Promise<void> =>
  request("users/deactivate", { data: { id } });

export const resetPassword = (id: number): Promise<{ password: string }> =>
  request<{ password: string }>("users/new_password", { data: { id } });

export interface CreateUserInput {
  username: string;
  admin?: boolean;
  role_id?: number;
  tenant?: string;
}

export const createUser = (
  input: CreateUserInput,
): Promise<{ username: string; password: string }> =>
  request<{ username: string; password: string }>("users", { data: input });

export { listRoles, type Role };
