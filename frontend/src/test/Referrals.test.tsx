import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import React from "react";
import { MemoryRouter } from "react-router";
import { App } from "antd";
import { AuthProvider } from "../auth/AuthContext";
import { ThemeProvider } from "../common/ThemeProvider";
import ReferralTracking from "../coordinator/ReferralTracking";

vi.mock("../api/ris", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api/ris")>();
  return {
    ...actual,
    listReferrals: vi.fn(),
    createReferral: vi.fn(),
    updateReferral: vi.fn(),
  };
});

vi.mock("../hooks", () => ({
  useDocumentTitle: vi.fn(),
  useTenantRefetch: vi.fn(),
}));

vi.mock("../auth/AuthContext", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../auth/AuthContext")>();
  return {
    ...actual,
    useAuth: () => ({ hasPermission: () => true }),
  };
});

import { listReferrals, createReferral, updateReferral } from "../api/ris";
const mockList = vi.mocked(listReferrals);
const mockCreate = vi.mocked(createReferral);
const mockUpdate = vi.mocked(updateReferral);

function renderReferrals() {
  localStorage.setItem("userId", "1");
  localStorage.setItem("username", "test");
  localStorage.setItem("permissions", JSON.stringify(["PATIENT_READ", "PATIENT_WRITE"]));
  localStorage.setItem("tenant_id", "t1");
  return render(
    <MemoryRouter>
      <App>
        <AuthProvider>
          <ThemeProvider>
            <ReferralTracking />
          </ThemeProvider>
        </AuthProvider>
      </App>
    </MemoryRouter>
  );
}

const mockReferral: import("../api/ris").Referral = {
  id: "ref-1",
  patient_id: "8675309",
  from_provider: "Dr. Jones",
  to_specialist: "Dr. Smith",
  specialty: "Cardiology",
  status: "pending",
  order_id: "",
  report_id: "",
  notes: "Routine consult for chest pain.",
  tenant_id: "t1",
  created_by: "1",
  created_at: "2026-08-22T10:00:00Z",
  updated_at: "2026-08-22T10:00:00Z",
};

describe("ReferralTracking", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockList.mockResolvedValue([mockReferral]);
  });

  it("renders referrals with status and specialist", async () => {
    renderReferrals();
    await waitFor(() => {
      expect(screen.getByText("Dr. Smith")).toBeInTheDocument();
    });
    expect(screen.getByText("PENDING")).toBeInTheDocument();
    expect(screen.getByText("Cardiology")).toBeInTheDocument();
  });

  it("lists referrals via listReferrals", async () => {
    renderReferrals();
    await waitFor(() => {
      expect(mockList).toHaveBeenCalled();
    });
  });

  it("creates a new referral from the modal", async () => {
    mockCreate.mockResolvedValue(mockReferral);
    renderReferrals();
    await waitFor(() => {
      expect(screen.getByText("New Referral")).toBeInTheDocument();
    });
    fireEvent.click(screen.getAllByText("New Referral")[0]);
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /create referral/i })).toBeInTheDocument();
    });

    fireEvent.change(screen.getByLabelText(/Patient ID/), {
      target: { value: "8675309" },
    });
    fireEvent.change(screen.getByLabelText(/To Specialist/), {
      target: { value: "Dr. Smith" },
    });
    fireEvent.click(screen.getByRole("button", { name: /create referral/i }));

    await waitFor(() => {
      expect(mockCreate).toHaveBeenCalledWith({
        patient_id: "8675309",
        from_provider: "",
        to_specialist: "Dr. Smith",
        specialty: "",
        notes: "",
      });
    });
  });

  it("opens the update modal from the row action", async () => {
    renderReferrals();
    await waitFor(() => {
      expect(screen.getByText("Dr. Smith")).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText("Update"));
    await waitFor(() => {
      expect(screen.getByText(/Referral to Dr. Smith/)).toBeInTheDocument();
    });
  });

  it("updates a referral status", async () => {
    mockUpdate.mockResolvedValue(undefined);
    renderReferrals();
    await waitFor(() => {
      expect(screen.getByText("Dr. Smith")).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText("Update"));
    await waitFor(() => {
      expect(screen.getByText(/Referral to Dr. Smith/)).toBeInTheDocument();
    });

    const getDialog = () =>
      screen.getAllByRole("dialog").find((d) => d.textContent?.includes("Referral to Dr. Smith"))!;

    await waitFor(() => {
      expect(screen.getAllByRole("combobox").length).toBeGreaterThan(0);
    });
    const comboboxes = screen.getAllByRole("combobox");
    fireEvent.mouseDown(comboboxes[comboboxes.length - 1]);
    fireEvent.click(await screen.findByTitle("Accepted"));
    fireEvent.click(getDialog().querySelector('button[type="submit"]') as HTMLElement);

    await waitFor(() => {
      expect(mockUpdate).toHaveBeenCalledWith("ref-1", {
        status: "accepted",
        notes: "Routine consult for chest pain.",
      });
    });
  });

  it("renders empty state when no referrals exist", async () => {
    mockList.mockResolvedValue([]);
    renderReferrals();
    await waitFor(() => {
      expect(screen.getByText(/No referrals yet/i)).toBeInTheDocument();
    });
  });
});
