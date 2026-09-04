import React from "react";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";
import BillingQueue from "../billing/BillingQueue";
import { renderWithAuth } from "./renderWithApp";

// Reuse the existing queue suite's mock surface; this file pins ONLY the
// B-02 submission flow so the two suites stay independently editable.
const mocks = vi.hoisted(() => ({
  list: vi.fn(),
  submitClaim: vi.fn(),
  batchSubmitClaims: vi.fn(),
}));

vi.mock("../api/billing-ris", async () => {
  const actual = await import("../api/billing-ris");
  return {
    ...actual,
    listBillingQueue: mocks.list,
    submitClaim: mocks.submitClaim,
    batchSubmitClaims: mocks.batchSubmitClaims,
    dropCharge: vi.fn(),
    getCptSuggestions: vi.fn().mockResolvedValue({ data: [] }),
    batchDropCharges: vi.fn(),
  };
});

const ENTRY = {
  id: "chg-1",
  patient_id: "P1",
  patient_name: "Jane Doe",
  accession_number: "ACC100",
  cpt_code: "71260",
  cpt_description: "CT Chest with contrast",
  icd10_code: "R91.1",
  charge_amount: 350,
  status: "PENDING",
  created_at: "2026-08-20T10:00:00Z",
};

beforeEach(() => {
  vi.clearAllMocks();
  localStorage.clear();
  localStorage.setItem("token", "t");
  localStorage.setItem("userId", "u3");
  localStorage.setItem("admin", "false");
  localStorage.setItem("role", "cashier");
  localStorage.setItem("permissions", JSON.stringify(["BILLING_READ", "BILLING_WRITE"]));
  mocks.list.mockResolvedValue({ data: [ENTRY], total: 1 });
  mocks.submitClaim.mockResolvedValue({
    id: "clm-9",
    claim_number: "CLM-000009",
    status: "SUBMITTED",
  });
});

describe("BillingQueue claim submission (B-02)", () => {
  it("reviews charge details, then submits and surfaces the claim number", async () => {
    const user = userEvent.setup();
    renderWithAuth(<BillingQueue />);
    await screen.findByText("Jane Doe");

    await user.click(screen.getByRole("button", { name: /submit claim/i }));

    // Review-before-submit: the modal names what will be billed.
    const dialog = await screen.findByRole("dialog");
    expect(dialog).toHaveTextContent("ACC100");
    expect(dialog).toHaveTextContent("71260");
    expect(dialog).toHaveTextContent("$350.00");

    // NOTE: userEvent inside an open antd Modal hangs jsdom (known D3-era
    // env limitation) — modal-phase interactions use fireEvent.
    const { fireEvent } = await import("@testing-library/react");
    fireEvent.click(screen.getByRole("button", { name: /^Submit$/i }));
    await vi.waitFor(() => expect(mocks.submitClaim).toHaveBeenCalledWith("chg-1"));
    expect(await screen.findByText(/CLM-000009/)).toBeInTheDocument();
    // Queue refreshes so the submitted charge leaves the list.
    await vi.waitFor(() => expect(mocks.list).toHaveBeenCalledTimes(2));
  });

  it("batch-submits every selected charge in one round-trip", async () => {
    const user = userEvent.setup();
    mocks.list.mockResolvedValue({
      data: [ENTRY, { ...ENTRY, id: "chg-2", patient_name: "John Roe" }],
      total: 2,
    });
    // Client fn unwraps .data — mocks must return the unwrapped shape.
    mocks.batchSubmitClaims.mockResolvedValue({
      submitted: [
        { charge_id: "chg-1", claim_number: "CLM-010", status: "SUBMITTED" },
        { charge_id: "chg-2", claim_number: "CLM-011", status: "SUBMITTED" },
      ],
      missing: [],
    });
    renderWithAuth(<BillingQueue />);
    await screen.findByText("Jane Doe");

    await user.click(screen.getByRole("checkbox", { name: /select all/i }));
    await user.click(screen.getByRole("button", { name: /submit claims \(2\)/i }));

    await vi.waitFor(() =>
      expect(mocks.batchSubmitClaims).toHaveBeenCalledWith(["chg-1", "chg-2"])
    );
    expect(await screen.findByText(/2 claim\(s\) submitted/)).toBeInTheDocument();
  });

  it("reports charges the server could not prepare", async () => {
    const user = userEvent.setup();
    mocks.batchSubmitClaims.mockResolvedValue({ submitted: [], missing: ["chg-1"] });
    renderWithAuth(<BillingQueue />);
    await screen.findByText("Jane Doe");

    await user.click(screen.getByRole("checkbox", { name: /select row/i }));
    await user.click(screen.getByRole("button", { name: /submit claims \(1\)/i }));

    expect(await screen.findByText(/1 not prepared/)).toBeInTheDocument();
  });
});
