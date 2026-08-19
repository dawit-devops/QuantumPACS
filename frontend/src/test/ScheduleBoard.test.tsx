import React from "react";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import dayjs from "dayjs";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { AuthProvider } from "../auth/AuthContext";
import { ThemeProvider } from "../common/ThemeProvider";
import ScheduleBoard from "../schedule/ScheduleBoard";

const mockRequest = vi.hoisted(() => vi.fn());
const mockListAppointments = vi.hoisted(() => vi.fn());
const mockGetAvailability = vi.hoisted(() => vi.fn());
const mockCreateAppointment = vi.hoisted(() => vi.fn());
const mockCancelAppointment = vi.hoisted(() => vi.fn());

vi.mock("../helpers", () => ({
  request: mockRequest,
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
}));

vi.mock("../api/frontdesk", () => ({
  listAppointments: mockListAppointments,
  cancelAppointment: mockCancelAppointment,
  getAvailability: mockGetAvailability,
  createAppointment: mockCreateAppointment,
  searchPatients: vi.fn(),
}));

function renderBoard() {
  return render(
    <ThemeProvider>
      <AuthProvider>
        <MemoryRouter initialEntries={["/schedule-board"]}>
          <ScheduleBoard />
        </MemoryRouter>
      </AuthProvider>
    </ThemeProvider>,
  );
}

const mockEntries = [
  {
    id: "1",
    patient_id: "P001",
    patient_name: "John Doe",
    accession_number: "ACC-001",
    modality: "CT",
    station_ae_title: "CT-1",
    scheduled_date: "2026-08-03",
    scheduled_time: "09:00",
    status: "scheduled",
    requested_procedure_desc: "CT Chest",
  },
  {
    id: "2",
    patient_id: "P002",
    patient_name: "Jane Smith",
    accession_number: "ACC-002",
    modality: "MRI",
    station_ae_title: "MR-1",
    scheduled_date: "2026-08-03",
    scheduled_time: "09:30",
    status: "performed",
    study_uid: "1.2.3.4",
    performed_at: "2026-08-03T09:45:00Z",
  },
  {
    id: "3",
    patient_id: "P003",
    patient_name: "Alex Brown",
    accession_number: "ACC-003",
    modality: "CT",
    station_ae_title: "CT-1",
    scheduled_date: "2026-08-03",
    scheduled_time: "14:15",
    status: "cancelled",
  },
];

describe("ScheduleBoard", () => {
  beforeEach(() => {
    localStorage.clear();
    mockRequest.mockReset();
    mockListAppointments.mockReset();
    mockGetAvailability.mockReset();
    mockListAppointments.mockResolvedValue([]);
    mockGetAvailability.mockResolvedValue([]);
  });

  it("renders the board grid with standard modalities and time slots", async () => {
    mockRequest.mockResolvedValue({ data: mockEntries });
    renderBoard();

    await waitFor(() => {
      expect(screen.getByText("Schedule Board")).toBeInTheDocument();
    });

    // Standard modalities per FR-R04-01 rendered as column headers.
    for (const mod of ["CT", "MRI", "PET", "DX", "MG", "US", "FL"]) {
      expect(screen.getByText(mod)).toBeInTheDocument();
    }
    // 08:00–18:00 window: hour labels render on even slots (half-hour cells are
    // visually empty), so the last visible label is 17:00.
    expect(screen.getByText("08:00")).toBeInTheDocument();
    expect(screen.getByText("17:00")).toBeInTheDocument();
  });

  it("places exam blocks in the correct time slots with patient names", async () => {
    mockRequest.mockResolvedValue({ data: mockEntries });
    renderBoard();

    await waitFor(() => {
      expect(screen.getByText("John Doe")).toBeInTheDocument();
    });

    // Exam at 09:00 lands in the first CT cell; 09:30 MRI in its column.
    expect(screen.getByText("Jane Smith")).toBeInTheDocument();
    expect(screen.getByText("Alex Brown")).toBeInTheDocument();
  });

  it("shows per-status stats", async () => {
    mockRequest.mockResolvedValue({ data: mockEntries });
    renderBoard();

    await waitFor(() => {
      expect(screen.getByText("John Doe")).toBeInTheDocument();
    });

    expect(screen.getByText("Total")).toBeInTheDocument();
    expect(screen.getByText("3")).toBeInTheDocument();
    expect(screen.getByText("Scheduled")).toBeInTheDocument();
    expect(screen.getByText("Performed")).toBeInTheDocument();
    expect(screen.getByText("Cancelled")).toBeInTheDocument();
  });

  it("opens the exam detail drawer on block click", async () => {
    mockRequest.mockResolvedValue({ data: mockEntries });
    renderBoard();

    await waitFor(() => {
      expect(screen.getByText("John Doe")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("John Doe"));

    await waitFor(() => {
      expect(screen.getByText("Exam Details")).toBeInTheDocument();
    });
    expect(screen.getByText("CT Chest")).toBeInTheDocument();
  });

  it("navigates to the next day", async () => {
    mockRequest.mockResolvedValue({ data: mockEntries });
    renderBoard();

    await waitFor(() => {
      expect(screen.getByText("John Doe")).toBeInTheDocument();
    });

    // Compute expected dates relative to the real "today" (the component defaults
    // `day` to dayjs()) so the test is date-independent.
    const today = dayjs().format("YYYY-MM-DD");
    const tomorrow = dayjs().add(1, "day").format("YYYY-MM-DD");
    expect(screen.getByText(today)).toBeInTheDocument();

    const nextDay = screen.getByRole("button", { name: "Next day" });
    fireEvent.click(nextDay);

    await waitFor(() => {
      // The date tag moves forward one day.
      expect(screen.getByText(tomorrow)).toBeInTheDocument();
    });
    // Next-day fetch fired with date_to = tomorrow.
    const lastCall = mockRequest.mock.calls[mockRequest.mock.calls.length - 1];
    expect(lastCall[1].query.date_from).toBe(tomorrow);
    expect(lastCall[1].query.date_to).toBe(tomorrow);
  });

  it("shows the empty notice but keeps the grid visible when no entries exist", async () => {
    mockRequest.mockResolvedValue({ data: [] });
    renderBoard();

    await waitFor(() => {
      expect(screen.getByText(/No worklist entries/i)).toBeInTheDocument();
    });
    // Grid stays visible so coordinators can see the empty time slots.
    expect(screen.getByText("08:00")).toBeInTheDocument();
    expect(screen.getByText("CT")).toBeInTheDocument();
  });
});
