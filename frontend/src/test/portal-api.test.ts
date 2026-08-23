import { describe, it, expect, vi, beforeEach } from "vitest";
import { request } from "../api/client";
import {
  listScope,
  getPortalPatient,
  getPortalOrders,
  getPortalReport,
  getPortalAppointments,
  listFollowUps,
  createFollowUp,
  updateFollowUp,
  updateConsent,
} from "../api/portal";

// R4-04: portal.ts is fully mocked in Portal.test.tsx; the request contract
// (paths + data unwrapping, including the scope-absence null convention) is
// pinned here against the real client module.

vi.mock("../api/client", () => ({
  request: vi.fn(),
}));

const mockRequest = vi.mocked(request);

describe("portal api client", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("listScope GETs portal/scope and unwraps res.data", async () => {
    mockRequest.mockResolvedValue({
      data: [{ id: "s1", patient_id: "P001", scope_type: "assigned" }],
    });
    const scope = await listScope();
    expect(mockRequest).toHaveBeenCalledWith("portal/scope");
    expect(scope).toEqual([
      { id: "s1", patient_id: "P001", scope_type: "assigned" },
    ]);
  });

  it("listScope falls back to an empty list when data is absent", async () => {
    mockRequest.mockResolvedValue({});
    expect(await listScope()).toEqual([]);
  });

  it("getPortalPatient resolves the bundle through res.data", async () => {
    mockRequest.mockResolvedValue({
      data: { patient: { id: 1 }, orders: [], reports: [] },
    });
    const bundle = await getPortalPatient("P001");
    expect(mockRequest).toHaveBeenCalledWith("portal/patients/P001");
    expect(bundle?.patient).toEqual({ id: 1 });
  });

  it("getPortalPatient returns null for an out-of-scope patient (data: null)", async () => {
    mockRequest.mockResolvedValue({ data: null });
    expect(await getPortalPatient("P999")).toBeNull();
  });

  it("getPortalOrders unwraps", async () => {
    mockRequest.mockResolvedValue({ data: [{ id: "o1" }] });
    expect(await getPortalOrders("P001")).toEqual([{ id: "o1" }]);
  });

  it("getPortalReport hits the report path and unwraps", async () => {
    mockRequest.mockResolvedValue({ data: { id: "r1", status: "signed" } });
    const report = await getPortalReport("P001", "r1");
    expect(mockRequest).toHaveBeenCalledWith("portal/patients/P001/reports/r1");
    expect(report?.status).toBe("signed");
  });

  it("listFollowUps passes the query and unwraps", async () => {
    mockRequest.mockResolvedValue({ data: [{ id: "f1" }] });
    const rows = await listFollowUps({ status: "open" });
    expect(mockRequest).toHaveBeenCalledWith("portal/follow-ups", {
      query: { status: "open" },
    });
    expect(rows).toEqual([{ id: "f1" }]);
  });

  it("createFollowUp posts and unwraps the new id", async () => {
    mockRequest.mockResolvedValue({ data: { id: "f2" } });
    const result = await createFollowUp({ reason: "follow-up" });
    expect(mockRequest).toHaveBeenCalledWith("portal/follow-ups", {
      data: { reason: "follow-up" },
    });
    expect(result).toEqual({ id: "f2" });
  });

  it("updateFollowUp PUTs the status change", async () => {
    mockRequest.mockResolvedValue({});
    await updateFollowUp("f1", { status: "cancelled" });
    expect(mockRequest).toHaveBeenCalledWith("portal/follow-ups/f1", {
      method: "PUT",
      data: { status: "cancelled" },
    });
  });

  it("updateConsent PUTs consent_results", async () => {
    mockRequest.mockResolvedValue({
      data: { patient_id: "P001", consent_results: false },
    });
    const result = await updateConsent("P001", false);
    expect(mockRequest).toHaveBeenCalledWith("portal/patients/P001/consent", {
      method: "PUT",
      data: { consent_results: false },
    });
    expect(result).toEqual({ patient_id: "P001", consent_results: false });
  });

  it("getPortalAppointments hits the appointments path and unwraps", async () => {
    mockRequest.mockResolvedValue({
      data: [
        {
          id: "a1",
          status: "SCHEDULED",
          modality: "CT",
          room: "CT-1",
          prep_instructions: "Fast 4 hours",
          procedure: "CT Chest",
          priority: "ROUTINE",
          start_time: "2026-08-28T10:30:00+00:00",
        },
      ],
    });
    const rows = await getPortalAppointments("P001");
    const call = mockRequest.mock.calls[0];
    expect(call[0]).toBe("portal/patients/P001/appointments");
    expect(rows).toHaveLength(1);
    expect(rows[0].room).toBe("CT-1");
    expect(rows[0].prep_instructions).toBe("Fast 4 hours");
  });
});
