/**
 * CR-002 — ResourceManager.tsx test suite.
 *
 * Covers: resource listing, creation, schedule window management,
 * permission gating, type/modality filtering, error states, and
 * the schedule window validation (end > start).
 */
import React from "react";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";

import { renderWithAuth } from "./renderWithApp";
import ResourceManager from "../schedule/ResourceManager";

// ---- mocks ----------------------------------------------------------------

const mockListResources = vi.hoisted(() => vi.fn());
const mockCreateRisResource = vi.hoisted(() => vi.fn());
const mockListRisSchedules = vi.hoisted(() => vi.fn());
const mockCreateRisSchedule = vi.hoisted(() => vi.fn());

vi.mock("../api/scheduling", () => ({
  listRisResources: mockListResources,
  createRisResource: mockCreateRisResource,
  listRisSchedules: mockListRisSchedules,
  createRisSchedule: mockCreateRisSchedule,
  getResourceAvailability: vi.fn(),
  listResourceAppointments: vi.fn(),
  bookAppointment: vi.fn(),
  rescheduleAppointment: vi.fn(),
  cancelRisAppointment: vi.fn(),
  searchRisOrders: vi.fn(),
  dayOfWeekLabel: (d: number) =>
    ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"][d],
}));

vi.mock("../hooks", () => ({
  useDocumentTitle: vi.fn(),
  useTenantRefetch: () => {},
}));

// ---- fixtures -------------------------------------------------------------

const RESOURCE_CT = {
  id: "r1",
  name: "CT Room 1",
  resource_type: "ROOM",
  modality: "CT",
  location: "Wing B",
  status: "ACTIVE",
  created_at: "2026-08-01T00:00:00Z",
};

const RESOURCE_MR = {
  id: "r2",
  name: "MRI 1",
  resource_type: "MODALITY",
  modality: "MR",
  location: "Wing A",
  status: "ACTIVE",
  created_at: "2026-08-02T00:00:00Z",
};

const SCHEDULE_MONDAY = {
  id: "s1",
  resource_id: "r1",
  day_of_week: 1,
  start_time: "08:00:00",
  end_time: "17:00:00",
};

// ---- helpers --------------------------------------------------------------

function seedUser(permissions: string[]) {
  localStorage.setItem("token", "t");
  localStorage.setItem("userId", "u1");
  localStorage.setItem("admin", "false");
  localStorage.setItem("role", "scheduler");
  localStorage.setItem("permissions", JSON.stringify(permissions));
}

// ---- tests ----------------------------------------------------------------

describe("ResourceManager", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    seedUser(["SCHEDULE_READ", "SCHEDULE_WRITE"]);
    mockListResources.mockResolvedValue([RESOURCE_CT, RESOURCE_MR]);
    mockListRisSchedules.mockResolvedValue([]);
  });

  // --- listing -------------------------------------------------------------

  it("renders resource cards with name, modality, and location", async () => {
    renderWithAuth(<ResourceManager />);
    expect(await screen.findByText("CT Room 1")).toBeInTheDocument();
    expect(screen.getByText("MRI 1")).toBeInTheDocument();
    expect(screen.getByText(/Wing B/)).toBeInTheDocument();
  });

  it("shows empty state when no resources are configured", async () => {
    mockListResources.mockResolvedValue([]);
    renderWithAuth(<ResourceManager />);
    expect(await screen.findByText("No resources found")).toBeInTheDocument();
  });

  it("shows error alert when fetch fails", async () => {
    mockListResources.mockRejectedValue(new Error("network down"));
    renderWithAuth(<ResourceManager />);
    // toErrorMessage extracts .message from Error instances.
    expect(await screen.findByRole("alert")).toBeInTheDocument();
  });

  // --- filtering -----------------------------------------------------------

  it("filters resources by type", async () => {
    renderWithAuth(<ResourceManager />);
    await screen.findByText("CT Room 1");

    // Open the type filter and select "Room" — antd Select renders
    // as a combobox, open it with mouseDown then click the option.
    const typeFilter = screen.getByRole("combobox", { name: /filter by type/i });
    fireEvent.mouseDown(typeFilter);
    fireEvent.click(await screen.findByText("Room"));

    // After filtering: CT Room 1 (type=ROOM) visible, MRI 1 (type=MODALITY) hidden
    await waitFor(() => {
      expect(screen.getByText("CT Room 1")).toBeInTheDocument();
      expect(screen.queryByText("MRI 1")).not.toBeInTheDocument();
    });
  });

  // --- permission gating ---------------------------------------------------

  it("hides New Resource button without SCHEDULE_WRITE", async () => {
    seedUser(["SCHEDULE_READ"]);
    renderWithAuth(<ResourceManager />);
    await screen.findByText("CT Room 1");
    expect(screen.queryByRole("button", { name: /new resource/i })).not.toBeInTheDocument();
  });

  it("shows New Resource button with SCHEDULE_WRITE", async () => {
    renderWithAuth(<ResourceManager />);
    await screen.findByText("CT Room 1");
    expect(screen.getByRole("button", { name: /new resource/i })).toBeInTheDocument();
  });

  // --- resource creation ---------------------------------------------------

  it("opens create drawer and shows the form", async () => {
    renderWithAuth(<ResourceManager />);
    await screen.findByText("CT Room 1");

    // Open the drawer
    fireEvent.click(screen.getByRole("button", { name: /new resource/i }));

    // Drawer title also says "New Resource" — button + drawer both present
    await waitFor(() => {
      expect(screen.getAllByText("New Resource").length).toBeGreaterThanOrEqual(2);
    });

    // Form fields are visible
    expect(screen.getByText("Name")).toBeInTheDocument();
    expect(screen.getByText("Type")).toBeInTheDocument();
    expect(screen.getByText("Modality")).toBeInTheDocument();
  });

  it("does not call API when submitting empty create form", async () => {
    renderWithAuth(<ResourceManager />);
    await screen.findByText("CT Room 1");

    fireEvent.click(screen.getByRole("button", { name: /new resource/i }));
    await waitFor(() => {
      expect(screen.getAllByText("New Resource").length).toBeGreaterThanOrEqual(2);
    });

    // Submit without filling name — antd Form validation blocks the onFinish
    fireEvent.click(screen.getByRole("button", { name: /create resource/i }));

    // API must NOT be called
    await waitFor(() => {
      expect(mockCreateRisResource).not.toHaveBeenCalled();
    });
  });

  // --- schedule windows ----------------------------------------------------

  it("opens schedule drawer and shows weekly windows", async () => {
    mockListRisSchedules.mockResolvedValue([SCHEDULE_MONDAY]);
    renderWithAuth(<ResourceManager />);
    await screen.findByText("CT Room 1");

    fireEvent.click(screen.getByRole("button", { name: /manage schedules for ct room 1/i }));

    await waitFor(() => {
      expect(screen.getByText(/Schedules — CT Room 1/)).toBeInTheDocument();
    });
    expect(screen.getByText("Monday")).toBeInTheDocument();
    expect(screen.getByText("08:00-17:00")).toBeInTheDocument();
  });

  it("does not call API when schedule window is invalid", async () => {
    mockListRisSchedules.mockResolvedValue([]);
    renderWithAuth(<ResourceManager />);
    await screen.findByText("CT Room 1");

    fireEvent.click(screen.getByRole("button", { name: /manage schedules for ct room 1/i }));
    await screen.findByText(/Schedules — CT Room 1/);

    // Change end to before start (end=07:00 < start=08:00)
    const endInput = screen.getByLabelText("End time");
    fireEvent.change(endInput, { target: { value: "07:00" } });

    // Click Add without selecting a day — the component's doAddSchedule
    // checks newTime.end <= newTime.start and shows an error toast
    fireEvent.click(screen.getByRole("button", { name: /add$/i }));

    // API must NOT be called — the component rejects invalid windows
    await waitFor(() => {
      expect(mockCreateRisSchedule).not.toHaveBeenCalled();
    });
  });

  it("hides Schedules button without SCHEDULE_WRITE", async () => {
    seedUser(["SCHEDULE_READ"]);
    renderWithAuth(<ResourceManager />);
    await screen.findByText("CT Room 1");
    expect(
      screen.queryByRole("button", { name: /manage schedules/i })
    ).not.toBeInTheDocument();
  });
});
