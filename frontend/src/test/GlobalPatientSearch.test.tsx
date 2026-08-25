import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { App as AntdApp } from "antd";
import { AuthProvider } from "../auth/AuthContext";
import { ThemeProvider } from "../common/ThemeProvider";

// CC-13: the patient quick-search overlay must be mounted beyond front
// desk — on the coordination and billing workspaces too. We mount a real
// withSidebar-wrapped page per route and assert the overlay trigger exists
// (sidebar item) plus that dispatching the open event reveals the dialog.

const mockSearch = vi.hoisted(() => vi.fn());

vi.mock("../helpers", () => ({
  request: mockSearch,
  isAdmin: () => false,
  setTokens: () => {},
  clearTokens: () => {},
  startRefreshTimer: () => {},
  stopRefreshTimer: () => {},
}));

vi.mock("../hooks", () => ({
  useDocumentTitle: vi.fn(),
  useTenantRefetch: vi.fn(),
  useFetch: () => ({ exec: vi.fn() }),
}));

// Real Sidebar (that's what we're testing: the section item + overlay mount)
// but silence its noisy children.
vi.mock("../notifications/NotificationBell", () => ({
  default: () => <div data-testid="bell-stub" />,
}));

import { searchRisPatients } from "../api/frontdesk";
import withSidebar from "../common/base";
import Sidebar from "../common/Sidebar";

const mockSearchPatients = vi.mocked(searchRisPatients);

function renderAt(path: string, children: React.ReactNode) {
  // The wrapped page must be a stable element (hooks bind to the tree).
  const Wrapped = withSidebar(() => <>{children}</>);
  return render(
    <AntdApp>
      <ThemeProvider>
        <AuthProvider>
          <MemoryRouter initialEntries={[path]}>
            <Wrapped />
          </MemoryRouter>
        </AuthProvider>
      </ThemeProvider>
    </AntdApp>,
  );
}

describe("global patient search mount (CC-13)", () => {
  beforeEach(() => {
    localStorage.clear();
    localStorage.setItem("token", "t");
    localStorage.setItem("userId", "u1");
    localStorage.setItem("admin", "false");
    localStorage.setItem(
      "permissions",
      JSON.stringify(["PATIENT_READ", "ORDER_READ", "BILLING_READ", "WORKLIST_READ"]),
    );
    mockSearch.mockReset();
    mockSearch.mockResolvedValue({ data: [] });
  });

  const openOverlay = async () => {
    window.dispatchEvent(new Event("fd.patient-search.open"));
    // Specific to the overlay (pages carry their own /search/i inputs).
    await waitFor(() => {
      expect(
        screen.getByPlaceholderText("Search patients by name or MRN"),
      ).toBeInTheDocument();
    });
  };

  it("mounts on coordination routes", async () => {
    renderAt("/orders", <div>page</div>);
    await openOverlay();
  });

  it("mounts on billing routes", async () => {
    renderAt("/billing/queue", <div>page</div>);
    await openOverlay();
  });

  it("still mounts on front desk routes", async () => {
    renderAt("/frontdesk/registration", <div>page</div>);
    await openOverlay();
  });

  it("does NOT mount on unrelated routes", async () => {
    renderAt("/exams", <div>page</div>);
    window.dispatchEvent(new Event("fd.patient-search.open"));
    // Give any accidental listener a tick.
    await new Promise((r) => setTimeout(r, 50));
    expect(
      screen.queryByPlaceholderText("Search patients by name or MRN"),
    ).toBeNull();
  });

  it("shows a Coordination sidebar Patient Search item", async () => {
    render(
      <AntdApp>
        <ThemeProvider>
          <AuthProvider>
            <MemoryRouter initialEntries={["/orders"]}>
              <Sidebar />
            </MemoryRouter>
          </AuthProvider>
        </ThemeProvider>
      </AntdApp>,
    );
    await waitFor(() => {
      const items = screen.getAllByText("Patient Search");
      expect(items.length).toBeGreaterThan(0);
    });
  });
});
