import { request } from "./client";

export interface OauthProvider {
  id: string;
  name?: string;
  provider?: string;
  client_id?: string;
  enabled?: boolean;
  auth_url?: string;
}

export interface Webhook {
  id: number;
  url?: string;
  event?: string;
  events?: string[];
  active?: boolean;
  secret?: string;
  created_at?: string;
}

export const listOauthProviders = (): Promise<OauthProvider[]> =>
  request<{ providers?: OauthProvider[]; data?: OauthProvider[] }>(
    "oauth/providers",
  ).then((res) => res?.providers ?? res?.data ?? []);

export const createOauthProvider = (
  data: Record<string, unknown>,
): Promise<void> => request("oauth/providers", { method: "POST", data });

export const updateOauthProvider = (
  id: string,
  data: Record<string, unknown>,
): Promise<void> =>
  request(`oauth/providers/${id}`, { method: "PUT", data });

export const deleteOauthProvider = (id: string): Promise<void> =>
  request(`oauth/providers/${id}`, { method: "DELETE" });

export interface WebhookList {
  webhooks: Webhook[];
  available_events: string[];
}

export const listWebhooks = (): Promise<WebhookList> =>
  request<WebhookList>("webhooks");

export const createWebhook = (
  data: Record<string, unknown>,
): Promise<Webhook> =>
  request<Webhook>("webhooks", { method: "POST", data });

export const updateWebhook = (
  id: number | string,
  data: Record<string, unknown>,
): Promise<Webhook> =>
  request<Webhook>(`webhooks/${id}`, { method: "PUT", data });

export const deleteWebhook = (id: number | string): Promise<void> =>
  request(`webhooks/${id}`, { method: "DELETE" });

export const testWebhook = (
  data: Record<string, unknown>,
): Promise<{ ok?: boolean; status_code?: number; error?: string }> =>
  request("webhooks/test", { method: "POST", data });
