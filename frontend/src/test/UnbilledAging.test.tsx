import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import React from "react";
import { MemoryRouter } from "react-router";
import { AuthProvider } from "../auth/AuthContext";
import { ThemeProvider } from "../common/ThemeProvider";
import UnbilledAging from "../billing/UnbilledAging";

vi.mock("../api/billing-ris", () => ({
  getUnbilledAging: vi.fn(),
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
      hasPermission: (perm: string) => ["BILLING_READ", "BILLING_WRITE"].includes(perm),
    }),
  };
});

import { getUnbilledAging } from "../api/billing-ris";
const mockGetUnbilledAging = vi.mocked(getUnbilledAging);

const mockReport = {
  groups: [
    {
      date: "2026-08-10",
      count: 2,
      total_amount: 500.0,
      oldest_charge_days: 11,
    },
    {
      date: "2026-08-15",
      count: 1,
      total_amount: 250.0,
      oldest_charge_days: 6,
    },
  ],
  total_unbilled: 3,
};

function renderAging() {
  localStorage.setItem("userId", "1");
  localStorage.setItem("username", "test");
  localStorage.setItem(
    "permissions",
    JSON.stringify(["BILLING_READ", "BILLING_WRITE"]),
  );
  localStorage.setItem("tenant_id", "t1");
  localStorage.setItem("tenant_name", "Test");
  return render(
    <MemoryRouter>
      <AuthProvider>
        <ThemeProvider>
          <UnbilledAging />
        </ThemeProvider>
      </AuthProvider>
    </MemoryRouter>,
  );
}

describe("UnbilledAging", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGetUnbilledAging.mockResolvedValue(mockReport);
  });

  it("renders aging groups from the API", async () => {
    renderAging();
    await waitFor(() => {
      expect(screen.getByText("2026-08-10")).toBeInTheDocument();
    });
    expect(screen.getByText("2026-08-15")).toBeInTheDocument();
  });

  it("shows total unbilled summary", async () => {
    renderAging();
    await waitFor(() => {
      expect(screen.getByText("3")).toBeInTheDocument();
    });
  });

  it("shows oldest charge day tag", async () => {
    renderAging();
    await waitFor(() => {
      expect(screen.getByText("11d")).toBeInTheDocument();
    });
  });

  it("exports the current groups as CSV (B-11)", async () => {
    const clickSpy = vi
      .spyOn(HTMLAnchorElement.prototype, "click")
      .mockImplementation(() => {});
    const createSpy = vi
      .spyOn(globalThis.URL, "createObjectURL")
      .mockReturnValue("blob:mock");
    renderAging();
    await waitFor(() => {
      expect(screen.getByText("2026-08-10")).toBeInTheDocument();
    });

    fireEvent.click(
      screen.getByRole("button", { name: /export unbilled aging csv/i }),
    );

    await waitFor(() => {
      expect(createSpy).toHaveBeenCalled();
      expect(clickSpy).toHaveBeenCalled();
    });
    clickSpy.mockRestore();
    createSpy.mockRestore();
  });
});