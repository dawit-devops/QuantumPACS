import { describe, it, expect, vi, beforeEach } from "vitest";

import { request } from "../api/client";
import {
  listRisResources,
  createRisResource,
  listRisSchedules,
  createRisSchedule,
  getResourceAvailability,
  listResourceAppointments,
  bookAppointment,
  rescheduleAppointment,
  cancelRisAppointment,
  searchRisOrders,
  dayOfWeekLabel,
} from "../api/scheduling";

// S4 Chain C: the real request contract (paths, methods, unwrapping) is
// pinned here so the calendar/resource UI tests can mock this module freely.

vi.mock("../api/client", () => ({
  request: vi.fn(),
}));

const mockRequest = vi.mocked(request);

describe("scheduling api client", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("listRisResources passes filters and unwraps res.data", async () => {
    mockRequest.mockResolvedValue({
      data: [{ id: "r1", name: "CT Room 1", resource_type: "ROOM" }],
    });
    const rows = await listRisResources({ resource_type: "ROOM", modality: "CT" });
    expect(mockRequest).toHaveBeenCalledWith("ris/resources", {
      query: { resource_type: "ROOM", modality: "CT" },
    });
    expect(rows).toHaveLength(1);
  });

  it("listRisResources omits empty filters and falls back to []", async () => {
    mockRequest.mockResolvedValue({});
    expect(await listRisResources()).toEqual([]);
    expect(mockRequest).toHaveBeenCalledWith("ris/resources", { query: {} });
  });

  it("createRisResource posts and unwraps", async () => {
    mockRequest.mockResolvedValue({ data: { id: "r2", name: "MRI 1" } });
    const resource = await createRisResource({
      name: "MRI 1",
      resource_type: "MODALITY",
      modality: "MR",
    });
    expect(mockRequest).toHaveBeenCalledWith("ris/resources", {
      data: { name: "MRI 1", resource_type: "MODALITY", modality: "MR" },
    });
    expect(resource.name).toBe("MRI 1");
  });

  it("listRisSchedules GETs per resource and unwraps", async () => {
    mockRequest.mockResolvedValue({
      data: [{ id: "s1", resource_id: "r1", day_of_week: 0 }],
    });
    const rows = await listRisSchedules("r1");
    expect(mockRequest).toHaveBeenCalledWith("ris/resources/r1/schedules");
    expect(rows).toHaveLength(1);
  });

  it("createRisSchedule posts day/window to the resource path", async () => {
    mockRequest.mockResolvedValue({
      data: { id: "s2", day_of_week: 1, start_time: "08:00:00" },
    });
    await createRisSchedule("r1", {
      day_of_week: 1,
      start_time: "08:00:00",
      end_time: "17:00:00",
    });
    expect(mockRequest).toHaveBeenCalledWith("ris/resources/r1/schedules", {
      data: { day_of_week: 1, start_time: "08:00:00", end_time: "17:00:00" },
    });
  });

  it("getResourceAvailability passes date query and unwraps", async () => {
    mockRequest.mockResolvedValue({
      data: [{ start: "09:00", end: "09:30" }],
    });
    const slots = await getResourceAvailability("r1", "2026-08-20");
    expect(mockRequest).toHaveBeenCalledWith("ris/resources/r1/availability", {
      query: { date: "2026-08-20" },
    });
    expect(slots[0].start).toBe("09:00");
  });

  it("listResourceAppointments passes resource_id+date and unwraps", async () => {
    mockRequest.mockResolvedValue({
      data: [{ id: "a1", patient_id: "P1", status: "SCHEDULED" }],
    });
    const rows = await listResourceAppointments("r1", "2026-08-20");
    expect(mockRequest).toHaveBeenCalledWith("ris/appointments", {
      query: { resource_id: "r1", date: "2026-08-20" },
    });
    expect(rows[0].status).toBe("SCHEDULED");
  });

  it("bookAppointment posts the payload unchanged", async () => {
    mockRequest.mockResolvedValue({ data: { id: "a2" } });
    const payload = {
      order_id: "o1",
      resource_id: "r1",
      patient_id: "P1",
      start_time: "2026-08-20T09:00:00.000Z",
      end_time: "2026-08-20T09:30:00.000Z",
    };
    const appt = await bookAppointment(payload);
    expect(mockRequest).toHaveBeenCalledWith("ris/appointments", {
      data: payload,
    });
    expect(appt.id).toBe("a2");
  });

  it("rescheduleAppointment posts new window to the reschedule path", async () => {
    mockRequest.mockResolvedValue({ data: { id: "a1" } });
    await rescheduleAppointment("a1", {
      new_start_time: "2026-08-20T10:00:00.000Z",
      new_end_time: "2026-08-20T10:30:00.000Z",
      reason: "conflict",
    });
    expect(mockRequest).toHaveBeenCalledWith("ris/appointments/a1/reschedule", {
      data: {
        new_start_time: "2026-08-20T10:00:00.000Z",
        new_end_time: "2026-08-20T10:30:00.000Z",
        reason: "conflict",
      },
    });
  });

  it("cancelRisAppointment posts the reason to the cancel path", async () => {
    mockRequest.mockResolvedValue({ data: { id: "a1", status: "CANCELLED" } });
    const appt = await cancelRisAppointment("a1", "no-show");
    expect(mockRequest).toHaveBeenCalledWith("ris/appointments/a1/cancel", {
      data: { reason: "no-show" },
    });
    expect(appt.status).toBe("CANCELLED");
  });

  it("searchRisOrders passes filters and defaults to an empty page", async () => {
    mockRequest.mockResolvedValue({
      data: [{ id: "o1", patient_id: "P1" }],
      total: 1,
      page: 1,
      per_page: 25,
    });
    const page = await searchRisOrders({ search: "Jane", page: 1, per_page: 10 });
    expect(mockRequest).toHaveBeenCalledWith("ris/orders", {
      query: { search: "Jane", page: "1", per_page: "10" },
    });
    expect(page.total).toBe(1);

    mockRequest.mockResolvedValue(undefined);
    expect(await searchRisOrders()).toEqual({
      data: [],
      total: 0,
      page: 1,
      per_page: 25,
    });
  });

  it("dayOfWeekLabel maps 0-6 to weekday names", () => {
    expect(dayOfWeekLabel(0)).toBe("Monday");
    expect(dayOfWeekLabel(6)).toBe("Sunday");
    expect(dayOfWeekLabel(9)).toBe("9");
  });
});
