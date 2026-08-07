import React from "react";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { renderWithAuth } from "./renderWithApp";
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
  emit: vi.fn(),
  subscribe: vi.fn(() => undefined),
}));

vi.mock("../common/QuantumLogo", () => ({
  default: () => <div>Logo</div>,
}));

vi.mock("react-chartjs-2", () => ({
  Bar: () => <div data-testid="mock-bar-chart">Bar Chart</div>,
  Line: () => <div data-testid="mock-line-chart">Line Chart</div>,
}));

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

describe("Metrics health drill-down links", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const healthWithAreaRows = {
    status: "ok",
    components: {
      database: { status: "ok", latency_ms: 2 },
      storage: { status: "ok", latency_ms: 3 },
      dicom_listener: { status: "ok", latency_ms: 200 },
      hl7: { status: "degraded", latency_ms: 500 },
      fhir: { status: "ok", latency_ms: 10 },
    },
  };

  it("renders mapped health rows as links with hrefs", async () => {
    mockGetDashboardMetrics.mockResolvedValue(mockData);
    mockGetHealth.mockResolvedValue(healthWithAreaRows);
    renderWithAuth(<Metrics />);

    await waitFor(() => {
      expect(
        screen.getByRole("link", {
          name: "View storage health dashboard",
        }),
      ).toHaveAttribute("href", "/replicas");
    });

    expect(
      screen.getByRole("link", {
        name: "View dicom listener health dashboard",
      }),
    ).toHaveAttribute("href", "/dicomweb");

    const hl7Link = screen.getByRole("link", {
      name: "View hl7 health dashboard",
    });
    expect(hl7Link).toHaveAttribute("href", "/hl7?period=30d");
    expect(hl7Link).toHaveTextContent("HL7");
    expect(hl7Link).toHaveTextContent("DEGRADED");

    const fhirLink = screen.getByRole("link", {
      name: "View fhir health dashboard",
    });
    expect(fhirLink).toHaveAttribute("href", "/fhir/monitoring?period=30d");

    expect(
      screen.queryByRole("link", { name: "View database health dashboard" }),
    ).not.toBeInTheDocument();
  });

  it("maps the current time scope to the period param (24h, 90d clamps to 30d)", async () => {
    mockGetDashboardMetrics.mockResolvedValue(mockData);
    mockGetHealth.mockResolvedValue({
      status: "ok",
      components: { hl7: { status: "ok", latency_ms: 5 } },
    });
    renderWithAuth(<Metrics />);

    await waitFor(() => {
      expect(
        screen.getByRole("link", { name: "View hl7 health dashboard" }),
      ).toHaveAttribute("href", "/hl7?period=30d");
    });

    fireEvent.click(screen.getByText("24h"));
    await waitFor(() => {
      expect(
        screen.getByRole("link", { name: "View hl7 health dashboard" }),
      ).toHaveAttribute("href", "/hl7?period=24h");
    });

    fireEvent.click(screen.getByText("90d"));
    await waitFor(() => {
      expect(
        screen.getByRole("link", { name: "View hl7 health dashboard" }),
      ).toHaveAttribute("href", "/hl7?period=30d");
    });
  });
});

describe("Metrics per-panel isolation", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows metrics unavailable + retry in the health card when health fails, totals still render", async () => {
    mockGetDashboardMetrics.mockResolvedValue(mockData);
    mockGetHealth.mockRejectedValue(new Error("health endpoint down"));
    renderWithAuth(<Metrics />);

    await waitFor(() => {
      expect(screen.getByText("Metrics unavailable")).toBeInTheDocument();
    });

    expect(screen.getByText("Patients")).toBeInTheDocument();
    expect(screen.getByText("Studies")).toBeInTheDocument();
    expect(screen.getByText("System Health")).toBeInTheDocument();

    mockGetHealth.mockResolvedValueOnce({
      status: "ok",
      components: { storage: { status: "ok", latency_ms: 3 } },
    });
    fireEvent.click(screen.getByRole("button", { name: /retry/i }));
    await waitFor(() => {
      expect(
        screen.getByRole("link", { name: "View storage health dashboard" }),
      ).toBeInTheDocument();
    });
  });

  it("shows the page error state while the health card still renders when metrics fails", async () => {
    mockGetDashboardMetrics.mockRejectedValue(new Error("metrics down"));
    mockGetHealth.mockResolvedValue({
      status: "ok",
      components: { database: { status: "ok", latency_ms: 2 } },
    });
    renderWithAuth(<Metrics />);

    await waitFor(() => {
      expect(screen.getByText("metrics down")).toBeInTheDocument();
    });

    expect(screen.getByText("System Health")).toBeInTheDocument();
    expect(screen.getByText("Database")).toBeInTheDocument();
  });

  it("shows the active tenant tag in the header when scoped", async () => {
    mockGetDashboardMetrics.mockResolvedValue(mockData);
    mockGetHealth.mockResolvedValue(null);
    localStorage.setItem("tenant_id", "main");
    localStorage.setItem("tenant_name", "Main Hospital");
    renderWithAuth(<Metrics />);

    await waitFor(() => {
      expect(screen.getByText("Tenant: Main Hospital")).toBeInTheDocument();
    });
  });

  it("omits the tenant tag when no tenant is active", async () => {
    mockGetDashboardMetrics.mockResolvedValue(mockData);
    mockGetHealth.mockResolvedValue(null);
    renderWithAuth(<Metrics />);

    await waitFor(() => {
      expect(screen.getByText("Patients")).toBeInTheDocument();
    });
    expect(screen.queryByText(/Tenant:/)).not.toBeInTheDocument();
  });
});
