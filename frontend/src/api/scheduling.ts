import { request } from "./client";

// ---------------------------------------------------------------------------
// S4 RIS scheduling API client — resources, schedules, availability,
// appointments (book/reschedule/cancel) and order search for the booking
// form. All handlers live in backend/api/scheduling.py + ris_orders.py and
// wrap payloads in {"data": ...}; these helpers unwrap so callers get the
// resource directly (same shape the frontdesk module surfaces).
// ---------------------------------------------------------------------------

export interface RisResource {
  id: string;
  name: string;
  resource_type: "ROOM" | "MODALITY" | "TECH";
  modality?: string | null;
  location?: string | null;
  status: "ACTIVE" | "INACTIVE";
  created_at?: string;
  [key: string]: unknown;
}

export interface RisSchedule {
  id: string;
  resource_id: string;
  day_of_week: number; // 0 = Monday .. 6 = Sunday
  start_time: string; // "HH:MM:SS"
  end_time: string;
  [key: string]: unknown;
}

export interface ResourceAvailabilitySlot {
  start: string; // "HH:MM" — UTC wall-clock (backend engine timezone)
  end: string; // "HH:MM" — UTC wall-clock
}

export interface RisAppointment {
  id: string;
  order_id?: string | null;
  resource_id: string;
  patient_id: string;
  status: "SCHEDULED" | "ARRIVED" | "IN_PROGRESS" | "COMPLETED" | "CANCELLED" | "NO_SHOW";
  start_time: string;
  end_time: string;
  reason?: string;
  override_reason?: string;
  created_at?: string;
  [key: string]: unknown;
}

export interface RisOrderRow {
  id: string;
  accession_number: string;
  patient_id: string;
  patient_name?: string;
  priority: "ROUTINE" | "URGENT" | "STAT";
  status: string;
  referring_physician?: string;
  clinical_indication?: string;
  prior_auth_status?: string;
  created_at?: string;
  [key: string]: unknown;
}

export interface RisOrderPage {
  data: RisOrderRow[];
  total: number;
  page: number;
  per_page: number;
}

const DAYS = [
  "Monday",
  "Tuesday",
  "Wednesday",
  "Thursday",
  "Friday",
  "Saturday",
  "Sunday",
] as const;

export const dayOfWeekLabel = (day: number): string => DAYS[day] ?? String(day);

// ---- Resources --------------------------------------------------------------

export const listRisResources = (
  params: { resource_type?: string; modality?: string } = {}
): Promise<RisResource[]> => {
  const query: Record<string, string> = {};
  if (params.resource_type) query.resource_type = params.resource_type;
  if (params.modality) query.modality = params.modality;
  return request<{ data: RisResource[] }>("ris/resources", { query }).then((res) => res.data ?? []);
};

export const createRisResource = (data: Record<string, unknown>): Promise<RisResource> =>
  request<{ data: RisResource }>("ris/resources", { data }).then((res) => res.data);

// ---- Schedules ----------------------------------------------------------------

export const listRisSchedules = (resourceId: string): Promise<RisSchedule[]> =>
  request<{ data: RisSchedule[] }>(`ris/resources/${resourceId}/schedules`).then(
    (res) => res.data ?? []
  );

export const createRisSchedule = (
  resourceId: string,
  data: Record<string, unknown>
): Promise<RisSchedule> =>
  request<{ data: RisSchedule }>(`ris/resources/${resourceId}/schedules`, {
    data,
  }).then((res) => res.data);

// ---- Availability ---------------------------------------------------------------

export const getResourceAvailability = (
  resourceId: string,
  date: string
): Promise<ResourceAvailabilitySlot[]> =>
  request<{ data: ResourceAvailabilitySlot[] }>(`ris/resources/${resourceId}/availability`, {
    query: { date },
  }).then((res) => res.data ?? []);

// ---- Appointments ----------------------------------------------------------------

export const listResourceAppointments = (
  resourceId: string,
  date: string
): Promise<RisAppointment[]> =>
  request<{ data: RisAppointment[] }>("ris/appointments", {
    query: { resource_id: resourceId, date },
  }).then((res) => res.data ?? []);

export interface BookAppointmentInput {
  order_id?: string; // omitted/empty for order-less (patient-ID) bookings
  resource_id: string;
  patient_id: string;
  // ISO-8601 UTC instants — slots returned by getResourceAvailability are
  // UTC wall-clock ("HH:MM") and MUST be converted to UTC instants, not
  // browser-local ones, or the engine rejects them as outside availability.
  start_time: string;
  end_time: string;
  reason?: string;
  override_reason?: string;
}

export const bookAppointment = (data: BookAppointmentInput): Promise<RisAppointment> =>
  request<{ data: RisAppointment }>("ris/appointments", { data }).then((res) => res.data);

export const rescheduleAppointment = (
  appointmentId: string,
  data: { new_start_time: string; new_end_time: string; reason?: string }
): Promise<RisAppointment> =>
  request<{ data: RisAppointment }>(`ris/appointments/${appointmentId}/reschedule`, {
    data,
  }).then((res) => res.data);

export const cancelRisAppointment = (appointmentId: string, reason = ""): Promise<RisAppointment> =>
  request<{ data: RisAppointment }>(`ris/appointments/${appointmentId}/cancel`, {
    data: { reason },
  }).then((res) => res.data);

// S-13: mark appointment as no-show.
export const markNoShow = (appointmentId: string): Promise<RisAppointment> =>
  request<{ data: RisAppointment }>(`ris/appointments/${appointmentId}/no-show`, {
    method: "POST",
  }).then((res) => res.data);

// FD-04: staff one-click check-in (SCHEDULE_WRITE) — SCHEDULED → ARRIVED,
// idempotent for an already-ARRIVED appointment (409 surfaces as info).
export const checkInAppointment = (appointmentId: string): Promise<RisAppointment> =>
  request<{ data: RisAppointment }>(`ris/appointments/${appointmentId}/check-in`, {
    method: "POST",
  }).then((res) => res.data);

// S-03: date-range appointments for week/month calendar views.
export const listAppointmentsDateRange = (
  dateFrom: string,
  dateTo: string,
  params: { resource_id?: string } = {}
): Promise<RisAppointment[]> =>
  request<{ data: RisAppointment[] }>("ris/appointments", {
    query: { date_from: dateFrom, date_to: dateTo, ...params },
  }).then((res) => res.data ?? []);

// ---- Orders (booking form patient/order search) --------------------------------

export const searchRisOrders = (
  params: {
    search?: string;
    status?: string;
    page?: number;
    per_page?: number;
  } = {}
): Promise<RisOrderPage> => {
  const query: Record<string, string> = {};
  if (params.search) query.search = params.search;
  if (params.status) query.status = params.status;
  if (params.page !== undefined) query.page = String(params.page);
  if (params.per_page !== undefined) query.per_page = String(params.per_page);
  return request<RisOrderPage>("ris/orders", { query }).then(
    (res) => res ?? { data: [], total: 0, page: 1, per_page: 25 }
  );
};

// ---- C4: order detail for the booking form ---------------------------------

export interface RisOrderProcedure {
  id?: string;
  procedure_code?: string;
  procedure_name?: string;
  modality?: string;
  body_part?: string;
  contrast?: boolean;
  [key: string]: unknown;
}

export interface RisOrderDetail {
  order: RisOrderRow;
  procedures: RisOrderProcedure[];
  appointments: RisAppointment[];
}

export const getRisOrder = (orderId: string): Promise<RisOrderDetail> =>
  request<{ data: RisOrderDetail }>(`ris/orders/${orderId}`).then((res) => res.data);
