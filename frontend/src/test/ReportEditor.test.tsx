import React from "react";
import {
  render,
  screen,
  waitFor,
  fireEvent,
  act,
} from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { AuthProvider } from "../auth/AuthContext";
import { ThemeProvider } from "../common/ThemeProvider";
import ReportEditor from "../radiologist/ReportEditor";

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

const mockExam = {
  id: "e1",
  patient_id: "P001",
  patient_name: "John Doe",
  patient_birth_date: "19800101",
  patient_sex: "M",
  accession_number: "ACC-001",
  modality: "CT",
  protocol_name: "CT Head (Routine)",
  priority: "stat",
  completed_at: "2026-08-03T10:00:00Z",
};

const mockReport = {
  id: "rep-1",
  exam_id: "e1",
  status: "draft",
  findings: "Initial findings",
  impression: "",
  recommendations: "",
  template_name: "",
  signed_by: "",
  signed_at: null,
  updated_at: "2026-08-03T10:00:00Z",
};

function renderEditor() {
  return render(
    <ThemeProvider>
      <AuthProvider>
        <MemoryRouter initialEntries={["/reading/e1"]}>
          <Routes>
            <Route path="/reading/:examId" element={<ReportEditor />} />
          </Routes>
        </MemoryRouter>
      </AuthProvider>
    </ThemeProvider>,
  );
}

describe("ReportEditor", () => {
  beforeEach(() => {
    localStorage.clear();
    // A full radiologist: editing (REPORT_WRITE) and finalizing (REPORT_SIGN)
    // both unlocked. Gate-specific variants seed their own sessions.
    localStorage.setItem("token", "t");
    localStorage.setItem("userId", "u1");
    localStorage.setItem("admin", "false");
    localStorage.setItem("role", "radiologist");
    localStorage.setItem(
      "permissions",
      JSON.stringify(["REPORT_READ", "REPORT_WRITE", "REPORT_SIGN"]),
    );
    mockRequest.mockReset();
  });

  it("loads the exam and existing report", async () => {
    mockRequest.mockImplementation((url: string) => {
      if (url === "reports/e1") {
        return Promise.resolve({
          data: { exam: mockExam, report: mockReport },
        });
      }
      return Promise.resolve({ data: [] });
    });
    renderEditor();

    await waitFor(() => {
      expect(screen.getByText("John Doe")).toBeInTheDocument();
    });
    expect(screen.getByDisplayValue("Initial findings")).toBeInTheDocument();
    expect(screen.getByText("DRAFT")).toBeInTheDocument();
  });

  it("disables sign until an impression is entered", async () => {
    mockRequest.mockImplementation((url: string) => {
      if (url === "reports/e1") {
        return Promise.resolve({
          data: { exam: mockExam, report: mockReport },
        });
      }
      return Promise.resolve({ data: [] });
    });
    renderEditor();

    await waitFor(() => {
      expect(screen.getByText("John Doe")).toBeInTheDocument();
    });

    // Header Sign button + actions Sign button; the enabled state lives on the
    // native <button> under the antd Button wrapper.
    const signBtn = screen
      .getAllByRole("button", { name: /sign report/i })
      .find((b) => (b as HTMLButtonElement).disabled === true);
    expect(signBtn).toBeDefined();

    fireEvent.change(screen.getByPlaceholderText(/Impression/), {
      target: { value: "No acute intracranial abnormality." },
    });

    await waitFor(() => {
      const btn = screen
        .getAllByRole("button", { name: /sign report/i })
        .find((b) => (b as HTMLButtonElement).disabled === false);
      expect(btn).toBeDefined();
    });
  });

  it("autosaves the draft after edits", async () => {
    vi.useFakeTimers();
    try {
      mockRequest.mockImplementation((url: string) => {
        if (url === "reports/e1") {
          return Promise.resolve({
            data: { exam: mockExam, report: mockReport },
          });
        }
        return Promise.resolve({ data: [] });
      });
      renderEditor();

      // Flush the initial load promises + antd mount timers.
      await act(async () => {
        await vi.advanceTimersByTimeAsync(200);
      });
      expect(screen.getByText("John Doe")).toBeInTheDocument();

      fireEvent.change(screen.getByPlaceholderText(/Impression/), {
        target: { value: "Normal head CT." },
      });

      // Autosave cadence is 3s; advance past it and flush the async save.
      await act(async () => {
        await vi.advanceTimersByTimeAsync(3500);
      });

      const saveCall = mockRequest.mock.calls.find(
        (c: any) =>
          c[0] === "reports/e1" && c[1]?.data?.impression === "Normal head CT.",
      );
      expect(saveCall).toBeDefined();
    } finally {
      vi.useRealTimers();
    }
  });

  it("signs the report and shows final status", async () => {
    mockRequest.mockImplementation((url: string) => {
      if (url === "reports/e1") {
        return Promise.resolve({
          data: { exam: mockExam, report: mockReport },
        });
      }
      if (url === "reports/templates") {
        return Promise.resolve({ data: [] });
      }
      if (url === "reports/e1/sign") {
        return Promise.resolve({
          data: {
            ...mockReport,
            status: "final",
            signed_by: "50",
            signed_at: "2026-08-03T12:00:00Z",
          },
        });
      }
      return Promise.resolve({ data: [] });
    });
    renderEditor();

    await waitFor(() => {
      expect(screen.getByText("John Doe")).toBeInTheDocument();
    });

    fireEvent.change(screen.getByPlaceholderText(/Impression/), {
      target: { value: "Normal." },
    });

    const signBtn = screen
      .getAllByRole("button", { name: /sign report/i })
      .find((b) => (b as HTMLButtonElement).disabled === false);
    expect(signBtn).toBeDefined();
    fireEvent.click(signBtn!);

    await waitFor(() => {
      expect(screen.getByText(/Sign & Finalize/)).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText("Sign & Finalize"));

    await waitFor(() => {
      expect(screen.getByText("FINAL")).toBeInTheDocument();
    });
    expect(screen.getByText(/This report is FINAL/)).toBeInTheDocument();
  });

  it("renders a read-only view for a REPORT_READ-only user", async () => {
    // referring_physician / care_coordinator hold REPORT_READ only: the
    // editing affordances (template, save, mark preliminary, sign) must not
    // advertise writes the backend rejects.
    localStorage.setItem(
      "permissions",
      JSON.stringify(["REPORT_READ"]),
    );
    mockRequest.mockImplementation((url: string) => {
      if (url === "reports/e1") {
        return Promise.resolve({
          data: { exam: mockExam, report: mockReport },
        });
      }
      return Promise.resolve({ data: [] });
    });
    renderEditor();

    await waitFor(() => {
      expect(screen.getByText("John Doe")).toBeInTheDocument();
    });
    expect(screen.getByText("Read-only report")).toBeInTheDocument();
    expect(screen.queryByText("Save Draft")).not.toBeInTheDocument();
    expect(screen.queryByText("Mark Preliminary")).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /sign report/i }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByPlaceholderText("Apply a template"),
    ).not.toBeInTheDocument();
    const findings = screen.getByDisplayValue("Initial findings");
    expect(findings).toHaveProperty("readOnly", true);
  });

  it("hides Sign Report for a resident without REPORT_SIGN", async () => {
    // resident drafts (REPORT_WRITE) but the attending cosigns: the sign
    // affordance must be absent, save must remain.
    localStorage.setItem(
      "permissions",
      JSON.stringify(["REPORT_READ", "REPORT_WRITE"]),
    );
    mockRequest.mockImplementation((url: string) => {
      if (url === "reports/e1") {
        return Promise.resolve({
          data: { exam: mockExam, report: mockReport },
        });
      }
      return Promise.resolve({ data: [] });
    });
    renderEditor();

    await waitFor(() => {
      expect(screen.getByText("John Doe")).toBeInTheDocument();
    });
    expect(screen.getByText("Save Draft")).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /sign report/i }),
    ).not.toBeInTheDocument();
  });
});
