import { render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import React from "react";
import { MemoryRouter } from "react-router";
import { App } from "antd";
import { AuthProvider } from "../auth/AuthContext";
import { ThemeProvider } from "../common/ThemeProvider";
import PriorAuthPanel from "../coordinator/PriorAuthPanel";

vi.mock("../api/prior-auth", () => ({
  listPriorAuth: vi.fn(),
  submitPriorAuth: vi.fn(),
  decidePriorAuth: vi.fn(),
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
      hasPermission: () => true,
    }),
  };
});

import { listPriorAuth } from "../api/prior-auth";
const mockList = vi.mocked(listPriorAuth);

const mockData = [
  {
    id: "pa-1",
    order_id: "ord-1",
    procedure_code: "CT CHEST",
    payer_name: "Medicare",
    status: "PENDING",
    auth_number: "",
    expiry_date: null,
  },
  {
    id: "pa-2",
    order_id: "ord-2",
    procedure_code: "MRI BRAIN",
    payer_name: "Blue Cross",
    status: "APPROVED",
    auth_number: "AUTH-123",
    expiry_date: "2026-09-21",
  },
];

function renderPanel() {
  localStorage.setItem("userId", "1");
  localStorage.setItem("username", "test");
  localStorage.setItem("permissions", JSON.stringify(["PRIOR_AUTH_READ"]));
  localStorage.setItem("tenant_id", "t1");
  return render(
    <MemoryRouter>
      <App>
        <AuthProvider>
          <ThemeProvider>
            <PriorAuthPanel />
          </ThemeProvider>
        </AuthProvider>
      </App>
    </MemoryRouter>,
  );
}

describe("PriorAuthPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockList.mockResolvedValue({ data: mockData, total: 2 });
  });

  it("renders prior-auth requests from the API", async () => {
    renderPanel();
    await waitFor(() => {
      expect(screen.getByText("ord-1")).toBeInTheDocument();
    });
    expect(screen.getByText("ord-2")).toBeInTheDocument();
  });

  it("shows status tags", async () => {
    renderPanel();
    await waitFor(() => {
      expect(screen.getByText("PENDING")).toBeInTheDocument();
    });
    expect(screen.getByText("APPROVED")).toBeInTheDocument();
  });

  it("shows auth number for approved requests", async () => {
    renderPanel();
    await waitFor(() => {
      expect(screen.getByText("AUTH-123")).toBeInTheDocument();
    });
  });
});