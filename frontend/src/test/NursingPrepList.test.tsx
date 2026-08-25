import React from "react";
import { screen } from "@testing-library/react";
import { renderWithAuth } from "./renderWithApp";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { AuthProvider } from "../auth/AuthContext";
import { ThemeProvider } from "../common/ThemeProvider";
import NursingPrepList from "../nursing/NursingPrepList";

const mockGetPrepList = vi.hoisted(() => vi.fn());

vi.mock("../api/nursing", () => ({
  getPrepList: mockGetPrepList,
}));

vi.mock("../hooks", () => ({
  useDocumentTitle: vi.fn(),
  useFetch: () => ({ exec: vi.fn() }),
}));

const ROWS = [
  {
    exam_id: "e-1",
    patient_name: "Jane Doe",
    patient_id: "P1",
    modality: "CT",
    priority: "stat",
    status: "ready",
    checklist_id: "c1",
    checklist_status: "in_progress" as const,
    checked_count: 2,
    required_count: 5,
  },
  {
    exam_id: "e-2",
    patient_name: "John Roe",
    patient_id: "P2",
    modality: "MR",
    priority: "routine",
    status: "in_progress",
    checklist_status: null,
    checklist_id: null,
  },
];

function renderPage() {
  // renderWithAuth supplies the MemoryRouter — no second Router here.
  return renderWithAuth(<NursingPrepList />);
}

beforeEach(() => {
  vi.clearAllMocks();
  localStorage.clear();
  localStorage.setItem("token", "t");
  localStorage.setItem("userId", "u2");
  localStorage.setItem("admin", "false");
  localStorage.setItem("role", "care_coordinator");
  localStorage.setItem("permissions", JSON.stringify(["NURSING_READ", "NURSING_WRITE"]));
  mockGetPrepList.mockResolvedValue(ROWS);
});

describe("NursingPrepList (§2.11)", () => {
  it("lists exams awaiting prep with checklist state", async () => {
    renderPage();

    expect(await screen.findByText("Jane Doe")).toBeInTheDocument();
    expect(screen.getByText("John Roe")).toBeInTheDocument();
    expect(screen.getByText("2/5 REQUIRED CHECKED")).toBeInTheDocument();
    expect(screen.getByText("Not started")).toBeInTheDocument();
    expect(screen.getByText("STAT")).toBeInTheDocument();
  });

  it("deep-links rows into the exam console", async () => {
    renderPage();
    await screen.findByText("Jane Doe");
    const openBtns = await screen.findAllByRole("button", {
      name: /open exam console/i,
    });
    expect(openBtns.length).toBe(2);
  });

  it("shows an empty state when nothing awaits preparation", async () => {
    mockGetPrepList.mockResolvedValue([]);
    renderPage();

    expect(await screen.findByText(/No exams awaiting preparation/)).toBeInTheDocument();
  });

  it("surfaces load errors with the error state", async () => {
    mockGetPrepList.mockRejectedValue(new Error("backend unreachable"));
    renderPage();

    expect(await screen.findByText(/backend unreachable/)).toBeInTheDocument();
  });

  it("passes an axe serious-violations scan", async () => {
    const { container } = renderPage();
    await screen.findByText("Jane Doe");

    const { scanA11y, seriousViolations } = await import("./axe");
    const results = await scanA11y(container);
    expect(seriousViolations(results)).toEqual([]);
  });
});
