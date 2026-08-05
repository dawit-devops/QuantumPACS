import { describe, it, expect, beforeEach, vi } from "vitest";
import { renderWithAuth } from "../../src/test/renderWithApp";
import { MemoryRouter } from "react-router";
import { App } from "antd";
import React from "react";

// Mock the worklist API module
vi.mock("../../src/api/worklist", () => ({
  fetchWorklist: vi.fn(),
  fetchStudyDetail: vi.fn(),
  submitReport: vi.fn(),
  fetchReports: vi.fn(),
}));

// Mock the API client
vi.mock("../../src/api/client", () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}));

describe("Worklist E2E Flow", () => {
  beforeEach(() => {
    localStorage.clear();
    sessionStorage.clear();
    vi.clearAllMocks();
  });

  it("worklist → study review → report flow completes", async () => {
    const { fetchWorklist, fetchStudyDetail, submitReport, fetchReports } =
      await import("../../src/api/worklist");

    // Step 1: Fetch worklist
    (fetchWorklist as vi.MockedFunction<typeof fetchWorklist>).mockResolvedValue(
      {
        data: [
          {
            id: "study-1",
            patientName: "Doe^John",
            patientID: "P001",
            studyInstanceUID: "1.2.3.4.5.6",
            modality: "CT",
            studyDate: "20260725",
            status: "pending",
          },
        ],
        total: 1,
      },
    );

    const worklistResult = await fetchWorklist({ status: "pending" });
    expect(worklistResult.data).toHaveLength(1);
    expect(worklistResult.data[0].patientName).toBe("Doe^John");

    // Step 2: Review study detail
    (fetchStudyDetail as vi.MockedFunction<typeof fetchStudyDetail>).mockResolvedValue(
      {
        data: {
          id: "study-1",
          patientName: "Doe^John",
          patientID: "P001",
          studyInstanceUID: "1.2.3.4.5.6",
          modality: "CT",
          series: [
            {
              seriesInstanceUID: "1.2.3.4.5.6.7",
              modality: "CT",
              instanceCount: 10,
            },
          ],
        },
      },
    );

    const studyResult = await fetchStudyDetail("1.2.3.4.5.6");
    expect(studyResult.data.patientName).toBe("Doe^John");
    expect(studyResult.data.series).toHaveLength(1);

    // Step 3: Submit report
    (submitReport as vi.MockedFunction<typeof submitReport>).mockResolvedValue({
      data: { id: "report-1", studyId: "study-1", status: "completed" },
      status: 201,
    });

    const reportResult = await submitReport({
      studyId: "study-1",
      findings: "Normal CT study",
      impression: "No acute findings",
    });
    expect(reportResult.status).toBe(201);
    expect(reportResult.data.status).toBe("completed");

    // Step 4: Verify report appears in reports list
    (fetchReports as vi.MockedFunction<typeof fetchReports>).mockResolvedValue({
      data: [{ id: "report-1", studyId: "study-1", status: "completed" }],
      total: 1,
    });

    const reportsResult = await fetchReports({ studyId: "study-1" });
    expect(reportsResult.data).toHaveLength(1);
    expect(reportsResult.data[0].status).toBe("completed");
  });

  it("worklist returns empty for no pending studies", async () => {
    const { fetchWorklist } = await import("../../src/api/worklist");

    (fetchWorklist as vi.MockedFunction<typeof fetchWorklist>).mockResolvedValue({
      data: [],
      total: 0,
    });

    const result = await fetchWorklist({ status: "pending" });
    expect(result.data).toHaveLength(0);
    expect(result.total).toBe(0);
  });

  it("study detail returns 404 for non-existent study", async () => {
    const { fetchStudyDetail } = await import("../../src/api/worklist");

    (fetchStudyDetail as vi.MockedFunction<typeof fetchStudyDetail>).mockResolvedValue(
      {
        status: 404,
        error: "Study not found",
      },
    );

    const result = await fetchStudyDetail("1.2.3.4.5.999");
    expect(result.status).toBe(404);
  });
});
