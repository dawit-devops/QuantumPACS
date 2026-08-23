import React from "react";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { App as AntdApp } from "antd";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import CheckIn from "../kiosk/CheckIn";
import { ThemeProvider } from "../common/ThemeProvider";

const mockGetCheckIn = vi.hoisted(() => vi.fn());
const mockConfirmCheckIn = vi.hoisted(() => vi.fn());
const mockSubmitConsent = vi.hoisted(() => vi.fn());
const mockSubmitPayment = vi.hoisted(() => vi.fn());

vi.mock("../api/checkin", () => ({
  getCheckIn: mockGetCheckIn,
  confirmCheckIn: mockConfirmCheckIn,
  submitConsent: mockSubmitConsent,
  submitPayment: mockSubmitPayment,
}));

vi.mock("../hooks", () => ({
  useDocumentTitle: vi.fn(),
  useTenantRefetch: () => {},
}));

const originalLocation = window.location;

function renderKiosk(token = "test-token-123") {
  // CheckIn reads window.location.search directly — MemoryRouter doesn't set it
  Object.defineProperty(window, "location", {
    value: {
      search: token ? "?token=" + token : "",
      pathname: "/checkin",
    },
    writable: true,
    configurable: true,
  });
  return render(
    <AntdApp>
      <ThemeProvider>
        <MemoryRouter initialEntries={["/checkin?token=" + token]}>
          <CheckIn />
        </MemoryRouter>
      </ThemeProvider>
    </AntdApp>,
  );
}

const SUMMARY = {
  patient_name: "Jane Smith",
  start_time: "2026-08-28T10:30:00Z",
  status: "SCHEDULED",
  modality: "CT",
  prep_instructions: "Fast for 4 hours before your CT exam",
};

beforeEach(() => {
  mockSubmitConsent.mockResolvedValue({ id: "a1", accepted: true });
});

describe("CheckIn (enhanced kiosk)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    Object.defineProperty(window, "location", {
      value: originalLocation,
      writable: true,
      configurable: true,
    });
  });

  // --- Error states ---

  it("shows error when no token in URL", () => {
    renderKiosk("");
    expect(screen.getByText("Cannot check in")).toBeInTheDocument();
    expect(screen.getByText("No check-in token in link.")).toBeInTheDocument();
  });

  it("shows error when API fails", async () => {
    mockGetCheckIn.mockRejectedValue(new Error("Invalid token"));
    renderKiosk();
    expect(
      await screen.findByText("Cannot check in"),
    ).toBeInTheDocument();
  });

  // --- Prep instructions phase ---

  it("shows prep instructions after loading", async () => {
    mockGetCheckIn.mockResolvedValue(SUMMARY);
    renderKiosk();
    expect(
      await screen.findByText(/Preparation Instructions/),
    ).toBeInTheDocument();
  });

  it("displays patient name in welcome message", async () => {
    mockGetCheckIn.mockResolvedValue(SUMMARY);
    renderKiosk();
    expect(
      await screen.findByText(/Welcome, Jane Smith/),
    ).toBeInTheDocument();
  });

  it("shows modality badge", async () => {
    mockGetCheckIn.mockResolvedValue(SUMMARY);
    renderKiosk();
    expect(await screen.findByText("CT Examination")).toBeInTheDocument();
  });

  it("shows appointment time", async () => {
    mockGetCheckIn.mockResolvedValue(SUMMARY);
    renderKiosk();
    await waitFor(() => {
      // Time may render as 10:30 AM or 10:30 depending on locale
      const timeEl = screen.getByTestId("checkin-prep");
      expect(timeEl.textContent).toMatch(/10:30/);
    });
  });

  it("displays prep instructions from backend", async () => {
    mockGetCheckIn.mockResolvedValue(SUMMARY);
    renderKiosk();
    expect(
      await screen.findByText(/Fast for 4 hours/),
    ).toBeInTheDocument();
  });

  it("falls back to default prep instructions when backend provides none", async () => {
    mockGetCheckIn.mockResolvedValue({
      ...SUMMARY,
      prep_instructions: "",
    });
    renderKiosk();
    expect(
      await screen.findByText(/Do not eat or drink for 4 hours/),
    ).toBeInTheDocument();
  });

  it("navigates to consent phase on continue button click", async () => {
    const user = userEvent.setup();
    mockGetCheckIn.mockResolvedValue(SUMMARY);
    renderKiosk();
    await screen.findByText(/Preparation Instructions/);
    await user.click(
      screen.getByText(/I understand — continue to consent/),
    );
    expect(
      screen.getByText("Consent for Imaging"),
    ).toBeInTheDocument();
  });

  // --- Consent form phase ---

  it("shows consent text", async () => {
    const user = userEvent.setup();
    mockGetCheckIn.mockResolvedValue(SUMMARY);
    renderKiosk();
    await screen.findByText(/Preparation Instructions/);
    await user.click(
      screen.getByText(/I understand — continue to consent/),
    );
    expect(
      screen.getByText(/I understand that I am here for an imaging examination/),
    ).toBeInTheDocument();
  });

  it("shows signature pad", async () => {
    const user = userEvent.setup();
    mockGetCheckIn.mockResolvedValue(SUMMARY);
    renderKiosk();
    await screen.findByText(/Preparation Instructions/);
    await user.click(
      screen.getByText(/I understand — continue to consent/),
    );
    expect(screen.getByTestId("signature-canvas")).toBeInTheDocument();
  });

  it("shows consent checkbox", async () => {
    const user = userEvent.setup();
    mockGetCheckIn.mockResolvedValue(SUMMARY);
    renderKiosk();
    await screen.findByText(/Preparation Instructions/);
    await user.click(
      screen.getByText(/I understand — continue to consent/),
    );
    expect(screen.getByTestId("consent-checkbox")).toBeInTheDocument();
  });

  it("submit button is disabled until checkbox and signature", async () => {
    const user = userEvent.setup();
    mockGetCheckIn.mockResolvedValue(SUMMARY);
    renderKiosk();
    await screen.findByText(/Preparation Instructions/);
    await user.click(
      screen.getByText(/I understand — continue to consent/),
    );
    const submitBtn = screen.getByTestId("consent-submit");
    expect(submitBtn).toBeDisabled();
  });

  it("navigates back to prep instructions", async () => {
    const user = userEvent.setup();
    mockGetCheckIn.mockResolvedValue(SUMMARY);
    renderKiosk();
    await screen.findByText(/Preparation Instructions/);
    await user.click(
      screen.getByText(/I understand — continue to consent/),
    );
    await user.click(screen.getByText(/Back to preparation instructions/));
    expect(
      screen.getByText(/Preparation Instructions/),
    ).toBeInTheDocument();
  });

  // --- Ready phase ---

  it("shows ready-to-check-in after consent", async () => {
    const user = userEvent.setup();
    mockGetCheckIn.mockResolvedValue(SUMMARY);
    renderKiosk();
    await screen.findByText(/Preparation Instructions/);
    await user.click(
      screen.getByText(/I understand — continue to consent/),
    );
    // Draw on signature pad — use fireEvent sequence
    const canvas = screen.getByTestId("signature-canvas");
    fireEvent.mouseDown(canvas, { clientX: 10, clientY: 10 });
    fireEvent.mouseMove(canvas, { clientX: 50, clientY: 50 });
    fireEvent.mouseUp(canvas, { clientX: 50, clientY: 50 });
    // Check consent checkbox
    await user.click(screen.getByTestId("consent-checkbox"));
    // Submit consent
    await user.click(screen.getByTestId("consent-submit"));
    // Should now show ready phase
    await waitFor(() => {
      expect(screen.getByText(/I'm here/)).toBeInTheDocument();
    });
  });

  // --- Check-in confirmation ---

  it("confirms check-in and shows success", async () => {
    const user = userEvent.setup();
    mockGetCheckIn.mockResolvedValue(SUMMARY);
    mockConfirmCheckIn.mockResolvedValue({ id: "a1", status: "ARRIVED" });
    renderKiosk();
    await screen.findByText(/Preparation Instructions/);
    await user.click(
      screen.getByText(/I understand — continue to consent/),
    );
    // Draw signature
    const canvas = screen.getByTestId("signature-canvas");
    fireEvent.mouseDown(canvas, { clientX: 10, clientY: 10 });
    fireEvent.mouseMove(canvas, { clientX: 50, clientY: 50 });
    fireEvent.mouseUp(canvas, { clientX: 50, clientY: 50 });
    // Check consent
    await user.click(screen.getByTestId("consent-checkbox"));
    // Submit consent
    await user.click(screen.getByTestId("consent-submit"));
    // Confirm check-in
    await user.click(screen.getByTestId("checkin-confirm"));
    // Co-pay phase — skip it
    await waitFor(() => {
      expect(screen.getByTestId("copay-skip")).toBeInTheDocument();
    });
    await user.click(screen.getByTestId("copay-skip"));
    await waitFor(() => {
      expect(screen.getByText(/checked in/)).toBeInTheDocument();
    });
    expect(mockConfirmCheckIn).toHaveBeenCalledWith("test-token-123");
  });

  it("shows error on duplicate check-in (409)", async () => {
    const user = userEvent.setup();
    mockGetCheckIn.mockResolvedValue(SUMMARY);
    mockConfirmCheckIn.mockRejectedValue({ status: 409, message: "Already" });
    renderKiosk();
    await screen.findByText(/Preparation Instructions/);
    await user.click(
      screen.getByText(/I understand — continue to consent/),
    );
    const canvas = screen.getByTestId("signature-canvas");
    fireEvent.mouseDown(canvas, { clientX: 10, clientY: 10 });
    fireEvent.mouseMove(canvas, { clientX: 50, clientY: 50 });
    fireEvent.mouseUp(canvas, { clientX: 50, clientY: 50 });
    await user.click(screen.getByTestId("consent-checkbox"));
    await user.click(screen.getByTestId("consent-submit"));
    await user.click(screen.getByTestId("checkin-confirm"));
    expect(
      await screen.findByText(/already checked in/),
    ).toBeInTheDocument();
  });

  // --- Default prep for unknown modality ---

  it("shows generic prep when modality is unknown", async () => {
    mockGetCheckIn.mockResolvedValue({
      ...SUMMARY,
      modality: "XX",
      prep_instructions: "",
    });
    renderKiosk();
    expect(
      await screen.findByText(/Bring your insurance card/),
    ).toBeInTheDocument();
  });

  it("decline requires a reason and submits decline consent", async () => {
    const user = userEvent.setup();
    mockGetCheckIn.mockResolvedValue(SUMMARY);
    renderKiosk();
    await screen.findByText(/Preparation Instructions/);
    await user.click(
      screen.getByText(/I understand — continue to consent/),
    );
    // Submit must be disabled before a reason is typed.
    await user.click(screen.getByTestId("decline-consent"));
    expect(screen.getByTestId("decline-submit")).toBeDisabled();
    await user.type(screen.getByTestId("decline-reason"), "Not comfortable");
    await user.click(screen.getByTestId("decline-submit"));
    await waitFor(() => {
      expect(mockSubmitConsent).toHaveBeenCalledWith("test-token-123", {
        accepted: false,
        signature_png: "",
        decline_reason: "Not comfortable",
      });
    });
    // Refusal still proceeds to the ready-to-check-in phase.
    await waitFor(() => {
      expect(screen.getByText(/I'm here/)).toBeInTheDocument();
    });
  });
});
