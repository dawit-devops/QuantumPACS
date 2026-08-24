import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { AuthProvider } from "../auth/AuthContext";
import { ThemeProvider } from "../common/ThemeProvider";
import ResidentProgress from "../radiologist/ResidentProgress";

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
  useFetch: () => ({ exec: vi.fn() }),
}));

// withSidebar is bypassed in tests (the real Sidebar mounts NotificationBell
// whose WebSocket hangs under a user session) — identity wrapper instead.
vi.mock("../common/base", () => ({
  default: (Component: React.ComponentType) =>
    function MockedBase() {
      return <Component />;
    },
}));

function renderProgress() {
  return render(
    <ThemeProvider>
      <AuthProvider>
        <MemoryRouter initialEntries={["/reading/progress"]}>
          <ResidentProgress />
        </MemoryRouter>
      </AuthProvider>
    </ThemeProvider>,
  );
}

describe("ResidentProgress", () => {
  beforeEach(() => {
    localStorage.clear();
    localStorage.setItem("token", "t");
    localStorage.setItem("userId", "u1");
    localStorage.setItem("admin", "false");
    localStorage.setItem("role", "resident");
    localStorage.setItem(
      "permissions",
      JSON.stringify(["REPORT_READ", "REPORT_WRITE"]),
    );
    mockRequest.mockReset();
  });

  it("renders personal progress metrics (RES-04)", async () => {
    mockRequest.mockImplementation((url: string) => {
      if (url === "reports/reading-stats?days=14") {
        return Promise.resolve({
          data: {
            signed_today: 4,
            avg_tat_seconds: { stat: 2400 },
            stat_compliance_pct: 90,
            feedback_received: 2,
            trend: [
              { date: "2026-08-23", count: 3, avg_tat_seconds: 2100 },
            ],
          },
        });
      }
      return Promise.resolve({ data: [] });
    });
    renderProgress();

    await waitFor(() => {
      expect(screen.getByText("4")).toBeInTheDocument();
      expect(screen.getByText("40")).toBeInTheDocument(); // 2400s → 40 min
      expect(screen.getByText("90")).toBeInTheDocument();
      expect(screen.getByText("2026-08-23")).toBeInTheDocument();
    });
  });
});
