import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { renderWithAuth } from "./renderWithApp";
import DenialRework from "../billing/DenialRework";

const mockListDenials = vi.hoisted(() => vi.fn());
const mockResubmit = vi.hoisted(() => vi.fn());
const mockHistory = vi.hoisted(() => vi.fn());

vi.mock("../api/billing-ris", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api/billing-ris")>();
  return {
    ...actual,
    listDenialRework: mockListDenials,
    resubmitClaim: mockResubmit,
    getClaimHistory: mockHistory,
  };
});

const deniedRow = {
  id: "clm-9",
  claim_number: "CLM-123456",
  payer_name: "Medicare",
  status: "DENIED",
  rejection_code: "CO-16",
  rejection_reason: "Missing information",
  correction_count: 0,
  prior_auth_number: "AUTH-77",
  patient_name: "Jane Doe",
  accession_number: "ACC-1",
  cpt_code: "71250",
  charge_amount: 250,
};

describe("DenialRework", () => {
  beforeEach(() => {
    localStorage.setItem("token", "t");
    localStorage.setItem("userId", "u1");
    localStorage.setItem("admin", "true");
    localStorage.setItem(
      "permissions",
      JSON.stringify(["BILLING_READ", "BILLING_WRITE"]),
    );
    mockResubmit.mockResolvedValue({ id: "clm-9", status: "SUBMITTED" });
    mockHistory.mockResolvedValue([
      { event_type: "DENIED", note: "CO-16: Missing information" },
    ]);
  });

  it("lists denied claims with reason codes and auth linkage", async () => {
    mockListDenials.mockResolvedValue([deniedRow]);
    renderWithAuth(<DenialRework />);
    await waitFor(() => {
      expect(screen.getByText("CO-16")).toBeInTheDocument();
    });
    expect(screen.getByText(/Jane Doe/)).toBeInTheDocument();
    // R2-02-04: prior-auth linkage visible on rework rows.
    expect(screen.getByText("AUTH-77")).toBeInTheDocument();
  });

  it("resubmits a corrected claim with a note", async () => {
    const user = userEvent.setup();
    mockListDenials.mockResolvedValue([deniedRow]);
    renderWithAuth(<DenialRework />);

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /rework/i })).toBeInTheDocument();
    });
    await user.click(screen.getByRole("button", { name: /rework/i }));

    const noteBox = await screen.findByRole("textbox");
    await user.type(noteBox, "added missing contrast info");
    await user.click(screen.getByRole("button", { name: /^submit$/i }));

    await waitFor(() => {
      expect(mockResubmit).toHaveBeenCalledWith("clm-9", {
        note: "added missing contrast info",
      });
    });
  });

  it("shows the rework history for a claim", async () => {
    const user = userEvent.setup();
    mockListDenials.mockResolvedValue([deniedRow]);
    renderWithAuth(<DenialRework />);
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /history/i })).toBeInTheDocument();
    });
    await user.click(screen.getByRole("button", { name: /history/i }));
    await waitFor(() => {
      expect(mockHistory).toHaveBeenCalledWith("clm-9");
    });
    expect(await screen.findByText(/DENIED/)).toBeInTheDocument();
  });
});
