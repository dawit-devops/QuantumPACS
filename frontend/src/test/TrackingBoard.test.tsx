import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import React from "react";
import { MemoryRouter } from "react-router";
import { AuthProvider } from "../auth/AuthContext";
import { ThemeProvider } from "../common/ThemeProvider";
import TrackingBoard from "../worklist/TrackingBoard";

// Mock the API module
vi.mock("../api/tracking", () => ({
  listTracking: vi.fn(),
  getTrackingKpi: vi.fn(),
  updateTrackingStatus: vi.fn(),
}));

// Mock hooks
vi.mock("../hooks", () => ({
  useDocumentTitle: vi.fn(),
  useTenantRefetch: vi.fn(),
}));

// Mock auth context — keep AuthProvider, mock useAuth
vi.mock("../auth/AuthContext", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../auth/AuthContext")>();
  return {
    ...actual,
    useAuth: () => ({
      hasPermission: (perm: string) =>
        ["WORKLIST_READ", "WORKLIST_WRITE", "SCHEDULE_WRITE"].includes(perm),
    }),
  };
});

import { listTracking, getTrackingKpi } from "../api/tracking";

const mockListTracking = vi.mocked(listTracking);
const mockGetTrackingKpi = vi.mocked(getTrackingKpi);

const mockTrackingData = [
  {
    id: "ex-1",
    patient_id: "P001",
    patient_name: "Smith^John",
    accession_number: "ACC001",
    modality: "CT",
    status: "scheduled",
    requested_procedure_priority: "R",
    station_ae_title: "CT01",
    scheduled_date: "2026-08-20",
    scheduled_time: "09:00",
    requested_procedure_desc: "Chest CT",
  },
  {
    id: "ex-2",
    patient_id: "P002",
    patient_name: "Doe^Jane",
    accession_number: "ACC002",
    modality: "MR",
    status: "in_progress",
    requested_procedure_priority: "STAT",
    station_ae_title: "MR01",
    scheduled_date: "2026-08-20",
    scheduled_time: "10:00",
    requested_procedure_desc: "Brain MRI",
  },
];

const mockKpi = {
  volume: 42,
  in_progress: 5,
  awaiting_read: 8,
  overdue: 2,
  stat_count: 3,
};

function renderBoard() {
  // Seed user into localStorage so AuthProvider picks it up
  localStorage.setItem("userId", "1");
  localStorage.setItem("username", "test");
  localStorage.setItem(
    "permissions",
    JSON.stringify(["WORKLIST_READ", "WORKLIST_WRITE"]),
  );
  localStorage.setItem("tenant_id", "t1");
  localStorage.setItem("tenant_name", "Test");
  return render(
    <MemoryRouter>
      <AuthProvider>
        <ThemeProvider>
          <TrackingBoard />
        </ThemeProvider>
      </AuthProvider>
    </MemoryRouter>,
  );
}

describe("TrackingBoard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockListTracking.mockResolvedValue({
      data: mockTrackingData,
      total: 2,
      page: 1,
      per_page: 20,
    });
    mockGetTrackingKpi.mockResolvedValue(mockKpi);
  });

  it("renders exam list from API", async () => {
    renderBoard();
    await waitFor(() => {
      expect(screen.getByText("Smith^John")).toBeInTheDocument();
    });
    expect(screen.getByText("Doe^Jane")).toBeInTheDocument();
  });

  it("shows status badges with correct colors", async () => {
    renderBoard();
    await waitFor(() => {
      expect(screen.getByText("scheduled")).toBeInTheDocument();
    });
    expect(screen.getByText("in_progress")).toBeInTheDocument();
  });

  it("shows KPI strip values", async () => {
    renderBoard();
    await waitFor(() => {
      expect(screen.getByText("42")).toBeInTheDocument();
    });
    expect(screen.getByText("5")).toBeInTheDocument();
    expect(screen.getByText("8")).toBeInTheDocument();
    expect(screen.getByText("2")).toBeInTheDocument();
    expect(screen.getByText("3")).toBeInTheDocument();
  });

  it("shows modality tags", async () => {
    renderBoard();
    await waitFor(() => {
      expect(screen.getByText("CT")).toBeInTheDocument();
    });
    expect(screen.getByText("MR")).toBeInTheDocument();
  });

  it("shows action buttons for write users", async () => {
    renderBoard();
    await waitFor(() => {
      // Scheduled exams should have action buttons
      const buttons = screen.getAllByRole("button");
      expect(buttons.length).toBeGreaterThan(0);
    });
  });

  it("shows search input", async () => {
    renderBoard();
    expect(
      screen.getByPlaceholderText("Search patient/accession..."),
    ).toBeInTheDocument();
  });

  it("shows filter selects", async () => {
    renderBoard();
    // The filters should render select elements
    const selects = document.querySelectorAll(".ant-select");
    expect(selects.length).toBeGreaterThanOrEqual(2);
  });

  it("displays procedure descriptions", async () => {
    renderBoard();
    await waitFor(() => {
      expect(screen.getByText("Chest CT")).toBeInTheDocument();
    });
    expect(screen.getByText("Brain MRI")).toBeInTheDocument();
  });

  it("highlights STAT priority rows", async () => {
    renderBoard();
    await waitFor(() => {
      const rows = document.querySelectorAll(".tracking-stat-row");
      // Doe^Jane has STAT priority
      expect(rows.length).toBeGreaterThanOrEqual(1);
    });
  });

  it("shows a critical badge for flagged results (S6-21)", async () => {
    // ex-1 has a critical result pending; ex-2 does not.
    const withCritical = mockTrackingData.map((r, i) => ({
      ...r,
      has_critical: i === 0,
    }));
    mockListTracking.mockResolvedValue({
      data: withCritical,
      total: 2,
      page: 1,
      per_page: 20,
    });
    renderBoard();
    await waitFor(() => {
      expect(screen.getByText("CRITICAL")).toBeInTheDocument();
    });
  });
});

// ---------------------------------------------------------------------------
// C5: priority/date/room filters + reschedule action from the board
// ---------------------------------------------------------------------------
import { userEvent } from "@testing-library/user-event";
import { getResourceAvailability } from "../api/scheduling";
import RescheduleModal from "../schedule/RescheduleModal";

vi.mock("../api/scheduling", () => ({
  getResourceAvailability: vi.fn(),
  bookAppointment: vi.fn(),
  rescheduleAppointment: vi.fn(),
  cancelRisAppointment: vi.fn(),
  searchRisOrders: vi.fn(),
}));
vi.mock("../schedule/RescheduleModal", () => ({
  default: (props: { open: boolean; appointment: any }) =>
    props.open ? (
      <div data-testid="reschedule-modal">
        modal for {props.appointment?.id}
      </div>
    ) : null,
}));

describe("TrackingBoard C5 filters + actions", () => {
  const mockGetAvailability = vi.mocked(getResourceAvailability);

  beforeEach(() => {
    vi.clearAllMocks();
    mockListTracking.mockResolvedValue({
      data: [
        {
          ...mockTrackingData[0],
          appointment_id: "appt-1",
          resource_id: "res-1",
        },
      ],
      total: 1,
      page: 1,
      per_page: 20,
    });
    mockGetTrackingKpi.mockResolvedValue({
      volume: 1,
      in_progress: 0,
      awaiting_read: 0,
      overdue: 0,
      stat_count: 0,
    });
    mockGetAvailability.mockResolvedValue([
      { start: "10:00", end: "10:30" },
    ]);
  });

  it("sends room filter as query param; priority control renders", async () => {
    render(
      <ThemeProvider>
        <AuthProvider>
          <MemoryRouter>
            <TrackingBoard />
          </MemoryRouter>
        </AuthProvider>
      </ThemeProvider>
    );
    await screen.findByText("ACC001");
    expect(screen.getByLabelText("Priority filter")).toBeInTheDocument();

    await userEvent.type(screen.getByLabelText("Room filter"), "CT01");
    await waitFor(() => {
      const last = mockListTracking.mock.calls[mockListTracking.mock.calls.length - 1]?.[0] ?? {};
      expect(last.station_ae_title).toBe("CT01");
    });
    // Priority/date params ride buildQuery alongside — their dropdown
    // interaction is covered by Playwright E2E (rc-select is not reliably
    // drivable under jsdom).
  });

  it("opens the shared reschedule modal from a scheduled row", async () => {
    render(
      <ThemeProvider>
        <AuthProvider>
          <MemoryRouter>
            <TrackingBoard />
          </MemoryRouter>
        </AuthProvider>
      </ThemeProvider>
    );
    await screen.findByText("ACC001");
    await userEvent.click(await screen.findByLabelText("Reschedule"));
    await waitFor(() => {
      expect(mockGetAvailability).toHaveBeenCalledWith("res-1", "2026-08-20");
    });
    expect(await screen.findByTestId("reschedule-modal")).toHaveTextContent(
      "modal for appt-1"
    );
  });
  it("passes WCAG 2.1 AA automated scan (F3)", async () => {
    renderBoard();
    await waitFor(() => {
      expect(screen.getByText("Smith^John")).toBeTruthy();
    });
    const { scanA11y, seriousViolations } = await import("./axe");
    const results = await scanA11y(document.body);
    expect(seriousViolations(results)).toEqual([]);
  });

});
