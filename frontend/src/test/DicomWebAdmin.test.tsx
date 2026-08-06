import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import { renderWithAuth } from "./renderWithApp";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { AuthProvider } from "../auth/AuthContext";
import { ThemeProvider } from "../common/ThemeProvider";
import DicomWebAdmin from "../dicomweb/DicomWebAdmin";

const mockGetDicomwebAdmin = vi.hoisted(() => vi.fn());
const mockGetDicomwebMetrics = vi.hoisted(() => vi.fn());
vi.mock("../api/dicomweb-admin", () => ({
  getDicomwebAdmin: mockGetDicomwebAdmin,
  getDicomwebMetrics: mockGetDicomwebMetrics,
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

const mockMetrics = {
  period: "24h",
  files_stored: 7,
  studies_stored: 2,
  totals: { studies: 12, series: 20, files: 34 },
  metrics_note: "no request logging",
};

describe("DicomWebAdmin", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGetDicomwebAdmin.mockResolvedValue(mockInfo);
    mockGetDicomwebMetrics.mockResolvedValue(mockMetrics);
    localStorage.setItem("token", "t");
    localStorage.setItem("userId", "u1");
    localStorage.setItem("admin", "true");
  });

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

  it("renders five tabs", async () => {
    renderWithAuth(<DicomWebAdmin />);
    await waitForReady();
    const tabs = screen.getAllByRole("tab").map((t) => t.textContent);
    for (const label of [
      "Endpoints",
      "Search Parameters",
      "Modalities",
      "Metrics",
      "Missing Features",
    ]) {
      expect(tabs).toContain(label);
    }
  });

  it("fetches metrics on mount", async () => {
    renderWithAuth(<DicomWebAdmin />);
    await waitForReady();
    expect(mockGetDicomwebMetrics).toHaveBeenCalled();
  });

  it("renders metrics tab statistics", async () => {
    const user = userEvent.setup();
    renderWithAuth(<DicomWebAdmin />);
    await waitForReady();
    const metricsTab = screen
      .getAllByRole("tab")
      .find((t) => t.textContent === "Metrics");
    expect(metricsTab).toBeDefined();
    await user.click(metricsTab!);
    expect(await screen.findByText("Total studies")).toBeInTheDocument();
    expect(await screen.findByText("12")).toBeInTheDocument();
    expect(await screen.findByText("Total instances")).toBeInTheDocument();
    expect(await screen.findByText("34")).toBeInTheDocument();
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
