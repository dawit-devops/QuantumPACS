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
import ReadingConsole from "../radiologist/ReadingConsole";

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

function renderConsole() {
  return render(
    <ThemeProvider>
      <AuthProvider>
        <MemoryRouter initialEntries={["/reading/e1"]}>
          <Routes>
            <Route path="/reading/:examId" element={<ReadingConsole />} />
          </Routes>
        </MemoryRouter>
      </AuthProvider>
    </ThemeProvider>,
  );
}

// The images endpoint is mocked to the no-imaging marker so the suite keeps
// exercising the report lifecycle without mounting the Cornerstone viewer.
function mockNoImaging() {
  mockRequest.mockImplementation((url: string) => {
    if (url === "reports/e1") {
      return Promise.resolve({ data: { exam: mockExam, report: mockReport } });
    }
    if (url === "reports/e1/images") {
      return Promise.resolve({ data: { imaging: false } });
    }
    return Promise.resolve({ data: [] });
  });
}

describe("ReadingConsole", () => {
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
    mockNoImaging();
    renderConsole();

    await waitFor(() => {
      expect(screen.getByText("John Doe")).toBeInTheDocument();
    });
    expect(screen.getByDisplayValue("Initial findings")).toBeInTheDocument();
    expect(screen.getByText("DRAFT")).toBeInTheDocument();
  });

  it("shows a no-imaging notice when the exam has no DICOM", async () => {
    mockNoImaging();
    renderConsole();

    await waitFor(() => {
      expect(screen.getByText(/No imaging available/)).toBeInTheDocument();
    });
    expect(screen.getByDisplayValue("Initial findings")).toBeInTheDocument();
  });

  it("disables sign until an impression is entered", async () => {
    mockNoImaging();
    renderConsole();

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
      mockNoImaging();
      renderConsole();

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
        return Promise.resolve({ data: { exam: mockExam, report: mockReport } });
      }
      if (url === "reports/e1/images") {
        return Promise.resolve({ data: { imaging: false } });
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
    renderConsole();

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
      expect(screen.getByText("Sign & Finalize")).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText("Sign & Finalize"));

    await waitFor(() => {
      expect(screen.getByText("FINAL")).toBeInTheDocument();
    });
    expect(screen.getByText(/This report is FINAL/)).toBeInTheDocument();
  });

  it("Sign & Next jumps to the next exam in the filtered queue", async () => {
    mockRequest.mockImplementation((url: string) => {
      if (url === "reports/e1") {
        return Promise.resolve({ data: { exam: mockExam, report: mockReport } });
      }
      if (url === "reports/e1/images") {
        return Promise.resolve({ data: { imaging: false } });
      }
      if (url === "reports/templates") {
        return Promise.resolve({ data: [] });
      }
      if (url === "reports/reading-list") {
        // Queue in worklist sort order (STAT → urgent → routine, FIFO).
        return Promise.resolve({
          data: [
            { ...mockExam, exam_id: "e1", priority: "stat" },
            {
              exam_id: "e2",
              patient_name: "Jane Roe",
              patient_id: "P002",
              accession_number: "ACC-002",
              modality: "CT",
              priority: "stat",
              report_status: null,
            },
            {
              exam_id: "e3",
              patient_name: "Sam Poe",
              patient_id: "P003",
              accession_number: "ACC-003",
              modality: "MR",
              priority: "urgent",
              report_status: null,
            },
          ],
        });
      }
      if (url === "reports/e1/sign") {
        return Promise.resolve({
          data: { ...mockReport, status: "final", signed_by: "50" },
        });
      }
      return Promise.resolve({ data: [] });
    });
    renderConsole();

    await waitFor(() => {
      expect(screen.getByText("John Doe")).toBeInTheDocument();
    });

    fireEvent.change(screen.getByPlaceholderText(/Impression/), {
      target: { value: "Normal." },
    });
    const signBtn = screen
      .getAllByRole("button", { name: /sign report/i })
      .find((b) => (b as HTMLButtonElement).disabled === false);
    fireEvent.click(signBtn!);

    await waitFor(() => {
      expect(screen.getByText("Sign & Next")).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText("Sign & Next"));

    // The console navigates to the next queue item — the router re-mounts it
    // with examId=e2 and the next load request goes out.
    await waitFor(() => {
      const nextLoad = mockRequest.mock.calls.find(
        (c: any) => c[0] === "reports/e2",
      );
      expect(nextLoad).toBeDefined();
    });
  });

  it("Sign & Next returns to the worklist when the queue is exhausted", async () => {
    mockRequest.mockImplementation((url: string) => {
      if (url === "reports/e1") {
        return Promise.resolve({ data: { exam: mockExam, report: mockReport } });
      }
      if (url === "reports/e1/images") {
        return Promise.resolve({ data: { imaging: false } });
      }
      if (url === "reports/templates") {
        return Promise.resolve({ data: [] });
      }
      if (url === "reports/reading-list") {
        // e1 is the only (last) item in the queue.
        return Promise.resolve({ data: [{ ...mockExam, exam_id: "e1" }] });
      }
      if (url === "reports/e1/sign") {
        return Promise.resolve({
          data: { ...mockReport, status: "final", signed_by: "50" },
        });
      }
      return Promise.resolve({ data: [] });
    });
    renderConsole();

    await waitFor(() => {
      expect(screen.getByText("John Doe")).toBeInTheDocument();
    });

    fireEvent.change(screen.getByPlaceholderText(/Impression/), {
      target: { value: "Normal." },
    });
    const signBtn = screen
      .getAllByRole("button", { name: /sign report/i })
      .find((b) => (b as HTMLButtonElement).disabled === false);
    fireEvent.click(signBtn!);

    await waitFor(() => {
      expect(screen.getByText("Sign & Next")).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText("Sign & Next"));

    // No next exam exists → navigate to /reading; no e2 load is ever issued.
    await waitFor(() => {
      const nextLoad = mockRequest.mock.calls.find(
        (c: any) => c[0] === "reports/e2",
      );
      expect(nextLoad).toBeUndefined();
    });
  });

  it("renders a read-only view for a REPORT_READ-only user", async () => {
    // referring_physician / care_coordinator hold REPORT_READ only: the
    // editing affordances (template, save, mark preliminary, sign) must not
    // advertise writes the backend rejects.
    localStorage.setItem("permissions", JSON.stringify(["REPORT_READ"]));
    mockNoImaging();
    renderConsole();

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
    mockNoImaging();
    renderConsole();

    await waitFor(() => {
      expect(screen.getByText("John Doe")).toBeInTheDocument();
    });
    expect(screen.getByText("Save Draft")).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /sign report/i }),
    ).not.toBeInTheDocument();
  });

  it("lets a resident submit the draft for attending review", async () => {
    localStorage.setItem("role", "resident");
    localStorage.setItem(
      "permissions",
      JSON.stringify(["REPORT_READ", "REPORT_WRITE"]),
    );
    mockRequest.mockImplementation((url: string) => {
      if (url === "reports/e1") {
        return Promise.resolve({ data: { exam: mockExam, report: mockReport } });
      }
      if (url === "reports/e1/images") {
        return Promise.resolve({ data: { imaging: false } });
      }
      if (url === "reports/templates") {
        return Promise.resolve({ data: [] });
      }
      if (url === "reports/e1/submit") {
        return Promise.resolve({
          data: { ...mockReport, status: "submitted", impression: "Normal." },
        });
      }
      return Promise.resolve({ data: [] });
    });
    renderConsole();

    await waitFor(() => {
      expect(screen.getByText("John Doe")).toBeInTheDocument();
    });

    fireEvent.change(screen.getByPlaceholderText(/Impression/), {
      target: { value: "Normal." },
    });

    const submitBtn = screen
      .getAllByRole("button", { name: /submit for review/i })
      .find((b) => (b as HTMLButtonElement).disabled === false);
    expect(submitBtn).toBeDefined();
    fireEvent.click(submitBtn!);

    await waitFor(() => {
      const submitCall = mockRequest.mock.calls.find(
        (c: any) => c[0] === "reports/e1/submit",
      );
      expect(submitCall).toBeDefined();
    });
    // The submitted report locks: header shows SUBMITTED and the panel
    // advertises the attending's hands are on it.
    await waitFor(() => {
      expect(screen.getByText("SUBMITTED")).toBeInTheDocument();
    });
    expect(
      screen.getByText(/Submitted for attending review/i),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /submit for review/i }),
    ).not.toBeInTheDocument();
  });

  it("attending returns a submitted report for revision", async () => {
    mockRequest.mockImplementation((url: string) => {
      if (url === "reports/e1") {
        return Promise.resolve({
          data: {
            exam: mockExam,
            report: { ...mockReport, status: "submitted", impression: "Normal." },
          },
        });
      }
      if (url === "reports/e1/images") {
        return Promise.resolve({ data: { imaging: false } });
      }
      if (url === "reports/templates") {
        return Promise.resolve({ data: [] });
      }
      if (url === "reports/e1/return") {
        return Promise.resolve({
          data: {
            ...mockReport,
            status: "draft",
            impression: "Normal.",
            review_feedback: "Add comparison with prior CT.",
          },
        });
      }
      return Promise.resolve({ data: [] });
    });
    renderConsole();

    await waitFor(() => {
      expect(screen.getByText("John Doe")).toBeInTheDocument();
    });
    // The attending's review actions replace the plain sign button.
    expect(
      screen.getAllByRole("button", { name: /approve & co-sign/i }).length,
    ).toBeGreaterThan(0);
    expect(
      screen.getAllByRole("button", { name: /return for revision/i }).length,
    ).toBeGreaterThan(0);

    fireEvent.click(
      screen.getAllByRole("button", { name: /return for revision/i })[0],
    );
    await waitFor(() => {
      expect(screen.getByText("Return Report for Revision")).toBeInTheDocument();
    });
    fireEvent.change(screen.getByPlaceholderText(/What should the resident revise/), {
      target: { value: "Add comparison with prior CT." },
    });
    fireEvent.click(screen.getByText("Return & Reopen Draft"));

    await waitFor(() => {
      const returnCall = mockRequest.mock.calls.find(
        (c: any) => c[0] === "reports/e1/return",
      );
      expect(returnCall).toBeDefined();
    });
    // Back to an editable draft, carrying the attending's feedback.
    await waitFor(() => {
      expect(screen.getByText("DRAFT")).toBeInTheDocument();
    });
    expect(
      screen.getByText(/Attending returned this report/i),
    ).toBeInTheDocument();
    expect(
      screen.getAllByText(/Add comparison with prior CT/i).length,
    ).toBeGreaterThan(0);
  });
});
