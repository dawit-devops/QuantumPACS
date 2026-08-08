import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import { renderWithAuth } from "./renderWithApp";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";
import Portal from "../portal/Portal";

const mockListScope = vi.hoisted(() => vi.fn());
const mockGetPortalPatient = vi.hoisted(() => vi.fn());
const mockGetPortalOrders = vi.hoisted(() => vi.fn());

vi.mock("../api/portal", () => ({
  listScope: mockListScope,
  searchScopedPatients: vi.fn(),
  getPortalPatient: mockGetPortalPatient,
  getPortalOrders: mockGetPortalOrders,
  getPortalReport: vi.fn(),
  listFollowUps: vi.fn(),
  createFollowUp: vi.fn(),
}));

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
  },
  orders: [
    {
      id: "o1",
      requested_procedure: "CT Chest",
      urgency: "stat",
      status: "open",
      created_at: "2026-08-01T10:00:00+00:00",
    },
  ],
  reports: [
    {
      id: "r1",
      accession_number: "ACC-001",
      modality: "CT",
      status: "final",
      impression: "No acute findings",
      signed_at: "2026-08-02T10:00:00+00:00",
    },
  ],
};

describe("Portal", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    seedPatient();
    mockListScope.mockResolvedValue([
      { id: "s1", patient_id: "P001", scope_type: "assigned" },
    ]);
    mockGetPortalPatient.mockResolvedValue(BUNDLE);
    mockGetPortalOrders.mockResolvedValue(BUNDLE.orders);
  });

  it("renders an empty state when no records are shared", async () => {
    mockListScope.mockResolvedValue([]);
    renderWithAuth(<Portal />);
    expect(
      await screen.findByText(/No records are shared with you yet/),
    ).toBeInTheDocument();
  });

  it("renders demographics, orders and reports for the scoped patient", async () => {
    const user = userEvent.setup();
    renderWithAuth(<Portal />);
    expect(await screen.findByText("John Doe")).toBeInTheDocument();
    // Orders tab is active by default.
    expect(await screen.findByText("CT Chest")).toBeInTheDocument();
    // Switch to the Reports tab to see final report impressions.
    await user.click(
      screen.getByRole("tab", { name: /reports \(1\)/i }),
    );
    expect(await screen.findByText("No acute findings")).toBeInTheDocument();
  });

  it("shows a warning when the patient record is out of scope", async () => {
    mockGetPortalPatient.mockResolvedValue(null);
    renderWithAuth(<Portal />);
    expect(
      await screen.findByText(/No records are currently shared for this patient/),
    ).toBeInTheDocument();
  });
});
