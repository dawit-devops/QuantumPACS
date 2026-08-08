import React from "react";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { AuthProvider } from "../auth/AuthContext";
import { ThemeProvider } from "../common/ThemeProvider";
import ExamConsole from "../technologist/ExamConsole";

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

function renderConsole() {
  return render(
    <ThemeProvider>
      <AuthProvider>
        <MemoryRouter initialEntries={["/exams/e1"]}>
          <Routes>
            <Route path="/exams/:id" element={<ExamConsole />} />
          </Routes>
        </MemoryRouter>
      </AuthProvider>
    </ThemeProvider>,
  );
}

const readyExam = {
  id: "e1",
  patient_id: "P001",
  patient_name: "John Doe",
  patient_birth_date: "19800101",
  patient_sex: "M",
  accession_number: "ACC-001",
  requested_procedure_desc: "CT Head",
  modality: "CT",
  station_ae_title: "CT-1",
  priority: "stat",
  status: "ready",
  protocol_name: "",
  acquisitions: [],
  safety_checks: [],
  incidents: [],
  overrides: [],
  dose: { total_dlp: 0, total_ctdivol: 0, total_mas: 0, total_exposure: 0 },
};

const inProgressExam = {
  ...readyExam,
  status: "in_progress",
  identity_confirmed_at: "2026-08-03T08:00:00Z",
  protocol_name: "CT Head (Routine)",
  dose: {
    total_dlp: 520,
    total_ctdivol: 12.5,
    total_mas: 210,
    total_exposure: 0,
  },
  benchmark_dlp: 1300,
  dose_level: "ok",
};

const mockProtocols = {
  data: [
    {
      name: "CT Head (Routine)",
      modality: "CT",
      is_default: true,
      sequences: [],
    },
    {
      name: "CT Chest (Routine)",
      modality: "CT",
      is_default: false,
      sequences: [],
    },
  ],
};

describe("ExamConsole", () => {
  beforeEach(() => {
    localStorage.clear();
    // A technologist: full acquisition surface (EXAM_WRITE). The read-only
    // variant seeds its own session below.
    localStorage.setItem("token", "t");
    localStorage.setItem("userId", "u1");
    localStorage.setItem("admin", "false");
    localStorage.setItem("role", "technologist");
    localStorage.setItem("permissions", JSON.stringify(["EXAM_READ", "EXAM_WRITE"]));
    mockRequest.mockReset();
  });

  it("shows patient identity verification for a ready exam", async () => {
    mockRequest.mockImplementation((url: string) => {
      if (url === "exams/e1") return Promise.resolve({ data: readyExam });
      if (url === "protocols") return Promise.resolve(mockProtocols);
      return Promise.resolve({ data: [] });
    });
    renderConsole();

    await waitFor(() => {
      expect(
        screen.getByText("Patient Identity Verification"),
      ).toBeInTheDocument();
    });
    expect(screen.getByText("John Doe")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /Confirm Patient/i }),
    ).toBeInTheDocument();
  });

  it("confirms identity and moves to in-progress", async () => {
    mockRequest.mockImplementation((url: string) => {
      if (url === "exams/e1") return Promise.resolve({ data: readyExam });
      if (url === "protocols") return Promise.resolve(mockProtocols);
      return Promise.resolve({ data: [] });
    });
    renderConsole();

    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: /Confirm Patient/i }),
      ).toBeInTheDocument();
    });

    // Confirm identity writes via the API; the refetch returns in-progress.
    mockRequest.mockImplementation((url: string) => {
      if (url === "exams/e1/identity-confirm")
        return Promise.resolve({ data: {} });
      if (url === "exams/e1") return Promise.resolve({ data: inProgressExam });
      if (url === "protocols") return Promise.resolve(mockProtocols);
      return Promise.resolve({ data: [] });
    });

    fireEvent.click(screen.getByRole("button", { name: /Confirm Patient/i }));

    await waitFor(() => {
      expect(screen.getByText(/Verified/i)).toBeInTheDocument();
    });
  });

  it("starts the protocol from the registry", async () => {
    mockRequest.mockImplementation((url: string) => {
      if (url === "exams/e1") return Promise.resolve({ data: inProgressExam });
      if (url === "protocols") return Promise.resolve(mockProtocols);
      return Promise.resolve({ data: [] });
    });
    renderConsole();

    await waitFor(() => {
      expect(screen.getByText("CT Head (Routine)")).toBeInTheDocument();
    });
  });

  it("acquires an image and queues it for QA", async () => {
    let examState: any = { ...inProgressExam };
    mockRequest.mockImplementation((url: string) => {
      if (url === "exams/e1") return Promise.resolve({ data: examState });
      if (url === "protocols") return Promise.resolve(mockProtocols);
      if (url === "exams/e1/acquisitions") {
        const acq = {
          id: "acq-1",
          series_number: 1,
          description: "Localizer",
          kvp: 120,
          mas: 210,
          dlp: 520,
          ctdivol: 12.5,
        };
        examState = {
          ...examState,
          acquisitions: [...examState.acquisitions, acq],
          dose: {
            total_dlp: 1040,
            total_ctdivol: 25,
            total_mas: 420,
            total_exposure: 0,
          },
        };
        return Promise.resolve({ data: acq });
      }
      return Promise.resolve({ data: [] });
    });
    renderConsole();

    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: /Acquire Image/i }),
      ).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /Acquire Image/i }));

    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: /Accept/i }),
      ).toBeInTheDocument();
    });
    expect(screen.getByRole("button", { name: /Reject/i })).toBeInTheDocument();
    // The acquired image description appears in the QA queue.
    expect(screen.getByText("Localizer")).toBeInTheDocument();
  });

  it("accepts a pending acquisition and clears the QA queue", async () => {
    let examState: any = { ...inProgressExam };
    mockRequest.mockImplementation((url: string) => {
      if (url === "exams/e1") return Promise.resolve({ data: examState });
      if (url === "protocols") return Promise.resolve(mockProtocols);
      if (url === "exams/e1/acquisitions") {
        const acq = {
          id: "acq-1",
          series_number: 1,
          description: "Localizer",
          dlp: 520,
        };
        examState = {
          ...examState,
          acquisitions: [...examState.acquisitions, acq],
        };
        return Promise.resolve({ data: acq });
      }
      if (url.includes("/accept"))
        return Promise.resolve({ data: { status: "accepted" } });
      return Promise.resolve({ data: [] });
    });
    renderConsole();

    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: /Acquire Image/i }),
      ).toBeInTheDocument();
    });
    fireEvent.click(screen.getByRole("button", { name: /Acquire Image/i }));

    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: /Accept/i }),
      ).toBeInTheDocument();
    });
    fireEvent.click(screen.getByRole("button", { name: /Accept/i }));

    await waitFor(() => {
      expect(
        screen.queryByRole("button", { name: /Accept/i }),
      ).not.toBeInTheDocument();
    });
  });

  it("requires a justification for emergency override", async () => {
    mockRequest.mockImplementation((url: string) => {
      if (url === "exams/e1") return Promise.resolve({ data: inProgressExam });
      if (url === "protocols") return Promise.resolve(mockProtocols);
      return Promise.resolve({ data: [] });
    });
    renderConsole();

    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: /Emergency Override/i }),
      ).toBeInTheDocument();
    });
    fireEvent.click(
      screen.getByRole("button", { name: /Emergency Override/i }),
    );

    await waitFor(() => {
      expect(
        screen.getByText("Emergency Protocol Override"),
      ).toBeInTheDocument();
    });
    // Submit without justification — validation should block the API call.
    fireEvent.click(screen.getByRole("button", { name: /Confirm Override/i }));

    await waitFor(() => {
      expect(
        screen.getByText(/Justification is required/i),
      ).toBeInTheDocument();
    });
  });

  it("logs an incident through the modal", async () => {
    mockRequest.mockImplementation((url: string) => {
      if (url === "exams/e1") return Promise.resolve({ data: inProgressExam });
      if (url === "protocols") return Promise.resolve(mockProtocols);
      if (url === "exams/e1/incidents")
        return Promise.resolve({ data: { id: "inc-1" } });
      return Promise.resolve({ data: [] });
    });
    renderConsole();

    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: /Log Incident/i }),
      ).toBeInTheDocument();
    });
    fireEvent.click(screen.getByRole("button", { name: /Log Incident/i }));

    await waitFor(() => {
      expect(screen.getByRole("dialog")).toBeInTheDocument();
    });
    expect(screen.getByText(/Incident type/i)).toBeInTheDocument();
  });

  it("shows dose documentation with an ACR benchmark progress bar", async () => {
    mockRequest.mockImplementation((url: string) => {
      if (url === "exams/e1") return Promise.resolve({ data: inProgressExam });
      if (url === "protocols") return Promise.resolve(mockProtocols);
      return Promise.resolve({ data: [] });
    });
    renderConsole();

    await waitFor(() => {
      expect(screen.getByText("Dose Documentation")).toBeInTheDocument();
    });
    expect(screen.getByText(/520.0 mGy·cm/)).toBeInTheDocument();
    expect(screen.getByText(/ACR benchmark/)).toBeInTheDocument();
  });

  it("shows completion state for a completed exam", async () => {
    const completed = {
      ...inProgressExam,
      status: "completed",
      completed_at: "2026-08-03T10:00:00Z",
    };
    mockRequest.mockImplementation((url: string) => {
      if (url === "exams/e1") return Promise.resolve({ data: completed });
      if (url === "protocols") return Promise.resolve(mockProtocols);
      return Promise.resolve({ data: [] });
    });
    renderConsole();

    await waitFor(() => {
      expect(
        screen.getByText(/Exam completed and handed off/i),
      ).toBeInTheDocument();
    });
  });

  it("renders a read-only console for an EXAM_READ-only user", async () => {
    // nurse / resident hold EXAM_READ only: every acquisition write
    // (identity, protocol, acquire, safety, complete) is EXAM_WRITE-gated.
    localStorage.setItem(
      "permissions",
      JSON.stringify(["EXAM_READ"]),
    );
    mockRequest.mockImplementation((url: string) => {
      if (url === "exams/e1") return Promise.resolve({ data: readyExam });
      if (url === "protocols") return Promise.resolve(mockProtocols);
      return Promise.resolve({ data: [] });
    });
    renderConsole();

    await waitFor(() => {
      expect(
        screen.getByText("Patient Identity Verification"),
      ).toBeInTheDocument();
    });
    expect(
      screen.queryByRole("button", { name: /Confirm Patient/i }),
    ).not.toBeInTheDocument();
    expect(screen.queryByText("Start Protocol")).not.toBeInTheDocument();
    expect(screen.queryByText("Acquire Image")).not.toBeInTheDocument();
    expect(screen.queryByText("Complete Exam")).not.toBeInTheDocument();
    expect(screen.queryByText("Log Incident")).not.toBeInTheDocument();
    expect(screen.getByText("Read-only exam console")).toBeInTheDocument();
  });
});
