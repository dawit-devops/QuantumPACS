import React from "react";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";
import UserDashboard from "../dashboard/UserDashboard";
import { WIDGETS, ROLE_DEFAULT_LAYOUTS } from "../dashboard/widgets/registry";
import { request } from "../api/client";
import { renderWithAuth } from "./renderWithApp";

const mockGetPrefs = vi.hoisted(() => vi.fn());
const mockUpdatePrefs = vi.hoisted(() => vi.fn());

vi.mock("../api/preferences", () => ({
  getPreferences: mockGetPrefs,
  updatePreferences: mockUpdatePrefs,
}));

vi.mock("../api/client", () => ({
  request: vi.fn(),
}));

/** Route each widget's self-fetch to deterministic fixture payloads. */
function stubClient() {
  const mocked = request as unknown as ReturnType<typeof vi.fn>;
  mocked.mockImplementation((path: string) => {
    switch (path) {
      case "v2/dashboard/metrics":
        return Promise.resolve({
          totals: { patients: 3, studies: 4, files: 5, users: 6, storage_bytes: 1024 },
        });
      case "qa/dashboard":
        return Promise.resolve({
          data: { exams_reviewed: 9, compliance_pct: 97.5, open_incidents: 2, open_actions: 1 },
        });
      case "orders":
        return Promise.resolve({
          data: [
            { order_status: "requested", created_at: new Date().toISOString() },
            { order_status: "reported", created_at: new Date().toISOString() },
            {
              order_status: "scheduled",
              created_at: new Date(Date.now() - 3 * 86_400_000).toISOString(),
            },
          ],
        });
      case "ris/billing/unbilled":
        return Promise.resolve({
          groups: [{ date: "2026-08-20", count: 2, total_amount: 350, oldest_charge_days: 7 }],
          total_unbilled: 350,
          buckets: { over5: 2, over10: 1 },
        });
      case "queue":
        return Promise.resolve({
          data: [{ wait_minutes: 12 }, { wait_minutes: 41 }, { wait_minutes: 5 }],
        });
      default:
        return Promise.reject(new Error(`unexpected path ${path}`));
    }
  });
}

function setSession(perms: string[], role = "care_coordinator") {
  localStorage.clear();
  localStorage.setItem("token", "t");
  localStorage.setItem("userId", "u2");
  localStorage.setItem("admin", "false");
  localStorage.setItem("role", role);
  localStorage.setItem("permissions", JSON.stringify(perms));
}

beforeEach(() => {
  vi.clearAllMocks();
  stubClient();
  setSession(["METRICS_READ"]);
  mockGetPrefs.mockResolvedValue({});
  mockUpdatePrefs.mockResolvedValue({});
});

describe("UserDashboard (§3 configurable widgets)", () => {
  it("renders the default registered widget for a permitted user", async () => {
    setSession(["METRICS_READ"], "super_admin");
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
    setSession(["METRICS_READ"], "super_admin");
    const user = userEvent.setup();
    mockGetPrefs.mockResolvedValue({
      dashboard_layout: { order: [], hidden: ["platform-totals"] },
    });
    renderWithAuth(<UserDashboard />);

    expect(await screen.findByTestId("dashboard-empty")).toBeInTheDocument();

    await user.click(screen.getByRole("combobox", { name: /add widget/i }));
    await user.click(await screen.findByTitle("Platform totals"));
    expect((await screen.findAllByText("Platform totals")).length).toBeGreaterThan(0);
  });

  it("persists removal through Save layout with order + hidden", async () => {
    setSession(["METRICS_READ"], "super_admin");
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
    setSession(["METRICS_READ"], "super_admin");
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

describe("persona widget sets (registry)", () => {
  it("registers unique ids with renderable components", () => {
    const ids = WIDGETS.map((w) => w.id);
    expect(new Set(ids).size).toBe(ids.length);
    for (const w of WIDGETS) {
      expect(w.title).toBeTruthy();
      expect(["sm", "md", "lg"]).toContain(w.defaultSize);
      expect(w.component).toBeDefined();
    }
  });

  it("maps role defaults to registered widget ids", () => {
    for (const layout of Object.values(ROLE_DEFAULT_LAYOUTS)) {
      for (const id of layout) {
        expect(WIDGETS.some((w) => w.id === id)).toBe(true);
      }
    }
  });
});

describe("persona widgets render their data", () => {
  it("QA overview surfaces the qa-dashboard aggregate", async () => {
    setSession(["QA_READ", "ORDER_READ", "BILLING_READ"], "dept_manager");
    renderWithAuth(<UserDashboard />);
    expect(await screen.findByText("QA overview")).toBeInTheDocument();
    expect(await screen.findByText("Exams reviewed")).toBeInTheDocument();
    expect(screen.getByText("Open incidents")).toBeInTheDocument();
  });

  it("order pipeline counts open and stuck orders", async () => {
    setSession(["ORDER_READ"]);
    renderWithAuth(<UserDashboard />);
    expect(await screen.findByText("Order pipeline")).toBeInTheDocument();
    expect(await screen.findByText("Open orders")).toBeInTheDocument();
    expect(await screen.findByText("Stuck >24h")).toBeInTheDocument();
  });

  it("unbilled charges widget shows totals and aging bucket", async () => {
    setSession(["BILLING_READ"], "cashier");
    renderWithAuth(<UserDashboard />);
    expect(await screen.findByText("Unbilled charges")).toBeInTheDocument();
    expect(await screen.findByText("Aged >5 days")).toBeInTheDocument();
  });

  it("waiting-room widget renders queue counts", async () => {
    setSession(["QUEUE_READ"], "receptionist");
    renderWithAuth(<UserDashboard />);
    expect(await screen.findByText("Waiting room")).toBeInTheDocument();
    expect(await screen.findByText("Waiting >30 min")).toBeInTheDocument();
  });
});
