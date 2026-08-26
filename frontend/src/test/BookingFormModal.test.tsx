import React from "react";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";
import BookingFormModal from "../schedule/BookingFormModal";
import { renderWithAuth } from "./renderWithApp";

const mockSearchOrders = vi.hoisted(() => vi.fn());
const mockGetOrder = vi.hoisted(() => vi.fn());
const mockBook = vi.hoisted(() => vi.fn());

vi.mock("../api/scheduling", () => ({
  searchRisOrders: mockSearchOrders,
  getRisOrder: mockGetOrder,
  bookAppointment: mockBook,
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
    id: "ord-1",
    procedures: [{ id: "p1", procedure_name: "CT Chest" }],
  });
  mockBook.mockResolvedValue({ id: "appt-new" });
});

describe("BookingFormModal S-10 proactive prior-auth warning", () => {
  it("warns before confirm when the picked order's auth is not obtained", async () => {
    const user = userEvent.setup();
    mockGetOrder.mockResolvedValue({
      id: "ord-1",
      prior_auth_status: "PENDING",
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
      id: "ord-1",
      prior_auth_status: "APPROVED",
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
      id: "ord-1",
      prior_auth_status: "DENIED",
      procedures: [],
    });
    renderModal();

    await user.type(screen.getByLabelText(/search order/i), "jane");
    await user.click(screen.getByRole("button", { name: /search/i }));
    await user.click(await screen.findByRole("button", { name: /select order jane/i }));

    expect(await screen.findByTestId("prior-auth-warning")).toBeInTheDocument();
  });
});
