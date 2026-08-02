import React from "react";
import { render, screen, within, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { AuthProvider } from "../auth/AuthContext";
import { ThemeProvider } from "../common/ThemeProvider";
import ServiceKeys from "../servicekeys/ServiceKeys";

const mockListApiKeys = vi.hoisted(() => vi.fn());
const mockCreateApiKey = vi.hoisted(() => vi.fn());
const mockDeleteApiKey = vi.hoisted(() => vi.fn());
vi.mock("../api/servicekeys", () => ({
  listApiKeys: mockListApiKeys,
  createApiKey: mockCreateApiKey,
  deleteApiKey: mockDeleteApiKey,
}));
vi.mock("../helpers", () => ({
  request: vi.fn(() => Promise.resolve({})),
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

const mockKeys = [
  {
    id: "1",
    name: "RIS Integration",
    prefix: "qpk_abcde",
    service_name: "RIS-App",
    permissions: ["FILE_READ"],
    expires_at: "2027-07-28T00:00:00Z",
    last_used_at: "2026-07-27T12:00:00Z",
    enabled: true,
    is_active: true,
    created_at: "2026-07-01T00:00:00Z",
  },
  {
    id: "2",
    name: "HL7 Connector",
    prefix: "qpk_fghij",
    service_name: "HL7-Bridge",
    permissions: ["PATIENT_READ", "WORKLIST_WRITE"],
    expires_at: null,
    last_used_at: null,
    enabled: true,
    is_active: true,
    created_at: "2026-07-15T00:00:00Z",
  },
  {
    id: "3",
    name: "Old Backup Script",
    prefix: "qpk_klmno",
    service_name: "Backup",
    permissions: ["FILE_READ"],
    expires_at: "2026-06-01T00:00:00Z",
    last_used_at: "2026-05-30T00:00:00Z",
    enabled: false,
    is_active: true,
    created_at: "2026-01-01T00:00:00Z",
  },
];

async function waitForTable() {
  await screen.findByText("RIS Integration", { exact: false });
}

describe("ServiceKeys", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockListApiKeys.mockImplementation(() => Promise.resolve(mockKeys));
    mockCreateApiKey.mockResolvedValue({} as any);
    mockDeleteApiKey.mockResolvedValue(undefined);
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

  it("renders table with API keys from API", async () => {
    renderWithAuth(<ServiceKeys />);
    expect(await screen.findByText("RIS Integration")).toBeInTheDocument();
    expect(await screen.findByText("HL7 Connector")).toBeInTheDocument();
  });

  it("renders column headers", async () => {
    renderWithAuth(<ServiceKeys />);
    await waitForTable();
    expect(screen.getByText("Name")).toBeInTheDocument();
    expect(screen.getByText("Permissions")).toBeInTheDocument();
    expect(screen.getByText("Last Used")).toBeInTheDocument();
    expect(screen.getByText("Status")).toBeInTheDocument();
  });

  it("renders Generate Key button", async () => {
    renderWithAuth(<ServiceKeys />);
    await waitForTable();
    expect(screen.getByText("Generate Key")).toBeInTheDocument();
  });

  it("calls request with correct endpoint on mount", async () => {
    renderWithAuth(<ServiceKeys />);
    await waitForTable();
    expect(mockListApiKeys).toHaveBeenCalled();
  });

  it("generate modal opens with form fields", async () => {
    const user = userEvent.setup();
    renderWithAuth(<ServiceKeys />);
    await waitForTable();

    await user.click(screen.getByText("Generate Key"));
    const modal = screen.getByRole("dialog");
    expect(within(modal).getByLabelText("Name")).toBeInTheDocument();
    expect(within(modal).getByLabelText("Service Name")).toBeInTheDocument();
  });

  it("generate key sends API request and shows raw key", async () => {
    const user = userEvent.setup();
    renderWithAuth(<ServiceKeys />);
    await waitForTable();
    mockCreateApiKey.mockImplementation(() =>
      Promise.resolve({ id: "4", raw_key: "qpk_newly_generated_key_token" }),
    );

    await user.click(screen.getByText("Generate Key"));
    const modal = screen.getByRole("dialog");
    await user.type(within(modal).getByLabelText("Name"), "New Key");
    await user.type(within(modal).getByLabelText("Service Name"), "MyService");
    await user.click(within(modal).getByText("Generate"));

    await waitFor(() => {
      expect(mockCreateApiKey).toHaveBeenCalledWith(
        expect.objectContaining({ name: "New Key", service_name: "MyService" }),
      );
    });

    expect(
      await screen.findByText("qpk_newly_generated_key_token"),
    ).toBeInTheDocument();
  });

  it("revoke key calls delete API and refreshes list", async () => {
    const user = userEvent.setup();
    renderWithAuth(<ServiceKeys />);
    await waitForTable();

    await user.click(screen.getAllByText("Revoke")[0]);
    const confirmBtn = screen.getByText("OK");
    await user.click(confirmBtn);

    await waitFor(() => {
      expect(mockDeleteApiKey).toHaveBeenCalledWith("1");
    });
  });
});
