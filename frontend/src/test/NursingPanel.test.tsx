import React from "react";
import { screen, waitFor } from "@testing-library/react";
import { renderWithAuth } from "./renderWithApp";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";
import NursingPanel from "../technologist/NursingPanel";

const mockVitals = vi.hoisted(() => vi.fn());
const mockRecordVitals = vi.hoisted(() => vi.fn());
const mockGetChecklist = vi.hoisted(() => vi.fn());
const mockUpdateChecklist = vi.hoisted(() => vi.fn());
const mockGetConsent = vi.hoisted(() => vi.fn());
const mockRecordConsent = vi.hoisted(() => vi.fn());
const mockGetNotes = vi.hoisted(() => vi.fn());
const mockAddNote = vi.hoisted(() => vi.fn());

vi.mock("../api/nursing", () => ({
  getExamVitals: mockVitals,
  recordExamVitals: mockRecordVitals,
  getChecklist: mockGetChecklist,
  updateChecklist: mockUpdateChecklist,
  getConsent: mockGetConsent,
  recordConsent: mockRecordConsent,
  getNurseNotes: mockGetNotes,
  addNurseNote: mockAddNote,
}));

// jsdom has no canvas: stand in a pad whose capture returns a data URL once
// the test "draws" (fires onSignatureChange).
let padDrawn = false;
vi.mock("../common/SignaturePad", () => ({
  __esModule: true,
  default: React.forwardRef(function MockPad(_props: any, ref: any) {
    React.useImperativeHandle(ref, () => ({
      // No canvas exists under jsdom; the drawn flag alone drives capture.
      capture: () => (padDrawn ? "data:image/png;base64,AAAA" : ""),
      clear: () => {
        padDrawn = false;
      },
    }));
    return (
      <button
        type="button"
        aria-label="mock signature pad"
        onClick={() => {
          padDrawn = true;
          _props.onSignatureChange?.(true);
        }}
      >
        draw
      </button>
    );
  }),
}));

const EXAM = { id: "e1", patient_id: "P1", patient_name: "Jane Doe" };

const DEFAULT_ITEMS = [
  { key: "allergy_verification", label: "Allergy verification", required: true, checked: false },
  { key: "medication_review", label: "Medication review", required: true, checked: false },
  { key: "npo_status", label: "NPO status verified", required: true, checked: false },
  { key: "consent_form", label: "Consent form on file", required: true, checked: false },
  { key: "id_band_verified", label: "ID band verified", required: true, checked: false },
];

function setSession(perms: string[]) {
  localStorage.clear();
  localStorage.setItem("token", "t");
  localStorage.setItem("userId", "u2");
  localStorage.setItem("admin", "false");
  localStorage.setItem("role", "care_coordinator");
  localStorage.setItem("permissions", JSON.stringify(perms));
}

function renderPanel() {
  return renderWithAuth(<NursingPanel exam={EXAM} />);
}

beforeEach(() => {
  vi.clearAllMocks();
  padDrawn = false;
  setSession(["NURSING_READ", "NURSING_WRITE"]);
  mockVitals.mockResolvedValue([
    { id: "v1", bp_systolic: 120, bp_diastolic: 80, hr: 72, recorded_at: "2026-08-25T10:00:00Z" },
  ]);
  mockGetChecklist.mockResolvedValue({
    id: "c1",
    status: "in_progress",
    items: DEFAULT_ITEMS,
  });
  mockGetConsent.mockResolvedValue(null);
  mockGetNotes.mockResolvedValue([
    { id: "n1", note: "IV placed.", author_id: "7", created_at: "2026-08-25T09:00:00Z" },
  ]);
  mockUpdateChecklist.mockImplementation((_examId: string, p: any) =>
    Promise.resolve({
      id: "c1",
      items: p.items,
      status: p.confirmed ? "complete" : "in_progress",
    })
  );
  mockRecordConsent.mockResolvedValue({ id: "k1", accepted: true, signed_at: "now" });
  mockAddNote.mockResolvedValue({ id: "n2", note: "x", created_at: "now" });
  mockRecordVitals.mockResolvedValue({ id: "v9" });
});

describe("NursingPanel visibility", () => {
  it("renders nothing for holders of neither NURSING_READ nor EXAM_READ", () => {
    setSession(["PATIENT_READ"]);
    const { queryByTestId } = renderPanel();
    // The permission gate is synchronous — a waitFor here would pass
    // vacuously on the first tick even if the panel leaked through.
    expect(queryByTestId("nursing-panel")).not.toBeInTheDocument();
  });

  it("shows records read-only for EXAM_READ-only holders (spec N-04)", async () => {
    setSession(["EXAM_READ"]);
    const { getByTestId } = renderPanel();
    expect(getByTestId("nursing-panel")).toBeInTheDocument();
    expect(await screen.findByText("read-only")).toBeInTheDocument();
    // Write controls stay hidden.
    expect(screen.queryByText("Record vitals")).not.toBeInTheDocument();
    expect(screen.queryByText("Add note")).not.toBeInTheDocument();
  });
});

describe("NursingPanel vitals (N-01)", () => {
  it("lists recorded vitals and submits new ones", async () => {
    const user = userEvent.setup();
    renderPanel();

    expect(await screen.findByText("120/80")).toBeInTheDocument();

    await user.type(await screen.findByPlaceholderText("SpO₂"), "98");
    await user.click(screen.getByRole("button", { name: /record vitals/i }));

    await waitFor(() => {
      expect(mockRecordVitals).toHaveBeenCalledWith("e1", expect.objectContaining({ spo2: 98 }));
    });
  });
});

describe("NursingPanel checklist (N-02)", () => {
  async function openChecklistTab() {
    const user = userEvent.setup();
    renderPanel();
    await user.click(await screen.findByRole("tab", { name: /pre-procedure/i }));
    return user;
  }

  it("keeps Confirm disabled until every required item is checked", async () => {
    const user = await openChecklistTab();

    const confirmBtn = await screen.findByRole("button", {
      name: /confirm checklist/i,
    });
    expect(confirmBtn).toBeDisabled();

    for (const item of DEFAULT_ITEMS) {
      // The checkbox label carries a trailing 'required' tag; click the
      // wrapping <label> element.
      const labelEl = screen.getAllByText(item.label)[0].closest("label");
      await user.click(labelEl as HTMLElement);
    }
    await waitFor(() => expect(confirmBtn).toBeEnabled());

    await user.click(confirmBtn);
    await waitFor(() => {
      expect(mockUpdateChecklist).toHaveBeenCalledWith(
        "e1",
        expect.objectContaining({ confirmed: true })
      );
    });
  });

  it("saves progress without confirming", async () => {
    const user = await openChecklistTab();
    await screen.findByRole("button", { name: /confirm checklist/i });

    await user.click(screen.getByRole("button", { name: /save progress/i }));

    await waitFor(() => {
      expect(mockUpdateChecklist).toHaveBeenCalledWith(
        "e1",
        expect.objectContaining({ confirmed: false })
      );
    });
  });
});

describe("NursingPanel consent (N-03)", () => {
  it("enables Store consent only after acknowledgment and a signature", async () => {
    const user = userEvent.setup();
    renderPanel();

    await user.click(await screen.findByRole("tab", { name: /contrast consent/i }));

    await user.click(await screen.findByRole("checkbox", { name: /risks acknowledged/i }));
    const storeBtn = screen.getByRole("button", { name: /store consent/i });
    expect(storeBtn).toBeDisabled();

    // Simulate drawing on the pad.
    await user.click(screen.getByRole("button", { name: /mock signature pad/i }));
    await waitFor(() => expect(storeBtn).toBeEnabled());

    await user.click(storeBtn);
    await waitFor(() => {
      expect(mockRecordConsent).toHaveBeenCalledWith(
        "e1",
        expect.objectContaining({
          accepted: true,
          signature_png: "data:image/png;base64,AAAA",
          consent_text_version: "contrast-v1",
        })
      );
    });
  });

  it("shows an existing consent decision instead of the form", async () => {
    mockGetConsent.mockResolvedValue({
      id: "k1",
      accepted: false,
      declined_reason: "Patient refused",
      signed_at: "2026-08-25T09:30:00Z",
    });
    const user = userEvent.setup();
    renderPanel();

    await user.click(await screen.findByRole("tab", { name: /contrast consent/i }));

    expect(await screen.findByText("DECLINED")).toBeInTheDocument();
    expect(screen.getByText(/Patient refused/)).toBeInTheDocument();
    expect(screen.queryByRole("checkbox", { name: /risks acknowledged/i })).not.toBeInTheDocument();
  });
});

describe("NursingPanel load failures", () => {
  it("surfaces a retryable error when the checklist fetch fails", async () => {
    mockGetChecklist.mockRejectedValue(new Error("backend down"));
    const user = userEvent.setup();
    renderPanel();

    await user.click(await screen.findByRole("tab", { name: /pre-procedure/i }));
    const banner = await screen.findByTestId("nursing-checklist-load-error");
    expect(banner).toHaveTextContent(/failed to load/i);

    // Retry recovers once the API answers again.
    mockGetChecklist.mockResolvedValue({
      id: "c1",
      status: "in_progress",
      items: DEFAULT_ITEMS,
    });
    await user.click(screen.getByRole("button", { name: /retry/i }));
    expect(await screen.findByText("Allergy verification")).toBeInTheDocument();
    expect(screen.queryByTestId("nursing-checklist-load-error")).not.toBeInTheDocument();
  });

  it("flags vitals load failures instead of rendering an empty record", async () => {
    mockVitals.mockRejectedValue(new Error("timeout"));
    renderPanel();

    // Vitals is the initial tab — no click needed.
    expect(await screen.findByTestId("nursing-vitals-load-error")).toBeInTheDocument();
    // The empty-table message must NOT imply "no vitals exist".
    expect(screen.queryByText(/No vitals recorded for this exam yet/)).not.toBeInTheDocument();
  });

  it("flags consent load failures above the consent form", async () => {
    mockGetConsent.mockRejectedValue(new Error("boom"));
    const user = userEvent.setup();
    renderPanel();

    await user.click(await screen.findByRole("tab", { name: /contrast consent/i }));
    expect(await screen.findByTestId("nursing-consent-load-error")).toBeInTheDocument();
  });

  it("flags nurse notes load failures instead of the empty-state copy", async () => {
    mockGetNotes.mockRejectedValue(new Error("boom"));
    const user = userEvent.setup();
    renderPanel();

    await user.click(await screen.findByRole("tab", { name: /^notes$/i }));
    expect(await screen.findByTestId("nursing-notes-load-error")).toBeInTheDocument();
    expect(screen.queryByText(/No nurse notes on this exam yet/)).not.toBeInTheDocument();
  });
});

describe("NursingPanel notes (N-04)", () => {
  it("lists existing notes and posts new ones", async () => {
    const user = userEvent.setup();
    renderPanel();

    await user.click(await screen.findByRole("tab", { name: /^notes$/i }));

    expect(await screen.findByText("IV placed.")).toBeInTheDocument();

    await user.type(await screen.findByPlaceholderText(/nursing note visible/i), "Patient ready.");
    await user.click(screen.getByRole("button", { name: /add note/i }));

    await waitFor(() => {
      expect(mockAddNote).toHaveBeenCalledWith("e1", "Patient ready.");
    });
  });
});
