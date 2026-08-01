import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { AuthProvider } from "../auth/AuthContext";
import { ThemeProvider } from "../common/ThemeProvider";
import FhirConfig from "../fhir/FhirConfig";

const mockGetFhirConfig = vi.hoisted(() => vi.fn());
const mockUpdateFhirConfig = vi.hoisted(() => vi.fn());
const mockListFhirClients = vi.hoisted(() => vi.fn());
const mockCreateFhirClient = vi.hoisted(() => vi.fn());

vi.mock("../api/fhir", () => ({
  getFhirConfig: mockGetFhirConfig,
  updateFhirConfig: mockUpdateFhirConfig,
  listFhirClients: mockListFhirClients,
  createFhirClient: mockCreateFhirClient,
  updateFhirClient: vi.fn(),
  deleteFhirClient: vi.fn(),
  testFhirConnection: vi.fn(),
}));

vi.mock("../helpers", () => ({
  request: vi.fn(() => Promise.resolve({})),
  isAdmin: () => true,
}));

vi.mock("../hooks", () => ({
  useDocumentTitle: vi.fn(),
  useFetch: () => ({ exec: vi.fn() }),
}));

const mockConfig = {
  enabled: true,
  base_url: "https://fhir.example.com",
  publisher: "QuantumPACS",
  max_search_results: 100,
  log_retention_days: 90,
};
const mockClients = [
  {
    id: "c1",
    name: "Epic",
    client_id: "epic-client",
    active: true,
    grant_type: "authorization_code",
    last_used: "2026-07-01T12:00:00Z",
  },
  {
    id: "c2",
    name: "Cerner",
    client_id: "cerner-client",
    active: false,
    grant_type: "authorization_code",
    last_used: null,
  },
];

async function waitForReady() {
  await screen.findByText("FHIR R4 Server");
}

describe("FhirConfig", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGetFhirConfig.mockImplementation(() => Promise.resolve(mockConfig));
    mockListFhirClients.mockImplementation(() => Promise.resolve(mockClients));
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

  it("fetches config and clients on mount", async () => {
    renderWithAuth(<FhirConfig />);
    await waitForReady();
    expect(mockGetFhirConfig).toHaveBeenCalled();
    expect(mockListFhirClients).toHaveBeenCalled();
  });

  it("renders config fields", async () => {
    renderWithAuth(<FhirConfig />);
    await waitForReady();
    const baseUrlInput = screen.getByDisplayValue("https://fhir.example.com");
    expect(baseUrlInput).toBeInTheDocument();
    expect(screen.getByDisplayValue("QuantumPACS")).toBeInTheDocument();
  });

  it("renders enabled status tag", async () => {
    renderWithAuth(<FhirConfig />);
    await waitForReady();
    expect(screen.getByText("Enabled")).toBeInTheDocument();
  });

  it("renders client table with names", async () => {
    renderWithAuth(<FhirConfig />);
    await waitForReady();
    expect(screen.getByText("Epic")).toBeInTheDocument();
    expect(screen.getByText("Cerner")).toBeInTheDocument();
  });

  it("renders register client button", async () => {
    renderWithAuth(<FhirConfig />);
    await waitForReady();
    expect(screen.getByText("Register Client")).toBeInTheDocument();
  });

  it("opens register modal on click", async () => {
    const user = userEvent.setup();
    renderWithAuth(<FhirConfig />);
    await waitForReady();
    await user.click(screen.getByText("Register Client"));
    const modal = screen.getByRole("dialog");
    expect(modal).toBeInTheDocument();
    expect(modal).toHaveTextContent("Register SMART-on-FHIR Client");
  });

  it("creates a client via modal", async () => {
    const user = userEvent.setup();
    mockCreateFhirClient.mockImplementation(() =>
      Promise.resolve({ client_id: "new-client", client_secret: "s3cret" }),
    );
    renderWithAuth(<FhirConfig />);
    await waitForReady();
    await user.click(screen.getByText("Register Client"));
    const modal = screen.getByRole("dialog");
    const nameInput = modal.querySelector("input");
    if (nameInput) await user.type(nameInput, "New EHR");
    await user.click(screen.getByText("OK"));
    await waitFor(() => {
      expect(mockCreateFhirClient).toHaveBeenCalled();
    });
  });

  it("renders save and test buttons", async () => {
    renderWithAuth(<FhirConfig />);
    await waitForReady();
    expect(screen.getByText("Save")).toBeInTheDocument();
    expect(screen.getByText("Test Connection")).toBeInTheDocument();
  });
});
