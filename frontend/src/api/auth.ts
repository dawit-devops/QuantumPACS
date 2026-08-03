import { request } from "./client";

export const logout = (): Promise<void> =>
  request("auth/logout", { method: "POST" });

export interface OauthProviderOption {
  id?: string;
  name?: string;
  [key: string]: unknown;
}

export const listLoginProviders = (): Promise<OauthProviderOption[]> =>
  request<{ providers?: OauthProviderOption[]; data?: OauthProviderOption[] }>(
    "oauth/providers/public",
  ).then((res) => res?.providers ?? res?.data ?? []);
