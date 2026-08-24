import React from "react";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { App as AntdApp } from "antd";
import { AuthProvider } from "../auth/AuthContext";
import { ThemeProvider } from "../common/ThemeProvider";
import ClaimsStatus from "../billing/ClaimsStatus";

const mockListClaims = vi.hoisted(() => vi.fn());
const mockHistory = vi.hoisted(() => vi.fn());

vi.mock("../api/billing-ris", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api/billing-ris")>();
  return {
    ...actual,
    listClaims: mockListClaims,
    getClaimHistory: mockHistory,
  };
});

vi.mock("../hooks", () => ({
  useDocumentTitle: vi.fn(),
  useTenantRefetch: vi.fn(),
}));

// The real Sidebar mounts NotificationBell whose WebSocket hangs under a
// user session — identity wrapper instead.
vi.mock("../common/base", () => ({
  default: (Component: React.ComponentType) =>
    function MockedBase() {
      return <Component />;
    },
}));

const rows = [
  {
    id: "clm-1",
    claim_number: "CLM-111",
    payer_name: "Medicare",
    status: "PAID",
    patient_name: "Smith^John",
    accession_number: "ACC-1",
    cpt_code: "71250",
    charge_amount: 250,
    correction_count: 0,
  },
  {
    id: "clm-2",
    claim_number: "CLM-222",
    payer_name: "Aetna",
    status: "DENIED",
    rejection_code: "CO-16",
    patient_name: "Doe^Jane",
    accession_number: "ACC-2",
    cpt_code: "70450",
    charge_amount: 180,
    correction_count: 1,
  },
];

function renderPage() {
  return render(
    <AntdApp>
      <ThemeProvider>
        <AuthProvider>
          <MemoryRouter>
            <ClaimsStatus />
          </MemoryRouter>
        </AuthProvider>
      </ThemeProvider>
    </AntdApp>,
  );
}

describe("ClaimsStatus", () => {
  beforeEach(() => {
    localStorage.clear();
    localStorage.setItem("token", "t");
    localStorage.setItem("userId", "u1");
    localStorage.setItem("admin", "false");
    localStorage.setItem(
      "permissions",
      JSON.stringify(["BILLING_READ", "BILLING_WRITE"]),
    );
    mockListClaims.mockReset();
    mockHistory.mockReset();
    mockListClaims.mockResolvedValue(rows);
    mockHistory.mockResolvedValue([
      { event_type: "SUBMITTED", note: "initial submission" },
    ]);
  });

  it("renders the claim lifecycle dashboard (B-06)", async () => {
    renderPage();

    await waitFor(() => {
      expect(screen.getByText("CLM-111")).toBeInTheDocument();
      expect(screen.getByText("CLM-222")).toBeInTheDocument();
    });
    // Lifecycle statuses appear as both KPI titles and row tags.
    expect(screen.getAllByText("PAID").length).toBeGreaterThan(0);
    expect(screen.getAllByText("DENIED").length).toBeGreaterThan(0);
  });

  it("passes the status filter through to the API", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("CLM-111")).toBeInTheDocument();
    });

    // antd Select opens on mousedown of its selector; target the first
    // combobox (status filter) directly.
    const combo = screen.getAllByRole("combobox")[0];
    fireEvent.mouseDown(combo);
    const paid = await screen.findByText("PAID", {
      selector: ".ant-select-item-option-content",
    });
    fireEvent.click(paid);

    await waitFor(() => {
      expect(mockListClaims).toHaveBeenCalledWith(
        expect.objectContaining({ status: "PAID" }),
      );
    });
  });

  it("drills into a claim's rework history", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("CLM-111")).toBeInTheDocument();
    });

    const historyButtons = screen.getAllByRole("button", { name: "History" });
    fireEvent.click(historyButtons[0]);

    await waitFor(() => {
      expect(mockHistory).toHaveBeenCalledWith("clm-1");
      expect(screen.getByText(/initial submission/)).toBeInTheDocument();
    });
  });
});
