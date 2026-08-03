import React from "react";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { AuthProvider } from "../auth/AuthContext";
import { ThemeProvider } from "../common/ThemeProvider";
import TechnologistWorklist from "../technologist/TechnologistWorklist";

const mockRequest = vi.hoisted(() => vi.fn());

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
}));

function renderWorklist() {
  return render(
    <ThemeProvider>
      <AuthProvider>
        <MemoryRouter initialEntries={["/exams"]}>
          <TechnologistWorklist />
        </MemoryRouter>
      </AuthProvider>
    </ThemeProvider>,
  );
}

const mockExams = [
  {
    id: "e1",
    patient_id: "P001",
    patient_name: "John Doe",
    accession_number: "ACC-001",
    modality: "CT",
    protocol_name: "CT Head (Routine)",
    status: "in_progress",
    priority: "stat",
  },
  {
    id: "e2",
    patient_id: "P002",
    patient_name: "Jane Smith",
    accession_number: "ACC-002",
    modality: "MR",
    protocol_name: "MRI Brain (Routine)",
    status: "ready",
    priority: "routine",
  },
  {
    id: "e3",
    patient_id: "P003",
    patient_name: "Alex Brown",
    accession_number: "ACC-003",
    modality: "CT",
    protocol_name: "CT Chest (Routine)",
    status: "completed",
    priority: "urgent",
  },
];

describe("TechnologistWorklist", () => {
  beforeEach(() => {
    localStorage.clear();
    mockRequest.mockReset();
  });

  it("renders the assigned exams with priority, modality, and status", async () => {
    mockRequest.mockResolvedValue({ data: mockExams });
    renderWorklist();

    await waitFor(() => {
      expect(screen.getByText("John Doe")).toBeInTheDocument();
    });
    expect(screen.getByText("Jane Smith")).toBeInTheDocument();
    expect(screen.getByText("Alex Brown")).toBeInTheDocument();
    expect(screen.getByText("STAT")).toBeInTheDocument();
    expect(screen.getByText("CT Head (Routine)")).toBeInTheDocument();
  });

  it("fetches exams with the selected status filter", async () => {
    mockRequest.mockResolvedValue({ data: mockExams });
    renderWorklist();

    await waitFor(() => {
      expect(screen.getByText("John Doe")).toBeInTheDocument();
    });

    // antd v6 Select renders a combobox; open the first (Status) select.
    const statusCombobox = screen.getAllByRole("combobox")[0];
    fireEvent.mouseDown(statusCombobox);
    fireEvent.click(await screen.findByTitle("completed"));

    await waitFor(() => {
      const lastCall = mockRequest.mock.calls[mockRequest.mock.calls.length - 1];
      expect(lastCall[0]).toBe("exams");
      expect(lastCall[1].query.status).toBe("completed");
    });
  });

  it("shows an empty state when no exams are assigned", async () => {
    mockRequest.mockResolvedValue({ data: [] });
    renderWorklist();

    await waitFor(() => {
      expect(screen.getByText(/No exams assigned/i)).toBeInTheDocument();
    });
  });

  it("shows an error alert when the fetch fails", async () => {
    mockRequest.mockRejectedValue(new Error("Network down"));
    renderWorklist();

    await waitFor(() => {
      expect(screen.getByText("Failed to load worklist")).toBeInTheDocument();
    });
  });
});
