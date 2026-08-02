import { request } from "./client";

export interface UserProfile {
  username?: string;
  email?: string;
  full_name?: string;
  role?: string;
}

export const getProfile = (): Promise<UserProfile> =>
  request<UserProfile>("account/profile", { method: "GET" });

export const updateProfile = (
  data: Record<string, unknown>,
): Promise<{ message: string }> =>
  request<{ message: string }>("account/profile", { method: "PUT", data });

export const changePassword = (
  data: Record<string, unknown>,
): Promise<unknown> => request("change_password", { data });
