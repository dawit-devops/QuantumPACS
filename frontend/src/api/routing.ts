import { request } from "./client";

export interface RoutingRule {
  id: number;
  name?: string;
  description?: string;
  conditions?: unknown;
  destination?: string;
  enabled?: boolean;
  priority?: number;
}

export interface RoutingPagination {
  page: number;
  per_page: number;
  total: number;
  pages: number;
}

export interface RoutingPage {
  data: RoutingRule[];
  pagination: RoutingPagination;
}

export const listRoutingRules = (
  params: Record<string, string> = {},
): Promise<RoutingPage> =>
  request<RoutingPage>("routing", { query: params });

export const createRoutingRule = (
  data: Record<string, unknown>,
): Promise<RoutingRule> =>
  request<RoutingRule>("routing", { data }).then((res) => res ?? {});

export const updateRoutingRule = (
  id: number | string,
  data: Record<string, unknown>,
): Promise<void> => request(`routing/${id}`, { data });

export const deleteRoutingRule = (id: number | string): Promise<void> =>
  request(`routing/${id}`, { data: undefined, method: "DELETE" });
