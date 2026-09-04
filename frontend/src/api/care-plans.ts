import { request } from "./client";

// CS5/CC-02: care plans — coordinator board of per-patient plans.
export interface CarePlanTask {
  label: string;
  done: boolean;
}

export interface CarePlan {
  id: string;
  patient_id: string;
  title: string;
  status: "active" | "completed" | "on_hold";
  tasks: CarePlanTask[];
  responsible_provider: string;
  follow_up_at: string | null;
  notes: string;
  tenant_id: string;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface CarePlanInput {
  patient_id: string;
  title: string;
  status?: string;
  tasks?: CarePlanTask[];
  responsible_provider?: string;
  follow_up_at?: string | null;
  notes?: string;
}

export const listCarePlans = (
  query: Record<string, string> = {},
): Promise<{ data: CarePlan[] }> =>
  request<{ data: CarePlan[] }>("ris/care-plans", { query });

export const createCarePlan = (data: CarePlanInput): Promise<{ data: CarePlan }> =>
  request("ris/care-plans", { method: "POST", data });

export const updateCarePlan = (
  id: string,
  data: CarePlanInput,
): Promise<{ status: string }> =>
  request(`ris/care-plans/${id}`, { method: "PATCH", data });
