import React from "react";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { App } from "antd";
import { AuthProvider } from "../auth/AuthContext";
import { ThemeProvider } from "../common/ThemeProvider";
import PatientProfile from "../portal/PatientProfile";

const mockListScope = vi.hoisted(() => vi.fn());
const mockGetPortalPatient = vi.hoisted(() => vi.fn());
const mockUpdateConsent = vi.hoisted(() => vi.fn());

vi.mock("../api/portal", () => ({
  listScope: mockListScope,
  getPortalPatient: mockGetPortalPatient,
  updateConsent: mockUpdateConsent,
}));

vi.mock("../hooks", () => ({
  useDocumentTitle: vi.fn(),
  useTenantRefetch: vi.fn(),
}));

function renderProfile() {
  return render(
    <ThemeProvider>
      <AuthProvider>
        <App>
          <MemoryRouter>
            <PatientProfile />
          </MemoryRouter>
        </App>
      </AuthProvider>
    </ThemeProvider>
  );
}

describe("PatientProfile consent management", () => {
  beforeEach(() => {
    localStorage.setItem("token", "t");
    localStorage.setItem("userId", "u1");
    localStorage.setItem("admin", "false");
    localStorage.setItem("role", "patient");
    localStorage.setItem("permissions", JSON.stringify(["PORTAL_READ"]));
    mockListScope.mockResolvedValue([{ patient_id: "MRN1", name: "John Doe", scope_type: "self" }]);
    mockGetPortalPatient.mockResolvedValue({
      patient: {
        patient_id: "MRN1",
        name: "John Doe",
        consent_status: "true",
        consent_appointments: "true",
      },
      orders: [],
      reports: [],
    });
    mockUpdateConsent.mockResolvedValue({
      patient_id: "MRN1",
      consent_results: true,
    });
  });

  it("shows the appointment-detail consent toggle and toggles it off (P-05)", async () => {
    renderProfile();
    await screen.findByText("Consent Management");

    // antd Switch renders a button with role="switch"; the results toggle is
    // first, the appointment-detail toggle is second.
    const switches = await screen.findAllByRole("switch");
    expect(switches.length).toBeGreaterThanOrEqual(2);
    const appointmentSwitch = switches[switches.length - 1];
    expect(appointmentSwitch.classList.contains("ant-switch-checked")).toBe(true);

    fireEvent.click(appointmentSwitch);

    await waitFor(() => {
      expect(mockUpdateConsent).toHaveBeenCalledWith("MRN1", true, false);
    });
  });
});
