import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";

import { renderWithAuth } from "./renderWithApp";
import CalendarView from "../schedule/CalendarView";

const mockListResources = vi.hoisted(() => vi.fn());
const mockListAppointments = vi.hoisted(() => vi.fn());
const mockGetAvailability = vi.hoisted(() => vi.fn());
const mockBook = vi.hoisted(() => vi.fn());
const mockReschedule = vi.hoisted(() => vi.fn());
const mockCancel = vi.hoisted(() => vi.fn());
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

vi.mock("../hooks", () => ({
  useDocumentTitle: vi.fn(),
  useTenantRefetch: () => {},
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
      .getAllByRole("gridcell")
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
});
