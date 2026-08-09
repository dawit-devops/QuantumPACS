import { describe, it, expect, vi, beforeEach } from "vitest";
import { request } from "../api/client";
import {
  searchPatients,
  createPatient,
  listVisits,
  createVisit,
  getVisit,
  updateVisit,
  checkInVisit,
  listOrders,
  createOrder,
  listConsents,
  attachConsent,
  listInsurance,
  createInsurance,
  getAvailability,
  listAppointments,
  createAppointment,
  cancelAppointment,
  getWaitingQueue,
} from "../api/frontdesk";

// R4-04: the FrontDesk.test.tsx suite mocks this whole module, so the real
// request contract (paths, methods, unwrapping) is only pinned here.

vi.mock("../api/client", () => ({
  request: vi.fn(),
}));

const mockRequest = vi.mocked(request);

describe("frontdesk api client", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("checkInVisit sends PUT visits/{id} with status checked_in", async () => {
    mockRequest.mockResolvedValue(undefined);
    await checkInVisit("v1");
    expect(mockRequest).toHaveBeenCalledWith("visits/v1", {
      method: "PUT",
      data: { status: "checked_in" },
    });
  });

  it("updateVisit sends a PUT with the caller's patch", async () => {
    mockRequest.mockResolvedValue(undefined);
    await updateVisit("v1", { status: "in_progress", destination_room: "CT1" });
    expect(mockRequest).toHaveBeenCalledWith("visits/v1", {
      method: "PUT",
      data: { status: "in_progress", destination_room: "CT1" },
    });
  });

  it("getWaitingQueue passes the date and unwraps res.data", async () => {
    mockRequest.mockResolvedValue({
      data: [{ visit_id: "v1", initials: "J.S.", last4: "2345" }],
    });
    const rows = await getWaitingQueue({ date: "2026-08-09" });
    expect(mockRequest).toHaveBeenCalledWith("queue", {
      query: { date: "2026-08-09" },
    });
    expect(rows).toEqual([{ visit_id: "v1", initials: "J.S.", last4: "2345" }]);
  });

  it("getWaitingQueue falls back to an empty list when data is absent", async () => {
    mockRequest.mockResolvedValue({});
    expect(await getWaitingQueue()).toEqual([]);
  });

  it("createAppointment posts the payload unchanged", async () => {
    mockRequest.mockResolvedValue({ data: { id: "a1" } });
    const payload = {
      patient_id: "P001",
      modality: "CT",
      scheduled_date: "2026-08-09",
      scheduled_time: "09:00:00",
    };
    const appt = await createAppointment(payload);
    expect(mockRequest).toHaveBeenCalledWith("appointments", { data: payload });
    expect(appt).toEqual({ id: "a1" });
  });

  it("cancelAppointment sends a DELETE", async () => {
    mockRequest.mockResolvedValue(undefined);
    await cancelAppointment("a1");
    expect(mockRequest).toHaveBeenCalledWith("appointments/a1", {
      data: undefined,
      method: "DELETE",
    });
  });

  it("getAvailability passes modality/date and unwraps", async () => {
    mockRequest.mockResolvedValue({
      data: [{ time: "09:00", capacity: 2, booked: 0, state: "free" }],
    });
    const slots = await getAvailability({
      modality: "CT",
      date: "2026-08-09",
    });
    expect(mockRequest).toHaveBeenCalledWith("schedule/availability", {
      query: { modality: "CT", date: "2026-08-09" },
    });
    expect(slots).toHaveLength(1);
  });

  it("searchPatients passes the term and unwraps", async () => {
    mockRequest.mockResolvedValue({
      data: [{ id: 1, patient_id: "P001", name: "Jane Roe" }],
    });
    const rows = await searchPatients("Jane");
    expect(mockRequest).toHaveBeenCalledWith("patients/search", {
      query: { q: "Jane" },
    });
    expect(rows).toHaveLength(1);
  });

  it("createPatient posts and unwraps the created patient", async () => {
    mockRequest.mockResolvedValue({
      data: { id: 2, patient_id: "P002", name: "Jane Roe" },
    });
    const patient = await createPatient({ name: "Jane Roe" });
    expect(mockRequest).toHaveBeenCalledWith("patients", {
      data: { name: "Jane Roe" },
    });
    expect(patient.patient_id).toBe("P002");
  });

  it("listVisits defaults to an empty page when the response is absent", async () => {
    mockRequest.mockResolvedValue(undefined);
    expect(await listVisits({ page: "1" })).toEqual({
      data: [],
      total: 0,
      page: 1,
      per_page: 20,
    });
  });

  it("createVisit posts and unwraps", async () => {
    mockRequest.mockResolvedValue({
      data: { id: "v9", patient_id: "P001", status: "registered" },
    });
    const visit = await createVisit({ patient_id: "P001" });
    expect(mockRequest).toHaveBeenCalledWith("visits", {
      data: { patient_id: "P001" },
    });
    expect(visit.id).toBe("v9");
  });

  it("getVisit returns null when no data is present", async () => {
    mockRequest.mockResolvedValue({ data: null });
    expect(await getVisit("v1")).toBeNull();
  });

  it("orders/consents/insurance helpers unwrap their arrays", async () => {
    mockRequest.mockResolvedValue({ data: [{ id: "o1" }] });
    expect(await listOrders("v1")).toEqual([{ id: "o1" }]);
    expect(await listConsents("v1")).toEqual([{ id: "o1" }]);
    expect(await listInsurance("P001")).toEqual([{ id: "o1" }]);
    mockRequest.mockResolvedValue({ data: { id: "o2" } });
    expect(await createOrder("v1", { requested_procedure: "CT" })).toEqual({
      id: "o2",
    });
    expect(await attachConsent("v1", { consent_type: "surgery" })).toEqual({
      id: "o2",
    });
    expect(await createInsurance("P001", { policy_number: "X" })).toEqual({
      id: "o2",
    });
  });

  it("listAppointments unwraps and defaults to an empty list", async () => {
    mockRequest.mockResolvedValue({});
    expect(await listAppointments()).toEqual([]);
  });
});
