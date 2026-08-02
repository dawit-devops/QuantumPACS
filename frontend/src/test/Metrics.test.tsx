import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { MemoryRouter } from "react-router";
import { AuthProvider } from "../auth/AuthContext";
import { ThemeProvider } from "../common/ThemeProvider";
import Metrics from "../metrics/Metrics";

const mockGetDashboardMetrics = vi.hoisted(() => vi.fn());
const mockGetHealth = vi.hoisted(() => vi.fn());
vi.mock("../api/metrics", () => ({
  getDashboardMetrics: mockGetDashboardMetrics,
  getHealth: mockGetHealth,
}));
vi.mock("../helpers", () => ({
  request: vi.fn(() => Promise.resolve({})),
  isAdmin: () => false,
  setTokens: () => {},
  clearTokens: () => {},
  startRefreshTimer: () => {},
  stopRefreshTimer: () => {},
}));

vi.mock("../common/QuantumLogo", () => ({
  default: () => <div>Logo</div>,
}));

vi.mock("react-chartjs-2", () => ({
  Bar: () => <div data-testid="mock-bar-chart">Bar Chart</div>,
  Line: () => <div data-testid="mock-line-chart">Line Chart</div>,
}));

function renderWithAuth(ui: React.ReactElement) {
  return render(
    <ThemeProvider>
      <AuthProvider>
        <MemoryRouter>{ui}</MemoryRouter>
      </AuthProvider>
    </ThemeProvider>,
  );
}

const mockData = {
  totals: {
    patients: 10,
    studies: 20,
    series: 30,
    files: 40,
    users: 5,
    storage_bytes: 1000000,
  },
  modalities: { CT: 15, MR: 10, XA: 8 },
  ingestion_30d: [
    { date: "2026-07-20", count: 5 },
    { date: "2026-07-21", count: 12 },
    { date: "2026-07-22", count: 8 },
  ],
  latest_files: [{ id: 1, name: "test.dcm", created: "2026-07-26" }],
};

describe("Metrics", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders spinner while loading", () => {
    mockGetDashboardMetrics.mockReturnValue(new Promise(() => {}));
    mockGetHealth.mockResolvedValue(null);
    renderWithAuth(<Metrics />);

    const spinner = document.querySelector(".ant-spin-spinning");
    expect(spinner).toBeTruthy();
  });

  it("renders stat cards after data loads", async () => {
    mockGetDashboardMetrics.mockResolvedValue(mockData);
    mockGetHealth.mockResolvedValue(null);
    renderWithAuth(<Metrics />);

    await waitFor(() => {
      expect(screen.getByText("Patients")).toBeInTheDocument();
    });

    expect(screen.getByText("Studies")).toBeInTheDocument();
    expect(screen.getByText("Series")).toBeInTheDocument();
    expect(screen.getByText("Users")).toBeInTheDocument();
    expect(screen.getByText("Storage")).toBeInTheDocument();
  });

  it("renders modality distribution chart", async () => {
    mockGetDashboardMetrics.mockResolvedValue(mockData);
    mockGetHealth.mockResolvedValue(null);
    renderWithAuth(<Metrics />);

    await waitFor(() => {
      expect(screen.getByText("Modality Distribution")).toBeInTheDocument();
    });

    expect(
      screen.getAllByTestId("mock-bar-chart").length,
    ).toBeGreaterThanOrEqual(1);
  });

  it("renders ingestion chart", async () => {
    mockGetDashboardMetrics.mockResolvedValue(mockData);
    mockGetHealth.mockResolvedValue(null);
    renderWithAuth(<Metrics />);

    await waitFor(() => {
      expect(screen.getByText("Ingestion (30 days)")).toBeInTheDocument();
    });

    const lineCharts = screen.getAllByTestId("mock-line-chart");
    const barCharts = screen.getAllByTestId("mock-bar-chart");
    expect(lineCharts.length + barCharts.length).toBeGreaterThanOrEqual(1);
  });

  it("renders system health pills", async () => {
    mockGetDashboardMetrics.mockResolvedValue(mockData);
    mockGetHealth.mockResolvedValue({
      status: "ok",
      components: {
        database: { status: "ok", latency_ms: 2 },
        elasticsearch: { status: "ok", latency_ms: 5 },
        redis: { status: "ok", latency_ms: 1 },
        storage: { status: "ok", latency_ms: 3 },
        dicom_listener: { status: "degraded", latency_ms: 200 },
        ingestion_service: { status: "ok", latency_ms: 10 },
      },
    });
    renderWithAuth(<Metrics />);

    await waitFor(() => {
      expect(screen.getByText("System Health")).toBeInTheDocument();
    });

    expect(screen.getByText("Database")).toBeInTheDocument();
    expect(screen.getByText("DICOM Listener")).toBeInTheDocument();
    expect(screen.getByText("DEGRADED")).toBeInTheDocument();
  });

  it("renders component latency chart", async () => {
    mockGetDashboardMetrics.mockResolvedValue(mockData);
    mockGetHealth.mockResolvedValue({
      status: "ok",
      components: {
        database: { status: "ok", latency_ms: 2 },
        elasticsearch: { status: "degraded", latency_ms: 500 },
      },
    });
    renderWithAuth(<Metrics />);

    await waitFor(() => {
      expect(screen.getByText("Component Latency")).toBeInTheDocument();
    });

    const barCharts = screen.getAllByTestId("mock-bar-chart");
    expect(barCharts.length).toBeGreaterThanOrEqual(1);
  });
});
