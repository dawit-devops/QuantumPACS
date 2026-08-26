import React from "react";
import { screen } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import QAAnalyticsDashboard from "../qa/QAAnalyticsDashboard";
import { renderWithAuth } from "./renderWithApp";

const mockReject = vi.hoisted(() => vi.fn());

vi.mock("../api/qa-analytics", () => ({
  getRejectAnalysis: mockReject,
  getDoseTracking: vi.fn().mockResolvedValue({ by_modality: [], exceedances: [] }),
  getTechMetrics: vi.fn().mockResolvedValue([]),
  getProtocolCompliance: vi.fn().mockResolvedValue([]),
  getTrends: vi.fn().mockResolvedValue([]),
}));

vi.mock("../hooks", () => ({
  useDocumentTitle: vi.fn(),
  useTenantRefetch: () => {},
}));

beforeEach(() => {
  vi.clearAllMocks();
  localStorage.clear();
  localStorage.setItem("token", "t");
  localStorage.setItem("userId", "u1");
  localStorage.setItem("admin", "false");
  localStorage.setItem("role", "dept_manager");
  localStorage.setItem("permissions", JSON.stringify(["QA_READ"]));
});

describe("QAAnalyticsDashboard reject analysis (QA-02)", () => {
  it("renders the by-protocol breakdown the backend already returns", async () => {
    mockReject.mockResolvedValue({
      by_modality: [{ modality: "CT", total: 10, fails: 2, reject_rate: 20 }],
      by_technologist: [{ tech: "u7", total: 8, fails: 1, reject_rate: 12.5 }],
      // The dimension the UI never rendered (QA-02 gap).
      by_protocol: [
        {
          protocol_name: "CT Chest w/ contrast",
          modality: "CT",
          total: 6,
          fails: 2,
          reject_rate: 33.3,
        },
        { protocol_name: "CXR 1 View", modality: "DX", total: 4, fails: 0, reject_rate: 0 },
      ],
      by_discrepancy: [{ discrepancy_level: "none", n: 4 }],
    });

    renderWithAuth(<QAAnalyticsDashboard />);

    expect(await screen.findByText("Reject Rate by Protocol")).toBeInTheDocument();
    expect(await screen.findByText("CT Chest w/ contrast")).toBeInTheDocument();
    expect(screen.getByText("CXR 1 View")).toBeInTheDocument();
    // Rate coloring contract holds on the new table too.
    expect(screen.getByText("33.3%")).toBeInTheDocument();
    expect(screen.getByText("0%")).toBeInTheDocument();
  });
});
