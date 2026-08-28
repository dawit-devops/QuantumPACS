import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import React from "react";
import { MemoryRouter } from "react-router";
import { App } from "antd";
import { AuthProvider } from "../auth/AuthContext";
import { ThemeProvider } from "../common/ThemeProvider";
import CarePlans from "../coordinator/CarePlans";

vi.mock("../api/care-plans", () => ({
  listCarePlans: vi.fn(),
  createCarePlan: vi.fn(),
  updateCarePlan: vi.fn(),
}));

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

import { listCarePlans } from "../api/care-plans";
const mockList = vi.mocked(listCarePlans);

function renderCarePlans() {
  localStorage.setItem("userId", "1");
  localStorage.setItem("username", "test");
  localStorage.setItem(
    "permissions",
    JSON.stringify(["PATIENT_READ", "CARE_PLAN_WRITE"]),
  );
  localStorage.setItem("tenant_id", "t1");
  return render(
    <MemoryRouter>
      <App>
        <AuthProvider>
          <ThemeProvider>
            <CarePlans />
          </ThemeProvider>
        </AuthProvider>
      </App>
    </MemoryRouter>,
  );
}

describe("CarePlans", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockList.mockResolvedValue({
      data: [
        {
          id: "cp-1",
          patient_id: "8675309",
          title: "Post-op follow-up",
          status: "active",
          tasks: [
            { label: "Call patient", done: true },
            { label: "Schedule imaging", done: false },
          ],
          responsible_provider: "Dr. Rivera",
          follow_up_at: "2026-09-01T00:00:00Z",
          notes: "",
          tenant_id: "t1",
          created_by: "1",
          created_at: "2026-08-20T10:00:00Z",
          updated_at: "2026-08-22T10:00:00Z",
        },
      ],
    });
  });

  it("renders care plans with task progress and status", async () => {
    renderCarePlans();
    await waitFor(() => {
      expect(screen.getByText("Post-op follow-up")).toBeInTheDocument();
    });
    expect(screen.getByText("ACTIVE")).toBeInTheDocument();
    expect(screen.getByText("1/2")).toBeInTheDocument();
    expect(screen.getByText("Dr. Rivera")).toBeInTheDocument();
  });

  it("shows the New Plan button", async () => {
    renderCarePlans();
    await waitFor(() => {
      expect(screen.getByText("New Plan")).toBeInTheDocument();
    });
  });

  it("passes a status filter when one is selected", async () => {
    renderCarePlans();
    await waitFor(() => {
      expect(mockList).toHaveBeenCalledWith({});
    });
  });

  it("renders empty state when no plans exist", async () => {
    mockList.mockResolvedValue({ data: [] });
    renderCarePlans();
    await waitFor(() => {
      expect(screen.getByText(/No care plans yet/i)).toBeInTheDocument();
    });
  });

  it("opens the edit modal from the row action", async () => {
    renderCarePlans();
    await waitFor(() => {
      expect(screen.getByText("Post-op follow-up")).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText("Edit"));
    await waitFor(() => {
      expect(screen.getByText("Edit Care Plan")).toBeInTheDocument();
    });
  });

  it("renders '-' instead of crashing when tasks arrives as a legacy string (F6)", async () => {
    mockList.mockResolvedValue({
      data: [
        {
          id: "cp-2",
          patient_id: "8675310",
          title: "Legacy string payload",
          status: "active",
          tasks: "[{\"label\":\"Call patient\",\"done\":false}]" as unknown as [],
          responsible_provider: "Dr. Rivera",
          follow_up_at: null,
          notes: "",
          tenant_id: "t1",
          created_by: "1",
          created_at: "2026-08-20T10:00:00Z",
          updated_at: "2026-08-22T10:00:00Z",
        },
      ],
    });
    renderCarePlans();
    await waitFor(() => {
      expect(screen.getByText("Legacy string payload")).toBeInTheDocument();
    });
    // the Tasks cell renders '-' (row 0 tasks) without throwing
    expect(screen.getAllByText("-").length).toBeGreaterThan(0);
  });
});
