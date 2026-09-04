import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import React from "react";
import { MemoryRouter } from "react-router";
import { App } from "antd";
import { AuthProvider } from "../auth/AuthContext";
import { ThemeProvider } from "../common/ThemeProvider";
import DischargeChecklists from "../coordinator/DischargeChecklists";

vi.mock("../api/ris", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api/ris")>();
  return {
    ...actual,
    listDischargeChecklists: vi.fn(),
    createDischargeChecklist: vi.fn(),
    updateDischargeChecklist: vi.fn(),
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

import {
  listDischargeChecklists,
  createDischargeChecklist,
  updateDischargeChecklist,
} from "../api/ris";
const mockList = vi.mocked(listDischargeChecklists);
const mockCreate = vi.mocked(createDischargeChecklist);
const mockUpdate = vi.mocked(updateDischargeChecklist);

function renderDischarge() {
  localStorage.setItem("userId", "1");
  localStorage.setItem("username", "test");
  localStorage.setItem("permissions", JSON.stringify(["PATIENT_READ", "PATIENT_WRITE"]));
  localStorage.setItem("tenant_id", "t1");
  return render(
    <MemoryRouter>
      <App>
        <AuthProvider>
          <ThemeProvider>
            <DischargeChecklists />
          </ThemeProvider>
        </AuthProvider>
      </App>
    </MemoryRouter>
  );
}

const mockChecklist: import("../api/ris").DischargeChecklist = {
  id: "dc-1",
  patient_id: "8675309",
  title: "Discharge Checklist",
  status: "open",
  items: [
    { label: "Follow-up appointment scheduled", done: true },
    { label: "Medication reconciliation", done: false },
    { label: "Patient education provided", done: false },
  ],
  notes: "",
  tenant_id: "t1",
  created_by: "1",
  created_at: "2026-08-22T10:00:00Z",
  updated_at: "2026-08-22T10:00:00Z",
};

describe("DischargeChecklists", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockList.mockResolvedValue([mockChecklist]);
  });

  it("renders checklists with status and item progress", async () => {
    renderDischarge();
    await waitFor(() => {
      expect(screen.getByText("Discharge Checklist")).toBeInTheDocument();
    });
    expect(screen.getByText("OPEN")).toBeInTheDocument();
    expect(screen.getByText("1/3")).toBeInTheDocument();
  });

  it("lists checklists via listDischargeChecklists", async () => {
    renderDischarge();
    await waitFor(() => {
      expect(mockList).toHaveBeenCalled();
    });
  });

  it("creates a new checklist from the modal", async () => {
    mockCreate.mockResolvedValue(mockChecklist);
    renderDischarge();
    await waitFor(() => {
      expect(screen.getByText("New Checklist")).toBeInTheDocument();
    });
    fireEvent.click(screen.getAllByText("New Checklist")[0]);
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /create checklist/i })).toBeInTheDocument();
    });

    fireEvent.change(screen.getByLabelText(/Patient ID/), {
      target: { value: "8675309" },
    });
    fireEvent.click(screen.getByRole("button", { name: /create checklist/i }));

    await waitFor(() => {
      expect(mockCreate).toHaveBeenCalledWith({
        patient_id: "8675309",
        notes: "",
        items: [
          { label: "Follow-up appointment scheduled", done: false },
          { label: "Medication reconciliation", done: false },
          { label: "Patient education provided", done: false },
        ],
      });
    });
  });

  it("opens the edit modal from the row action", async () => {
    renderDischarge();
    await waitFor(() => {
      expect(screen.getByText("Discharge Checklist")).toBeInTheDocument();
    });
    fireEvent.click(screen.getAllByText("Edit")[0]);
    await waitFor(() => {
      expect(screen.getByText(/Edit: Discharge Checklist/)).toBeInTheDocument();
    });
  });

  it("updates a checklist status", async () => {
    mockUpdate.mockResolvedValue(undefined);
    renderDischarge();
    await waitFor(() => {
      expect(screen.getByText("Discharge Checklist")).toBeInTheDocument();
    });
    fireEvent.click(screen.getAllByText("Edit")[0]);
    await waitFor(() => {
      expect(screen.getByText(/Edit: Discharge Checklist/)).toBeInTheDocument();
    });

    const dialog = screen
      .getAllByRole("dialog")
      .find((d) => d.textContent?.includes("Edit: Discharge Checklist"))!;
    await waitFor(() => {
      expect(screen.getAllByRole("combobox").length).toBeGreaterThan(0);
    });
    const comboboxes = screen.getAllByRole("combobox");
    fireEvent.mouseDown(comboboxes[comboboxes.length - 1]);
    fireEvent.click(await screen.findByTitle("Completed"));
    fireEvent.click(dialog.querySelector('button[type="submit"]') as HTMLElement);

    await waitFor(() => {
      expect(mockUpdate).toHaveBeenCalledWith(
        "dc-1",
        expect.objectContaining({ status: "completed" })
      );
    });
  });

  it("renders empty state when no checklists exist", async () => {
    mockList.mockResolvedValue([]);
    renderDischarge();
    await waitFor(() => {
      expect(screen.getByText(/No discharge checklists yet/i)).toBeInTheDocument();
    });
  });
});
