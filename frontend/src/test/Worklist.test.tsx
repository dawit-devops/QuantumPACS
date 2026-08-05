import React from "react";
import {
  render,
  screen,
  within,
  waitFor,
  fireEvent,
} from "@testing-library/react";
import { renderWithAuth } from "./renderWithApp";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { AuthProvider } from "../auth/AuthContext";
import { ThemeProvider } from "../common/ThemeProvider";
import Worklist from "../worklist/Worklist";

const mockListWorklist = vi.hoisted(() => vi.fn());
const mockListStationAes = vi.hoisted(() => vi.fn());
const mockCreateWorklistEntry = vi.hoisted(() => vi.fn());
const mockUpdateWorklistEntry = vi.hoisted(() => vi.fn());
const mockDeleteWorklistEntry = vi.hoisted(() => vi.fn());
const mockMarkWorklistPerformed = vi.hoisted(() => vi.fn());

vi.mock("../api/worklist", () => ({
  listWorklist: mockListWorklist,
  listStationAes: mockListStationAes,
  createWorklistEntry: mockCreateWorklistEntry,
  updateWorklistEntry: mockUpdateWorklistEntry,
  deleteWorklistEntry: mockDeleteWorklistEntry,
  markWorklistPerformed: mockMarkWorklistPerformed,
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

const mockOnConfirm = vi.hoisted(() => vi.fn());

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
      children,
    );
  return { ...actual, Popconfirm };
});

const mockEntries = [
  {
    id: "1",
    patient_id: "P001",
    patient_name: "John Doe",
    patient_birth_date: "1980-05-15",
    patient_sex: "M",
    accession_number: "ACC-001",
    requested_procedure_desc: "CT Chest",
    modality: "CT",
    scheduled_date: "2026-07-28",
    scheduled_time: "09:00",
    status: "scheduled",
    station_ae_title: "CT-SCANNER-1",
  },
  {
    id: "2",
    patient_id: "P002",
    patient_name: "Jane Smith",
    patient_birth_date: "1990-11-20",
    patient_sex: "F",
    accession_number: "ACC-002",
    requested_procedure_desc: "MRI Brain",
    modality: "MR",
    scheduled_date: "2026-07-28",
    scheduled_time: "10:30",
    status: "scheduled",
    station_ae_title: "MR-SCANNER-2",
  },
  {
    id: "3",
    patient_id: "P003",
    patient_name: "Bob Wilson",
    patient_birth_date: "1975-03-08",
    patient_sex: "M",
    accession_number: "ACC-003",
    requested_procedure_desc: "XR Chest",
    modality: "XR",
    scheduled_date: "2026-07-27",
    scheduled_time: "14:00",
    status: "performed",
    station_ae_title: "XR-SCANNER-1",
  },
];

async function waitForTable() {
  await screen.findByText("John Doe");
}

describe("Worklist", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockListWorklist.mockImplementation(() =>
      Promise.resolve({
        data: mockEntries,
        total: mockEntries.length,
        page: 1,
        per_page: 20,
      }),
    );
    mockListStationAes.mockResolvedValue([]);
    mockCreateWorklistEntry.mockResolvedValue({} as any);
    mockUpdateWorklistEntry.mockResolvedValue(undefined);
    mockDeleteWorklistEntry.mockResolvedValue(undefined);
    mockMarkWorklistPerformed.mockResolvedValue(undefined);
    localStorage.setItem("token", "t");
    localStorage.setItem("userId", "u1");
    localStorage.setItem("admin", "true");
  });

  it("renders table, headers, and create button from API", async () => {
    renderWithAuth(<Worklist />);
    expect(await screen.findByText("John Doe")).toBeInTheDocument();
    expect(await screen.findByText("Jane Smith")).toBeInTheDocument();
    expect(await screen.findByText("Bob Wilson")).toBeInTheDocument();
    expect(screen.getByText("Patient Name")).toBeInTheDocument();
    expect(screen.getByText("Patient ID")).toBeInTheDocument();
    expect(screen.getByText("Accession #")).toBeInTheDocument();
    expect(screen.getByText("Modality")).toBeInTheDocument();
    expect(screen.getByText("Scheduled Date")).toBeInTheDocument();
    expect(screen.getByText("Status")).toBeInTheDocument();
    expect(screen.getByText("Create Entry")).toBeInTheDocument();
  });

  it("calls list endpoint with default query on mount", async () => {
    renderWithAuth(<Worklist />);
    await waitForTable();
    expect(mockListWorklist).toHaveBeenCalledWith({});
  });

  it("sends debounced search text as a query param", async () => {
    const user = userEvent.setup();
    renderWithAuth(<Worklist />);
    await waitForTable();

    await user.type(screen.getByPlaceholderText("Search patients..."), "CT");

    await waitFor(
      () => {
        expect(mockListWorklist).toHaveBeenCalledWith(
          expect.objectContaining({ search: "CT" }),
        );
      },
      { timeout: 5000 },
    );
  });

  it("sends status tab and pagination as query params", async () => {
    const user = userEvent.setup();
    renderWithAuth(<Worklist />);
    await waitForTable();

    await user.click(
      screen
        .getAllByRole("tab")
        .find((t) => t.textContent?.startsWith("Performed"))!,
    );
    await waitFor(
      () => {
        expect(mockListWorklist).toHaveBeenCalledWith(
          expect.objectContaining({ status: "performed" }),
        );
      },
      { timeout: 5000 },
    );
  });

  it("create modal opens with form fields and sends correct API request", async () => {
    const user = userEvent.setup();
    renderWithAuth(<Worklist />);
    await waitForTable();

    await user.click(screen.getByText("Create Entry"));
    const modal = screen.getByRole("dialog");
    expect(
      within(modal).getByText("Create Worklist Entry"),
    ).toBeInTheDocument();
    expect(within(modal).getByLabelText("Patient ID")).toBeInTheDocument();
    expect(within(modal).getByLabelText("Patient Name")).toBeInTheDocument();

    await user.type(within(modal).getByLabelText("Patient ID"), "P004");
    await user.type(
      within(modal).getByLabelText("Patient Name"),
      "Test Patient",
    );
    await user.type(within(modal).getByLabelText("Accession #"), "ACC-004");
    await user.click(within(modal).getByText("OK"));

    await waitFor(() => {
      expect(mockCreateWorklistEntry).toHaveBeenCalledWith(
        expect.objectContaining({
          patient_id: "P004",
          patient_name: "Test Patient",
          accession_number: "ACC-004",
        }),
      );
    });
  });

  it("edit modal opens with pre-filled values", async () => {
    const user = userEvent.setup();
    renderWithAuth(<Worklist />);
    await waitForTable();

    const editIcons = document.querySelectorAll(".anticon-edit");
    await user.click(editIcons[0]);
    const modal = screen.getByRole("dialog");
    expect(within(modal).getByDisplayValue("John Doe")).toBeInTheDocument();
    expect(within(modal).getByDisplayValue("P001")).toBeInTheDocument();
  });

  it("cancel entry calls delete API", async () => {
    renderWithAuth(<Worklist />);
    await waitForTable();

    const mockSpans = document.querySelectorAll(".mock-popconfirm");
    const cancelSpan = Array.from(mockSpans).find((s) =>
      s.getAttribute("data-title")?.includes("Cancel"),
    );
    expect(cancelSpan).toBeTruthy();
    fireEvent.click(cancelSpan!);

    await waitFor(
      () => {
        expect(mockDeleteWorklistEntry).toHaveBeenCalledWith("1");
      },
      { timeout: 10000 },
    );
  });

  it("renders an error state when the list request fails (T-M4)", async () => {
    mockListWorklist.mockRejectedValue(new Error("worklist down"));
    renderWithAuth(<Worklist />);

    expect(await screen.findByText(/worklist down/)).toBeInTheDocument();
  });

  it("renders an empty state when there are no entries (T-M4)", async () => {
    mockListWorklist.mockResolvedValue({
      data: [],
      total: 0,
      page: 1,
      per_page: 20,
    });
    renderWithAuth(<Worklist />);

    expect(await screen.findByText(/No worklist entries/)).toBeInTheDocument();
  });

  it("shows an error message when cancel fails (T-M4)", async () => {
    mockDeleteWorklistEntry.mockRejectedValue(new Error("delete denied"));
    renderWithAuth(<Worklist />);
    await waitForTable();

    const mockSpans = document.querySelectorAll(".mock-popconfirm");
    const cancelSpan = Array.from(mockSpans).find((s) =>
      s.getAttribute("data-title")?.includes("Cancel"),
    );
    fireEvent.click(cancelSpan!);

    expect(await screen.findByText(/delete denied/)).toBeInTheDocument();
  });
});
