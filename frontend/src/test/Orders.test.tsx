import React from "react";
import { render, screen, waitFor, fireEvent, within } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { ThemeProvider } from "../common/ThemeProvider";
import Orders, {
  derivedOrderStatus,
  ageDays,
} from "../coordinator/Orders";

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

vi.mock("../auth/AuthContext", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../auth/AuthContext")>();
  return {
    ...actual,
    useAuth: () => ({ hasPermission: () => true }),
  };
});

const HOUR = 3_600_000;
const DAY = 86_400_000;

function row(overrides: Partial<any> = {}): any {
  return {
    id: "ro-1",
    patient_id: "P1",
    patient_name: "Doe^Jane",
    requested_procedure: "CT Head",
    urgency: "routine",
    order_status: "active",
    created_at: new Date(Date.now() - 2 * DAY).toISOString(),
    modality: "CT",
    ...overrides,
  };
}

describe("derivedOrderStatus (CS8)", () => {
  it("cancelled wins over everything", () => {
    expect(
      derivedOrderStatus(
        row({ order_status: "cancelled", report_status: "final" }),
      ),
    ).toBe("cancelled");
  });

  it("non-draft reports mean reported", () => {
    expect(derivedOrderStatus(row({ report_status: "final" }))).toBe(
      "reported",
    );
    expect(derivedOrderStatus(row({ report_status: "prelim" }))).toBe(
      "reported",
    );
  });

  it("draft reports are in progress", () => {
    expect(derivedOrderStatus(row({ report_status: "draft" }))).toBe(
      "in progress",
    );
  });

  it("exam states map to performed / in progress", () => {
    expect(derivedOrderStatus(row({ exam_status: "completed" }))).toBe(
      "performed",
    );
    expect(derivedOrderStatus(row({ exam_status: "in_progress" }))).toBe(
      "in progress",
    );
    expect(derivedOrderStatus(row({ exam_status: "ready" }))).toBe(
      "in progress",
    );
  });

  it("scheduled worklist beats bare request", () => {
    expect(derivedOrderStatus(row({ wl_status: "scheduled" }))).toBe(
      "scheduled",
    );
    expect(derivedOrderStatus(row())).toBe("requested");
  });
});

describe("ageDays stuck-work boundaries (CS8)", () => {
  it("returns null without a timestamp", () => {
    expect(ageDays(row({ created_at: undefined }))).toBeNull();
    expect(ageDays(row({ created_at: "not-a-date" }))).toBeNull();
  });

  it("24h is the amber boundary (<=1d not waiting)", () => {
    // Exactly 24h old — NOT >1d, so not amber.
    expect(ageDays(row({ created_at: new Date(Date.now() - DAY).toISOString() }))!).toBeLessThanOrEqual(1);
    // Just over 24h — amber territory.
    expect(
      ageDays(row({ created_at: new Date(Date.now() - DAY - HOUR).toISOString() }))!,
    ).toBeGreaterThan(1);
  });

  it("72h is the red boundary (>3d)", () => {
    expect(
      ageDays(row({ created_at: new Date(Date.now() - 3 * DAY).toISOString() }))!,
    ).toBeLessThanOrEqual(3);
    expect(
      ageDays(
        row({ created_at: new Date(Date.now() - 3 * DAY - HOUR).toISOString() })!,
      ),
    ).toBeGreaterThan(3);
  });
});

describe("Orders board summary + filters (CS8)", () => {
  beforeEach(() => {
    mockRequest.mockReset();
    mockRequest.mockResolvedValue({
      data: [
        row({
          id: "fresh",
          patient_id: "P1",
          created_at: new Date(Date.now() - 2 * HOUR).toISOString(),
        }),
        row({
          id: "amber",
          patient_id: "P2",
          requested_procedure: "CXR",
          created_at: new Date(Date.now() - 30 * HOUR).toISOString(),
        }),
        row({
          id: "red",
          patient_id: "P3",
          modality: "MR",
          created_at: new Date(Date.now() - 96 * HOUR).toISOString(),
        }),
        row({
          id: "done",
          patient_id: "P4",
          report_status: "final",
          created_at: new Date().toISOString(),
        }),
      ],
    });
  });

  function renderOrders() {
    return render(
      <ThemeProvider>
        <MemoryRouter>
          <Orders />
        </MemoryRouter>
      </ThemeProvider>,
    );
  }

  it("counts open and >24h-waiting orders; reported-today excluded from open", async () => {
    renderOrders();
    const alert = await screen.findByRole("alert");
    // 3 open (fresh/amber/red); done is reported.
    expect(within(alert).getByText("3")).toBeInTheDocument();
    // amber (30h) + red (96h) exceed 24h → waiting = 2.
    expect(within(alert).getByText("2")).toBeInTheDocument();
    expect(within(alert).getByText("1")).toBeInTheDocument();
  });

  it("filters rows by status", async () => {
    renderOrders();
    await waitFor(() => {
      expect(screen.getByText("P3")).toBeInTheDocument();
    });
    fireEvent.mouseDown(screen.getByLabelText("Order status"));
    const opt = await screen.findAllByText(/^reported$/i);
    fireEvent.click(opt[opt.length - 1]);
    await waitFor(() => {
      expect(screen.getByText("P4")).toBeInTheDocument();
      expect(screen.queryByText("P1")).not.toBeInTheDocument();
    });
  });

  it("filters rows by free-text patient search", async () => {
    renderOrders();
    await waitFor(() => {
      expect(screen.getByText("P1")).toBeInTheDocument();
    });
    fireEvent.change(
      screen.getByPlaceholderText(/search patient or procedure/i),
      { target: { value: "p1" } },
    );
    await waitFor(() => {
      expect(screen.getByText("P1")).toBeInTheDocument();
      expect(screen.queryByText("P3")).not.toBeInTheDocument();
    });
  });
});
