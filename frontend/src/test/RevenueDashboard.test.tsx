import React from "react";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { App as AntdApp } from "antd";
import { AuthProvider } from "../auth/AuthContext";
import { ThemeProvider } from "../common/ThemeProvider";
import RevenueDashboard from "../billing/RevenueDashboard";

const mockRequest = vi.hoisted(() => vi.fn());

vi.mock("../helpers", () => ({
  request: mockRequest,
  isAdmin: () => false,
  setTokens: () => {},
  clearTokens: () => {},
  startRefreshTimer: () => {},
  stopRefreshTimer: () => {},
}));

vi.mock("../hooks", () => ({
  useDocumentTitle: vi.fn(),
  useTenantRefetch: vi.fn(),
}));

vi.mock("../common/base", () => ({
  default: (Component: React.ComponentType) =>
    function MockedBase() {
      return <Component />;
    },
}));

const revenuePayload = {
  data: {
    days: 30,
    daily: [
      { day: "2026-08-23T00:00:00+00:00", collected: 250 },
      { day: "2026-08-24T00:00:00+00:00", collected: 500 },
    ],
    by_payer: [{ payer_name: "Medicare", paid: 300 }],
    by_modality: [{ modality: "CT", billed: 430 }],
    ar_aging: { current: 100, over5: 200, over10: 50 },
  },
};

function renderPage() {
  return render(
    <AntdApp>
      <ThemeProvider>
        <AuthProvider>
          <MemoryRouter>
            <RevenueDashboard />
          </MemoryRouter>
        </AuthProvider>
      </ThemeProvider>
    </AntdApp>,
  );
}

describe("RevenueDashboard", () => {
  beforeEach(() => {
    localStorage.clear();
    localStorage.setItem("token", "t");
    localStorage.setItem("userId", "u1");
    localStorage.setItem("admin", "false");
    localStorage.setItem(
      "permissions",
      JSON.stringify(["BILLING_READ"]),
    );
    mockRequest.mockReset();
    mockRequest.mockResolvedValue(revenuePayload);
  });

  it("renders collections trend and AR aging (B-07)", async () => {
    renderPage();

    await waitFor(() => {
      expect(screen.getByText("$750.00")).toBeInTheDocument(); // 250 + 500
      expect(screen.getByText("$200.00")).toBeInTheDocument(); // AR > 5d
      expect(screen.getByText("Medicare")).toBeInTheDocument();
      expect(screen.getByText("CT")).toBeInTheDocument();
    });
  });

  it("requests the default 30-day window", async () => {
    renderPage();
    await waitFor(() => {
      expect(mockRequest).toHaveBeenCalledWith("ris/billing/revenue?days=30");
    });
  });
});
