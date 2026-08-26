import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import { renderWithAuth } from "./renderWithApp";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { Route, Routes } from "react-router";
import PortalHome from "../portal/PortalHome";
import PatientProfile from "../portal/PatientProfile";
import ReportDetail from "../portal/ReportDetail";
import AppointmentList from "../portal/AppointmentList";
import ReportList from "../portal/ReportList";
import FollowUpHub from "../portal/FollowUpHub";

// --- Mocks ---

const mockListScope = vi.hoisted(() => vi.fn());
const mockGetPortalPatient = vi.hoisted(() => vi.fn());
const mockGetPortalOrders = vi.hoisted(() => vi.fn());
const mockGetPortalReport = vi.hoisted(() => vi.fn());
const mockListFollowUps = vi.hoisted(() => vi.fn());
const mockCreateFollowUp = vi.hoisted(() => vi.fn());
const mockUpdateFollowUp = vi.hoisted(() => vi.fn());
const mockGetPortalAppointments = vi.hoisted(() => vi.fn());
const mockUpdateConsent = vi.hoisted(() => vi.fn());

vi.mock("../api/portal", () => ({
  listScope: mockListScope,
  searchScopedPatients: vi.fn(),
  getPortalPatient: mockGetPortalPatient,
  getPortalOrders: mockGetPortalOrders,
  getPortalReport: mockGetPortalReport,
  listFollowUps: mockListFollowUps,
  createFollowUp: mockCreateFollowUp,
  updateFollowUp: mockUpdateFollowUp,
  getPortalAppointments: mockGetPortalAppointments,
  updateConsent: mockUpdateConsent,
}));

vi.mock("../helpers", () => ({
  request: vi.fn(() => Promise.resolve({})),
  isAdmin: () => false,
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

function seedPatient() {
  localStorage.setItem("token", "t");
  localStorage.setItem("userId", "u1");
  localStorage.setItem("admin", "false");
  localStorage.setItem("role", "patient");
  localStorage.setItem(
    "permissions",
    JSON.stringify(["PORTAL_READ", "CHART_READ", "RESULTS_READ"]),
  );
}

const BUNDLE = {
  patient: {
    id: 1,
    patient_id: "P001",
    name: "John Doe",
    birth_date: "1980-05-15",
    sex: "M",
    phone: "(555) 123-4567",
    email: "john@example.com",
    consent_status: "true",
  },
  orders: [
    {
      id: "o1",
      requested_procedure: "CT Chest",
      urgency: "stat",
      status: "scheduled",
      created_at: "2026-08-28T10:00:00+00:00",
    },
    {
      id: "o2",
      requested_procedure: "MR Brain",
      urgency: "routine",
      status: "completed",
      created_at: "2026-08-15T10:00:00+00:00",
    },
  ],
  reports: [
    {
      id: "r1",
      exam_id: "e1",
      accession_number: "ACC-001",
      modality: "CT",
      requested_procedure_desc: "CT Chest",
      status: "final",
      impression: "No acute findings",
      signed_by_name: "Dr. Smith",
      signed_at: "2026-08-22T10:00:00+00:00",
    },
  ],
};

const REPORT_DETAIL = {
  report_id: "r1",
  exam_id: "e1",
  accession_number: "ACC-001",
  findings: "The lungs are clear. No pleural effusion.",
  impression: "No acute cardiopulmonary process.",
  recommendations: "Follow up in 6 months.",
  signed_by: "Dr. Smith",
  signed_at: "2026-08-22T10:00:00+00:00",
};

const FOLLOWUPS = [
  {
    id: "f1",
    patient_id: "P001",
    reason: "Question about CT results",
    status: "submitted",
    created_at: "2026-08-23T10:00:00+00:00",
  },
  {
    id: "f2",
    patient_id: "P001",
    reason: "Request appointment",
    status: "completed",
    created_at: "2026-08-20T10:00:00+00:00",
  },
];

const APPOINTMENTS = [
  {
    id: "appt-1",
    patient_id: "P001",
    start_time: "2026-08-28T10:30:00+00:00",
    end_time: "2026-08-28T11:00:00+00:00",
    status: "SCHEDULED",
    modality: "CT",
    room: "CT-1",
    prep_instructions: "Fast for 4 hours before your exam",
    procedure: "CT Chest with Contrast",
    priority: "ROUTINE",
    accession_number: "ACC-002",
  },
];

const HISTORY_APPOINTMENTS = [
  {
    id: "appt-9",
    patient_id: "P001",
    start_time: "2026-08-15T09:00:00+00:00",
    end_time: "2026-08-15T09:30:00+00:00",
    status: "COMPLETED",
    modality: "MR",
    room: "MR-2",
    prep_instructions: "",
    procedure: "MR Brain",
    priority: "ROUTINE",
    accession_number: "ACC-001",
    report_id: "r1",
  },
  {
    id: "appt-10",
    patient_id: "P001",
    start_time: "2026-08-20T10:00:00+00:00",
    end_time: "2026-08-20T10:30:00+00:00",
    status: "CANCELLED",
    modality: "CT",
    room: "CT-1",
    prep_instructions: "",
    procedure: "CT Abdomen",
    priority: "URGENT",
    accession_number: "ACC-003",
    report_id: null,
  },
];

const ARRIVED_APPOINTMENTS = [
  {
    id: "appt-7",
    patient_id: "P001",
    start_time: "2026-08-28T10:30:00+00:00",
    end_time: "2026-08-28T11:00:00+00:00",
    status: "ARRIVED",
    modality: "CT",
    room: "CT-1",
    prep_instructions: "",
    procedure: "CT Chest",
    priority: "ROUTINE",
    accession_number: "ACC-005",
  },
];

// ========================================================================
// PortalHome tests
// ========================================================================

describe("PortalHome", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    seedPatient();
    mockListScope.mockResolvedValue([
      { id: "s1", patient_id: "P001", scope_type: "assigned" },
    ]);
    mockGetPortalPatient.mockResolvedValue(BUNDLE);
    mockGetPortalOrders.mockResolvedValue(BUNDLE.orders);
    mockGetPortalAppointments.mockResolvedValue(APPOINTMENTS);
  });

  it("renders empty state when no records are shared", async () => {
    mockListScope.mockResolvedValue([]);
    renderWithAuth(<PortalHome />);
    expect(
      await screen.findByText(/No records are shared with you yet/),
    ).toBeInTheDocument();
  });

  it("renders dashboard with patient info and imaging summary", async () => {
    renderWithAuth(<PortalHome />);
    expect(await screen.findByText("John Doe")).toBeInTheDocument();
    expect(screen.getByText("P001")).toBeInTheDocument();
    expect(screen.getByText("1980-05-15")).toBeInTheDocument();
    expect(screen.getByText("M")).toBeInTheDocument();
  });

  it("renders upcoming appointments card", async () => {
    renderWithAuth(<PortalHome />);
    await waitFor(() => {
      expect(screen.getByText("CT Chest with Contrast")).toBeInTheDocument();
    });
    expect(screen.getByText(/Room: CT-1/)).toBeInTheDocument();
  });

  it("renders recent results card", async () => {
    renderWithAuth(<PortalHome />);
    await waitFor(() => {
      expect(screen.getByText("CT Chest")).toBeInTheDocument();
    });
  });

  it("renders quick action buttons", async () => {
    renderWithAuth(<PortalHome />);
    expect(
      await screen.findByText("Request Follow-up"),
    ).toBeInTheDocument();
    expect(screen.getByText("View Records")).toBeInTheDocument();
    expect(screen.getByText("View Appointments")).toBeInTheDocument();
  });

  it("renders imaging summary", async () => {
    renderWithAuth(<PortalHome />);
    await waitFor(() => {
      expect(screen.getByText("My Imaging Summary")).toBeInTheDocument();
    });
    expect(screen.getByText("Total Reports")).toBeInTheDocument();
  });

  it("shows error state on API failure", async () => {
    mockGetPortalPatient.mockRejectedValue(new Error("Network error"));
    renderWithAuth(<PortalHome />);
    await waitFor(() => {
      expect(screen.getByText(/Some data could not be loaded|Failed to load/)).toBeInTheDocument();
    });
  });
});

// ========================================================================
// PatientProfile tests
// ========================================================================

describe("PatientProfile", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    seedPatient();
    mockListScope.mockResolvedValue([
      { id: "s1", patient_id: "P001", scope_type: "assigned" },
    ]);
    mockGetPortalPatient.mockResolvedValue(BUNDLE);
  });

  it("renders read-only demographics", async () => {
    renderWithAuth(<PatientProfile />);
    expect(await screen.findByText("John Doe")).toBeInTheDocument();
    expect(screen.getByText("P001")).toBeInTheDocument();
    expect(screen.getByText("1980-05-15")).toBeInTheDocument();
    expect(screen.getByText("M")).toBeInTheDocument();
    // S8: phone/email from the demographics bundle (not placeholders).
    expect(screen.getByText("(555) 123-4567")).toBeInTheDocument();
    expect(screen.getByText("john@example.com")).toBeInTheDocument();
  });

  it("shows read-only tag", async () => {
    renderWithAuth(<PatientProfile />);
    expect(
      await screen.findByText(/Read-only/),
    ).toBeInTheDocument();
  });

  it("renders consent management section", async () => {
    renderWithAuth(<PatientProfile />);
    expect(
      await screen.findByText("Consent Management"),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Share imaging results via portal/),
    ).toBeInTheDocument();
  });

  it("shows consent toggle", async () => {
    renderWithAuth(<PatientProfile />);
    await waitFor(() => {
      const switches = screen.getAllByRole("switch");
      expect(switches.length).toBeGreaterThanOrEqual(1);
    });
  });

  it("opens consent withdrawal modal when toggling off", async () => {
    const user = userEvent.setup();
    renderWithAuth(<PatientProfile />);
    await waitFor(() => {
      const switches = screen.getAllByRole("switch");
      expect(switches.length).toBeGreaterThanOrEqual(1);
    });
    // First switch is the consent toggle (second is the disabled appointments one)
    const switches = screen.getAllByRole("switch");
    const consentSwitch = switches[0];
    await user.click(consentSwitch);
    expect(
      screen.getByText("Withdraw Consent for Results Sharing"),
    ).toBeInTheDocument();
  });

  it("calls updateConsent with false on withdrawal confirm", async () => {
    const user = userEvent.setup();
    mockUpdateConsent.mockResolvedValue({
      patient_id: "P001",
      consent_results: false,
    });
    renderWithAuth(<PatientProfile />);
    await waitFor(() => {
      const switches = screen.getAllByRole("switch");
      expect(switches.length).toBeGreaterThanOrEqual(1);
    });
    // Consent defaults ON when reports are visible (BUNDLE has reports) —
    // clicking it withdraws, then confirming calls the endpoint.
    const consentSwitch = screen.getAllByRole("switch")[0];
    await user.click(consentSwitch);
    await waitFor(() => {
      expect(
        screen.getByText("Withdraw Consent for Results Sharing"),
      ).toBeInTheDocument();
    });
    await user.click(screen.getByText("Yes, Withdraw Consent"));
    await waitFor(() => {
      expect(mockUpdateConsent).toHaveBeenCalledWith("P001", false, true);
    });
  });
});

// ========================================================================
// ReportDetail tests
// ========================================================================

describe("ReportDetail", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    seedPatient();
    mockListScope.mockResolvedValue([
      { id: "s1", patient_id: "P001", scope_type: "assigned" },
    ]);
    mockGetPortalReport.mockResolvedValue(REPORT_DETAIL);
  });

  it("renders report findings", async () => {
    renderWithAuth(
      <Routes>
        <Route path="/portal/results/:reportId" element={<ReportDetail />} />
      </Routes>,
      { initialEntries: ["/portal/results/r1"] },
    );
    expect(
      await screen.findByText(/The lungs are clear/),
    ).toBeInTheDocument();
  });

  it("renders impression", async () => {
    renderWithAuth(
      <Routes>
        <Route path="/portal/results/:reportId" element={<ReportDetail />} />
      </Routes>,
      { initialEntries: ["/portal/results/r1"] },
    );
    expect(
      await screen.findByText(/No acute cardiopulmonary process/),
    ).toBeInTheDocument();
  });

  it("renders recommendations", async () => {
    renderWithAuth(
      <Routes>
        <Route path="/portal/results/:reportId" element={<ReportDetail />} />
      </Routes>,
      { initialEntries: ["/portal/results/r1"] },
    );
    expect(
      await screen.findByText(/Follow up in 6 months/),
    ).toBeInTheDocument();
  });

  it("renders signing info", async () => {
    renderWithAuth(
      <Routes>
        <Route path="/portal/results/:reportId" element={<ReportDetail />} />
      </Routes>,
      { initialEntries: ["/portal/results/r1"] },
    );
    expect(await screen.findByText("Dr. Smith")).toBeInTheDocument();
    expect(screen.getAllByText("ACC-001").length).toBeGreaterThan(0);
  });

  it("shows 404 when report not found", async () => {
    mockGetPortalReport.mockResolvedValue(null);
    renderWithAuth(
      <Routes>
        <Route path="/portal/results/:reportId" element={<ReportDetail />} />
      </Routes>,
      { initialEntries: ["/portal/results/r999"] },
    );
    expect(
      await screen.findByText(/Report not found/),
    ).toBeInTheDocument();
  });
});

// ========================================================================
// AppointmentList tests
// ========================================================================

describe("AppointmentList", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    seedPatient();
    mockListScope.mockResolvedValue([
      { id: "s1", patient_id: "P001", scope_type: "assigned" },
    ]);
    mockGetPortalAppointments.mockResolvedValue(APPOINTMENTS);
  });

  it("renders upcoming appointments", async () => {
    renderWithAuth(<AppointmentList />);
    expect(
      await screen.findByText("CT Chest with Contrast"),
    ).toBeInTheDocument();
  });

  it("shows modality tag", async () => {
    renderWithAuth(<AppointmentList />);
    await waitFor(() => {
      expect(screen.getByText("CT")).toBeInTheDocument();
    });
  });

  it("shows priority tags", async () => {
    renderWithAuth(<AppointmentList />);
    await waitFor(() => {
      expect(screen.getByText("routine")).toBeInTheDocument();
    });
  });

  it("shows a checked-in badge for ARRIVED appointments", async () => {
    mockGetPortalAppointments.mockResolvedValue(ARRIVED_APPOINTMENTS);
    renderWithAuth(<AppointmentList />);
    await waitFor(() => {
      expect(
        screen.getByText(/checked in/i),
      ).toBeInTheDocument();
    });
  });

  it("links a completed appointment to its report", async () => {
    mockGetPortalAppointments.mockResolvedValue(HISTORY_APPOINTMENTS);
    renderWithAuth(<AppointmentList />);
    await waitFor(() => {
      expect(screen.getByText("MR Brain")).toBeInTheDocument();
    });
    // Switch to history tab, then the completed row links to the report.
    const historyTab = screen.getByRole("tab", { name: /history/i });
    await userEvent.setup().click(historyTab);
    await waitFor(() => {
      expect(screen.getAllByText("View Report").length).toBeGreaterThan(0);
    });
  });
});

// ========================================================================
// ReportList tests
// ========================================================================

describe("ReportList", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    seedPatient();
    mockListScope.mockResolvedValue([
      { id: "s1", patient_id: "P001", scope_type: "assigned" },
    ]);
    mockGetPortalPatient.mockResolvedValue(BUNDLE);
  });

  it("renders signed reports", async () => {
    renderWithAuth(<ReportList />);
    expect(
      await screen.findByText("ACC-001"),
    ).toBeInTheDocument();
  });

  it("shows report status tag", async () => {
    renderWithAuth(<ReportList />);
    await waitFor(() => {
      expect(screen.getByText("final")).toBeInTheDocument();
    });
  });

  it("shows impression column", async () => {
    renderWithAuth(<ReportList />);
    await waitFor(() => {
      expect(screen.getByText("No acute findings")).toBeInTheDocument();
    });
  });

  it("shows empty state when no reports", async () => {
    mockGetPortalPatient.mockResolvedValue({
      ...BUNDLE,
      reports: [],
    });
    renderWithAuth(<ReportList />);
    expect(
      await screen.findByText(/No signed reports available yet/),
    ).toBeInTheDocument();
  });
});

// ========================================================================
// FollowUpHub tests
// ========================================================================

describe("FollowUpHub", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    seedPatient();
    mockListScope.mockResolvedValue([
      { id: "s1", patient_id: "P001", scope_type: "assigned" },
    ]);
    mockListFollowUps.mockResolvedValue(FOLLOWUPS);
    mockCreateFollowUp.mockResolvedValue({ id: "f3" });
    mockGetPortalAppointments.mockResolvedValue(APPOINTMENTS);
    mockGetPortalPatient.mockResolvedValue(BUNDLE);
  });

  it("renders the request form", async () => {
    renderWithAuth(<FollowUpHub />);
    expect(
      await screen.findByText("New Request"),
    ).toBeInTheDocument();
    expect(screen.getByText("Submit Request")).toBeInTheDocument();
  });

  it("renders existing follow-up requests", async () => {
    renderWithAuth(<FollowUpHub />);
    await waitFor(() => {
      expect(screen.getByText(/Question about CT results/)).toBeInTheDocument();
    });
  });

  it("shows status tags", async () => {
    renderWithAuth(<FollowUpHub />);
    await waitFor(() => {
      expect(screen.getByText("Submitted")).toBeInTheDocument();
      expect(screen.getByText("Completed")).toBeInTheDocument();
    });
  });

  it("submits a new follow-up request", async () => {
    const user = userEvent.setup();
    renderWithAuth(<FollowUpHub />);
    await waitFor(() => {
      expect(screen.getByText("Submit Request")).toBeInTheDocument();
    });

    // Select reason
    const reasonSelect = screen.getByLabelText("Reason for follow-up");
    await user.click(reasonSelect);
    await user.click(screen.getByText("Question about results"));

    // Add note
    const noteInput = screen.getByPlaceholderText(
      /Describe your question/,
    );
    await user.type(noteInput, "What does my CT result mean?");

    // Submit
    await user.click(screen.getByText("Submit Request"));

    await waitFor(() => {
      expect(mockCreateFollowUp).toHaveBeenCalledWith(
        expect.objectContaining({
          patient_id: "P001",
          reason: "result_question",
          note: "What does my CT result mean?",
        }),
      );
    });
  });

  it("shows empty state when no follow-ups", async () => {
    mockListFollowUps.mockResolvedValue([]);
    renderWithAuth(<FollowUpHub />);
    expect(
      await screen.findByText(/No active follow-up requests/),
    ).toBeInTheDocument();
  });

  it("cancels a submitted follow-up via updateFollowUp", async () => {
    const user = userEvent.setup();
    mockUpdateFollowUp.mockResolvedValue(undefined);
    renderWithAuth(<FollowUpHub />);
    await waitFor(() => {
      expect(screen.getByText(/Question about CT results/)).toBeInTheDocument();
    });
    await user.click(screen.getByText("Cancel"));
    // Confirmation modal — target the unique confirm button.
    await waitFor(() => {
      expect(screen.getByText("Yes, cancel")).toBeInTheDocument();
    });
    await user.click(screen.getByText("Yes, cancel"));
    await waitFor(() => {
      expect(mockUpdateFollowUp).toHaveBeenCalledWith("f1", {
        status: "cancelled",
      });
    });
  });

  it("shows linked report and preferred time fields", async () => {
    mockGetPortalAppointments.mockResolvedValue(APPOINTMENTS);
    mockGetPortalPatient.mockResolvedValue(BUNDLE);
    renderWithAuth(<FollowUpHub />);
    await waitFor(() => {
      expect(screen.getByText("New Request")).toBeInTheDocument();
    });
    // The form should have a linked report/appointment selector and a
    // preferred time window field (spec P-05).
    expect(screen.getByText(/Linked report/i)).toBeInTheDocument();
    expect(screen.getByText(/Preferred contact time/i)).toBeInTheDocument();
  });
});
