import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import { renderWithAuth } from "./renderWithApp";
import { describe, it, expect, vi, beforeEach } from "vitest";
import AdminDashboard from "../dashboard/AdminDashboard";

const mockGetDashboardMetrics = vi.hoisted(() => vi.fn());
const mockGetHealth = vi.hoisted(() => vi.fn());
const mockListUsers = vi.hoisted(() => vi.fn());
const mockGetDicomwebMetrics = vi.hoisted(() => vi.fn());
const mockListReplicas = vi.hoisted(() => vi.fn());
const mockListLogs = vi.hoisted(() => vi.fn());

vi.mock("../api/metrics", () => ({
  getDashboardMetrics: mockGetDashboardMetrics,
  getHealth: mockGetHealth,
}));
vi.mock("../api/users", () => ({
  listUsers: mockListUsers,
}));
vi.mock("../api/dicomweb-admin", () => ({
  getDicomwebMetrics: mockGetDicomwebMetrics,
}));
vi.mock("../api/replicas", () => ({
  listReplicas: mockListReplicas,
}));
vi.mock("../api/logs", () => ({
  listLogs: mockListLogs,
  listLogActors: vi.fn(),
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
vi.mock("../hooks", () => ({
  useDocumentTitle: vi.fn(),
  useTenantRefetch: vi.fn(),
}));
vi.mock("../common/QuantumLogo", () => ({
  default: () => <div>Logo</div>,
}));
vi.mock("react-chartjs-2", () => ({
  Bar: () => <div data-testid="mock-bar-chart">Bar Chart</div>,
  Line: () => <div data-testid="mock-line-chart">Line Chart</div>,
}));

function seedAdmin(pacPermissions: string[]) {
  localStorage.setItem("token", "t");
  localStorage.setItem("userId", "u1");
  localStorage.setItem("username", "pacs-admin");
  localStorage.setItem("admin", "false");
  localStorage.setItem("role", "pacs_admin");
  localStorage.setItem("permissions", JSON.stringify(pacPermissions));
}

const health = {
  status: "ok",
  components: {
    database: { status: "ok", latency_ms: 4 },
    storage: { status: "degraded", latency_ms: 210 },
    dicom_listener: { status: "ok", latency_ms: 12 },
  },
};

const metrics = {
  totals: {
    patients: 10,
    studies: 20,
    series: 30,
    files: 40,
    storage_bytes: 1048576,
  },
  modalities: { CT: 15, MR: 10, XA: 8 },
  ingestion_30d: [
    { date: "2026-07-20", count: 5 },
    { date: "2026-07-21", count: 12 },
  ],
};

const replicas = [
  { id: 1, name: "node-a", status: "ok", delay: 0 },
  { id: 2, name: "node-b", status: "synced", delay: 4 },
];

const logs = [
  {
    id: 1,
    created_at: "2026-07-26T10:00:00Z",
    actor: "alice",
    event_type: "user.login",
    description: "Alice signed in",
  },
];

describe("AdminDashboard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGetHealth.mockResolvedValue(health);
    mockGetDashboardMetrics.mockResolvedValue(metrics);
    mockListUsers.mockResolvedValue({ data: [], total: 7 });
    mockGetDicomwebMetrics.mockResolvedValue({
      requests_total: 42,
      requests_failed: 0,
      totals: { studies: 1, series: 2, files: 3 },
    });
    mockListReplicas.mockResolvedValue(replicas);
    mockListLogs.mockResolvedValue({
      data: logs,
      next_cursor: null,
      has_more: false,
      total: 1,
    });
  });

  it("renders the health strip with component statuses", async () => {
    // tenant_admin review P1-1: drill-down "Open … dashboard" buttons are
    // permission-gated — REPLICA_READ unlocks Storage, DICOMWEB_READ the
    // DICOM Listener link.
    seedAdmin(["METRICS_READ", "REPLICA_READ", "DICOMWEB_READ"]);
    renderWithAuth(<AdminDashboard />);

    await waitFor(() => {
      expect(screen.getByText("Database")).toBeInTheDocument();
    });
    expect(
      screen.getByRole("button", { name: "Open Storage dashboard" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Open DICOM Listener dashboard" }),
    ).toBeInTheDocument();
  });

  it("renders KPI cards and charts when METRICS_READ passes", async () => {
    seedAdmin(["METRICS_READ", "USER_READ", "REPLICA_READ"]);
    renderWithAuth(<AdminDashboard />);

    await waitFor(() => {
      expect(screen.getByText("Studies")).toBeInTheDocument();
    });
    expect(screen.getByText("Patients")).toBeInTheDocument();
    expect(screen.getByText("1.0 MB")).toBeInTheDocument();
    expect(screen.getByTestId("mock-line-chart")).toBeInTheDocument();
    expect(screen.getByTestId("mock-bar-chart")).toBeInTheDocument();
  });

  it("shows the user count from the users endpoint", async () => {
    seedAdmin(["METRICS_READ", "USER_READ"]);
    renderWithAuth(<AdminDashboard />);

    await waitFor(() => {
      expect(screen.getByText("7")).toBeInTheDocument();
    });
    expect(mockListUsers).toHaveBeenCalled();
  });

  it("renders replica rows when REPLICA_READ passes", async () => {
    seedAdmin(["REPLICA_READ"]);
    renderWithAuth(<AdminDashboard />);

    await waitFor(() => {
      expect(screen.getByText("node-a")).toBeInTheDocument();
    });
    expect(screen.getByText("node-b")).toBeInTheDocument();
  });

  it("renders recent activity when a log permission passes", async () => {
    seedAdmin(["LOG_READ"]);
    renderWithAuth(<AdminDashboard />);

    await waitFor(() => {
      expect(screen.getByText("alice")).toBeInTheDocument();
    });
    expect(mockListLogs).toHaveBeenCalled();
  });

  it("gates the DICOMweb requests card behind DICOMWEB_READ", async () => {
    seedAdmin(["METRICS_READ"]);
    renderWithAuth(<AdminDashboard />);

    await waitFor(() => {
      expect(screen.getByText("Studies")).toBeInTheDocument();
    });
    expect(screen.queryByText("DICOMweb Requests")).not.toBeInTheDocument();
    expect(mockGetDicomwebMetrics).not.toHaveBeenCalled();
  });

  it("hides the metrics section entirely without METRICS_READ", async () => {
    seedAdmin(["USER_READ"]);
    renderWithAuth(<AdminDashboard />);

    await waitFor(() => {
      expect(screen.getByText("Operations Dashboard")).toBeInTheDocument();
    });
    expect(screen.queryByText("Studies")).not.toBeInTheDocument();
    expect(screen.queryByTestId("mock-bar-chart")).not.toBeInTheDocument();
    expect(mockGetDashboardMetrics).not.toHaveBeenCalled();
  });

  it("shows only permitted quick links", async () => {
    seedAdmin(["USER_READ"]);
    renderWithAuth(<AdminDashboard />);

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /Users/ })).toBeInTheDocument();
    });
    expect(
      screen.queryByRole("button", { name: /Replicas/ }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /Metrics/ }),
    ).not.toBeInTheDocument();
  });
});
