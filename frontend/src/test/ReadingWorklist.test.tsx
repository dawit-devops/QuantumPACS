import React from "react";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { AuthProvider } from "../auth/AuthContext";
import { ThemeProvider } from "../common/ThemeProvider";
import ReadingWorklist from "../radiologist/ReadingWorklist";

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
        <MemoryRouter initialEntries={["/reading"]}>
          <ReadingWorklist />
        </MemoryRouter>
      </AuthProvider>
    </ThemeProvider>,
  );
}

const mockItems = [
  {
    exam_id: "e1",
    patient_id: "P001",
    patient_name: "John Doe",
    accession_number: "ACC-001",
    modality: "CT",
    protocol_name: "CT Head (Routine)",
    priority: "stat",
    completed_at: "2026-08-03T10:00:00Z",
    report_status: null,
  },
  {
    exam_id: "e2",
    patient_id: "P002",
    patient_name: "Jane Smith",
    accession_number: "ACC-002",
    modality: "MR",
    protocol_name: "MRI Brain (Routine)",
    priority: "routine",
    completed_at: "2026-08-03T09:00:00Z",
    report_status: "draft",
  },
];

describe("ReadingWorklist", () => {
  beforeEach(() => {
    localStorage.clear();
    mockRequest.mockReset();
  });

  it("renders handed-off exams with priority and report status", async () => {
    mockRequest.mockResolvedValue({ data: mockItems });
    renderWorklist();

    await waitFor(() => {
      expect(screen.getByText("John Doe")).toBeInTheDocument();
    });
    expect(screen.getByText("Jane Smith")).toBeInTheDocument();
    expect(screen.getByText("STAT")).toBeInTheDocument();
    expect(screen.getByText("draft")).toBeInTheDocument();
  });

  it("fetches the reading list from reports/reading-list", async () => {
    mockRequest.mockResolvedValue({ data: mockItems });
    renderWorklist();

    await waitFor(() => {
      expect(mockRequest).toHaveBeenCalledWith("reports/reading-list", {
        query: {},
      });
    });
  });

  it("shows Read Study vs Continue based on report state", async () => {
    mockRequest.mockResolvedValue({ data: mockItems });
    renderWorklist();

    await waitFor(() => {
      expect(screen.getByText("Read Study")).toBeInTheDocument();
    });
    expect(screen.getByText("Continue")).toBeInTheDocument();
  });

  it("shows an empty state when nothing is awaiting interpretation", async () => {
    mockRequest.mockResolvedValue({ data: [] });
    renderWorklist();

    await waitFor(() => {
      expect(
        screen.getByText(/No studies awaiting interpretation/i),
      ).toBeInTheDocument();
    });
  });

  it("shows an error alert when the fetch fails", async () => {
    mockRequest.mockRejectedValue(new Error("Network down"));
    renderWorklist();

    await waitFor(() => {
      expect(
        screen.getByText("Failed to load reading worklist"),
      ).toBeInTheDocument();
    });
  });

  it("passes the modality filter through to the request", async () => {
    mockRequest.mockResolvedValue({ data: mockItems });
    renderWorklist();

    await waitFor(() => {
      expect(screen.getByText("John Doe")).toBeInTheDocument();
    });

    const modalityCombobox = screen.getAllByRole("combobox")[1];
    fireEvent.mouseDown(modalityCombobox);
    fireEvent.click(await screen.findByTitle("CT"));

    await waitFor(() => {
      const lastCall =
        mockRequest.mock.calls[mockRequest.mock.calls.length - 1];
      expect(lastCall[0]).toBe("reports/reading-list");
      expect(lastCall[1].query.modality).toBe("CT");
    });
  });
});
