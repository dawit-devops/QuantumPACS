import React from "react";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";
import ScheduleToday from "../frontdesk/ScheduleToday";
import { renderWithAuth } from "./renderWithApp";

const mockList = vi.hoisted(() => vi.fn());
const mockCheckIn = vi.hoisted(() => vi.fn());

vi.mock("../api/frontdesk", () => ({
  listRisAppointments: mockList,
}));

vi.mock("../api/scheduling", () => ({
  checkInAppointment: mockCheckIn,
}));

vi.mock("../hooks", () => ({
  useDocumentTitle: vi.fn(),
  useTenantRefetch: () => {},
}));

const ROWS = [
  {
    id: "appt-1",
    status: "SCHEDULED",
    patient_name: "Jane Doe",
    patient_id: "P1",
    modality: "CT",
    room: "CT1",
    start_time: "2026-08-26T10:30:00Z",
    priority: "ROUTINE",
  },
  {
    id: "appt-2",
    status: "ARRIVED",
    patient_name: "John Roe",
    patient_id: "P2",
    modality: "MR",
    room: "MR1",
    start_time: "2026-08-26T11:00:00Z",
    priority: "ROUTINE",
  },
];

function setSession(perms: string[]) {
  localStorage.clear();
  localStorage.setItem("token", "t");
  localStorage.setItem("userId", "u2");
  localStorage.setItem("admin", "false");
  localStorage.setItem("role", "receptionist");
  localStorage.setItem("permissions", JSON.stringify(perms));
}

beforeEach(() => {
  vi.clearAllMocks();
  setSession(["REGISTRATION_READ", "SCHEDULE_WRITE"]);
  mockList.mockResolvedValue(ROWS);
  mockCheckIn.mockResolvedValue({ id: "appt-1", status: "ARRIVED" });
});

describe("ScheduleToday FD-04 one-click check-in", () => {
  it("offers Check-in only on scheduled rows", async () => {
    renderWithAuth(<ScheduleToday />);
    expect(await screen.findByText("Jane Doe")).toBeInTheDocument();

    expect(screen.getByRole("button", { name: /check in/i })).toBeInTheDocument();
    // The already-ARRIVED row has no check-in affordance.
    const buttons = screen.getAllByRole("button", { name: /check in/i });
    expect(buttons).toHaveLength(1);
  });

  it("hides the action without SCHEDULE_WRITE", async () => {
    setSession(["REGISTRATION_READ"]);
    renderWithAuth(<ScheduleToday />);
    await screen.findByText("Jane Doe");
    expect(screen.queryByRole("button", { name: /check in/i })).not.toBeInTheDocument();
  });

  it("posts the check-in and refreshes the board", async () => {
    const user = userEvent.setup();
    renderWithAuth(<ScheduleToday />);
    await screen.findByText("Jane Doe");

    await user.click(screen.getByRole("button", { name: /check in/i }));
    await vi.waitFor(() => expect(mockCheckIn).toHaveBeenCalledWith("appt-1"));
    // Board refetches so the row flips to ARRIVED without a manual reload.
    await vi.waitFor(() => expect(mockList).toHaveBeenCalledTimes(2));
  });

  it("treats a repeat check-in as informational, not an error", async () => {
    mockCheckIn.mockRejectedValue({ status: 409, message: "Already checked in" });
    const user = userEvent.setup();
    renderWithAuth(<ScheduleToday />);
    await screen.findByText("Jane Doe");

    await user.click(screen.getByRole("button", { name: /check in/i }));
    // No crash, board still refreshes to show server truth.
    await vi.waitFor(() => expect(mockList).toHaveBeenCalledTimes(2));
  });
});
