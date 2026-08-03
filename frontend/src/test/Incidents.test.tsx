import React from "react";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { AuthProvider } from "../auth/AuthContext";
import { ThemeProvider } from "../common/ThemeProvider";
import Incidents from "../qa/Incidents";

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

// antd's static message API spawns a real React root + auto-dismiss timer;
// after jsdom tears down, the pending scheduler callback throws
// "window is not defined". Stub it like Worklist.test.tsx does.
vi.mock("antd", async () => {
  const actual = await vi.importActual("antd");
  return {
    ...actual,
    message: {
      success: vi.fn(),
      error: vi.fn(),
      info: vi.fn(),
      warning: vi.fn(),
    },
  };
});

function renderIncidents() {
  return render(
    <ThemeProvider>
      <AuthProvider>
        <MemoryRouter initialEntries={["/qa/incidents"]}>
          <Incidents />
        </MemoryRouter>
      </AuthProvider>
    </ThemeProvider>,
  );
}

const mockIncidents = [
  {
    id: "i1",
    incident_type: "patient_motion",
    severity: "medium",
    patient_name: "John Doe",
    accession_number: "ACC-100",
    description: "Patient moved during scan",
    status: "open",
  },
  {
    id: "i2",
    incident_type: "artifact",
    severity: "low",
    patient_name: "Jane Smith",
    accession_number: "ACC-101",
    description: "Metal artifact",
    status: "resolved",
  },
];

describe("Incidents", () => {
  beforeEach(() => {
    localStorage.clear();
    localStorage.setItem("userId", "qa-1");
    localStorage.setItem("username", "qa_user");
    localStorage.setItem("admin", "true");
    localStorage.setItem("role", "qa_team");
    localStorage.setItem(
      "permissions",
      JSON.stringify(["QA_READ", "QA_WRITE", "PROTOCOL_MANAGE"]),
    );
    mockRequest.mockReset();
    mockRequest.mockResolvedValue({ data: mockIncidents });
  });

  it("renders the incident rows", async () => {
    renderIncidents();
    expect(await screen.findByText("patient_motion")).toBeInTheDocument();
    expect(screen.getByText("Patient moved during scan")).toBeInTheDocument();
    expect(screen.getByText("resolved")).toBeInTheDocument();
  });

  it("shows severity tags", async () => {
    renderIncidents();
    expect(await screen.findByText("medium")).toBeInTheDocument();
    expect(screen.getByText("low")).toBeInTheDocument();
  });

  it("only shows Resolve on open incidents", async () => {
    renderIncidents();
    await screen.findByText("patient_motion");
    expect(screen.getAllByText("Resolve")).toHaveLength(1);
  });

  it("logs an incident via the modal", async () => {
    renderIncidents();
    await screen.findByText("patient_motion");
    fireEvent.click(screen.getByText("Log Incident"));
    await screen.findByText("Log incident");
    fireEvent.change(screen.getByLabelText("Exam ID"), {
      target: { value: "e9" },
    });
    // Required Select: open the incident-type dropdown in the modal and pick an option.
    fireEvent.mouseDown(screen.getByLabelText("Incident Type"));
    await waitFor(() => {
      expect(
        document.querySelectorAll(".ant-select-item-option").length,
      ).toBeGreaterThan(0);
    });
    const options = Array.from(
      document.querySelectorAll(".ant-select-item-option"),
    );
    const option = options.find((o) => o.textContent === "patient_motion");
    expect(option).toBeTruthy();
    fireEvent.click(option!);
    fireEvent.change(screen.getByLabelText("Description"), {
      target: { value: "Contrast extravasation" },
    });
    fireEvent.click(screen.getByText("Log incident"));
    await waitFor(() => {
      const postCall = mockRequest.mock.calls.find(
        (c: any[]) => c[0] === "qa/incidents" && c[1].method === "POST",
      );
      expect(postCall).toBeTruthy();
      expect(postCall![1].data.exam_id).toBe("e9");
    });
  });

  it("resolves an incident with notes", async () => {
    renderIncidents();
    await screen.findByText("patient_motion");
    fireEvent.click(screen.getByText("Resolve"));
    await screen.findByText("Resolve Incident");
    fireEvent.change(screen.getByLabelText("Resolution notes"), {
      target: { value: "Retake scheduled" },
    });
    fireEvent.click(screen.getAllByText("Resolve")[1]);
    await waitFor(() => {
      const postCall = mockRequest.mock.calls.find(
        (c: any[]) =>
          c[0] === "qa/incidents/i1/resolve" && c[1].method === "POST",
      );
      expect(postCall).toBeTruthy();
      expect(postCall![1].data.notes).toBe("Retake scheduled");
    });
  });
});
