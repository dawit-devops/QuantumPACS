import React from "react";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { AuthProvider } from "../auth/AuthContext";
import { ThemeProvider } from "../common/ThemeProvider";
import CorrectiveActions from "../qa/CorrectiveActions";

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

function renderActions() {
  return render(
    <ThemeProvider>
      <AuthProvider>
        <MemoryRouter initialEntries={["/qa/corrective-actions"]}>
          <CorrectiveActions />
        </MemoryRouter>
      </AuthProvider>
    </ThemeProvider>,
  );
}

const mockActions = [
  {
    id: "ca1",
    source: "R05_self",
    status: "open",
    issue: "DLP exceeded ACR benchmark on CT Head",
    study_uids: ["1.2.3.4"],
    created_at: "2026-08-03T09:00:00Z",
    resolved_at: null,
  },
  {
    id: "ca2",
    source: "R06",
    status: "resolved",
    issue: "Repeat scans above threshold",
    study_uids: [],
    created_at: "2026-08-01T09:00:00Z",
    resolved_at: "2026-08-02T09:00:00Z",
    findings: "Root cause: motion artifact",
    actions_taken: "Retraining scheduled",
  },
];

describe("CorrectiveActions", () => {
  beforeEach(() => {
    localStorage.clear();
    localStorage.setItem("userId", "qa-1");
    localStorage.setItem("username", "qa_user");
    localStorage.setItem("admin", "true");
    localStorage.setItem("role", "qa_officer");
    localStorage.setItem(
      "permissions",
      JSON.stringify(["QA_READ", "QA_WRITE", "PROTOCOL_MANAGE"]),
    );
    mockRequest.mockReset();
    mockRequest.mockResolvedValue({ data: mockActions });
  });

  it("renders the open corrective actions with an open badge", async () => {
    renderActions();
    expect(
      await screen.findByText("DLP exceeded ACR benchmark on CT Head"),
    ).toBeInTheDocument();
    expect(screen.getByText("1")).toBeInTheDocument();
  });

  it("shows resolution details for resolved actions", async () => {
    renderActions();
    await screen.findByText("DLP exceeded ACR benchmark on CT Head");
    expect(screen.getByText(/Root cause: motion artifact/)).toBeInTheDocument();
    expect(screen.getByText(/Retraining scheduled/)).toBeInTheDocument();
  });

  it("only offers Resolve on open actions", async () => {
    renderActions();
    await screen.findByText("DLP exceeded ACR benchmark on CT Head");
    expect(screen.getAllByText("Resolve")).toHaveLength(1);
  });

  it("resolves an action with findings and actions taken", async () => {
    renderActions();
    await screen.findByText("DLP exceeded ACR benchmark on CT Head");
    fireEvent.click(screen.getByText("Resolve"));
    await screen.findByText("Resolve Corrective Action");
    fireEvent.change(screen.getByLabelText("Findings"), {
      target: { value: "kVp drift" },
    });
    fireEvent.change(screen.getByLabelText("Actions taken"), {
      target: { value: "Calibrated tube" },
    });
    fireEvent.click(screen.getByText("Mark resolved"));
    await waitFor(() => {
      const postCall = mockRequest.mock.calls.find(
        (c: any[]) =>
          c[0] === "qa/corrective-actions/ca1/resolve" &&
          c[1].method === "POST",
      );
      expect(postCall).toBeTruthy();
      expect(postCall![1].data.findings).toBe("kVp drift");
      expect(postCall![1].data.actions_taken).toBe("Calibrated tube");
    });
  });

  it("shows an empty state when no actions exist", async () => {
    mockRequest.mockResolvedValue({ data: [] });
    renderActions();
    expect(
      await screen.findByText("No corrective actions assigned"),
    ).toBeInTheDocument();
  });
});
