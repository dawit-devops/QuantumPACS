import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import { renderWithApp } from "./renderWithApp";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { AuthProvider } from "../auth/AuthContext";
import { ThemeProvider } from "../common/ThemeProvider";
import FhirMonitoring from "../fhir/FhirMonitoring";

const mockGetFhirMetrics = vi.hoisted(() => vi.fn());
const mockGetFhirRecentRequests = vi.hoisted(() => vi.fn());
const mockOpen = vi.hoisted(() => vi.fn(() => Promise.resolve()));

vi.mock("../api/fhir", () => ({
  getFhirMetrics: mockGetFhirMetrics,
  getFhirRecentRequests: mockGetFhirRecentRequests,
}));

vi.mock("../helpers", () => ({
  request: vi.fn(() => Promise.resolve({})),
  open: mockOpen,
  isAdmin: () => true,
}));

vi.mock("../hooks", () => ({
  useDocumentTitle: vi.fn(),
  useFetch: () => ({ exec: vi.fn() }),
}));

const mockMetrics = {
  total_requests: 150,
  error_rate: 3.2,
  latency: { p50: 45, p99: 890 },
  volume: [
    { resource_type: "Patient", method: "GET", count: 80 },
    { resource_type: "ImagingStudy", method: "GET", count: 70 },
  ],
  status_codes: [
    { status_family: 200, count: 130 },
    { status_family: 404, count: 15 },
    { status_family: 500, count: 5 },
  ],
};
const mockRequests = [
  {
    id: 1,
    created_at: "2026-07-01T12:00:00Z",
    method: "GET",
    path: "/Patient/123",
    status_code: 200,
    duration_ms: 42,
    resource_type: "Patient",
    caller: "admin",
  },
  {
    id: 2,
    created_at: "2026-07-01T12:01:00Z",
    method: "GET",
    path: "/ImagingStudy/456",
    status_code: 404,
    duration_ms: 15,
    resource_type: "ImagingStudy",
    caller: "system",
  },
];

async function waitForReady() {
  await screen.findByText("FHIR Monitoring");
}

describe("FhirMonitoring", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGetFhirMetrics.mockImplementation(() => Promise.resolve(mockMetrics));
    mockGetFhirRecentRequests.mockImplementation(() =>
      Promise.resolve({ requests: mockRequests, total: 2 }),
    );
    localStorage.setItem("token", "t");
    localStorage.setItem("userId", "u1");
    localStorage.setItem("admin", "true");
  });

  function renderWithAuth(ui: React.ReactElement) {
    return renderWithApp(
      <ThemeProvider>
        <AuthProvider>
          <MemoryRouter>{ui}</MemoryRouter>
        </AuthProvider>
      </ThemeProvider>,
    );
  }

  it("fetches metrics and requests on mount", async () => {
    renderWithAuth(<FhirMonitoring />);
    await waitForReady();
    expect(mockGetFhirMetrics).toHaveBeenCalledWith("24h");
    expect(mockGetFhirRecentRequests).toHaveBeenCalledWith(
      expect.objectContaining({ limit: 50, offset: 0 }),
    );
  });

  it("renders statistic cards", async () => {
    renderWithAuth(<FhirMonitoring />);
    await waitForReady();
    expect(screen.getByText("Total Requests")).toBeInTheDocument();
    expect(screen.getByText("Error Rate")).toBeInTheDocument();
    expect(screen.getByText("p50 Latency")).toBeInTheDocument();
    expect(screen.getByText("p99 Latency")).toBeInTheDocument();
  });

  it("renders volume table", async () => {
    renderWithAuth(<FhirMonitoring />);
    await waitForReady();
    expect(screen.getAllByText("Patient").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("ImagingStudy").length).toBeGreaterThanOrEqual(
      1,
    );
  });

  it("renders status codes table", async () => {
    renderWithAuth(<FhirMonitoring />);
    await waitForReady();
    expect(screen.getByText("200xx")).toBeInTheDocument();
    expect(screen.getByText("404xx")).toBeInTheDocument();
    expect(screen.getByText("500xx")).toBeInTheDocument();
  });

  it("renders recent requests table", async () => {
    renderWithAuth(<FhirMonitoring />);
    await waitForReady();
    expect(screen.getByText("/Patient/123")).toBeInTheDocument();
    expect(screen.getByText("/ImagingStudy/456")).toBeInTheDocument();
  });

  it("renders refresh and export buttons", async () => {
    renderWithAuth(<FhirMonitoring />);
    await waitForReady();
    expect(screen.getByText("Refresh")).toBeInTheDocument();
    expect(screen.getByText("Export CSV")).toBeInTheDocument();
  });

  it("renders period selector", async () => {
    renderWithAuth(<FhirMonitoring />);
    await waitForReady();
    expect(screen.getByText("Last 24 Hours")).toBeInTheDocument();
  });
});
