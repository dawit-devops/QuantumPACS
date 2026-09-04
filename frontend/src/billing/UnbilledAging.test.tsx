import React from "react";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { AuthProvider } from "../auth/AuthContext";
import { ThemeProvider } from "../common/ThemeProvider";
import UnbilledAging from "./UnbilledAging";
import * as api from "../api/billing-ris";

vi.mock("../helpers", () => ({
  request: vi.fn(),
  isAdmin: () => true,
  setTokens: () => {},
  clearTokens: () => {},
  startRefreshTimer: () => {},
  stopRefreshTimer: () => {},
}));

vi.mock("../hooks", () => ({
  useDocumentTitle: vi.fn(),
  useFetch: () => ({ exec: vi.fn() }),
  useTenantRefetch: () => {},
}));

vi.mock("../api/billing-ris", async (importOriginal) => {
  const actual = await importOriginal<typeof api>();
  return { ...actual, getUnbilledAging: vi.fn() };
});

vi.mock("antd", async (importOriginal) => {
  const actual = await importOriginal<typeof import("antd")>();
  return { ...actual, App: { useApp: () => ({ message: { error: vi.fn() } }) } };
});

function renderAging() {
  return render(
    <ThemeProvider>
      <AuthProvider>
        <MemoryRouter initialEntries={["/billing/aging"]}>
          <UnbilledAging />
        </MemoryRouter>
      </AuthProvider>
    </ThemeProvider>,
  );
}

const dateRows = [
  { date: "2026-08-10", count: 2, total_amount: 350, oldest_charge_days: 12 },
  { date: "2026-08-14", count: 1, total_amount: 120, oldest_charge_days: 8 },
];
const siteRows = [
  { bucket: "CT 1", count: 2, total_amount: 350, oldest_charge_days: 12 },
  { bucket: "(no room)", count: 1, total_amount: 120, oldest_charge_days: 8 },
];

describe("UnbilledAging group-by", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const setup = (groups: any[]) => {
    (api.getUnbilledAging as any).mockResolvedValue({
      groups,
      total_unbilled: groups.length,
      group_by: "date",
    });
    return renderAging();
  };

  it("renders sign-date columns by default and requests group_by=date", async () => {
    setup(dateRows);
    await waitFor(() => {
      expect(screen.getByText("Sign Date")).toBeTruthy();
    });
    expect(screen.getByText("$350.00")).toBeTruthy();
    expect((api.getUnbilledAging as any).mock.calls[0][0]).toEqual({
      group_by: "date",
    });
  });

  it("switches to site grouping and renders the site column", async () => {
    setup(siteRows);
    await waitFor(() => {
      expect(screen.getByText("Sign Date")).toBeTruthy();
    });
    fireEvent.mouseDown(screen.getByLabelText("Group aging by"));
    const bySite = await screen.findByText("By site");
    fireEvent.click(bySite);
    await waitFor(() => {
      expect(screen.getByText("Site / Room")).toBeTruthy();
    });
    expect(screen.getByText("CT 1")).toBeTruthy();
    expect(screen.getByText("(no room)")).toBeTruthy();
    const calls = (api.getUnbilledAging as any).mock.calls;
    expect(calls[calls.length - 1][0]).toEqual({ group_by: "site" });
  });
});
