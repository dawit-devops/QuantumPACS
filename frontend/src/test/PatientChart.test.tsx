import React from "react";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { App as AntdApp } from "antd";
import { AuthProvider } from "../auth/AuthContext";
import { ThemeProvider } from "../common/ThemeProvider";
import Patient from "../patient/Patient";

const mockRequest = vi.hoisted(() => vi.fn());

vi.mock("../helpers", () => ({
  request: mockRequest,
  isAdmin: () => false,
  setTokens: () => {},
  clearTokens: () => {},
  startRefreshTimer: () => {},
  stopRefreshTimer: () => {},
}));

vi.mock("../hooks", () => ({
  useDocumentTitle: vi.fn(),
  useTenantRefetch: vi.fn(),
}));

// The page pulls the imaging aggregate through its own client.
const mockGetPatient = vi.hoisted(() => vi.fn());
vi.mock("../api/patient", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api/patient")>();
  return { ...actual, getPatient: mockGetPatient };
});

// CS6: encounters ride their own client module.
const mockListEncounters = vi.hoisted(() => vi.fn());
const mockCreateEncounter = vi.hoisted(() => vi.fn());
vi.mock("../api/encounters", () => ({
  listEncounters: mockListEncounters,
  createEncounter: mockCreateEncounter,
}));

vi.mock("../common/base", () => ({
  default: (C: React.ComponentType) => (p: any) => <C {...p} />,
}));

const patientPayload = {
  id: "P1",
  patient_id: "P1",
  name: "Doe^Jane",
  patient_birth_date: "19800101",
  patient_sex: "F",
  reports: [
    {
      id: "rep-1",
      status: "final",
      procedure_desc: "CT Head",
      accession_number: "ACC-1",
      signed_at: "2026-08-20T10:00:00Z",
    },
  ],
  studies: [],
};

function renderChart() {
  return render(
    <AntdApp>
      <ThemeProvider>
        <AuthProvider>
          <MemoryRouter initialEntries={["/patients/P1"]}>
            <Routes>
              <Route path="/patients/:id" element={<Patient />} />
            </Routes>
          </MemoryRouter>
        </AuthProvider>
      </ThemeProvider>
    </AntdApp>,
  );
}

describe("Patient chart tabs (CC-09/CC-10)", () => {
  beforeEach(() => {
    localStorage.clear();
    localStorage.setItem("token", "t");
    localStorage.setItem("userId", "u1");
    localStorage.setItem("admin", "false");
    localStorage.setItem(
      "permissions",
      JSON.stringify([
        "PATIENT_READ",
        "REPORT_READ",
        "ORDER_READ",
        "ENCOUNTER_WRITE",
      ]),
    );
    mockGetPatient.mockReset();
    mockGetPatient.mockResolvedValue(patientPayload);
    mockListEncounters.mockReset();
    mockListEncounters.mockResolvedValue({
      data: [
        {
          id: "enc-1",
          patient_id: "P1",
          encounter_type: "call",
          occurred_at: "2026-08-22T14:30:00Z",
          summary: "Discussed follow-up imaging",
          linked_order_id: "",
          linked_report_id: "",
          recorded_by: "u1",
          tenant_id: "t1",
          created_at: "2026-08-22T14:30:00Z",
        },
      ],
    });
    mockCreateEncounter.mockReset();
    mockCreateEncounter.mockResolvedValue({ data: {} });
    mockRequest.mockReset();
    mockRequest.mockImplementation((url: string) => {
      if (url.startsWith("reports/priors")) {
        return Promise.resolve({
          data: [
            {
              report_id: "rep-9",
              exam_id: "exam-9",
              accession_number: "ACC-9",
              modality: "CT",
              status: "final",
              impression_excerpt: "Old impression text",
              recommendations_excerpt: "Follow up in 6 weeks",
            },
          ],
        });
      }
      if (url.startsWith("ris/orders")) {
        return Promise.resolve({
          data: [
            {
              id: "ro-1",
              accession_number: "ACC-2",
              status: "COMPLETED",
              priority: "routine",
              referring_md: "Dr House",
            },
          ],
        });
      }
      return Promise.resolve({ data: [] });
    });
  });

  it("renders chart tabs with prior report summaries (CC-09/CC-10)", async () => {
    renderChart();

    await waitFor(() => {
      expect(screen.getAllByText("Doe^Jane").length).toBeGreaterThan(0);
    });

    // Tabs exist.
    expect(screen.getByRole("tab", { name: /reports/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /orders/i })).toBeInTheDocument();

    // Prior summaries load into the Reports tab.
    await waitFor(() => {
      expect(screen.getByText(/Old impression text/)).toBeInTheDocument();
      expect(screen.getByText(/Follow up in 6 weeks/)).toBeInTheDocument();
    });
  });

  it("lists the patient's orders on the Orders tab", async () => {
    renderChart();

    await waitFor(() => {
      expect(mockRequest).toHaveBeenCalledWith(
        "ris/orders",
        expect.objectContaining({
          query: expect.objectContaining({ patient: "P1" }),
        }),
      );
    });

    fireEvent.click(screen.getByRole("tab", { name: /orders/i }));
    await waitFor(() => {
      expect(screen.getByText("ACC-2")).toBeInTheDocument();
    });
  });

  it("shows the encounter timeline on the Encounters tab (CS6)", async () => {
    renderChart();
    await waitFor(() => {
      expect(screen.getAllByText("Doe^Jane").length).toBeGreaterThan(0);
    });
    expect(mockListEncounters).toHaveBeenCalledWith({ patient_id: "P1" });
    fireEvent.click(screen.getByRole("tab", { name: /encounters/i }));
    await waitFor(() => {
      expect(
        screen.getByText(/Discussed follow-up imaging/),
      ).toBeInTheDocument();
    });
    expect(screen.getByText("CALL")).toBeInTheDocument();
  });

  it("offers Log Encounter when ENCOUNTER_WRITE is held (CS6)", async () => {
    renderChart();
    await waitFor(() => {
      expect(screen.getAllByText("Doe^Jane").length).toBeGreaterThan(0);
    });
    fireEvent.click(screen.getByRole("tab", { name: /encounters/i }));
    await waitFor(() => {
      expect(screen.getByText("Log Encounter")).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText("Log Encounter"));
    await waitFor(() => {
      expect(screen.getByText(/Summary/i)).toBeInTheDocument();
    });
  });
});
