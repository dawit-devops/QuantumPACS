import React from "react";
import {
  render,
  screen,
  waitFor,
  fireEvent,
  within,
} from "@testing-library/react";
import { renderWithAuth } from "./renderWithApp";
import userEvent from "@testing-library/user-event";
import dayjs from "dayjs";
import { describe, it, expect, vi, beforeEach } from "vitest";
import Registration from "../frontdesk/Registration";
import Visits from "../frontdesk/Visits";
import WaitingQueue from "../frontdesk/WaitingQueue";
import AppointmentBooking from "../frontdesk/AppointmentBooking";

const mockSearchPatients = vi.hoisted(() => vi.fn());
const mockCreatePatient = vi.hoisted(() => vi.fn());
const mockCreateVisit = vi.hoisted(() => vi.fn());
const mockListVisits = vi.hoisted(() => vi.fn());
const mockGetVisit = vi.hoisted(() => vi.fn());
const mockListOrders = vi.hoisted(() => vi.fn());
const mockCreateOrder = vi.hoisted(() => vi.fn());
const mockListConsents = vi.hoisted(() => vi.fn());
const mockAttachConsent = vi.hoisted(() => vi.fn());
const mockListInsurance = vi.hoisted(() => vi.fn());
const mockCreateInsurance = vi.hoisted(() => vi.fn());
const mockUpdateVisit = vi.hoisted(() => vi.fn());
const mockGetWaitingQueue = vi.hoisted(() => vi.fn());
const mockGetAvailability = vi.hoisted(() => vi.fn());
const mockCreateAppointment = vi.hoisted(() => vi.fn());

vi.mock("../api/frontdesk", () => ({
  searchPatients: mockSearchPatients,
  createPatient: mockCreatePatient,
  createVisit: mockCreateVisit,
  listVisits: mockListVisits,
  getVisit: mockGetVisit,
  updateVisit: mockUpdateVisit,
  checkInVisit: (id: string) => mockUpdateVisit(id, { status: "checked_in" }),
  listOrders: mockListOrders,
  createOrder: mockCreateOrder,
  listConsents: mockListConsents,
  attachConsent: mockAttachConsent,
  listInsurance: mockListInsurance,
  createInsurance: mockCreateInsurance,
  getAvailability: mockGetAvailability,
  createAppointment: mockCreateAppointment,
  cancelAppointment: vi.fn(),
  getWaitingQueue: mockGetWaitingQueue,
}));

// Real antd Popconfirm renders a portal overlay that needs act() plumbing;
// stub it to invoke onConfirm directly like the Worklist suite does.
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
      children,
    );
  return { ...actual, Popconfirm };
});

vi.mock("../helpers", () => ({
  request: vi.fn(() => Promise.resolve({})),
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
  useVisibilityGatedInterval: () => {},
}));

function seedUser(permissions: string[]) {
  localStorage.setItem("token", "t");
  localStorage.setItem("userId", "u1");
  localStorage.setItem("admin", "false");
  localStorage.setItem("role", "receptionist");
  localStorage.setItem("permissions", JSON.stringify(permissions));
}

const PATIENT = {
  id: 1,
  patient_id: "P001",
  name: "John Doe",
  birth_date: "1980-05-15",
  sex: "M",
};

describe("Registration", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    seedUser(["REGISTRATION_READ", "REGISTRATION_WRITE", "SCHEDULE_WRITE"]);
    mockSearchPatients.mockResolvedValue([]);
    mockCreatePatient.mockResolvedValue(PATIENT);
    mockCreateVisit.mockResolvedValue({
      id: "v1",
      patient_id: "P001",
      status: "registered",
    });
  });

  it("searches patients on submit and shows a dedup banner when none match", async () => {
    const user = userEvent.setup();
    renderWithAuth(<Registration />);
    await user.type(screen.getByPlaceholderText(/Search name or MRN/), "Jo");
    await user.click(screen.getByRole("button", { name: /search/i }));
    await waitFor(() => expect(mockSearchPatients).toHaveBeenCalledWith("Jo"));
    expect(
      await screen.findByText(/No existing patient matched/),
    ).toBeInTheDocument();
  });

  it("shows matching patients and offers to use the existing record", async () => {
    mockSearchPatients.mockResolvedValue([PATIENT]);
    const user = userEvent.setup();
    renderWithAuth(<Registration />);
    await user.type(screen.getByPlaceholderText(/Search name or MRN/), "Jo");
    await user.click(screen.getByRole("button", { name: /search/i }));
    expect(await screen.findByText("John Doe")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /use this patient/i }));
    expect(await screen.findByText(/Selected John Doe/)).toBeInTheDocument();
  });

  it("registers a new patient and opens a visit", async () => {
    const user = userEvent.setup();
    renderWithAuth(<Registration />);
    await user.type(screen.getByLabelText("Full name"), "Jane Roe");
    await user.type(
      screen.getByLabelText("MRN / Patient ID (optional)"),
      "P099",
    );
    await user.click(
      screen.getByRole("button", { name: /register & open visit/i }),
    );
    await waitFor(() => {
      expect(mockCreatePatient).toHaveBeenCalledWith(
        expect.objectContaining({ name: "Jane Roe", patient_id: "P099" }),
      );
      // The visit opens against the server-returned patient id (P001 fixture).
      expect(mockCreateVisit).toHaveBeenCalledWith(
        expect.objectContaining({ patient_id: "P001" }),
      );
    });
  });

  it("hides write affordances for a read-only user", async () => {
    seedUser(["REGISTRATION_READ"]);
    renderWithAuth(<Registration />);
    expect(screen.getByText(/Read-only registration/)).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /register new patient/i }),
    ).toBeNull();
  });
});

describe("Visits & Check-In", () => {
  const VISIT = {
    id: "v1",
    patient_id: "P001",
    visit_date: "2026-08-08",
    status: "registered",
    destination_room: "CT1",
    hl7_sync_status: "pending",
  };

  beforeEach(() => {
    vi.clearAllMocks();
    seedUser(["REGISTRATION_READ", "REGISTRATION_WRITE"]);
    mockListVisits.mockResolvedValue({
      data: [VISIT],
      total: 1,
      page: 1,
      per_page: 20,
    });
    mockGetVisit.mockResolvedValue(VISIT);
    mockListOrders.mockResolvedValue([]);
    mockListConsents.mockResolvedValue([]);
    mockListInsurance.mockResolvedValue([]);
    mockUpdateVisit.mockResolvedValue(undefined);
    mockCreateOrder.mockResolvedValue({});
    mockAttachConsent.mockResolvedValue({});
    mockCreateInsurance.mockResolvedValue({});
  });

  it("lists visits and lets the user check one in", async () => {
    const user = userEvent.setup();
    renderWithAuth(<Visits />);
    expect(await screen.findByText("P001")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /check in/i }));
    await waitFor(() => {
      expect(mockUpdateVisit).toHaveBeenCalledWith("v1", {
        status: "checked_in",
      });
    });
  });

  it("opens the detail drawer with orders, consents and insurance sections", async () => {
    const user = userEvent.setup();
    renderWithAuth(<Visits />);
    expect(await screen.findByText("P001")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /details/i }));
    expect(await screen.findByText(/Orders/)).toBeInTheDocument();
    expect(await screen.findByText(/Consents/)).toBeInTheDocument();
    expect(
      await screen.findByText(/Insurance \/ Guarantor/),
    ).toBeInTheDocument();
  });

  it("adds an order from the drawer", async () => {
    const user = userEvent.setup();
    renderWithAuth(<Visits />);
    expect(await screen.findByText("P001")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /details/i }));
    await user.type(
      await screen.findByPlaceholderText(/CT CHEST W CONTRAST/),
      "CT CHEST W CONTRAST",
    );
    await user.click(screen.getByRole("button", { name: /add order/i }));
    await waitFor(() => {
      expect(mockCreateOrder).toHaveBeenCalledWith(
        "v1",
        expect.objectContaining({ requested_procedure: "CT CHEST W CONTRAST" }),
      );
    });
  });
});

describe("WaitingQueue", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    seedUser(["QUEUE_READ"]);
    mockGetWaitingQueue.mockResolvedValue([
      {
        visit_id: "v1",
        // The payload leaks a full name (a projection bug would surface it):
        // the board must still render initials/last4 only (R4-07).
        name: "John Smith",
        initials: "J.S.",
        last4: "2345",
        status: "checked_in",
        destination: "CT1",
        updated_at: "2026-08-08T10:00:00+00:00",
      },
    ]);
  });

  it("renders the privacy-projected queue and the HIPAA note", async () => {
    renderWithAuth(<WaitingQueue />);
    expect(await screen.findByText(/J\.S\./)).toBeInTheDocument();
    expect(screen.getByText(/· · · · 2345/)).toBeInTheDocument();
    expect(screen.getByText(/HIPAA minimum necessary/)).toBeInTheDocument();
    // Full names never appear on the board — even when the payload leaks one.
    expect(screen.queryByText(/John Smith/)).toBeNull();
  });

  it("refetches with the selected day when the date changes", async () => {
    const user = userEvent.setup();
    renderWithAuth(<WaitingQueue />);
    expect(await screen.findByText(/J\.S\./)).toBeInTheDocument();

    // Role/label query instead of the brittle .ant-picker CSS class (the
    // input carries the aria-label the component sets on the DatePicker).
    const pickerInput = screen.getByRole("textbox", {
      name: "Queue date",
    }) as HTMLInputElement;
    expect(pickerInput).not.toBeNull();
    await user.click(pickerInput);
    await user.clear(pickerInput);
    await user.keyboard("2026-08-09");
    await user.keyboard("{Enter}");

    await waitFor(() =>
      expect(mockGetWaitingQueue).toHaveBeenCalledWith({
        date: "2026-08-09",
      }),
    );
  });

  it("surfaces a load failure with a working Retry", async () => {
    const user = userEvent.setup();
    mockGetWaitingQueue.mockRejectedValue({ message: "Network down" });
    renderWithAuth(<WaitingQueue />);

    expect(await screen.findByText("Failed to load queue")).toBeInTheDocument();
    expect(screen.getByText("Network down")).toBeInTheDocument();

    mockGetWaitingQueue.mockResolvedValue([
      {
        visit_id: "v1",
        initials: "J.S.",
        last4: "2345",
        status: "checked_in",
      },
    ]);
    await user.click(screen.getByRole("button", { name: /retry/i }));
    expect(await screen.findByText(/J\.S\./)).toBeInTheDocument();
  });

  it("renders the empty state for a day with no waiting patients", async () => {
    mockGetWaitingQueue.mockResolvedValue([]);
    renderWithAuth(<WaitingQueue />);
    const today = dayjs().format("YYYY-MM-DD");
    expect(
      await screen.findByText(`No patients waiting on ${today}`),
    ).toBeInTheDocument();
  });

  it("fetches the queue once on mount (interval behavior lives in the hook)", async () => {
    renderWithAuth(<WaitingQueue />);
    await screen.findByText(/J\.S\./);
    expect(mockGetWaitingQueue).toHaveBeenCalledTimes(1);
  });

  it("color-codes the wait badge by minutes since check-in", async () => {
    // FD-05: green <15m, amber 15-30m, red >30m.
    mockGetWaitingQueue.mockResolvedValue([
      {
        visit_id: "v1", initials: "A.B.", last4: "1111",
        status: "checked_in", destination: "CT1",
        updated_at: "2026-08-08T10:00:00+00:00", wait_minutes: 12,
      },
      {
        visit_id: "v2", initials: "C.D.", last4: "2222",
        status: "checked_in", destination: "MR1",
        updated_at: "2026-08-08T10:00:00+00:00", wait_minutes: 22,
      },
      {
        visit_id: "v3", initials: "E.F.", last4: "3333",
        status: "checked_in", destination: "XR1",
        updated_at: "2026-08-08T10:00:00+00:00", wait_minutes: 45,
      },
    ]);
    renderWithAuth(<WaitingQueue />);
    await screen.findByText(/A\.B\./);
    expect(screen.getByText("12m")).toHaveClass("fd-wait-green");
    expect(screen.getByText("22m")).toHaveClass("fd-wait-amber");
    expect(screen.getByText("45m")).toHaveClass("fd-wait-red");
  });
});

describe("AppointmentBooking", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    seedUser(["SCHEDULE_WRITE"]);
    mockGetAvailability.mockResolvedValue([
      { time: "09:00", capacity: 2, booked: 0, state: "free" },
      { time: "09:30", capacity: 2, booked: 2, state: "full" },
    ]);
    mockCreateAppointment.mockResolvedValue({ id: "a1" });
  });

  it("renders free slots enabled and full slots disabled", async () => {
    renderWithAuth(
      <AppointmentBooking
        open
        onClose={() => {}}
        patientId="P001"
        patientName="John Doe"
      />,
    );
    const freeSlot = await screen.findByRole("gridcell", {
      name: /09:00/,
    });
    const fullSlot = screen.getByRole("gridcell", { name: /09:30/ });
    expect(freeSlot).toBeEnabled();
    expect(fullSlot).toBeDisabled();
  });

  it("books the selected slot for the patient", async () => {
    const user = userEvent.setup();
    renderWithAuth(
      <AppointmentBooking
        open
        onClose={() => {}}
        patientId="P001"
        patientName="John Doe"
      />,
    );
    await screen.findByRole("gridcell", { name: /09:00/ });
    await user.click(screen.getByRole("gridcell", { name: /09:00/ }));
    await user.click(screen.getByRole("button", { name: /confirm booking/i }));
    await waitFor(() => {
      expect(mockCreateAppointment).toHaveBeenCalledWith(
        expect.objectContaining({
          patient_id: "P001",
          scheduled_time: "09:00:00",
        }),
      );
    });
  });

  it("surfaces a 409 slot conflict and keeps the modal open", async () => {
    mockCreateAppointment.mockRejectedValue({
      code: "SLOT_CONFLICT",
      status: 409,
      message: "Slot already booked",
    });
    const user = userEvent.setup();
    const onClose = vi.fn();
    const onBooked = vi.fn();
    renderWithAuth(
      <AppointmentBooking
        open
        onClose={onClose}
        onBooked={onBooked}
        patientId="P001"
        patientName="John Doe"
      />,
    );
    await screen.findByRole("gridcell", { name: /09:00/ });
    await user.click(screen.getByRole("gridcell", { name: /09:00/ }));
    await user.click(screen.getByRole("button", { name: /confirm booking/i }));
    // The backend 409 message surfaces in the conflict alert.
    expect(await screen.findByText(/Slot already booked/)).toBeInTheDocument();
    // Availability reloads after the conflict.
    await waitFor(() =>
      expect(mockGetAvailability.mock.calls.length).toBeGreaterThan(1),
    );
    // The modal must STAY open with the refreshed grid: closing it or firing
    // onBooked here would drop the booking attempt (R4-06).
    expect(screen.getByText("Book Appointment")).toBeInTheDocument();
    expect(onClose).not.toHaveBeenCalled();
    expect(onBooked).not.toHaveBeenCalled();
    expect(screen.getByRole("gridcell", { name: /09:00/ })).toBeInTheDocument();
  });

  it("keeps the modal open on a non-conflict booking failure", async () => {
    mockCreateAppointment.mockRejectedValue(new Error("Network down"));
    const user = userEvent.setup();
    const onClose = vi.fn();
    const onBooked = vi.fn();
    renderWithAuth(
      <AppointmentBooking
        open
        onClose={onClose}
        onBooked={onBooked}
        patientId="P001"
        patientName="John Doe"
      />,
    );
    await screen.findByRole("gridcell", { name: /09:00/ });
    await user.click(screen.getByRole("gridcell", { name: /09:00/ }));
    await user.click(screen.getByRole("button", { name: /confirm booking/i }));
    // The generic failure surfaces as a toast, not a conflict banner...
    expect(await screen.findByText("Network down")).toBeInTheDocument();
    expect(screen.queryByText(/Slot already booked/)).not.toBeInTheDocument();
    // ...and the attempt is recoverable: modal open, no success signals.
    expect(screen.getByText("Book Appointment")).toBeInTheDocument();
    expect(onClose).not.toHaveBeenCalled();
    expect(onBooked).not.toHaveBeenCalled();
  });

  it("closes the modal and clears the selection on success", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    const onBooked = vi.fn();
    renderWithAuth(
      <AppointmentBooking
        open
        onClose={onClose}
        onBooked={onBooked}
        patientId="P001"
        patientName="John Doe"
      />,
    );
    const freeSlot = await screen.findByRole("gridcell", { name: /09:00/ });
    await user.click(freeSlot);
    await user.click(screen.getByRole("button", { name: /confirm booking/i }));
    await waitFor(() => expect(onBooked).toHaveBeenCalledTimes(1));
    expect(onClose).toHaveBeenCalledTimes(1);
    // The slot grid selection clears so a re-open starts fresh.
    await waitFor(() =>
      expect(screen.getByRole("gridcell", { name: /09:00/ })).toHaveAttribute(
        "aria-pressed",
        "false",
      ),
    );
  });
});
