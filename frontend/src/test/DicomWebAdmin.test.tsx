import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import { renderWithApp } from "./renderWithApp";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { AuthProvider } from "../auth/AuthContext";
import { ThemeProvider } from "../common/ThemeProvider";
import DicomWebAdmin from "../dicomweb/DicomWebAdmin";

const mockGetDicomwebAdmin = vi.hoisted(() => vi.fn());
vi.mock("../api/dicomweb-admin", () => ({
  getDicomwebAdmin: mockGetDicomwebAdmin,
}));
vi.mock("../helpers", () => ({
  request: vi.fn(() => Promise.resolve({})),
  isAdmin: () => true,
}));

vi.mock("../hooks", () => ({
  useDocumentTitle: vi.fn(),
  useFetch: () => ({ exec: vi.fn() }),
}));

const mockInfo = {
  qido: {
    enabled: true,
    response_format: "application/fhir+json",
    pagination: "cursor-based",
    features: { transfer_syntax: "*" },
    modality_validation: true,
    valid_modalities_count: 50,
    endpoints: [
      { method: "GET", path: "/{study}", description: "Query studies" },
    ],
    search_params: [
      { name: "PatientID", type: "string", description: "Filter by patient" },
    ],
  },
  wado: {
    enabled: true,
    response_format: "application/dicom",
    endpoints: [
      {
        method: "GET",
        path: "/{study}/{series}/{instance}",
        description: "Retrieve instance",
      },
    ],
  },
  stow: {
    enabled: false,
    response_format: "application/dicom",
    endpoints: [
      { method: "POST", path: "/{study}", description: "Store instances" },
    ],
  },
  modalities: ["CT", "MR", "XA", "US", "NM", "PET", "MG", "CR", "DX", "SR"],
  missing_features: ["BulkData exchange", "UPS RS"],
};

async function waitForReady() {
  await screen.findByText("DICOMweb Server");
}

describe("DicomWebAdmin", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGetDicomwebAdmin.mockResolvedValue(mockInfo);
    localStorage.setItem("token", "t");
    localStorage.setItem("userId", "u1");
    localStorage.setItem("admin", "true");
  });

  function renderWithAuth(ui: React.ReactElement) {
    return renderWithApp(
      <ThemeProvider>
        <AuthProvider>
          <MemoryRouter>{ui}</MemoryRouter>
        </AuthProvider>
      </ThemeProvider>,
    );
  }

  it("fetches info on mount", async () => {
    renderWithAuth(<DicomWebAdmin />);
    await waitForReady();
    expect(mockGetDicomwebAdmin).toHaveBeenCalled();
  });

  it("renders all three service cards", async () => {
    renderWithAuth(<DicomWebAdmin />);
    await waitForReady();
    expect(screen.getAllByText("QIDO-RS").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("WADO-RS").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("STOW-RS").length).toBeGreaterThanOrEqual(1);
  });

  it("shows enabled/disabled tags", async () => {
    renderWithAuth(<DicomWebAdmin />);
    await waitForReady();
    const enabledTags = screen.getAllByText("Enabled");
    expect(enabledTags.length).toBeGreaterThanOrEqual(2);
  });

  it("renders four tabs", async () => {
    renderWithAuth(<DicomWebAdmin />);
    await waitForReady();
    expect(screen.getByText("Endpoints")).toBeInTheDocument();
    expect(screen.getByText("Search Parameters")).toBeInTheDocument();
    expect(screen.getByText("Modalities")).toBeInTheDocument();
    expect(screen.getByText("Missing Features")).toBeInTheDocument();
  });

  it("renders modality tags in modalities tab", async () => {
    const user = userEvent.setup();
    renderWithAuth(<DicomWebAdmin />);
    await waitForReady();
    await user.click(screen.getByText("Modalities"));
    expect(await screen.findByText("CT")).toBeInTheDocument();
    expect(await screen.findByText("MR")).toBeInTheDocument();
    expect(await screen.findByText("XA")).toBeInTheDocument();
  });

  it("renders search parameters tab", async () => {
    const user = userEvent.setup();
    renderWithAuth(<DicomWebAdmin />);
    await waitForReady();
    await user.click(screen.getByText("Search Parameters"));
    expect(await screen.findByText("PatientID")).toBeInTheDocument();
  });

  it("renders missing features", async () => {
    const user = userEvent.setup();
    renderWithAuth(<DicomWebAdmin />);
    await waitForReady();
    await user.click(screen.getByText("Missing Features"));
    expect(await screen.findByText("BulkData exchange")).toBeInTheDocument();
    expect(await screen.findByText("UPS RS")).toBeInTheDocument();
  });

  it("renders modality count in modalities tab", async () => {
    const user = userEvent.setup();
    renderWithAuth(<DicomWebAdmin />);
    await waitForReady();
    await user.click(screen.getByText("Modalities"));
    expect(await screen.findByText(/10 valid modality/)).toBeInTheDocument();
  });
});
