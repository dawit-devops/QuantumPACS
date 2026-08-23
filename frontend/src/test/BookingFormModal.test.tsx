/**
 * C4 (GAP_AUDIT_TDD_PIPELINE.md): the booking form must surface order
 * procedures (picker that records the choice as the booking reason), show
 * the order's priority, and turn a prior-authorization 409 into an audited
 * override flow instead of a dead-end toast.
 */
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";

import { renderWithApp } from "./renderWithApp";
import BookingFormModal from "../schedule/BookingFormModal";

const mockBook = vi.hoisted(() => vi.fn());
const mockSearchOrders = vi.hoisted(() => vi.fn());
const mockGetOrder = vi.hoisted(() => vi.fn());

vi.mock("../api/scheduling", () => ({
  bookAppointment: mockBook,
  searchRisOrders: mockSearchOrders,
  getRisOrder: mockGetOrder,
}));

const RESOURCE = {
  id: "res-1",
  name: "CT Room 1",
  modality: "CT",
} as any;

const SLOT = { start: "09:00", end: "09:30" };
const DAY = "2026-08-22";

const ORDER = {
  id: "ord-1",
  accession_number: "ACC-77",
  patient_id: "MRN-77",
  patient_name: "Doe^Jane",
  priority: "STAT",
  status: "ORDERED",
};

const DETAIL = {
  order: ORDER,
  procedures: [
    { id: "proc-a", procedure_code: "CT CHEST", procedure_name: "Chest CT" },
    { id: "proc-b", procedure_code: "CT ABDOMEN", procedure_name: "Abdomen CT" },
  ],
  appointments: [],
};

const renderModal = () =>
  renderWithApp(
    <BookingFormModal
      open
      resource={RESOURCE}
      slot={SLOT}
      day={DAY}
      onClose={() => {}}
      onDone={() => {}}
    />
  );

describe("BookingFormModal C4", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockSearchOrders.mockResolvedValue({
      data: [ORDER],
      total: 1,
      page: 1,
      per_page: 20,
    });
    mockGetOrder.mockResolvedValue(DETAIL);
    mockBook.mockResolvedValue({ id: "appt-9" });
  });

  const pickOrder = async () => {
    const input = screen.getByLabelText("Search order");
    await userEvent.type(input, "Doe");
    await userEvent.click(screen.getByRole("button", { name: /search/i }));
    await screen.findByRole("button", { name: /select order Doe/i });
    await userEvent.click(
      screen.getByRole("button", { name: /select order Doe/i })
    );
    await waitFor(() =>
      expect(mockGetOrder).toHaveBeenCalledWith("ord-1")
    );
  };

  it("shows the order priority badge after picking an order", async () => {
    renderModal();
    await pickOrder();
    await waitFor(() => {
      expect(screen.getByTestId("booking-order-summary")).toHaveTextContent(
        "STAT"
      );
    });
  });

  it("offers multi-procedure picker and prefills reason with the choice", async () => {
    renderModal();
    await pickOrder();

    const combo = await screen.findByLabelText("Procedure");
    await userEvent.click(combo);
    const option = await screen.findByText("Abdomen CT");
    await userEvent.click(option);

    const reason = screen.getByLabelText("Reason") as HTMLInputElement;
    await waitFor(() => {
      expect(reason.value).toBe("Procedure: Abdomen CT");
    });
  });

  it("sends override_reason through the prior-auth conflict path", async () => {
    mockBook
      .mockRejectedValueOnce({
        status: 409,
        code: "SLOT_CONFLICT",
        message: "Order ord-1 requires prior authorization (PENDING)",
      })
      .mockResolvedValueOnce({ id: "appt-10" });

    renderModal();
    await pickOrder();
    await userEvent.click(
      screen.getByRole("button", { name: /confirm booking/i })
    );

    // The conflict keeps the modal open and offers the override…
    const warning = await screen.findByText(/blocked by prior authorization/i);
    expect(warning).toBeInTheDocument();
    expect(mockBook).toHaveBeenCalledTimes(1);

    // …but refuses to submit without a reason.
    await userEvent.click(
      screen.getByRole("button", { name: /book with override/i })
    );
    expect(mockBook).toHaveBeenCalledTimes(1);

    // With a reason, the retry carries override_reason and succeeds.
    await userEvent.type(
      screen.getByLabelText("Override reason"),
      "verbal payer approval"
    );
    await userEvent.click(
      screen.getByRole("button", { name: /book with override/i })
    );
    await waitFor(() => expect(mockBook).toHaveBeenCalledTimes(2));
    expect(mockBook).toHaveBeenLastCalledWith(
      expect.objectContaining({ override_reason: "verbal payer approval" })
    );
  });

  it("non-auth conflicts still bubble to onConflict", async () => {
    const onConflict = vi.fn();
    mockBook.mockRejectedValueOnce({
      status: 409,
      code: "SLOT_CONFLICT",
      message: "Resource already booked",
    });
    renderWithApp(
      <BookingFormModal
        open
        resource={RESOURCE}
        slot={SLOT}
        day={DAY}
        onClose={() => {}}
        onDone={() => {}}
        onConflict={onConflict}
      />
    );
    await userEvent.type(screen.getByLabelText("Patient ID"), "WALKIN-1");
    await userEvent.click(
      screen.getByRole("button", { name: /confirm booking/i })
    );
    await waitFor(() => expect(onConflict).toHaveBeenCalled());
  });
});
