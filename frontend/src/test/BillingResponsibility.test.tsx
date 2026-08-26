import React from "react";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";
import BillingQueue from "../billing/BillingQueue";
import { renderWithAuth } from "./renderWithApp";

const mocks = vi.hoisted(() => ({
  list: vi.fn(),
  responsibility: vi.fn(),
}));

vi.mock("../api/billing-ris", async () => {
  const actual = await import("../api/billing-ris");
  return {
    ...actual,
    listBillingQueue: mocks.list,
    getPatientResponsibility: mocks.responsibility,
    dropCharge: vi.fn(),
    getCptSuggestions: vi.fn().mockResolvedValue({ data: [] }),
    submitClaim: vi.fn(),
    batchSubmitClaims: vi.fn(),
    batchDropCharges: vi.fn(),
  };
});

const ENTRY = {
  id: "chg-1",
  patient_id: "P1",
  patient_name: "Jane Doe",
  accession_number: "ACC100",
  cpt_code: "71260",
  cpt_description: "",
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
});

describe("BillingQueue patient responsibility view (B-03)", () => {
  it("fetches and renders coverage plus financial responsibility", async () => {
    const user = userEvent.setup();
    mocks.responsibility.mockResolvedValue({
      patient_id: "P1",
      coverage_status: "active",
      provider: "Medicare",
      member_id: "M-4455",
      copay_amount: 25,
      deductible_total: 1500,
      deductible_remaining: 400,
      coinsurance_pct: null,
      open_charges_count: 2,
      open_charges_total: 510,
      open_invoices: 1,
      invoice_balance: 120.5,
    });
    renderWithAuth(<BillingQueue />);
    await screen.findByText("Jane Doe");

    await user.click(screen.getByRole("button", { name: /responsibility for jane doe/i }));

    expect(mocks.responsibility).toHaveBeenCalledWith("P1");
    const drawer = await screen.findByTestId("responsibility-drawer");
    expect(drawer).toHaveTextContent("Medicare");
    expect(drawer).toHaveTextContent("$25.00"); // copay
    expect(drawer).toHaveTextContent("$400.00"); // deductible remaining
    expect(drawer).toHaveTextContent("$510.00"); // open charges total
    expect(drawer).toHaveTextContent("$120.50"); // invoice balance
  });

  it("renders a no-coverage state without crashing on nulls", async () => {
    const user = userEvent.setup();
    mocks.responsibility.mockResolvedValue({
      patient_id: "P1",
      coverage_status: "none",
      provider: "",
      member_id: "",
      copay_amount: null,
      deductible_total: null,
      deductible_remaining: null,
      coinsurance_pct: null,
      open_charges_count: 0,
      open_charges_total: 0,
      open_invoices: 0,
      invoice_balance: 0,
    });
    renderWithAuth(<BillingQueue />);
    await screen.findByText("Jane Doe");

    await user.click(screen.getByRole("button", { name: /responsibility for jane doe/i }));

    const drawer = await screen.findByTestId("responsibility-drawer");
    expect(drawer).toHaveTextContent(/no active coverage/i);
  });
});
