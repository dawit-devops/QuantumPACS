import React from "react";
import { render, screen, waitFor, fireEvent, within } from "@testing-library/react";
import { App as AntdApp } from "antd";
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
    // ExamConsole uses App.useApp() for message/notification — that context
    // comes from antd's App provider, which must wrap the tree in tests
    // exactly as index.tsx does (the static message.* patch in setup.ts is
    // not the App.useApp() instance, so without the provider every
    // message.error/success call throws and the test hangs on retries).
    <AntdApp>
      <ThemeProvider>
        <AuthProvider>
          <MemoryRouter initialEntries={["/exams/e1"]}>
            <Routes>
              <Route path="/exams/:id" element={<ExamConsole />} />
              {/* Stub target for the Ctrl+Shift+W worklist shortcut test. */}
              <Route path="/exams" element={<div>Worklist Stub</div>} />
            </Routes>
          </MemoryRouter>
        </AuthProvider>
      </ThemeProvider>
    </AntdApp>
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
  // T-14: this CT exam has cleared the pregnancy/radiation-risk
  // acknowledgment, so acquiring is allowed (the gate tests below use a
  // copy with the check stripped).
  safety_checks: [
    {
      id: "sc-1",
      check_item: "Not pregnant (or documented radiation risk accepted)",
      answer: "confirmed",
      checked_by: "u1",
    },
  ],
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
      expect(screen.getByText("Patient Identity Verification")).toBeInTheDocument();
    });
    expect(screen.getByText("John Doe")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Confirm Patient/i })).toBeInTheDocument();
  });

  it("confirms identity and moves to in-progress", async () => {
    mockRequest.mockImplementation((url: string) => {
      if (url === "exams/e1") return Promise.resolve({ data: readyExam });
      if (url === "protocols") return Promise.resolve(mockProtocols);
      return Promise.resolve({ data: [] });
    });
    renderConsole();

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /Confirm Patient/i })).toBeInTheDocument();
    });

    // Confirm identity writes via the API; the refetch returns in-progress.
    mockRequest.mockImplementation((url: string) => {
      if (url === "exams/e1/identity-confirm") return Promise.resolve({ data: {} });
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

  it("favorites a protocol from the picker (T-06)", async () => {
    const protocolsWithIds = {
      data: [
        {
          id: "p1",
          name: "CT Head (Routine)",
          modality: "CT",
          body_part: "Head",
          is_default: true,
          is_favorite: false,
          sequences: [],
        },
        {
          id: "p2",
          name: "CT Chest (Routine)",
          modality: "CT",
          body_part: "Chest",
          is_default: false,
          is_favorite: false,
          sequences: [],
        },
      ],
    };
    mockRequest.mockImplementation((url: string) => {
      if (url === "exams/e1") return Promise.resolve({ data: readyExam });
      if (url === "protocols") return Promise.resolve(protocolsWithIds);
      return Promise.resolve({ data: [] });
    });
    renderConsole();

    // Default selection lands on the default protocol; favorite it.
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /favorite protocol/i })).toBeInTheDocument();
    });

    let favState = false;
    mockRequest.mockImplementation((url: string) => {
      if (url === "protocols/p1/favorite") {
        favState = !favState;
        return Promise.resolve({
          data: { protocol_id: "p1", is_favorite: favState },
        });
      }
      if (url === "exams/e1") return Promise.resolve({ data: readyExam });
      if (url === "protocols") return Promise.resolve(protocolsWithIds);
      return Promise.resolve({ data: [] });
    });
    fireEvent.click(screen.getByRole("button", { name: /favorite protocol/i }));

    // The star flips without a refetch.
    await waitFor(() => {
      expect(mockRequest).toHaveBeenCalledWith(
        "protocols/p1/favorite",
        expect.objectContaining({ method: "POST" })
      );
      expect(screen.getByRole("button", { name: /unfavorite protocol/i })).toBeInTheDocument();
    });
  });

  it("narrows the registry with favorites-only and body part filters (T-06)", async () => {
    const protocolsWithFav = {
      data: [
        {
          id: "p1",
          name: "CT Head (Routine)",
          modality: "CT",
          body_part: "Head",
          is_default: true,
          is_favorite: true,
          sequences: [],
        },
        {
          id: "p2",
          name: "CT Chest (Routine)",
          modality: "CT",
          body_part: "Chest",
          is_default: false,
          is_favorite: false,
          sequences: [],
        },
      ],
    };
    mockRequest.mockImplementation((url: string) => {
      if (url === "exams/e1") return Promise.resolve({ data: readyExam });
      if (url === "protocols") return Promise.resolve(protocolsWithFav);
      return Promise.resolve({ data: [] });
    });
    const { container } = renderConsole();

    // Open the registry dropdown — antd only mounts options when open.
    const openDropdown = async () => {
      const combos = await screen.findAllByRole("combobox");
      fireEvent.mouseDown(combos[0]);
    };
    await openDropdown();
    await waitFor(() => {
      expect(screen.getByRole("option", { name: "CT Chest (Routine)" })).toBeInTheDocument();
    });

    // Favorites-only hides the non-favorite chest protocol.
    fireEvent.click(screen.getByRole("checkbox", { name: /favorites only/i }));
    await openDropdown();
    await waitFor(() => {
      expect(screen.queryByRole("option", { name: "CT Chest (Routine)" })).toBeNull();
      expect(screen.getAllByRole("option", { name: /CT Head \(Routine\)/ }).length).toBeGreaterThan(
        0
      );
    });
  });

  it("narrows the registry by clinical indication (T-06)", async () => {
    const protocolsWithInd = {
      data: [
        {
          id: "p1",
          name: "CT Head (Trauma)",
          modality: "CT",
          body_part: "Head",
          clinical_indication: "Head trauma, stroke, severe headache",
          is_default: false,
          is_favorite: false,
          sequences: [],
        },
        {
          id: "p2",
          name: "CT Abdomen (Routine)",
          modality: "CT",
          body_part: "Abdomen",
          clinical_indication: "Abdominal pain, abnormal LFTs",
          is_default: false,
          is_favorite: false,
          sequences: [],
        },
      ],
    };
    mockRequest.mockImplementation((url: string) => {
      if (url === "exams/e1") return Promise.resolve({ data: readyExam });
      if (url === "protocols") return Promise.resolve(protocolsWithInd);
      return Promise.resolve({ data: [] });
    });
    renderConsole();

    // Pick "stroke" from the indication filter — the abdomen protocol,
    // whose indications never mention stroke, drops out of the registry.
    const indCombo = await screen.findByRole("combobox", {
      name: /filter by indication/i,
    });
    fireEvent.mouseDown(indCombo);
    // antd mounts the open dropdown's items without role attributes under
    // jsdom, so target the option elements directly.
    await waitFor(() => {
      const opts = Array.from(document.querySelectorAll<HTMLElement>(".ant-select-item-option"));
      expect(opts.some((o) => o.textContent === "stroke")).toBe(true);
    });
    const strokeOpt = Array.from(
      document.querySelectorAll<HTMLElement>(".ant-select-item-option")
    ).find((o) => o.textContent === "stroke");
    fireEvent.click(strokeOpt!);

    // Open the registry dropdown and confirm the narrowed option list.
    const combos = await screen.findAllByRole("combobox");
    fireEvent.mouseDown(combos[0]);
    await waitFor(() => {
      const names = Array.from(
        document.querySelectorAll<HTMLElement>(".ant-select-item-option")
      ).map((o) => o.textContent);
      expect(names).not.toContain("CT Abdomen (Routine)");
      expect(names).toContain("CT Head (Trauma)");
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
      expect(screen.getByRole("button", { name: /Acquire Image/i })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /Acquire Image/i }));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /Accept/i })).toBeInTheDocument();
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
      if (url.includes("/accept")) return Promise.resolve({ data: { status: "accepted" } });
      return Promise.resolve({ data: [] });
    });
    renderConsole();

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /Acquire Image/i })).toBeInTheDocument();
    });
    fireEvent.click(screen.getByRole("button", { name: /Acquire Image/i }));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /Accept/i })).toBeInTheDocument();
    });
    fireEvent.click(screen.getByRole("button", { name: /Accept/i }));

    await waitFor(() => {
      expect(screen.queryByRole("button", { name: /Accept/i })).not.toBeInTheDocument();
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
      expect(screen.getByRole("button", { name: /Emergency Override/i })).toBeInTheDocument();
    });
    fireEvent.click(screen.getByRole("button", { name: /Emergency Override/i }));

    await waitFor(() => {
      expect(screen.getByText("Emergency Protocol Override")).toBeInTheDocument();
    });
    // Submit without justification — validation should block the API call.
    fireEvent.click(screen.getByRole("button", { name: /Confirm Override/i }));

    await waitFor(() => {
      expect(screen.getByText(/Justification is required/i)).toBeInTheDocument();
    });
  });

  it("logs an incident through the modal", async () => {
    mockRequest.mockImplementation((url: string) => {
      if (url === "exams/e1") return Promise.resolve({ data: inProgressExam });
      if (url === "protocols") return Promise.resolve(mockProtocols);
      if (url === "exams/e1/incidents") return Promise.resolve({ data: { id: "inc-1" } });
      return Promise.resolve({ data: [] });
    });
    renderConsole();

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /Log Incident/i })).toBeInTheDocument();
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
      expect(screen.getByText(/Exam completed and handed off/i)).toBeInTheDocument();
    });
  });

  it("keeps a rejected acquisition visible with Retake and Log Incident", async () => {
    let examState: any = { ...inProgressExam, acquisitions: [] };
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
        };
        return Promise.resolve({ data: acq });
      }
      if (url.endsWith("/reject")) {
        // The server marks the acquisition rejected with the reason; the
        // console refetches and must surface it in the Rejected section.
        examState = {
          ...examState,
          acquisitions: examState.acquisitions.map((a: any) =>
            a.id === "acq-1" ? { ...a, status: "rejected", reject_reason: "Patient motion" } : a
          ),
        };
        return Promise.resolve({
          data: { status: "rejected", rejected_count: 1 },
        });
      }
      return Promise.resolve({ data: [] });
    });
    renderConsole();

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /Acquire Image/i })).toBeInTheDocument();
    });
    fireEvent.click(screen.getByRole("button", { name: /Acquire Image/i }));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /Reject/i })).toBeInTheDocument();
    });
    fireEvent.click(screen.getByRole("button", { name: /Reject/i }));

    // Pick a reject reason in the modal, then confirm.
    await waitFor(() => {
      expect(screen.getByRole("dialog")).toBeInTheDocument();
    });
    fireEvent.mouseDown(within(screen.getByRole("dialog")).getByLabelText("Reject reason"));
    await waitFor(() => {
      expect(document.querySelectorAll(".ant-select-item-option").length).toBeGreaterThan(0);
    });
    const option = Array.from(document.querySelectorAll(".ant-select-item-option")).find(
      (o) => o.textContent === "Patient motion"
    );
    expect(option).toBeTruthy();
    fireEvent.click(option!);
    // Modal title and OK button both read "Reject Image" — target the
    // button inside the dialog.
    fireEvent.click(
      within(screen.getByRole("dialog")).getByRole("button", {
        name: "Reject Image",
      })
    );

    // The rejected acquisition stays visible with reason + actions.
    await waitFor(() => {
      expect(screen.getByText(/Rejected \(1\)/)).toBeInTheDocument();
    });
    expect(screen.getByText(/Patient motion/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Retake/i })).toBeInTheDocument();
    // The rejected item's Log Incident button exists alongside the header's.
    const logIncidentBtns = screen.getAllByRole("button", {
      name: /Log Incident/i,
    });
    expect(logIncidentBtns.length).toBeGreaterThan(1);
  });

  it("retakes a rejected acquisition with an incremented series", async () => {
    // The ledger already holds an accepted series 3 (as after a reload),
    // so the retake of rejected series 1 must jump to 4 — never reuse a
    // series number that's already in the dose ledger.
    let examState: any = {
      ...inProgressExam,
      acquisitions: [
        {
          id: "acq-1",
          series_number: 1,
          description: "Localizer",
          status: "rejected",
          reject_reason: "Patient motion",
        },
        {
          id: "acq-3",
          series_number: 3,
          description: "Diagnostic series",
          status: "accepted",
        },
      ],
    };
    mockRequest.mockImplementation((url: string) => {
      if (url === "exams/e1") return Promise.resolve({ data: examState });
      if (url === "protocols") return Promise.resolve(mockProtocols);
      if (url === "exams/e1/acquisitions") {
        const acq = {
          id: "acq-4",
          series_number: 4,
          description: "Retake — Localizer",
          kvp: 120,
          mas: 210,
          dlp: 520,
          ctdivol: 12.5,
        };
        examState = {
          ...examState,
          acquisitions: [...examState.acquisitions, acq],
        };
        return Promise.resolve({ data: acq });
      }
      return Promise.resolve({ data: [] });
    });
    renderConsole();

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /Retake/i })).toBeInTheDocument();
    });
    fireEvent.click(screen.getByRole("button", { name: /Retake/i }));

    await waitFor(() => {
      const acqCall = mockRequest.mock.calls.find((c: any[]) => c[0] === "exams/e1/acquisitions");
      expect(acqCall).toBeTruthy();
      expect(acqCall![1].data.series_number).toBe(4);
      expect(acqCall![1].data.description).toBe("Retake — Localizer");
    });
    // The retake lands in the pending QA queue for accept/reject.
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /Accept/i })).toBeInTheDocument();
    });
  });

  it("shows server-pending acquisitions in the QA queue after a reload", async () => {
    // After a reload the pending acquisition comes back in exam.acquisitions
    // with status 'pending' (no optimistic local state) and must still offer
    // Accept/Reject (FR-R06-04).
    const examState: any = {
      ...inProgressExam,
      acquisitions: [
        {
          id: "acq-7",
          series_number: 2,
          description: "Diagnostic series",
          kvp: 120,
          dlp: 830,
          ctdivol: 17.5,
          status: "pending",
        },
      ],
    };
    mockRequest.mockImplementation((url: string) => {
      if (url === "exams/e1") return Promise.resolve({ data: examState });
      if (url === "protocols") return Promise.resolve(mockProtocols);
      return Promise.resolve({ data: [] });
    });
    renderConsole();

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /Accept/i })).toBeInTheDocument();
    });
    expect(screen.getByRole("button", { name: /Reject/i })).toBeInTheDocument();
    expect(screen.getByText("QA Queue (1 pending)")).toBeInTheDocument();
    // Each pending item is represented by a thumbnail, not text only (§3-10).
    expect(document.querySelectorAll(".sim-preview-canvas-mini").length).toBeGreaterThan(0);
  });

  it("pre-fills the incident modal from a rejected acquisition", async () => {
    const examState: any = {
      ...inProgressExam,
      acquisitions: [
        {
          id: "acq-1",
          series_number: 1,
          description: "Localizer",
          status: "rejected",
          reject_reason: "Patient motion",
        },
      ],
    };
    mockRequest.mockImplementation((url: string) => {
      if (url === "exams/e1") return Promise.resolve({ data: examState });
      if (url === "protocols") return Promise.resolve(mockProtocols);
      return Promise.resolve({ data: [] });
    });
    renderConsole();

    // Two "Log Incident" buttons exist (console header + rejected item); the
    // rejected item's action pre-fills the incident modal.
    const logIncidentBtn = await screen.findAllByRole("button", {
      name: /Log Incident/i,
    });
    expect(logIncidentBtn.length).toBeGreaterThan(1);
    fireEvent.click(logIncidentBtn[logIncidentBtn.length - 1]);

    // The incident type is pre-filled from the reject reason and the
    // description names the rejected series.
    await waitFor(() => {
      expect(screen.getByRole("dialog")).toBeInTheDocument();
    });
    // The Select renders the readable label (underscores stripped).
    expect(screen.getByText("patient motion")).toBeInTheDocument();
    expect(screen.getByDisplayValue(/Rejected series 1 \(Patient motion\)/)).toBeInTheDocument();
  });

  it("shows prior studies with a comparison link in the identity card", async () => {
    const examWithPriors = {
      ...readyExam,
      prior_studies: [
        {
          id: 101,
          description: "CT Head Prior",
          accession_number: "ACC-P1",
          modality: "CT",
          series_count: 2,
          file_count: 1,
          first_file_id: 501,
        },
      ],
    };
    mockRequest.mockImplementation((url: string) => {
      if (url === "exams/e1") return Promise.resolve({ data: examWithPriors });
      if (url === "protocols") return Promise.resolve(mockProtocols);
      return Promise.resolve({ data: [] });
    });
    renderConsole();

    await waitFor(() => {
      expect(screen.getByText("Patient Identity Verification")).toBeInTheDocument();
    });
    // Prior study description + modality render with a viewer link.
    expect(screen.getByText(/CT Head Prior/)).toBeInTheDocument();
    const link = screen.getByRole("link", { name: /Open in viewer/i });
    expect(link.getAttribute("href")).toBe("/files/501");
  });

  it("records only individually confirmed safety checks with a pregnancy warning", async () => {
    // The checklist only renders while no checks are recorded yet — the
    // shared inProgress fixture carries the ack, so strip it here.
    mockRequest.mockImplementation((url: string) => {
      if (url === "exams/e1")
        return Promise.resolve({ data: { ...inProgressExam, safety_checks: [] } });
      if (url === "protocols") return Promise.resolve(mockProtocols);
      return Promise.resolve({ data: [] });
    });
    renderConsole();

    await waitFor(() => {
      expect(screen.getByText("Safety Checks (pre-contrast)")).toBeInTheDocument();
    });

    // The pregnancy item surfaces a radiation warning (FR-R06-06).
    expect(screen.getByText(/Ionizing radiation risk/i)).toBeInTheDocument();

    // Record stays disabled until at least one item is explicitly confirmed.
    const recordBtn = screen.getByRole("button", {
      name: /Record Safety Checks/i,
    });
    expect(recordBtn.hasAttribute("disabled")).toBe(true);

    fireEvent.click(screen.getByLabelText("No known contrast allergies"));
    expect(recordBtn.hasAttribute("disabled")).toBe(false);

    fireEvent.click(recordBtn);

    // Only the confirmed item is sent — not a hardcoded all-confirmed list.
    await waitFor(() => {
      const call = mockRequest.mock.calls.find((c: any[]) => c[0] === "exams/e1/safety-checks");
      expect(call).toBeTruthy();
    });
    const call = mockRequest.mock.calls.find((c: any[]) => c[0] === "exams/e1/safety-checks");
    expect(call![1].data.checks).toEqual([
      {
        check_item: "No known contrast allergies",
        answer: "confirmed",
        notes: "",
      },
    ]);
  });

  it("disables acquiring until the pregnancy acknowledgment is recorded (T-14)", async () => {
    // Mirrors the server gate in api/exams.py — a CT exam without a recorded
    // pregnancy/radiation-risk check cannot acquire, client or server side.
    mockRequest.mockImplementation((url: string) => {
      if (url === "exams/e1")
        return Promise.resolve({ data: { ...inProgressExam, safety_checks: [] } });
      if (url === "protocols") return Promise.resolve(mockProtocols);
      return Promise.resolve({ data: [] });
    });
    renderConsole();

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /Acquire Image/i })).toBeInTheDocument();
    });
    const btn = screen.getByRole("button", { name: /Acquire Image/i });
    expect(btn.hasAttribute("disabled")).toBe(true);
    // The acquisition surface explains why (the Safety Checks card carries
    // the checklist that resolves it).
    expect(screen.getByText(/pregnancy\/radiation-risk acknowledgment/i)).toBeInTheDocument();
  });

  it("unlocks acquiring after the pregnancy check is recorded (T-14)", async () => {
    let examState: any = {
      ...inProgressExam,
      safety_checks: [],
      acquisitions: [],
    };
    mockRequest.mockImplementation((url: string) => {
      if (url === "exams/e1") return Promise.resolve({ data: examState });
      if (url === "protocols") return Promise.resolve(mockProtocols);
      if (url === "exams/e1/safety-checks") {
        examState = {
          ...examState,
          safety_checks: [
            {
              id: "sc-9",
              check_item: "Not pregnant (or documented radiation risk accepted)",
              answer: "confirmed",
            },
          ],
        };
        return Promise.resolve({ data: { recorded: 2 } });
      }
      return Promise.resolve({ data: [] });
    });
    renderConsole();

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /Acquire Image/i })).toBeInTheDocument();
    });
    expect(screen.getByRole("button", { name: /Acquire Image/i }).hasAttribute("disabled")).toBe(
      true
    );

    // Confirm the pregnancy item and record — the refetched exam carries the
    // ack row and Acquire unlocks.
    fireEvent.click(screen.getByLabelText(/Not pregnant \(or documented radiation risk/i));
    fireEvent.click(screen.getByRole("button", { name: /Record Safety Checks/i }));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /Acquire Image/i }).hasAttribute("disabled")).toBe(
        false
      );
    });
  });

  it("does not gate non-ionizing modalities (T-14)", async () => {
    mockRequest.mockImplementation((url: string) => {
      if (url === "exams/e1")
        return Promise.resolve({
          data: { ...inProgressExam, modality: "MR", safety_checks: [] },
        });
      if (url === "protocols") return Promise.resolve(mockProtocols);
      return Promise.resolve({ data: [] });
    });
    renderConsole();

    await waitFor(() => {
      const btn = screen.getByRole("button", { name: /Acquire Image/i });
      expect(btn.hasAttribute("disabled")).toBe(false);
    });
    expect(screen.queryByText(/pregnancy\/radiation-risk acknowledgment/i)).toBeNull();
  });

  it("lists per-series dose and flags the panel when the benchmark is exceeded", async () => {
    const examWithDose = {
      ...inProgressExam,
      dose: {
        total_dlp: 1350,
        total_ctdivol: 30,
        total_mas: 400,
        total_exposure: 0,
      },
      dose_level: "danger",
      acquisitions: [
        {
          id: "acq-1",
          series_number: 1,
          description: "Localizer",
          kvp: 120,
          dlp: 520,
          ctdivol: 12.5,
          status: "accepted",
        },
        {
          id: "acq-2",
          series_number: 2,
          description: "Diagnostic series",
          kvp: 120,
          dlp: 830,
          ctdivol: 17.5,
          status: "accepted",
        },
      ],
    };
    mockRequest.mockImplementation((url: string) => {
      if (url === "exams/e1") return Promise.resolve({ data: examWithDose });
      if (url === "protocols") return Promise.resolve(mockProtocols);
      return Promise.resolve({ data: [] });
    });
    renderConsole();

    await waitFor(() => {
      expect(screen.getByText("Per-series dose")).toBeInTheDocument();
    });
    expect(screen.getByText("S1 · Localizer")).toBeInTheDocument();
    expect(screen.getByText("S2 · Diagnostic series")).toBeInTheDocument();
    // dose_level danger flags the panel itself, not just the progress bar.
    expect(screen.getByText(/ACR dose benchmark exceeded/i)).toBeInTheDocument();
  });

  it("navigates to the worklist on Ctrl+Shift+W", async () => {
    mockRequest.mockImplementation((url: string) => {
      if (url === "exams/e1") return Promise.resolve({ data: inProgressExam });
      if (url === "protocols") return Promise.resolve(mockProtocols);
      return Promise.resolve({ data: [] });
    });
    renderConsole();

    await waitFor(() => {
      expect(screen.getByText("Patient Identity Verification")).toBeInTheDocument();
    });

    fireEvent.keyDown(window, { key: "w", ctrlKey: true, shiftKey: true });

    await waitFor(() => {
      expect(screen.getByText("Worklist Stub")).toBeInTheDocument();
    });
  });

  it("renders a read-only console for an EXAM_READ-only user", async () => {
    // nurse / resident hold EXAM_READ only: every acquisition write
    // (identity, protocol, acquire, safety, complete) is EXAM_WRITE-gated.
    localStorage.setItem("permissions", JSON.stringify(["EXAM_READ"]));
    mockRequest.mockImplementation((url: string) => {
      if (url === "exams/e1") return Promise.resolve({ data: readyExam });
      if (url === "protocols") return Promise.resolve(mockProtocols);
      return Promise.resolve({ data: [] });
    });
    renderConsole();

    await waitFor(() => {
      expect(screen.getByText("Patient Identity Verification")).toBeInTheDocument();
    });
    expect(screen.queryByRole("button", { name: /Confirm Patient/i })).not.toBeInTheDocument();
    expect(screen.queryByText("Start Protocol")).not.toBeInTheDocument();
    expect(screen.queryByText("Acquire Image")).not.toBeInTheDocument();
    expect(screen.queryByText("Complete Exam")).not.toBeInTheDocument();
    expect(screen.queryByText("Log Incident")).not.toBeInTheDocument();
    expect(screen.getByText("Read-only exam console")).toBeInTheDocument();
  });

  it("shows the next patient's queue wait as the ETA (T-03)", async () => {
    // The next-in-pool exam has been ready for 23 minutes — the console
    // surfaces that wait so the tech can sequence the room without
    // tabbing back to the worklist mid-scan.
    const waitedExam = {
      ...readyExam,
      id: "e2",
      accession_number: "ACC-NEXT",
      patient_name: "Next Patient",
      modality: "CT",
      priority: "urgent",
      status: "ready",
      created_at: new Date(Date.now() - 23 * 60_000).toISOString(),
    };
    mockRequest.mockImplementation((url: string) => {
      if (url === "exams/e1") return Promise.resolve({ data: inProgressExam });
      if (url === "protocols") return Promise.resolve(mockProtocols);
      if (url === "exams") return Promise.resolve({ data: [waitedExam] });
      return Promise.resolve({ data: [] });
    });
    renderConsole();

    // The provider bootstrap remounts the console a few times before
    // settling, so give the banner's async fetch room beyond the default.
    expect(await screen.findByText(/waiting 23 min/i, {}, { timeout: 5000 })).toBeInTheDocument();
    // The accession rides inside the composite banner text.
    expect(screen.getByText(/ACC-NEXT/)).toBeInTheDocument();
  });

  it("renders a red badge for documented prior contrast reactions (T-04)", async () => {
    const examWithReactions = {
      ...inProgressExam,
      prior_contrast_reactions: [
        {
          incident_type: "contrast_reaction",
          severity: "high",
          description: "Urticaria after iodinated contrast",
          accession_number: "ACC-P9",
          created_at: "2025-11-02T09:00:00Z",
        },
        {
          incident_type: "contrast_reaction",
          severity: "medium",
          description: "Flushing and nausea",
          accession_number: "ACC-P2",
          created_at: "2024-03-15T09:00:00Z",
        },
      ],
    };
    mockRequest.mockImplementation((url: string) => {
      if (url === "exams/e1") return Promise.resolve({ data: examWithReactions });
      if (url === "protocols") return Promise.resolve(mockProtocols);
      return Promise.resolve({ data: [] });
    });
    renderConsole();

    await waitFor(() => {
      // The badge sits in the Safety Checks card — the pre-contrast surface.
      expect(screen.getByTestId("contrast-reaction-badge")).toBeInTheDocument();
    });
    expect(screen.getByText(/prior contrast reactions \(2\)/i)).toBeInTheDocument();
    // Each documented reaction is readable: severity + description.
    expect(screen.getByText(/urticaria after iodinated contrast/i)).toBeInTheDocument();
    expect(screen.getByText(/flushing and nausea/i)).toBeInTheDocument();
  });

  it("shows no reaction badge when the patient history is clean (T-04)", async () => {
    mockRequest.mockImplementation((url: string) => {
      if (url === "exams/e1") return Promise.resolve({ data: inProgressExam });
      if (url === "protocols") return Promise.resolve(mockProtocols);
      return Promise.resolve({ data: [] });
    });
    renderConsole();

    await waitFor(() => {
      expect(screen.getByText("Patient Identity Verification")).toBeInTheDocument();
    });
    expect(screen.queryByTestId("contrast-reaction-badge")).toBeNull();
  });
});
