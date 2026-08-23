import { render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import React from "react";
import { MemoryRouter } from "react-router";
import { App } from "antd";
import { AuthProvider } from "../auth/AuthContext";
import { ThemeProvider } from "../common/ThemeProvider";
import RISDashboard from "../admin/RISDashboard";

vi.mock("../api/dashboard-ris", () => ({
  getRisDashboardKpi: vi.fn(),
}));

vi.mock("../hooks", () => ({
  useDocumentTitle: vi.fn(),
  useTenantRefetch: vi.fn(),
}));

vi.mock("../auth/AuthContext", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../auth/AuthContext")>();
  return {
    ...actual,
    useAuth: () => ({
      hasPermission: (perm: string) =>
        ["REPORT_READ", "BILLING_READ"].includes(perm),
    }),
  };
});

import { getRisDashboardKpi } from "../api/dashboard-ris";
const mockGetRisDashboardKpi = vi.mocked(getRisDashboardKpi);

const mockKpi = {
  tat_by_priority: [
    { priority: "stat", p95_seconds: 600 },
    { priority: "routine", p95_seconds: 3600 },
  ],
  prior_auth: {
    mix: [
      { status: "APPROVED", n: 21 },
      { status: "PENDING", n: 3 },
      { status: "DENIED", n: 1 },
      { status: "EXPIRED", n: 1 },
    ],
    approval_rate: 0.955,
  },
  utilization: 0.65,
  unbilled_aging: { total_unbilled: 3 },
  volume: 42,
  drill_down: [],
};

function renderDash() {
  localStorage.setItem("userId", "1");
  localStorage.setItem("username", "test");
  localStorage.setItem(
    "permissions",
    JSON.stringify(["REPORT_READ", "BILLING_READ"]),
  );
  localStorage.setItem("tenant_id", "t1");
  localStorage.setItem("tenant_name", "Test");
  return render(
    <MemoryRouter>
      <App>
        <AuthProvider>
          <ThemeProvider>
            <RISDashboard />
          </ThemeProvider>
        </AuthProvider>
      </App>
    </MemoryRouter>,
  );
}

describe("RISDashboard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGetRisDashboardKpi.mockResolvedValue(mockKpi);
  });

  it("renders summary KPI statistics", async () => {
    renderDash();
    await waitFor(() => {
      expect(screen.getByText("Today's Volume")).toBeInTheDocument();
    });
    expect(screen.getByText("42")).toBeInTheDocument();
    expect(screen.getByText("Unbilled")).toBeInTheDocument();
  });

  it("renders prior-auth status mix (R2-01-09)", async () => {
    renderDash();
    await waitFor(() => {
      expect(screen.getByText("Prior-Auth Approval")).toBeInTheDocument();
    });
    // Data flow proof: mix card renders only when the payload carried
    // prior_auth (the backend suite asserts the rate itself).
    await waitFor(() => {
      expect(screen.getByText("Prior-Auth APPROVED")).toBeInTheDocument();
    });
    expect(screen.getByText("Prior-Auth PENDING")).toBeInTheDocument();
    expect(screen.getByText("Prior-Auth EXPIRED")).toBeInTheDocument();
  });

  it("renders TAT by priority table", async () => {
    renderDash();
    await waitFor(() => {
      expect(screen.getByText("stat")).toBeInTheDocument();
    });
    expect(screen.getByText("routine")).toBeInTheDocument();
    expect(screen.getAllByText("10.0m").length).toBeGreaterThanOrEqual(1); // 600s -> 10m
  });

  it("formats long TATs in hours", async () => {
    mockGetRisDashboardKpi.mockResolvedValue({
      ...mockKpi,
      tat_by_priority: [{ priority: "routine", p95_seconds: 7200 }],
    });
    renderDash();
    await waitFor(() => {
      expect(screen.getByText("2.0h")).toBeInTheDocument();
    });
  });

  it("passes WCAG 2.1 AA automated scan (F3)", async () => {
    renderDash();
    await waitFor(() => {
      expect(screen.getByText("Today's Volume")).toBeInTheDocument();
    });
    const { scanA11y, seriousViolations } = await import("./axe");
    const results = await scanA11y(document.body);
    expect(seriousViolations(results)).toEqual([]);
  });
});