import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import React from "react";
import { MemoryRouter } from "react-router";
import { App } from "antd";
import { AuthProvider } from "../auth/AuthContext";
import { ThemeProvider } from "../common/ThemeProvider";
import BillingQueue from "../billing/BillingQueue";

vi.mock("../api/billing-ris", () => ({
  listBillingQueue: vi.fn(),
  dropCharge: vi.fn(),
  getCptSuggestions: vi.fn(),
  batchDropCharges: vi.fn(),
}));

vi.mock("../hooks", () => ({
  useDocumentTitle: vi.fn(),
  useTenantRefetch: vi.fn(),
}));

vi.mock("../auth/AuthContext", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../auth/AuthContext")>();
  return {
    ...actual,
    useAuth: () => ({
      hasPermission: (perm: string) =>
        ["WORKLIST_READ", "WORKLIST_WRITE", "BILLING_READ", "BILLING_WRITE"].includes(perm),
    }),
  };
});

import {
  listBillingQueue,
  dropCharge,
  getCptSuggestions,
  batchDropCharges,
} from "../api/billing-ris";

const mockListBillingQueue = vi.mocked(listBillingQueue);
const mockDropCharge = vi.mocked(dropCharge);
const mockGetCptSuggestions = vi.mocked(getCptSuggestions);
const mockBatchDropCharges = vi.mocked(batchDropCharges);

const mockQueueData = [
  {
    id: "chg-1",
    patient_id: "P001",
    patient_name: "Smith^John",
    accession_number: "ACC001",
    cpt_code: "71250",
    cpt_description: "CT chest without contrast",
    icd10_code: "R91.1",
    charge_amount: 250.0,
    status: "PENDING",
    created_at: "2026-08-20T00:00:00Z",
  },
  {
    id: "chg-2",
    patient_id: "P002",
    patient_name: "Doe^Jane",
    accession_number: "ACC002",
    cpt_code: "",
    cpt_description: "",
    icd10_code: "",
    charge_amount: 0,
    status: "PENDING",
    created_at: "2026-08-21T00:00:00Z",
  },
];

function renderQueue() {
  localStorage.setItem("userId", "1");
  localStorage.setItem("username", "test");
  localStorage.setItem(
    "permissions",
    JSON.stringify(["BILLING_READ", "BILLING_WRITE"]),
  );
  localStorage.setItem("tenant_id", "t1");
  localStorage.setItem("tenant_name", "Test");
  return render(
    <MemoryRouter>
      <App>
        <AuthProvider>
          <ThemeProvider>
            <BillingQueue />
          </ThemeProvider>
        </AuthProvider>
      </App>
    </MemoryRouter>,
  );
}

describe("BillingQueue", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockListBillingQueue.mockResolvedValue({
      data: mockQueueData,
      total: 2,
      page: 1,
      per_page: 20,
    });
    mockDropCharge.mockResolvedValue({ id: "chg-1", status: "BILLED" });
    mockBatchDropCharges.mockResolvedValue({
      dropped: ["chg-1", "chg-2"], missing: [], skipped: [],
    });
    mockGetCptSuggestions.mockResolvedValue({
      data: [
        {
          procedure_code: "CT CHEST",
          cpt_code: "71250",
          cpt_description: "CT chest without contrast",
          icd10_code: "R91.1",
          icd10_description: "Lung opacity",
        },
      ],
    });
  });

  it("renders unbilled charges from the API", async () => {
    renderQueue();
    await waitFor(() => {
      expect(screen.getByText("Smith^John")).toBeInTheDocument();
    });
    expect(screen.getByText("Doe^Jane")).toBeInTheDocument();
  });

  it("shows CPT codes as tags", async () => {
    renderQueue();
    await waitFor(() => {
      expect(screen.getByText("71250")).toBeInTheDocument();
    });
  });

  it("shows charge amounts", async () => {
    renderQueue();
    await waitFor(() => {
      expect(screen.getByText("$250.00")).toBeInTheDocument();
    });
  });

  it("drops selected charges in one batch (B-05)", async () => {
    renderQueue();
    await waitFor(() => {
      expect(screen.getByText("Smith^John")).toBeInTheDocument();
    });

    // Select both rows via the table checkboxes.
    const checkboxes = screen.getAllByRole("checkbox");
    fireEvent.click(checkboxes[1]);
    fireEvent.click(checkboxes[2]);

    fireEvent.click(
      screen.getByRole("button", { name: /drop selected charges/i }),
    );

    await waitFor(() => {
      expect(mockBatchDropCharges).toHaveBeenCalledWith(["chg-1", "chg-2"]);
    });
  });
  it("passes WCAG 2.1 AA automated scan (F3)", async () => {
    renderQueue();
    await waitFor(() => {
      expect(screen.getByText("$250.00")).toBeTruthy();
    });
    const { scanA11y, seriousViolations } = await import("./axe");
    const results = await scanA11y(document.body);
    expect(seriousViolations(results)).toEqual([]);
  });

});