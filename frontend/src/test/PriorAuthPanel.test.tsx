import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import React from "react";
import { MemoryRouter } from "react-router";
import { App } from "antd";
import { AuthProvider } from "../auth/AuthContext";
import { ThemeProvider } from "../common/ThemeProvider";
import PriorAuthPanel from "../coordinator/PriorAuthPanel";

const mockSubmitForReview = vi.hoisted(() => vi.fn());
const mockOverride = vi.hoisted(() => vi.fn());
const mockListExpiring = vi.hoisted(() => vi.fn());

vi.mock("../api/prior-auth", () => ({
  listPriorAuth: vi.fn(),
  submitPriorAuth: vi.fn(),
  decidePriorAuth: vi.fn(),
  listPriorAuthExpiring: mockListExpiring,
  submitForReview: mockSubmitForReview,
  overridePriorAuth: mockOverride,
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
      hasPermission: () => true,
    }),
  };
});

import {
  listPriorAuth,
  submitForReview,
  overridePriorAuth,
  type PriorAuthRequest,
} from "../api/prior-auth";
const mockList = vi.mocked(listPriorAuth);

const mockData: PriorAuthRequest[] = [
  {
    id: "pa-1",
    order_id: "ord-1",
    procedure_code: "CT CHEST",
    payer_id: "PAY-1",
    payer_name: "Medicare",
    status: "PENDING",
    auth_number: "",
    expiry_date: undefined,
  },
  {
    id: "pa-2",
    order_id: "ord-2",
    procedure_code: "MRI BRAIN",
    payer_id: "PAY-2",
    payer_name: "Blue Cross",
    status: "APPROVED",
    auth_number: "AUTH-123",
    expiry_date: "2026-09-21",
  },
];

// CS1 fixtures — a REQUIRED request for submit/override actions.
const requiredRow: PriorAuthRequest = {
  id: "pa-3",
  order_id: "ord-3",
  procedure_code: "PET CT",
  payer_id: "PAY-3",
  payer_name: "United",
  status: "REQUIRED",
};

function renderPanel() {
  localStorage.setItem("userId", "1");
  localStorage.setItem("username", "test");
  localStorage.setItem("permissions", JSON.stringify(["PRIOR_AUTH_READ"]));
  localStorage.setItem("tenant_id", "t1");
  return render(
    <MemoryRouter>
      <App>
        <AuthProvider>
          <ThemeProvider>
            <PriorAuthPanel />
          </ThemeProvider>
        </AuthProvider>
      </App>
    </MemoryRouter>,
  );
}

describe("PriorAuthPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockList.mockResolvedValue({ data: mockData, total: 2 });
    // CS1: expiring-soon toggle swaps the fetch target.
    mockListExpiring.mockResolvedValue({ data: [], total: 0 });
    mockSubmitForReview.mockResolvedValue({
      id: "pa-3",
      status: "PENDING",
    });
    mockOverride.mockResolvedValue({ id: "pa-3", status: "NOT_REQUIRED" });
  });

  it("renders prior-auth requests from the API", async () => {
    renderPanel();
    await waitFor(() => {
      expect(screen.getByText("ord-1")).toBeInTheDocument();
    });
    expect(screen.getByText("ord-2")).toBeInTheDocument();
  });

  it("shows status tags", async () => {
    renderPanel();
    await waitFor(() => {
      expect(screen.getByText("PENDING")).toBeInTheDocument();
    });
    expect(screen.getByText("APPROVED")).toBeInTheDocument();
  });

  it("shows auth number for approved requests", async () => {
    renderPanel();
    await waitFor(() => {
      expect(screen.getByText("AUTH-123")).toBeInTheDocument();
    });
  });

  it("submits a REQUIRED request for payer review (CS1)", async () => {
    mockList.mockResolvedValue({
      data: [...mockData, requiredRow],
      total: 3,
    });
    renderPanel();
    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: "Submit for review" }),
      ).toBeInTheDocument();
    });

    // aria-label wins over button text for the accessible name.
    fireEvent.click(screen.getByRole("button", { name: "Submit for review" }));

    await waitFor(() => {
      expect(mockSubmitForReview).toHaveBeenCalledWith("pa-3");
    });
  });

  it("overrides a request with a mandatory reason (CS1)", async () => {
    mockList.mockResolvedValue({
      data: [...mockData, requiredRow],
      total: 3,
    });
    renderPanel();
    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: /override prior auth ord-3/i }),
      ).toBeInTheDocument();
    });

    fireEvent.click(
      screen.getByRole("button", { name: /override prior auth ord-3/i }),
    );

    const noteBox = await screen.findByPlaceholderText(
      /Why is prior auth not required/i,
    );
    // OK disabled until a reason is typed.
    const okBtn = screen.getByRole("button", { name: "Override" });
    expect(okBtn).toBeDisabled();
    fireEvent.change(noteBox, {
      target: { value: "Payer confirmed low-dose CT exempt" },
    });
    fireEvent.click(okBtn);

    await waitFor(() => {
      expect(mockOverride).toHaveBeenCalledWith(
        "pa-3",
        "Payer confirmed low-dose CT exempt",
      );
    });
  });

  it("toggles the expiring-soon view (CS1)", async () => {
    renderPanel();
    await waitFor(() => {
      expect(screen.getByText("ord-1")).toBeInTheDocument();
    });

    fireEvent.click(
      screen.getByRole("button", { name: /expiring soon \(7d\)/i }),
    );
    await waitFor(() => {
      expect(mockListExpiring).toHaveBeenCalledWith(7);
    });
  });
});