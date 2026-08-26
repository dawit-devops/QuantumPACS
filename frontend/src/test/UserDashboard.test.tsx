import React from "react";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";
import UserDashboard from "../dashboard/UserDashboard";
import { renderWithAuth } from "./renderWithApp";

const mockGetPrefs = vi.hoisted(() => vi.fn());
const mockUpdatePrefs = vi.hoisted(() => vi.fn());

vi.mock("../api/preferences", () => ({
  getPreferences: mockGetPrefs,
  updatePreferences: mockUpdatePrefs,
}));

// Widgets self-fetch via the shared client; hand back deterministic totals.
vi.mock("../api/client", () => ({
  request: vi.fn().mockResolvedValue({
    totals: { patients: 3, studies: 4, files: 5, users: 6, storage_bytes: 1024 },
  }),
}));

function setSession(perms: string[]) {
  localStorage.clear();
  localStorage.setItem("token", "t");
  localStorage.setItem("userId", "u2");
  localStorage.setItem("admin", "false");
  localStorage.setItem("role", "care_coordinator");
  localStorage.setItem("permissions", JSON.stringify(perms));
}

beforeEach(() => {
  vi.clearAllMocks();
  setSession(["METRICS_READ"]);
  mockGetPrefs.mockResolvedValue({});
  mockUpdatePrefs.mockResolvedValue({});
});

describe("UserDashboard (§3 configurable widgets)", () => {
  it("renders the default registered widget for a permitted user", async () => {
    renderWithAuth(<UserDashboard />);
    expect(await screen.findByText("Platform totals")).toBeInTheDocument();
    expect(await screen.findByText("Patients")).toBeInTheDocument();
  });

  it("filters widgets the viewer has no grant for", async () => {
    setSession(["BILLING_READ"]); // no METRICS_READ
    renderWithAuth(<UserDashboard />);

    expect(await screen.findByTestId("dashboard-empty")).toBeInTheDocument();
    expect(screen.queryByText("Platform totals")).not.toBeInTheDocument();
  });

  it("honors a saved hidden list and restores widgets via Add widget", async () => {
    const user = userEvent.setup();
    mockGetPrefs.mockResolvedValue({
      dashboard_layout: { order: [], hidden: ["platform-totals"] },
    });
    renderWithAuth(<UserDashboard />);

    expect(await screen.findByTestId("dashboard-empty")).toBeInTheDocument();

    await user.click(screen.getByRole("combobox", { name: /add widget/i }));
    await user.click(await screen.findByTitle("Platform totals"));
    expect(await screen.findByText("Platform totals")).toBeInTheDocument();
  });

  it("persists removal through Save layout with order + hidden", async () => {
    const user = userEvent.setup();
    renderWithAuth(<UserDashboard />);
    await screen.findByText("Platform totals");

    await user.click(screen.getByRole("button", { name: /remove platform totals/i }));
    await user.click(screen.getByRole("button", { name: /save layout/i }));

    await waitForAssert(() =>
      expect(mockUpdatePrefs).toHaveBeenCalledWith({
        dashboard_layout: { order: [], hidden: ["platform-totals"] },
      })
    );
  });

  it("passes an axe serious-violations scan", async () => {
    const { container } = renderWithAuth(<UserDashboard />);
    await screen.findByText("Platform totals");

    const { scanA11y, seriousViolations } = await import("./axe");
    const results = await scanA11y(container);
    expect(seriousViolations(results)).toEqual([]);
  });
});

async function waitForAssert(fn: () => void) {
  const { waitFor } = await import("@testing-library/react");
  await waitFor(fn);
}
