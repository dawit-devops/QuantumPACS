import React from "react";
import { render, screen, waitFor, fireEvent, act } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { App } from "antd";
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

const mockOpenInWeasis = vi.hoisted(() => vi.fn());
vi.mock("../api/weasis", () => ({
  getWeasisStatus: () => Promise.resolve({ enabled: true, launch_url: "http://weasis" }),
  weasisLaunchUrl: (uid: string) => `http://weasis/launch?studyUID=${uid}`,
  openInWeasis: mockOpenInWeasis,
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
        <App>
          <MemoryRouter initialEntries={["/reading/e1"]}>
            <Routes>
              <Route path="/reading/:examId" element={<ReadingConsole />} />
            </Routes>
          </MemoryRouter>
        </App>
      </AuthProvider>
    </ThemeProvider>
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
    if (url === "reports/e1/key-images") {
      return Promise.resolve({ data: [] });
    }
    return Promise.resolve({ data: [] });
  });
}

// The rich-text editor renders a contentEditable div carrying the field's
// placeholder in data-placeholder (no native textarea/placeholder attribute),
// so the old getByPlaceholderText/getByDisplayValue queries no longer match.
function rte(placeholder: string): HTMLElement {
  return document.querySelector(`[data-placeholder="${placeholder}"]`) as HTMLElement;
}

function setRte(placeholder: string, value: string) {
  const el = rte(placeholder);
  el.innerHTML = value;
  fireEvent.input(el);
}

// A.5 Part A: the AI-draft hook is wired into the console and seeds three
// unreviewed blocks per exam, which hard-gate signing/submitting. These
// lifecycle tests resolve them through the AI banner's "Accept all" before
// engaging the sign/submit flow (the A.5 UX, not a bypass).
async function resolveAiDraft() {
  // Click "Accept all" once the banner settles, then wait for it to clear so
  // the A.5 gate (unreviewedCount === 0) is lifted before the test proceeds —
  // otherwise the action button would still read as disabled on the next frame.
  await waitFor(
    () => {
      const acceptAll = screen
        .getAllByRole("button", { name: /accept all/i })
        .find((b) => (b as HTMLButtonElement).disabled === false);
      if (!acceptAll) throw new Error("AI draft banner not ready");
      fireEvent.click(acceptAll);
    },
    { timeout: 15000 },
  );
  await waitFor(
    () => {
      if (screen.queryAllByRole("button", { name: /accept all/i }).length > 0) {
        throw new Error("AI draft blocks still pending review");
      }
    },
    { timeout: 15000 },
  );
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
      JSON.stringify(["REPORT_READ", "REPORT_WRITE", "REPORT_SIGN"])
    );
    mockRequest.mockReset();
  });

  it("loads the exam and existing report", async () => {
    mockNoImaging();
    renderConsole();

    await waitFor(() => {
      expect(screen.getByText("John Doe")).toBeInTheDocument();
    });
    expect(rte("Structured findings — per template or free text…").innerHTML).toContain(
      "Initial findings"
    );
    expect(screen.getByText("DRAFT")).toBeInTheDocument();
  });

  it("shows a no-imaging notice when the exam has no DICOM", async () => {
    mockNoImaging();
    renderConsole();

    await waitFor(() => {
      expect(screen.getByText(/No imaging available/)).toBeInTheDocument();
    });
    expect(rte("Structured findings — per template or free text…").innerHTML).toContain(
      "Initial findings"
    );
  });

  it("disables sign until an impression is entered", async () => {
    mockNoImaging();
    renderConsole();

    await waitFor(() => {
      expect(screen.getByText("John Doe")).toBeInTheDocument();
    });

    // Header Sign button + actions Sign button; the enabled state lives on the
    // native <button> under the antd Button wrapper. Both sign buttons are
    // disabled until the impression field has content (A.5 / §4.4), so before
    // typing at least one must read disabled.
    const signBtn = screen
      .getAllByRole("button", { name: /sign report/i })
      .find((b) => (b as HTMLButtonElement).disabled === true);
    expect(signBtn).toBeDefined();

    setRte(
      "Impression / conclusion (required before signing)…",
      "No acute intracranial abnormality."
    );

    // Clear the A.5 AI gate (unreviewed draft blocks) so the impression alone
    // keeps sign enabled — the header Sign Report is gated the same way as the
    // footer, so both must un-disable together.
    await resolveAiDraft();

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

      setRte("Impression / conclusion (required before signing)…", "Normal head CT.");

      // Autosave cadence is 3s; advance past it and flush the async save.
      await act(async () => {
        await vi.advanceTimersByTimeAsync(3500);
      });

      const saveCall = mockRequest.mock.calls.find(
        (c: any) => c[0] === "reports/e1" && c[1]?.data?.impression === "Normal head CT."
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

    setRte("Impression / conclusion (required before signing)…", "Normal.");

    await resolveAiDraft();

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
      expect(screen.getAllByText("FINAL").length).toBeGreaterThan(0);
    });
    expect(screen.getByText(/This report is FINAL/)).toBeInTheDocument();
  });

  it("shows the distribution confirmation after signing (R-16)", async () => {
    mockRequest.mockImplementation((url: string) => {
      if (url === "reports/e1") {
        return Promise.resolve({ data: { exam: mockExam, report: mockReport } });
      }
      if (url === "reports/e1/images") {
        return Promise.resolve({ data: { imaging: false } });
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
      if (url.startsWith("notifications/delivery-status")) {
        return Promise.resolve({
          data: [
            {
              id: "d1",
              report_id: "rep-1",
              accession_number: "ACC-001",
              status: "SENT",
              attempts: 1,
              delivered_at: "2026-08-03T12:00:05Z",
            },
            {
              id: "d2",
              report_id: "rep-1",
              accession_number: "ACC-001",
              status: "FAILED",
              attempts: 3,
              delivered_at: null,
            },
          ],
        });
      }
      return Promise.resolve({ data: [] });
    });
    renderConsole();

    await waitFor(() => {
      expect(screen.getByText("John Doe")).toBeInTheDocument();
    });

    setRte("Impression / conclusion (required before signing)…", "Normal.");
    await resolveAiDraft();
    const signBtn = screen
      .getAllByRole("button", { name: /sign report/i })
      .find((b) => (b as HTMLButtonElement).disabled === false);
    fireEvent.click(signBtn!);
    fireEvent.click(await screen.findByText("Sign & Finalize"));

    await waitFor(() => {
      expect(screen.getByText(/Report distributed to 2 recipient/i)).toBeInTheDocument();
      expect(screen.getByText("SENT")).toBeInTheDocument();
      expect(screen.getByText("FAILED")).toBeInTheDocument();
    });
  });

  it("Sign & Next jumps to the next exam in the filtered queue", async () => {
    mockRequest.mockImplementation((url: string) => {
      if (url === "reports/e1") {
        return Promise.resolve({
          data: { exam: mockExam, report: mockReport },
        });
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

    setRte("Impression / conclusion (required before signing)…", "Normal.");
    await resolveAiDraft();
    const signBtn = screen
      .getAllByRole("button", { name: /sign report/i })
      .find((b) => (b as HTMLButtonElement).disabled === false);
    fireEvent.click(signBtn!);

    await waitFor(() => {
      expect(screen.getByText("Sign & Next")).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText("Sign & Next"));

    // R-15: the success toast names the next patient in the queue.
    await waitFor(() => {
      expect(screen.getByText("Report signed ✓ — Next: Jane Roe")).toBeInTheDocument();
    });

    // The console navigates to the next queue item — the router re-mounts it
    // with examId=e2 and the next load request goes out.
    await waitFor(() => {
      const nextLoad = mockRequest.mock.calls.find((c: any) => c[0] === "reports/e2");
      expect(nextLoad).toBeDefined();
    });
  });

  it("Sign & Next returns to the worklist when the queue is exhausted", async () => {
    mockRequest.mockImplementation((url: string) => {
      if (url === "reports/e1") {
        return Promise.resolve({
          data: { exam: mockExam, report: mockReport },
        });
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

    setRte("Impression / conclusion (required before signing)…", "Normal.");
    await resolveAiDraft();
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
      const nextLoad = mockRequest.mock.calls.find((c: any) => c[0] === "reports/e2");
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
      // The name renders twice (console topbar + branded report document).
      expect(screen.getAllByText("John Doe").length).toBeGreaterThan(0);
    });
    expect(screen.getByText("Read-only report")).toBeInTheDocument();
    expect(screen.queryByText("Save Draft")).not.toBeInTheDocument();
    expect(screen.queryByText("Mark Preliminary")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /sign report/i })).not.toBeInTheDocument();
    expect(screen.queryByPlaceholderText("Apply a template")).not.toBeInTheDocument();
    // Read-only surfaces render the branded report document (not a readonly
    // textarea) — the findings text is displayed as document body.
    expect(screen.getByText("Initial findings")).toBeInTheDocument();
    expect(screen.queryByDisplayValue("Initial findings")).not.toBeInTheDocument();
  });

  it("hides Sign Report for a resident without REPORT_SIGN", async () => {
    // resident drafts (REPORT_WRITE) but the attending cosigns: the sign
    // affordance must be absent, save must remain.
    localStorage.setItem("permissions", JSON.stringify(["REPORT_READ", "REPORT_WRITE"]));
    mockNoImaging();
    renderConsole();

    await waitFor(() => {
      expect(screen.getByText("John Doe")).toBeInTheDocument();
    });
    expect(screen.getByText("Save Draft")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /sign report/i })).not.toBeInTheDocument();
  });

  it("lets a resident submit the draft for attending review", async () => {
    localStorage.setItem("role", "resident");
    localStorage.setItem("permissions", JSON.stringify(["REPORT_READ", "REPORT_WRITE"]));
    mockRequest.mockImplementation((url: string) => {
      if (url === "reports/e1") {
        return Promise.resolve({
          data: { exam: mockExam, report: mockReport },
        });
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

    setRte("Impression / conclusion (required before signing)…", "Normal.");

    await resolveAiDraft();

    const submitBtn = screen
      .getAllByRole("button", { name: /submit for review/i })
      .find((b) => (b as HTMLButtonElement).disabled === false);
    expect(submitBtn).toBeDefined();
    fireEvent.click(submitBtn!);

    await waitFor(() => {
      const submitCall = mockRequest.mock.calls.find((c: any) => c[0] === "reports/e1/submit");
      expect(submitCall).toBeDefined();
    });
    // The submitted report locks: header shows SUBMITTED and the panel
    // advertises the attending's hands are on it.
    await waitFor(() => {
      expect(screen.getByText("SUBMITTED")).toBeInTheDocument();
    });
    // The report panel advertises the attending's hands are on it; with the
    // App wrapper the same text also renders as the toast, so match loosely.
    expect(screen.getAllByText(/Submitted for attending review/i).length).toBeGreaterThan(0);
    expect(screen.queryByRole("button", { name: /submit for review/i })).not.toBeInTheDocument();
  });

  it("attending returns a submitted report for revision", async () => {
    mockRequest.mockImplementation((url: string) => {
      if (url === "reports/e1") {
        return Promise.resolve({
          data: {
            exam: mockExam,
            report: {
              ...mockReport,
              status: "submitted",
              impression: "Normal.",
            },
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
      // The name renders twice (console topbar + branded report document for
      // the submitted/locked report).
      expect(screen.getAllByText("John Doe").length).toBeGreaterThan(0);
    });
    // The attending's review actions replace the plain sign button.
    expect(screen.getAllByRole("button", { name: /approve & co-sign/i }).length).toBeGreaterThan(0);
    expect(screen.getAllByRole("button", { name: /return for revision/i }).length).toBeGreaterThan(
      0
    );

    fireEvent.click(screen.getAllByRole("button", { name: /return for revision/i })[0]);
    await waitFor(() => {
      expect(screen.getByText("Return Report for Revision")).toBeInTheDocument();
    });
    fireEvent.change(screen.getByPlaceholderText(/What should the resident revise/), {
      target: { value: "Add comparison with prior CT." },
    });
    fireEvent.click(screen.getByText("Return & Reopen Draft"));

    await waitFor(() => {
      const returnCall = mockRequest.mock.calls.find((c: any) => c[0] === "reports/e1/return");
      expect(returnCall).toBeDefined();
    });
    // Back to an editable draft, carrying the attending's feedback.
    await waitFor(() => {
      expect(screen.getByText("DRAFT")).toBeInTheDocument();
    });
    expect(screen.getByText(/Attending returned this report/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Add comparison with prior CT/i).length).toBeGreaterThan(0);
  });

  it("shows version history and restores a prior version (R-06)", async () => {
    mockRequest.mockImplementation((url: string) => {
      if (url === "reports/e1") {
        return Promise.resolve({ data: { exam: mockExam, report: mockReport } });
      }
      if (url === "reports/e1/images") {
        return Promise.resolve({ data: { imaging: false } });
      }
      if (url === "reports/rep-1/versions") {
        return Promise.resolve({
          data: [
            {
              version_number: 1,
              findings: "Initial findings",
              impression: "",
              recommendations: "",
              edited_by: "50",
              created_at: "2026-08-03T09:00:00Z",
            },
            {
              version_number: 2,
              findings: "Older draft text",
              impression: "Prior impression",
              recommendations: "",
              edited_by: "50",
              created_at: "2026-08-03T08:30:00Z",
            },
          ],
        });
      }
      return Promise.resolve({ data: [] });
    });
    renderConsole();

    await waitFor(() => {
      expect(screen.getByText("John Doe")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /version history/i }));

    // History rows render.
    expect(await screen.findByText(/v2/)).toBeInTheDocument();

    // Restore v2 — the console reloads the report with the restored content.
    const restoredReport = {
      ...mockReport,
      findings: "Older draft text",
      impression: "Prior impression",
    };
    mockRequest.mockImplementation((url: string) => {
      if (url === "reports/rep-1/versions/2/restore") {
        return Promise.resolve({ data: restoredReport });
      }
      if (url === "reports/e1") {
        return Promise.resolve({
          data: { exam: mockExam, report: restoredReport },
        });
      }
      if (url === "reports/e1/images") {
        return Promise.resolve({ data: { imaging: false } });
      }
      return Promise.resolve({ data: [] });
    });
    fireEvent.click(screen.getByRole("button", { name: /restore version 2/i }));

    await waitFor(() => {
      expect(mockRequest).toHaveBeenCalledWith(
        "reports/rep-1/versions/2/restore",
        expect.objectContaining({ method: "POST" })
      );
    });
    await waitFor(() => {
      expect(rte("Structured findings — per template or free text…").innerHTML).toContain(
        "Older draft text"
      );
    });
  });

  it("lists prior reports and previews one without leaving (R-07)", async () => {
    mockRequest.mockImplementation((url: string) => {
      if (url === "reports/e1") {
        return Promise.resolve({ data: { exam: mockExam, report: mockReport } });
      }
      if (url === "reports/e1/images") {
        return Promise.resolve({ data: { imaging: false } });
      }
      if (url.startsWith("reports/priors")) {
        return Promise.resolve({
          data: [
            {
              report_id: "rep-9",
              exam_id: "exam-9",
              accession_number: "ACC-009",
              modality: "CT",
              status: "final",
              completed_at: "2025-01-15T10:00:00Z",
              impression_excerpt: "Old impression text",
            },
          ],
        });
      }
      if (url === "reports/exam-9") {
        return Promise.resolve({
          data: {
            exam: mockExam,
            report: {
              ...mockReport,
              id: "rep-9",
              impression: "Full prior impression",
              findings: "Full prior findings",
            },
          },
        });
      }
      return Promise.resolve({ data: [] });
    });
    renderConsole();

    await waitFor(() => {
      expect(screen.getByText("John Doe")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /prior reports/i }));

    expect(await screen.findByText(/Old impression text/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /open prior ACC-009/i }));
    await waitFor(() => {
      expect(mockRequest).toHaveBeenCalledWith("reports/exam-9");
      expect(screen.getByText(/Full prior impression/)).toBeInTheDocument();
    });
  });

  it("submits the case to the teaching library (R-11)", async () => {
    mockNoImaging();
    renderConsole();

    await waitFor(() => {
      expect(screen.getByText("John Doe")).toBeInTheDocument();
    });

    // The secondary actions live in the condensed More menu in the header.
    fireEvent.click(screen.getByRole("button", { name: /more actions/i }));
    fireEvent.click(await screen.findByRole("menuitem", { name: /submit to teaching file/i }));

    fireEvent.change(await screen.findByLabelText("Case title"), {
      target: { value: "Classic subdural" },
    });
    fireEvent.click(screen.getByRole("button", { name: /submit case/i }));

    await waitFor(() => {
      expect(mockRequest).toHaveBeenCalledWith(
        "teaching-files",
        expect.objectContaining({
          method: "POST",
          data: expect.objectContaining({
            exam_id: "e1",
            title: "Classic subdural",
          }),
        })
      );
    });
  });

  it("shows a Weasis launch button for the loaded study (ADR-028)", async () => {
    // Exam with a resolved imaging tree — the study carries a DICOM UID so
    // the header Weasis action appears next to Immersive.
    mockRequest.mockImplementation((url: string) => {
      if (url === "reports/e1") {
        return Promise.resolve({ data: { exam: mockExam, report: mockReport } });
      }
      if (url === "reports/e1/images") {
        return Promise.resolve({
          data: {
            imaging: true,
            patient: {
              studies: [
                {
                  id: 97,
                  accession_number: "E2E-RAD-CT-1",
                  study_instance_uid: "1.2.3.4",
                  series: [
                    {
                      id: 88,
                      files: [{ id: 71, name: "ct-001.dcm" }],
                    },
                  ],
                },
              ],
            },
          },
        });
      }
      if (url === "reports/templates") {
        return Promise.resolve({ data: [] });
      }
      if (url === "reports/reading-list") {
        return Promise.resolve({ data: [] });
      }
      return Promise.resolve({ data: [] });
    });
    renderConsole();

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /weasis/i })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /weasis/i }));
    expect(mockOpenInWeasis).toHaveBeenCalledWith("1.2.3.4");
  });
});
