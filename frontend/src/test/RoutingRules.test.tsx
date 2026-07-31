import React from "react";
import { render, screen, within, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { AuthProvider } from "../auth/AuthContext";
import { ThemeProvider } from "../common/ThemeProvider";
import RoutingRules from "../routing/RoutingRules";

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

const mockRules = [
  {
    id: "1",
    name: "Route CT Chest",
    description: "Route CT chest studies to fast storage",
    conditions: { modality: "CT", study_description: { contains: "CHEST" } },
    destination: "replica_2",
    priority: 10,
    enabled: true,
    created_at: "2026-07-01T00:00:00Z",
    updated_at: "2026-07-01T00:00:00Z",
  },
  {
    id: "2",
    name: "Route MR Brain",
    description: "Route MR brain studies to warm storage",
    conditions: { modality: "MR", study_description: { contains: "BRAIN" } },
    destination: "replica_3",
    priority: 5,
    enabled: false,
    created_at: "2026-07-15T00:00:00Z",
    updated_at: "2026-07-15T00:00:00Z",
  },
];

async function waitForTable() {
  await screen.findByText("Route CT Chest");
}

describe("RoutingRules", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockRequest.mockImplementation((url: string, opts?: any) => {
      if (opts?.data) return Promise.resolve({ data: { id: "new" } });
      return Promise.resolve({
        data: mockRules,
        pagination: { page: 1, per_page: 50, total: 2, pages: 1 },
      });
    });
    localStorage.setItem("token", "t");
    localStorage.setItem("userId", "u1");
    localStorage.setItem("admin", "true");
  });

  function renderWithAuth(ui: React.ReactElement) {
    return render(
      <ThemeProvider>
        <AuthProvider>
          <MemoryRouter>{ui}</MemoryRouter>
        </AuthProvider>
      </ThemeProvider>,
    );
  }

  it("renders table with routing rules from API", async () => {
    renderWithAuth(<RoutingRules />);
    expect(await screen.findByText("Route CT Chest")).toBeInTheDocument();
    expect(await screen.findByText("Route MR Brain")).toBeInTheDocument();
  });

  it("renders column headers", async () => {
    renderWithAuth(<RoutingRules />);
    await waitForTable();
    expect(screen.getByText("Name")).toBeInTheDocument();
    expect(screen.getByText("Destination")).toBeInTheDocument();
    expect(screen.getByText("Priority")).toBeInTheDocument();
    expect(screen.getByText("Status")).toBeInTheDocument();
  });

  it("renders Create Rule button", async () => {
    renderWithAuth(<RoutingRules />);
    await waitForTable();
    expect(screen.getByText("Create Rule")).toBeInTheDocument();
  });

  it("calls request with correct endpoint on mount", async () => {
    renderWithAuth(<RoutingRules />);
    await waitForTable();
    expect(mockRequest).toHaveBeenCalledWith("routing", {
      page: 1,
      per_page: 50,
    });
  });

  it("create modal opens with form fields", async () => {
    const user = userEvent.setup();
    renderWithAuth(<RoutingRules />);
    await waitForTable();

    await user.click(screen.getByText("Create Rule"));
    const modal = screen.getByRole("dialog");
    expect(within(modal).getByLabelText("Name")).toBeInTheDocument();
    expect(within(modal).getByLabelText("Destination")).toBeInTheDocument();
  });

  it("create rule sends correct API request", async () => {
    const user = userEvent.setup();
    renderWithAuth(<RoutingRules />);
    await waitForTable();

    await user.click(screen.getByText("Create Rule"));
    const modal = screen.getByRole("dialog");
    await user.type(within(modal).getByLabelText("Name"), "Route XR Chest");
    await user.type(within(modal).getByLabelText("Destination"), "replica_1");
    await user.click(within(modal).getByText("OK"));

    await waitFor(() => {
      const calls = mockRequest.mock.calls;
      const createCall = calls.find(
        (c: any) => c[0] === "routing" && c[1]?.data?.name === "Route XR Chest",
      );
      expect(createCall).toBeDefined();
      expect(createCall?.[1]?.data.name).toBe("Route XR Chest");
      expect(createCall?.[1]?.data.destination).toBe("replica_1");
    });
  });

  it("delete rule calls API and refreshes", async () => {
    const user = userEvent.setup();
    renderWithAuth(<RoutingRules />);
    await waitForTable();

    await user.click(screen.getAllByTitle("Delete")[0]);
    const confirmBtn = screen.getByRole("button", { name: /yes|confirm|ok/i });
    await user.click(confirmBtn);

    await waitFor(() => {
      expect(mockRequest).toHaveBeenCalledWith("routing/1", {
        data: undefined,
        method: "DELETE",
      });
    });
  });
});
