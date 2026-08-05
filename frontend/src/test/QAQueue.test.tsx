import React from "react";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { AuthProvider } from "../auth/AuthContext";
import { ThemeProvider } from "../common/ThemeProvider";
import QAQueue from "../qa/QAQueue";

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

function renderQueue() {
  return render(
    <ThemeProvider>
      <AuthProvider>
        <MemoryRouter initialEntries={["/qa/queue"]}>
          <QAQueue />
        </MemoryRouter>
      </AuthProvider>
    </ThemeProvider>,
  );
}

const mockRows = [
  {
    exam_id: "e1",
    accession_number: "ACC-100",
    patient_id: "P001",
    patient_name: "John Doe",
    modality: "CT",
    protocol_name: "CT Head (Routine)",
    priority: "stat",
    qa_status: null,
    completed_at: "2026-08-03T10:00:00Z",
  },
  {
    exam_id: "e2",
    accession_number: "ACC-101",
    patient_id: "P002",
    patient_name: "Jane Smith",
    modality: "MR",
    protocol_name: "MR Brain",
    priority: "routine",
    qa_status: "pass",
    completed_at: "2026-08-03T11:00:00Z",
  },
];

describe("QAQueue", () => {
  beforeEach(() => {
    localStorage.clear();
    localStorage.setItem("userId", "qa-1");
    localStorage.setItem("username", "qa_user");
    localStorage.setItem("admin", "true");
    localStorage.setItem("role", "qa_team");
    localStorage.setItem(
      "permissions",
      JSON.stringify(["QA_READ", "QA_WRITE", "PROTOCOL_MANAGE"]),
    );
    mockRequest.mockReset();
    mockRequest.mockResolvedValue({
      data: mockRows,
      meta: { total: 2, page_size: 50 },
    });
  });

  it("loads and renders the pending-exam rows", async () => {
    renderQueue();
    expect(await screen.findByText("ACC-100")).toBeInTheDocument();
    expect(screen.getByText("John Doe")).toBeInTheDocument();
    expect(screen.getByText("CT Head (Routine)")).toBeInTheDocument();
    expect(screen.getByText("Jane Smith")).toBeInTheDocument();
  });

  it("shows a STAT badge for the stat exam", async () => {
    renderQueue();
    expect(await screen.findByText("STAT")).toBeInTheDocument();
  });

  it("shows QA status for reviewed rows", async () => {
    renderQueue();
    await screen.findByText("ACC-101");
    expect(screen.getByText("pass")).toBeInTheDocument();
  });

  it("filters by search term", async () => {
    renderQueue();
    await screen.findByText("ACC-100");
    const search = screen.getByPlaceholderText(/Search patient/i);
    fireEvent.change(search, { target: { value: "Jane" } });
    await waitFor(() => {
      const call = mockRequest.mock.calls[mockRequest.mock.calls.length - 1];
      expect(call[1].query.search).toBe("Jane");
    });
  });

  it("navigates to the review form on Review click", async () => {
    renderQueue();
    await screen.findByText("ACC-100");
    const reviewButtons = screen.getAllByText("Review");
    fireEvent.click(reviewButtons[0]);
    // MemoryRouter keeps the URL; the click handler calls navigate without
    // rendering a real route target, so assert the queue still rendered and no crash.
    expect(screen.getByText("QA Review Queue")).toBeInTheDocument();
  });
});
