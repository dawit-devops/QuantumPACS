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

// Built-in role slugs -> display names (R2-16 catalog, 14 slugs). Kept in one
// place so every role the API can return renders a stable human name instead
// of relying on DB names.
export const NAME_MAP: Record<string, string> = {
  super_admin: "System Admin",
  tenant_admin: "Tenant Admin",
  patient: "Patient",
  radiologist: "Radiologist",
  teleradiologist: "Teleradiologist",
  technologist: "Technologist",
  receptionist: "Receptionist",
  referring_physician: "Referring Physician",
  pacs_admin: "PACS Administrator",
  physician: "Physician",
  resident: "Resident",
  care_coordinator: "Care Coordinator",
  emr_admin: "EMR Admin",
  cashier: "Cashier",
};

export function roleDisplayName(slug?: string, fallback?: string): string {
  if (!slug) return fallback ?? "";
  return NAME_MAP[slug] ?? fallback ?? slug;
}

// Permission codes -> human-readable labels. Covers the canonical codes from
// RBAC spec §3/§8 plus the legacy codes already emitted by the backend.
export const PERMISSION_LABELS: Record<string, string> = {
  // canonical (spec §3/§8)
  VIEWER_READ: "View images",
  STUDY_READ: "Access studies",
  STUDY_EXPORT: "Export studies",
  STORAGE_ADMIN: "Storage & retention admin",
  INTERFACE_MONITOR: "Monitor interfaces",
  INTERFACE_ADMIN: "Configure modalities/routing",
  METERING_READ: "View usage/billing",
  CRITICAL_RESULTS_WRITE: "Flag critical results",
  REPORT_TEMPLATE_ADMIN: "Manage report templates",
  AUDIT_READ: "View audit log",
  CHART_READ: "View patient chart",
  ENCOUNTER_WRITE: "Document encounters",
  NOTE_SIGN: "Sign notes",
  MED_ORDER_READ: "View medication orders",
  MED_ORDER_WRITE: "Order medications",
  MED_VERIFY: "Verify medications",
  MAR_READ: "View MAR",
  MAR_WRITE: "Chart medications",
  RESULTS_READ: "View results",
  RESULTS_RELEASE: "Release results",
  LAB_SPECIMEN_WRITE: "Specimen accession",
  CARE_PLAN_WRITE: "Care plans",
  HIM_WRITE: "Medical records",
  CDS_ADMIN: "Clinical decision support",
  CODING_WRITE: "Medical coding",
  PATIENT_MERGE: "Merge patients",
  MPI_ADMIN: "Patient identifiers",
  PRIOR_AUTH_READ: "View prior auth",
  PRIOR_AUTH_WRITE: "Prior auth",
  ORDER_READ: "View orders",
  ORDER_WRITE: "Manage orders",
  SCHEDULE_READ: "View schedule",
  SCHEDULE_WRITE: "Manage schedule",
  SYSTEM_ADMIN: "System admin",
  // legacy
  FILE_READ: "View files",
  FILE_WRITE: "Upload files",
  FILE_DELETE: "Delete files",
  PATIENT_READ: "View patients",
  PATIENT_WRITE: "Edit patients",
  STUDY_WRITE: "Manage studies",
  USER_READ: "View users",
  USER_WRITE: "Manage users",
  USER_DELETE: "Delete users",
  USER_ADMIN: "Administer users",
  REPLICA_READ: "View replicas",
  REPLICA_WRITE: "Manage replicas",
  REPLICA_DELETE: "Delete replicas",
  LOG_READ: "View audit log",
  TENANT_READ: "View tenants",
  TENANT_WRITE: "Manage tenants",
  TENANT_ADMIN: "Administer tenants",
  ROLE_READ: "View roles",
  ROLE_WRITE: "Manage roles",
  ROLE_DELETE: "Delete roles",
  SERVICE_KEY_READ: "View service keys",
  SERVICE_KEY_WRITE: "Manage service keys",
  SERVICE_KEY_DELETE: "Revoke service keys",
  WORKLIST_READ: "View worklist",
  WORKLIST_WRITE: "Update worklist",
  EXAM_READ: "View exams",
  EXAM_WRITE: "Manage exams",
  REPORT_READ: "View reports",
  REPORT_WRITE: "Write reports",
  REPORT_SIGN: "Sign reports",
  PEER_REVIEW_READ: "View peer review",
  PEER_REVIEW_WRITE: "Manage peer review",
  QA_READ: "View QA",
  QA_WRITE: "Manage QA",
  PROTOCOL_MANAGE: "Manage protocols",
  DICOMWEB_READ: "View DICOMweb",
  DICOMWEB_WRITE: "Manage DICOMweb",
  ROUTING_READ: "View routing",
  ROUTING_WRITE: "Manage routing",
  METRICS_READ: "View metrics",
  HL7_READ: "View HL7",
  HL7_WRITE: "Manage HL7",
  REGISTRATION_READ: "View registrations",
  REGISTRATION_WRITE: "Register patients",
  QUEUE_READ: "View queues",
  BILLING_READ: "View billing",
  BILLING_WRITE: "Manage billing",
  BILLING_ADMIN: "Administer billing",
  EQUIPMENT_READ: "View equipment",
  EQUIPMENT_WRITE: "Manage equipment",
  NURSING_READ: "View nursing",
  NURSING_WRITE: "Manage nursing",
  ANALYTICS_READ: "View analytics",
  ANALYTICS_EXPORT: "Export analytics",
  REPORT_BUILD: "Build reports",
  PORTAL_READ: "Patient portal",
  FOLLOW_UP_WRITE: "Follow-up tasks",
  CROSS_TENANT_READ: "Read other tenants (telemedicine/teleradiology)",
};

export function permissionLabel(code: string): string {
  return PERMISSION_LABELS[code] ?? code;
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
  request(`roles/${id}`, { data: input, method: "PUT" });

export const deleteRole = (id: number): Promise<void> =>
  request(`roles/${id}`, { data: undefined, method: "DELETE" });

export const listRoleUsers = (id: number): Promise<RoleUser[]> =>
  request<{ data: RoleUser[] }>(`roles/${id}/users`).then(
    (res) => res.data ?? [],
  );
