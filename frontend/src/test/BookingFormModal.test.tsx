import React from "react";
import { screen, fireEvent, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";
import BookingFormModal from "../schedule/BookingFormModal";
import { renderWithAuth } from "./renderWithApp";

const mockSearchOrders = vi.hoisted(() => vi.fn());
const mockGetOrder = vi.hoisted(() => vi.fn());
const mockBook = vi.hoisted(() => vi.fn());
const mockAvailability = vi.hoisted(() => vi.fn());

vi.mock("../api/scheduling", () => ({
  searchRisOrders: mockSearchOrders,
  getRisOrder: mockGetOrder,
  bookAppointment: mockBook,
  getResourceAvailability: mockAvailability,
}));

vi.mock("../common/errors", () => ({
  toErrorMessage: (e: any) => e?.message || "error",
}));

vi.mock("../hooks", () => ({ useDocumentTitle: vi.fn() }));

const RESOURCE = { id: "res-1", name: "CT Room 1" } as any;
const SLOT = { start: "10:00", end: "10:30" } as any;
const ORDER_ROW = {
  id: "ord-1",
  accession_number: "ACC100",
  patient_id: "P1",
  patient_name: "Jane Doe",
  status: "ORDERED",
  priority: "ROUTINE",
};

function renderModal(props = {}) {
  return renderWithAuth(
    <BookingFormModal
      open
      resource={RESOURCE}
      slot={SLOT}
      day="2026-08-26"
      onClose={vi.fn()}
      onDone={vi.fn()}
      {...props}
    />
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  localStorage.clear();
  localStorage.setItem("token", "t");
  localStorage.setItem("userId", "u2");
  localStorage.setItem("admin", "false");
  localStorage.setItem("role", "care_coordinator");
  localStorage.setItem("permissions", JSON.stringify(["SCHEDULE_WRITE", "ORDER_READ"]));
  mockSearchOrders.mockResolvedValue({ data: [ORDER_ROW] });
  mockGetOrder.mockResolvedValue({
    order: { id: "ord-1", prior_auth_status: "APPROVED" },
    procedures: [{ id: "p1", procedure_name: "CT Chest" }],
  });
  mockBook.mockResolvedValue({ id: "appt-new" });
  mockAvailability.mockResolvedValue([]);
});

describe("BookingFormModal S-02 conflict alternative", () => {
  it("stays open on a slot conflict and offers a one-click alternative slot", async () => {
    const user = userEvent.setup();
    // First attempt conflicts; availability shows two later free slots.
    mockBook.mockRejectedValueOnce({ status: 409, message: "Slot just taken" });
    mockBook.mockResolvedValueOnce({ id: "appt-2" });
    mockAvailability.mockResolvedValue([
      { start: "10:30", end: "11:00" },
      { start: "12:00", end: "12:30" },
    ]);
    renderModal();

    await user.type(screen.getByLabelText(/search order/i), "jane");
    await user.click(screen.getByRole("button", { name: /search/i }));
    await user.click(await screen.findByRole("button", { name: /select order jane/i }));

    fireEvent.click(screen.getByRole("button", { name: /confirm booking/i }));

    // The modal stays open and suggests the first later free slot.
    const alert = await screen.findByTestId("slot-conflict-alert");
    expect(alert).toHaveTextContent(/just taken/i);
    expect(alert).toHaveTextContent(/10:30–11:00/);

    fireEvent.click(screen.getByRole("button", { name: /book 10:30 instead/i }));

    await waitFor(() => {
      expect(mockBook).toHaveBeenLastCalledWith(
        expect.objectContaining({
          start_time: expect.stringContaining("T10:30"),
          end_time: expect.stringContaining("T11:00"),
        })
      );
    });
    expect(mockAvailability).toHaveBeenCalledWith("res-1", "2026-08-26");
  });

  it("does not suggest the failed slot itself as an alternative", async () => {
    const user = userEvent.setup();
    mockBook.mockRejectedValueOnce({ status: 409, message: "Slot just taken" });
    // Only the attempted slot comes back free (availability can lag).
    mockAvailability.mockResolvedValue([{ start: "10:00", end: "10:30" }]);
    renderModal();

    await user.type(screen.getByLabelText(/search order/i), "jane");
    await user.click(screen.getByRole("button", { name: /search/i }));
    await user.click(await screen.findByRole("button", { name: /select order jane/i }));

    fireEvent.click(screen.getByRole("button", { name: /confirm booking/i }));

    const alert = await screen.findByTestId("slot-conflict-alert");
    expect(alert).toHaveTextContent(/no later free slot/i);
  });
});

describe("BookingFormModal S-10 proactive prior-auth warning", () => {
  it("warns before confirm when the picked order's auth is not obtained", async () => {
    const user = userEvent.setup();
    mockGetOrder.mockResolvedValue({
      order: { id: "ord-1", prior_auth_status: "PENDING" },
      procedures: [],
    });
    renderModal();

    await user.type(screen.getByLabelText(/search order/i), "jane");
    await user.click(screen.getByRole("button", { name: /search/i }));
    await user.click(await screen.findByRole("button", { name: /select order jane/i }));

    expect(await screen.findByTestId("prior-auth-warning")).toHaveTextContent(/PENDING/i);
  });

  it("does not warn when auth is approved or absent", async () => {
    const user = userEvent.setup();
    mockGetOrder.mockResolvedValue({
      order: { id: "ord-1", prior_auth_status: "APPROVED" },
      procedures: [],
    });
    renderModal();

    await user.type(screen.getByLabelText(/search order/i), "jane");
    await user.click(screen.getByRole("button", { name: /search/i }));
    await user.click(await screen.findByRole("button", { name: /select order jane/i }));

    await screen.findByTestId("booking-order-summary");
    expect(screen.queryByTestId("prior-auth-warning")).not.toBeInTheDocument();
  });

  it("escalates the warning tone for denied auth", async () => {
    const user = userEvent.setup();
    mockGetOrder.mockResolvedValue({
      order: { id: "ord-1", prior_auth_status: "DENIED" },
      procedures: [],
    });
    renderModal();

    await user.type(screen.getByLabelText(/search order/i), "jane");
    await user.click(screen.getByRole("button", { name: /search/i }));
    await user.click(await screen.findByRole("button", { name: /select order jane/i }));

    expect(await screen.findByTestId("prior-auth-warning")).toBeInTheDocument();
  });
});

describe("BookingFormModal S-09 order prefill", () => {
  it("auto-loads a pre-selected order into the form (S-09)", async () => {
    mockGetOrder.mockResolvedValue({
      order: { ...ORDER_ROW, prior_auth_status: "APPROVED" },
      procedures: [{ id: "p1", procedure_name: "CT Chest" }],
    });
    renderModal({ orderId: "ord-1" });

    await waitFor(() => {
      expect(mockGetOrder).toHaveBeenCalledWith("ord-1");
    });
    // Patient pre-filled, procedure reason set, order summary visible —
    // the scheduler only has to pick a slot and confirm.
    expect(await screen.findByTestId("booking-order-summary")).toBeInTheDocument();
    expect(screen.getByLabelText("Patient ID")).toHaveValue("P1");
    expect(screen.getByLabelText("Reason")).toHaveValue("Procedure: CT Chest");
  });

  it("stays usable for search when a prefill order fails to load (S-09)", async () => {
    mockGetOrder.mockRejectedValue({ message: "order gone" });
    renderModal({ orderId: "ord-missing" });

    await waitFor(() => {
      expect(mockGetOrder).toHaveBeenCalledWith("ord-missing");
    });
    // No summary, no patient prefill — but the search box still works.
    expect(screen.queryByTestId("booking-order-summary")).not.toBeInTheDocument();
    expect(screen.getByLabelText("Search order")).toBeInTheDocument();
  });
});
