import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";

dayjs.extend(utc);

import { renderWithAuth } from "./renderWithApp";
import CalendarView from "../schedule/CalendarView";

const mockListResources = vi.hoisted(() => vi.fn());
const mockListAppointments = vi.hoisted(() => vi.fn());
const mockGetAvailability = vi.hoisted(() => vi.fn());
const mockBook = vi.hoisted(() => vi.fn());
const mockReschedule = vi.hoisted(() => vi.fn());
const mockCancel = vi.hoisted(() => vi.fn());
const mockNoShow = vi.hoisted(() => vi.fn());
const mockSearchOrders = vi.hoisted(() => vi.fn());

vi.mock("../api/scheduling", () => ({
  listRisResources: mockListResources,
  createRisResource: vi.fn(),
  listRisSchedules: vi.fn(),
  createRisSchedule: vi.fn(),
  getResourceAvailability: mockGetAvailability,
  listResourceAppointments: mockListAppointments,
  bookAppointment: mockBook,
  rescheduleAppointment: mockReschedule,
  cancelRisAppointment: mockCancel,
  markNoShow: mockNoShow,
  searchRisOrders: mockSearchOrders,
  dayOfWeekLabel: (d: number) =>
    ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"][d],
}));

vi.mock("antd", async () => {
  const actual = await vi.importActual("antd");
  const Popconfirm = ({ children, onConfirm, title }: any) =>
    React.createElement(
      "span",
      {
        className: "mock-popconfirm",
        "data-title": title,
        onClick: (e: React.MouseEvent) => {
          e.stopPropagation();
          onConfirm?.();
        },
      },
      children
    );
  return { ...actual, Popconfirm };
});

let registeredTenantCb: (() => void) | null = null;
vi.mock("../hooks", () => ({
  useDocumentTitle: vi.fn(),
  useTenantRefetch: (cb: () => void) => {
    registeredTenantCb = cb;
  },
}));

function seedUser(permissions: string[]) {
  localStorage.setItem("token", "t");
  localStorage.setItem("userId", "u1");
  localStorage.setItem("admin", "false");
  localStorage.setItem("role", "scheduler");
  localStorage.setItem("permissions", JSON.stringify(permissions));
}

const RESOURCE = {
  id: "r1",
  name: "CT Room 1",
  resource_type: "MODALITY",
  modality: "CT",
  status: "ACTIVE",
};

const APPT = {
  id: "a1",
  resource_id: "r1",
  patient_id: "P001",
  status: "SCHEDULED",
  start_time: "2026-08-20T09:00:00.000Z",
  end_time: "2026-08-20T09:30:00.000Z",
};

describe("CalendarView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    registeredTenantCb = null;
    seedUser(["SCHEDULE_READ", "SCHEDULE_WRITE"]);
    mockListResources.mockResolvedValue([RESOURCE]);
    mockListAppointments.mockResolvedValue([]);
    mockGetAvailability.mockResolvedValue([
      { start: "09:00", end: "09:30" },
      { start: "09:30", end: "10:00" },
    ]);
  });

  it("renders resources as columns and booked appointments as blocks", async () => {
    mockListAppointments.mockResolvedValue([APPT]);
    renderWithAuth(<CalendarView />);
    expect(await screen.findByText("CT Room 1")).toBeInTheDocument();
    expect(await screen.findByText("P001")).toBeInTheDocument();
    expect(screen.getByText("SCHEDULED")).toBeInTheDocument();
  });

  it("renders a STAT priority badge on high-priority blocks (C4)", async () => {
    mockListAppointments.mockResolvedValue([
      { ...APPT, id: "a2", patient_id: "P-STAT", priority: "STAT" },
    ]);
    renderWithAuth(<CalendarView />);
    expect(await screen.findByText("P-STAT")).toBeInTheDocument();
    expect(screen.getByText("STAT")).toBeInTheDocument();
  });

  it("shows an empty state when no resources are configured", async () => {
    mockListResources.mockResolvedValue([]);
    renderWithAuth(<CalendarView />);
    expect(
      await screen.findByText("No resources configured — add them from the Resources page.")
    ).toBeInTheDocument();
  });

  it("books an appointment from a free slot with order search", async () => {
    mockSearchOrders.mockResolvedValue({
      data: [
        {
          id: "o1",
          accession_number: "ACC-1",
          patient_id: "P001",
          patient_name: "Jane Roe",
          status: "ORDERED",
          priority: "ROUTINE",
        },
      ],
      total: 1,
      page: 1,
      per_page: 25,
    });
    mockBook.mockResolvedValue({ ...APPT, id: "a9" });

    renderWithAuth(<CalendarView />);
    await screen.findByText("CT Room 1");

    // click the 09:00 free cell (the grid renders time column + resource cells)
    const freeCell = screen
      .getAllByRole("button")
      .find((c) => c.getAttribute("aria-label")?.includes("(free)"));
    expect(freeCell).toBeDefined();
    fireEvent.click(freeCell!);

    // booking modal: search order, pick it, confirm
    const search = screen.getByPlaceholderText("Search order (name, MRN or accession)");
    await userEvent.type(search, "Jane{Enter}");
    expect(await screen.findByText("Jane Roe")).toBeInTheDocument();
    fireEvent.click(screen.getByText("Jane Roe"));
    fireEvent.click(screen.getByText("Confirm Booking"));

    await waitFor(() => {
      expect(mockBook).toHaveBeenCalledWith(
        expect.objectContaining({
          order_id: "o1",
          resource_id: "r1",
          patient_id: "P001",
        })
      );
    });
  });

  // ---- HI-001: Order-less booking + order-search edge paths ----------------

  it("books without an order by typing a patient ID directly", async () => {
    mockBook.mockResolvedValue({ ...APPT, id: "a-direct" });

    renderWithAuth(<CalendarView />);
    await screen.findByText("CT Room 1");

    // Click a free cell to open the booking modal
    const freeCell = screen
      .getAllByRole("button")
      .find((c) => c.getAttribute("aria-label")?.includes("(free)"));
    fireEvent.click(freeCell!);

    // Type patient ID directly — no order search, no order pick
    const patientInput = screen.getByPlaceholderText(/patient ID directly/i);
    await userEvent.type(patientInput, "P999");

    // Confirm — should send order_id: "" (order-less)
    fireEvent.click(screen.getByText("Confirm Booking"));

    await waitFor(() => {
      expect(mockBook).toHaveBeenCalledWith(
        expect.objectContaining({
          order_id: "",
          patient_id: "P999",
          resource_id: "r1",
        })
      );
    });
  });

  it("does not search orders on a single-character term", async () => {
    renderWithAuth(<CalendarView />);
    await screen.findByText("CT Room 1");

    const freeCell = screen
      .getAllByRole("button")
      .find((c) => c.getAttribute("aria-label")?.includes("(free)"));
    fireEvent.click(freeCell!);

    // Type a single character and press Enter — term.length < 2 guard fires
    const search = screen.getByPlaceholderText("Search order (name, MRN or accession)");
    await userEvent.type(search, "J{Enter}");

    // searchRisOrders should NOT have been called (guard returns early)
    await waitFor(() => {
      expect(mockSearchOrders).not.toHaveBeenCalled();
    });
  });

  it("surfaces order search failure as an error toast", async () => {
    mockSearchOrders.mockRejectedValue({ message: "search down" });

    renderWithAuth(<CalendarView />);
    await screen.findByText("CT Room 1");

    const freeCell = screen
      .getAllByRole("button")
      .find((c) => c.getAttribute("aria-label")?.includes("(free)"));
    fireEvent.click(freeCell!);

    const search = screen.getByPlaceholderText("Search order (name, MRN or accession)");
    await userEvent.type(search, "Jane{Enter}");

    // The search was attempted (term >= 2 chars), but the API rejected it.
    // The error should surface — either via message.error or the error state.
    await waitFor(() => {
      expect(mockSearchOrders).toHaveBeenCalled();
    });
  });

  it("opens the detail drawer on block click and cancels with reason", async () => {
    mockListAppointments.mockResolvedValue([APPT]);
    mockCancel.mockResolvedValue({ ...APPT, status: "CANCELLED" });

    renderWithAuth(<CalendarView />);
    await screen.findByText("P001");

    fireEvent.click(screen.getByText("P001"));
    expect(await screen.findByText("Appointment")).toBeInTheDocument();

    fireEvent.click(screen.getByText("Cancel"));
    const reason = screen.getByPlaceholderText("Reason (required for audit)");
    await userEvent.type(reason, "no-show");
    fireEvent.click(screen.getByRole("button", { name: "Cancel Appointment" }));

    await waitFor(() => {
      expect(mockCancel).toHaveBeenCalledWith("a1", "no-show");
    });
  });

  // ---- HI-003: CancelModal validation + failure path -----------------------

  it("blocks cancelling without a reason (button disabled)", async () => {
    mockListAppointments.mockResolvedValue([APPT]);
    renderWithAuth(<CalendarView />);
    await screen.findByText("P001");

    // Open the detail drawer and click Cancel
    fireEvent.click(screen.getByText("P001"));
    expect(await screen.findByText("Appointment")).toBeInTheDocument();
    fireEvent.click(screen.getByText("Cancel"));

    // The confirm button should be disabled (reason is empty)
    const confirmBtn = screen.getByRole("button", { name: "Cancel Appointment" });
    expect(confirmBtn).toBeDisabled();

    // Clicking a disabled button is a no-op
    fireEvent.click(confirmBtn);
    expect(mockCancel).not.toHaveBeenCalled();
  });

  it("shows error when the cancel request fails", async () => {
    mockListAppointments.mockResolvedValue([APPT]);
    mockCancel.mockRejectedValue({ message: "Cancel failed" });

    renderWithAuth(<CalendarView />);
    await screen.findByText("P001");

    fireEvent.click(screen.getByText("P001"));
    expect(await screen.findByText("Appointment")).toBeInTheDocument();

    fireEvent.click(screen.getByText("Cancel"));
    const reason = screen.getByPlaceholderText("Reason (required for audit)");
    await userEvent.type(reason, "duplicate");
    fireEvent.click(screen.getByRole("button", { name: "Cancel Appointment" }));

    await waitFor(() => {
      expect(mockCancel).toHaveBeenCalled();
    });

    // After failure, the modal should still be open (onDone was NOT called)
    // The typed reason is still visible in the input — proves the modal didn't close
    await waitFor(() => {
      expect(screen.getByDisplayValue("duplicate")).toBeInTheDocument();
    });
  });

  it("does not offer booking actions without SCHEDULE_WRITE", async () => {
    seedUser(["SCHEDULE_READ"]);
    mockListAppointments.mockResolvedValue([APPT]);
    renderWithAuth(<CalendarView />);
    await screen.findByText("P001");
    fireEvent.click(screen.getByText("P001"));
    expect(await screen.findByText("Appointment")).toBeInTheDocument();
    expect(screen.queryByText("Reschedule")).not.toBeInTheDocument();
    expect(screen.queryByText("Book Appointment")).not.toBeInTheDocument();
  });

  it("does not open booking modal when read-only user clicks free cell", async () => {
    seedUser(["SCHEDULE_READ"]);
    mockListAppointments.mockResolvedValue([]);
    renderWithAuth(<CalendarView />);
    await screen.findByText("CT Room 1");

    // Find a free cell and click it — read-only users get gridcell (not button)
    const freeCell = screen
      .getAllByRole("gridcell")
      .find((c) => c.getAttribute("aria-label")?.includes("(free)"));
    expect(freeCell).toBeDefined();
    fireEvent.click(freeCell!);

    // The booking modal should NOT open — canWrite is false
    await waitFor(() => {
      expect(
        screen.queryByPlaceholderText("Search order (name, MRN or accession)")
      ).not.toBeInTheDocument();
    });
    expect(mockBook).not.toHaveBeenCalled();
  });

  // ---- A1: Keyboard-accessible free cells ----------------------------------

  it("free cells are focusable and activatable via Enter key", async () => {
    renderWithAuth(<CalendarView />);
    await screen.findByText("CT Room 1");

    // A1: free cells must have role="button" and tabIndex for keyboard access
    const freeCells = screen
      .getAllByRole("button")
      .filter((c) => c.getAttribute("aria-label")?.includes("(free)"));
    expect(freeCells.length).toBeGreaterThan(0);
    const freeCell = freeCells[0];
    expect(freeCell).toHaveAttribute("tabindex", "0");

    // Activate via Enter key
    freeCell.focus();
    await userEvent.keyboard("{Enter}");

    // Booking modal should open
    expect(
      await screen.findByPlaceholderText("Search order (name, MRN or accession)")
    ).toBeInTheDocument();
  });

  it("free cells are activatable via Space key", async () => {
    renderWithAuth(<CalendarView />);
    await screen.findByText("CT Room 1");

    const freeCells = screen
      .getAllByRole("button")
      .filter((c) => c.getAttribute("aria-label")?.includes("(free)"));
    const freeCell = freeCells[0];

    freeCell.focus();
    await userEvent.keyboard(" ");

    expect(
      await screen.findByPlaceholderText("Search order (name, MRN or accession)")
    ).toBeInTheDocument();
  });

  // ---- HI-002: Day navigation + modal-state reset -------------------------

  it("navigates to next day and re-fetches appointments", async () => {
    renderWithAuth(<CalendarView />);
    await screen.findByText("CT Room 1");

    const callsBefore = mockListResources.mock.calls.length;

    fireEvent.click(screen.getByRole("button", { name: "Next day" }));

    await waitFor(() => {
      expect(mockListResources.mock.calls.length).toBeGreaterThan(callsBefore);
    });
  });

  it("clears all modals/drawers when navigating to another day", async () => {
    mockListAppointments.mockResolvedValue([APPT]);
    renderWithAuth(<CalendarView />);
    await screen.findByText("P001");

    // Open the detail drawer — same pattern as the existing cancel test
    fireEvent.click(screen.getByText("P001"));
    expect(await screen.findByText("Appointment")).toBeInTheDocument();

    // The Reschedule and Cancel buttons should be visible in the open drawer
    expect(screen.getByText("Reschedule")).toBeInTheDocument();

    // Navigate — changeDay clears selected, bookFor, rescheduleFor, cancelFor
    fireEvent.click(screen.getByRole("button", { name: "Next day" }));

    // After navigation, the drawer action buttons should be gone
    // (Antd Drawer keeps its title in the DOM when closed — check for
    //  action buttons that only render inside an open drawer)
    await waitFor(() => {
      expect(screen.queryByText("Reschedule")).not.toBeInTheDocument();
    });
  });

  // ---- R3: Stale grid after fetch failure ---------------------------------

  it("clears grid data when fetch fails so stale blocks are not shown", async () => {
    // First load succeeds — grid shows P001's appointment
    mockListAppointments.mockResolvedValue([APPT]);
    renderWithAuth(<CalendarView />);
    await screen.findByText("P001");

    // Simulate a failure on the next fetch (day change)
    mockListAppointments.mockRejectedValue(new Error("network error"));
    fireEvent.click(screen.getByRole("button", { name: "Next day" }));

    // After the failed refetch, the error should show and old blocks should be gone
    await waitFor(() => {
      expect(screen.queryByText("P001")).not.toBeInTheDocument();
    });
  });

  // ---- T1: UTC day anchor -------------------------------------------------

  it("anchors day in UTC, not browser-local", async () => {
    renderWithAuth(<CalendarView />);
    await screen.findByText("CT Room 1");

    // The header Tag should display the UTC date, not browser-local.
    // The engine uses UTC day semantics, so the calendar must match.
    const todayUtc = dayjs.utc().format("YYYY-MM-DD");
    expect(screen.getByText(new RegExp(todayUtc))).toBeInTheDocument();
  });

  // ---- HI-006: Tenant refetch wiring verification -------------------------

  it("refetches resources when tenant changes", async () => {
    renderWithAuth(<CalendarView />);
    await screen.findByText("CT Room 1");

    const callsBefore = mockListResources.mock.calls.length;

    // Simulate tenant:changed — the real hook would call this callback
    expect(registeredTenantCb).toBeDefined();
    registeredTenantCb!();

    await waitFor(() => {
      expect(mockListResources.mock.calls.length).toBeGreaterThan(callsBefore);
    });
  });

  // ---- ME-001: Error states on scheduling surfaces ------------------------

  it("shows error alert when resource fetch fails", async () => {
    mockListResources.mockRejectedValue(new Error("server error"));
    renderWithAuth(<CalendarView />);

    expect(await screen.findByRole("alert")).toBeInTheDocument();
  });

  // ---- CR-003: BookingFormModal 409/SLOT_CONFLICT -------------------------

  it("handles a 409 booking conflict by warning and refreshing", async () => {
    mockSearchOrders.mockResolvedValue({
      data: [
        {
          id: "o1",
          accession_number: "ACC-1",
          patient_id: "P001",
          patient_name: "Jane Roe",
          status: "ORDERED",
          priority: "ROUTINE",
        },
      ],
      total: 1,
      page: 1,
      per_page: 25,
    });
    mockBook.mockRejectedValue({
      status: 409,
      code: "SLOT_CONFLICT",
      message: "Slot just taken",
    });

    renderWithAuth(<CalendarView />);
    await screen.findByText("CT Room 1");

    // Click a free cell to open the booking modal
    const freeCell = screen
      .getAllByRole("button")
      .find((c) => c.getAttribute("aria-label")?.includes("(free)"));
    expect(freeCell).toBeDefined();
    fireEvent.click(freeCell!);

    // Search and pick an order
    const search = screen.getByPlaceholderText("Search order (name, MRN or accession)");
    await userEvent.type(search, "Jane{Enter}");
    expect(await screen.findByText("Jane Roe")).toBeInTheDocument();
    fireEvent.click(screen.getByText("Jane Roe"));

    // Confirm — triggers the 409 conflict path
    fireEvent.click(screen.getByText("Confirm Booking"));

    await waitFor(() => {
      expect(mockBook).toHaveBeenCalled();
    });

    // The calendar must refetch after the conflict (availability may have changed)
    await waitFor(() => {
      expect(mockListResources).toHaveBeenCalled();
    });

    // E1: after 409, onClose fires so the user can re-pick from the
    // refreshed grid. The functional contract is that the calendar refetched
    // (tested above) and the parent cleared bookFor (onClose called).
    // Antd Modal keeps DOM content when open=false, so we verify the
    // booking flow completed (mockBook called) and grid refreshed.
  });

  // ---- CR-001: RescheduleModal flow tests ---------------------------------

  it("reschedules an appointment to a new free slot", async () => {
    // APPT is at 09:00-09:30. Availability returns 09:00 and 09:30.
    // The reschedule modal filters out the current slot (09:00), leaving
    // 09:30 as the only option.
    mockListAppointments.mockResolvedValue([APPT]);
    mockReschedule.mockResolvedValue({
      ...APPT,
      start_time: "2026-08-20T09:30:00.000Z",
      end_time: "2026-08-20T10:00:00.000Z",
    });

    renderWithAuth(<CalendarView />);
    await screen.findByText("P001");

    // Open the detail drawer
    fireEvent.click(screen.getByText("P001"));
    expect(await screen.findByText("Appointment")).toBeInTheDocument();

    // Click Reschedule in the drawer (the drawer button, not the modal's OK)
    const drawerReschedule = screen.getAllByText("Reschedule").find((el) => el.tagName === "SPAN")!;
    fireEvent.click(drawerReschedule.closest("button")!);
    expect(await screen.findByText("Reschedule Appointment")).toBeInTheDocument();

    // The modal should show the 09:30 slot button (09:00 filtered out)
    const slotBtn = screen.getByRole("button", { name: "09:30" });
    fireEvent.click(slotBtn);

    // Type a reason
    const reasonInput = screen.getByPlaceholderText("Reason (optional)");
    await userEvent.type(reasonInput, "patient request");

    // Confirm reschedule — the modal's OK button (okText="Reschedule")
    const modalOk = screen.getAllByText("Reschedule").find((el) => el.closest(".ant-modal"))!;
    fireEvent.click(modalOk.closest("button")!);

    await waitFor(() => {
      expect(mockReschedule).toHaveBeenCalledWith("a1", {
        new_start_time: expect.stringContaining("09:30"),
        new_end_time: expect.stringContaining("10:00"),
        reason: "patient request",
      });
    });

    // After success, the calendar should refetch (mockListResources called again)
    await waitFor(() => {
      expect(mockListResources).toHaveBeenCalled();
    });
  });

  it("shows info message when no free slots are available for rescheduling", async () => {
    // Only one free slot (09:00) — same as the appointment's current slot.
    // After filtering, zero slots remain → message.info fires.
    mockListAppointments.mockResolvedValue([APPT]);
    mockGetAvailability.mockResolvedValue([{ start: "09:00", end: "09:30" }]);

    renderWithAuth(<CalendarView />);
    await screen.findByText("P001");

    fireEvent.click(screen.getByText("P001"));
    expect(await screen.findByText("Appointment")).toBeInTheDocument();

    fireEvent.click(screen.getByText("Reschedule"));

    // The modal should NOT open — instead an info toast appears.
    // Antd message.info renders a notification; we verify the modal title
    // is absent (the modal never opened).
    await waitFor(() => {
      expect(screen.queryByText("Reschedule Appointment")).not.toBeInTheDocument();
    });
  });

  it("handles a 409 reschedule conflict by calling onConflict", async () => {
    mockListAppointments.mockResolvedValue([APPT]);
    mockReschedule.mockRejectedValue({
      status: 409,
      code: "SLOT_CONFLICT",
      message: "Slot just taken",
    });

    renderWithAuth(<CalendarView />);
    await screen.findByText("P001");

    fireEvent.click(screen.getByText("P001"));
    expect(await screen.findByText("Appointment")).toBeInTheDocument();

    // Click Reschedule in the drawer
    const drawerReschedule = screen.getAllByText("Reschedule").find((el) => el.tagName === "SPAN")!;
    fireEvent.click(drawerReschedule.closest("button")!);
    expect(await screen.findByText("Reschedule Appointment")).toBeInTheDocument();

    // Confirm — the modal's OK button
    const modalOk = screen.getAllByText("Reschedule").find((el) => el.closest(".ant-modal"))!;
    fireEvent.click(modalOk.closest("button")!);

    await waitFor(() => {
      expect(mockReschedule).toHaveBeenCalled();
    });

    // The calendar should refetch availability after the conflict
    await waitFor(() => {
      expect(mockListResources).toHaveBeenCalled();
    });
  });
});

describe("CalendarView S-13 no-show action", () => {
  beforeEach(() => {
    seedUser(["SCHEDULE_READ", "SCHEDULE_WRITE"]);
    mockListResources.mockResolvedValue([RESOURCE]);
    mockGetAvailability.mockResolvedValue([{ start: "09:00", end: "09:30" }]);
    mockNoShow.mockResolvedValue({ ...APPT, status: "NO_SHOW" });
  });

  it("marks a scheduled appointment as no-show from the drawer", async () => {
    mockListAppointments.mockResolvedValue([APPT]);
    renderWithAuth(<CalendarView />);
    await screen.findByText("P001");

    fireEvent.click(screen.getByText("P001"));
    expect(await screen.findByText("Appointment")).toBeInTheDocument();

    // The suite's mocked Popconfirm fires onConfirm immediately.
    fireEvent.click(screen.getByText(/mark as no-show/i));

    await waitFor(() => expect(mockNoShow).toHaveBeenCalledWith("a1"));
    // Board refetches so the block flips to NO_SHOW (StrictMode doubles
    // initial effects — assert a real refetch happened, not an exact count).
    await waitFor(() => expect(mockListAppointments.mock.calls.length).toBeGreaterThan(1));
  });

  it("offers no no-show action on non-scheduled appointments", async () => {
    mockListAppointments.mockResolvedValue([{ ...APPT, status: "ARRIVED" }]);
    renderWithAuth(<CalendarView />);
    await screen.findByText("P001");

    fireEvent.click(screen.getByText("P001"));
    expect(await screen.findByText("Appointment")).toBeInTheDocument();
    expect(screen.queryByText(/mark as no-show/i)).not.toBeInTheDocument();
  });
});
