import React from "react";
import { render, screen, waitFor, fireEvent, within } from "@testing-library/react";
import { renderWithAuth } from "./renderWithApp";
import { describe, it, expect, vi, beforeEach } from "vitest";
import FeeSchedule from "../billing/FeeSchedule";

const mockRequest = vi.fn();

vi.mock("../api/billing-ris", () => ({
  listFeeSchedule: vi.fn(),
  listPayerContracts: vi.fn(),
  getContractComparison: vi.fn(),
  updateFeeScheduleItem: vi.fn(),
  importFeeSchedule: vi.fn(),
  getFeeScheduleHistory: vi.fn(),
  createPayerContract: vi.fn(),
  updatePayerContract: vi.fn(),
  deletePayerContract: vi.fn(),
}));

vi.mock("../hooks", () => ({
  useDocumentTitle: vi.fn(),
}));

vi.mock("../common/base", () => ({
  __esModule: true,
  default: (Component: React.ComponentType<any>) => (props: any) => <Component {...props} />,
}));

vi.mock("antd", async () => {
  const actual = await vi.importActual("antd");
  const Popconfirm = ({ children, onConfirm, title }: any) =>
    React.createElement(
      "span",
      {
        className: "mock-popconfirm",
        "data-title": title,
        onClick: (e: React.MouseEvent) => {
          onConfirm?.();
        },
      },
      children
    );
  return { ...actual, Popconfirm };
});

import {
  listFeeSchedule,
  listPayerContracts,
  getContractComparison,
  updateFeeScheduleItem,
  importFeeSchedule,
  getFeeScheduleHistory,
  createPayerContract,
  deletePayerContract,
} from "../api/billing-ris";

const mockListFeeSchedule = vi.mocked(listFeeSchedule);
const mockListContracts = vi.mocked(listPayerContracts);
const mockGetComparison = vi.mocked(getContractComparison);
const mockUpdateFee = vi.mocked(updateFeeScheduleItem);
const mockImportFee = vi.mocked(importFeeSchedule);
const mockGetHistory = vi.mocked(getFeeScheduleHistory);
const mockCreateContract = vi.mocked(createPayerContract);
const mockDeleteContract = vi.mocked(deletePayerContract);

const SCHEDULE_ITEMS = [
  { id: "p1", procedure_code: "71250", description: "CT Chest", list_price: 350.0, active: true },
  { id: "p2", procedure_code: "72125", description: "CT Head", list_price: 320.0, active: true },
];

const CONTRACTS = [
  {
    id: "c1",
    payer_id: "AETNA",
    payer_name: "Aetna",
    procedure_code: "71250",
    contracted_rate: 280.0,
    effective_date: "2026-01-01",
    active: true,
  },
];

const COMPARISON = [
  {
    charge_id: "ch1",
    procedure_code: "71250",
    payer_name: "Aetna",
    charged_amount: 400.0,
    contracted_rate: 280.0,
    variance: 120.0,
    flag: "over_charge" as const,
  },
];

describe("FeeSchedule B-08/B-09 page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.setItem("userId", "1");
    localStorage.setItem("permissions", JSON.stringify(["BILLING_READ", "BILLING_WRITE"]));
    mockListFeeSchedule.mockResolvedValue(SCHEDULE_ITEMS);
    mockListContracts.mockResolvedValue(CONTRACTS);
    mockGetComparison.mockResolvedValue(COMPARISON);
    mockGetHistory.mockResolvedValue([]);
  });

  it("renders fee schedule tab with procedures", async () => {
    renderWithAuth(<FeeSchedule />);
    expect(await screen.findByText("71250")).toBeInTheDocument();
    expect(screen.getByText("72125")).toBeInTheDocument();
  });

  it("renders payer contracts tab", async () => {
    renderWithAuth(<FeeSchedule />);
    fireEvent.click(await screen.findByText("Payer Contracts"));
    expect((await screen.findAllByText("Aetna")).length).toBeGreaterThan(0);
    expect(screen.getAllByText("71250").length).toBeGreaterThan(0);
  });

  it("shows charge vs contract comparison", async () => {
    renderWithAuth(<FeeSchedule />);
    fireEvent.click(await screen.findByText("Payer Contracts"));
    expect(await screen.findByText("over_charge")).toBeInTheDocument();
    expect(screen.getByText("+$120.00")).toBeInTheDocument();
  });

  it("opens edit modal and saves fee schedule update", async () => {
    mockUpdateFee.mockResolvedValue({ ...SCHEDULE_ITEMS[0], list_price: 400 });
    renderWithAuth(<FeeSchedule />);
    await screen.findByText("71250");
    const editButtons = screen.getAllByText("Edit");
    fireEvent.click(editButtons[0]);
    await waitFor(() => {
      expect(screen.getByText("71250")).toBeInTheDocument();
    });
    const modal = screen.getByRole("dialog");
    const priceInput = within(modal).getByRole("spinbutton");
    fireEvent.change(priceInput, { target: { value: "400" } });
    fireEvent.click(within(modal).getByRole("button", { name: "Save" }));
    await waitFor(() => {
      expect(mockUpdateFee).toHaveBeenCalledWith(
        "71250",
        expect.objectContaining({ list_price: 400 })
      );
    });
  });

  it("opens import modal and submits", async () => {
    mockImportFee.mockResolvedValue({ imported: 2 });
    renderWithAuth(<FeeSchedule />);
    await screen.findByText("71250");
    fireEvent.click(screen.getByText("Import (CMS)"));
    const modal = screen.getByRole("dialog");
    const textarea = within(modal).getByRole("textbox");
    fireEvent.change(textarea, { target: { value: "71250, CT Chest, 350\n72125, CT Head, 320" } });
    fireEvent.click(within(modal).getByRole("button", { name: "Import" }));
    await waitFor(() => {
      expect(mockImportFee).toHaveBeenCalled();
    });
  });

  it("opens history drawer", async () => {
    mockGetHistory.mockResolvedValue([
      {
        procedure_code: "71250",
        description: "CT Chest",
        list_price: 400,
        changed_by: "1",
        changed_at: "2026-08-27T00:00:00Z",
      },
    ]);
    renderWithAuth(<FeeSchedule />);
    await screen.findByText("71250");
    const historyButtons = screen.getAllByText("History");
    fireEvent.click(historyButtons[0]);
    expect(await screen.findByText("$400.00")).toBeInTheDocument();
  });

  it("creates a payer contract", async () => {
    mockCreateContract.mockResolvedValue({
      id: "c2",
      payer_id: "UNITED",
      payer_name: "UnitedHealth",
      procedure_code: "71250",
      contracted_rate: 290,
      effective_date: "2026-01-01",
      active: true,
    });
    renderWithAuth(<FeeSchedule />);
    fireEvent.click(await screen.findByText("Payer Contracts"));
    await screen.findAllByText("Aetna");
    fireEvent.click(screen.getAllByText("Add Contract")[0]);
    const modal = screen.getByRole("dialog");
    fireEvent.change(within(modal).getByLabelText("Payer ID"), { target: { value: "UNITED" } });
    fireEvent.change(within(modal).getByLabelText("Payer Name"), {
      target: { value: "UnitedHealth" },
    });
    fireEvent.change(within(modal).getByLabelText("Procedure Code"), {
      target: { value: "71250" },
    });
    const rateInput = within(modal).getByLabelText("Contracted Rate");
    const spinbutton = rateInput.closest(".ant-input-number")?.querySelector("input") || rateInput;
    fireEvent.change(spinbutton, { target: { value: "290" } });
    fireEvent.click(within(modal).getByRole("button", { name: "Save" }));
    await waitFor(() => {
      expect(mockCreateContract).toHaveBeenCalledWith(
        expect.objectContaining({ payer_id: "UNITED", procedure_code: "71250" })
      );
    });
  });

  it("deactivates a payer contract via popconfirm", async () => {
    mockDeleteContract.mockResolvedValue({ id: "c1", active: false });
    renderWithAuth(<FeeSchedule />);
    fireEvent.click(await screen.findByText("Payer Contracts"));
    await screen.findAllByText("Aetna");
    const deactivateButtons = screen.getAllByText("Deactivate");
    fireEvent.click(deactivateButtons[0]);
    await waitFor(() => {
      expect(mockDeleteContract).toHaveBeenCalledWith("c1");
    });
  });
});
