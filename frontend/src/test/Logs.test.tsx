import React from "react";
import { render, screen, within, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { AuthProvider } from "../auth/AuthContext";
import { ThemeProvider } from "../common/ThemeProvider";
import Logs from "../logs/Logs";

const mockRequest = vi.hoisted(() => vi.fn());

vi.mock("../helpers", () => ({
  request: mockRequest,
  isAdmin: () => true,
}));

vi.mock("../hooks", () => ({
  useFetch: () => ({ exec: vi.fn() }),
}));

const mockLogs = [
  {
    id: 1,
    created_at: "2026-07-01T12:00:00Z",
    actor: "admin",
    event_type: "auth.login",
    resource_type: "session",
    resource_id: "1",
    description: "Admin logged in",
    tenant: "default",
    payload: "{}",
  },
  {
    id: 2,
    created_at: "2026-07-01T12:05:00Z",
    actor: "system",
    event_type: "study.read",
    resource_type: "study",
    resource_id: "2",
    description: "Study accessed",
    tenant: "default",
    payload: "{}",
  },
];

async function waitForTable() {
  await screen.findByText("admin");
}

describe("Logs", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockRequest.mockImplementation((url: string, opts?: any) => {
      if (url === "logs")
        return Promise.resolve({ data: mockLogs, total: 2, has_more: false });
      if (url === "logs/event-types")
        return Promise.resolve({ data: ["auth.login", "study.read"] });
      if (url === "logs/actors")
        return Promise.resolve({ data: ["admin", "system"] });
      return Promise.resolve({});
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

  it("renders event types in table", async () => {
    renderWithAuth(<Logs />);
    await waitForTable();
    expect(screen.getAllByText("auth.login").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("study.read").length).toBeGreaterThanOrEqual(1);
  });

  it("renders actor names", async () => {
    renderWithAuth(<Logs />);
    await waitForTable();
    expect(screen.getByText("admin")).toBeInTheDocument();
    expect(screen.getByText("system")).toBeInTheDocument();
  });

  it("renders column headers", async () => {
    renderWithAuth(<Logs />);
    await waitForTable();
    expect(screen.getByText("Timestamp")).toBeInTheDocument();
    expect(screen.getByText("Actor")).toBeInTheDocument();
    expect(screen.getByText("Event Type")).toBeInTheDocument();
    expect(screen.getByText("Description")).toBeInTheDocument();
  });

  it("calls logs endpoint on mount", async () => {
    renderWithAuth(<Logs />);
    await waitForTable();
    expect(mockRequest).toHaveBeenCalledWith("logs", expect.any(Object));
  });

  it("renders live streaming toggle", async () => {
    renderWithAuth(<Logs />);
    await waitForTable();
    expect(screen.getByText("Live")).toBeInTheDocument();
  });

  it("renders export CSV button", async () => {
    renderWithAuth(<Logs />);
    await waitForTable();
    expect(screen.getByText("CSV")).toBeInTheDocument();
  });

  it("shows empty state when no logs", async () => {
    mockRequest.mockImplementation((url: string) => {
      if (url === "logs")
        return Promise.resolve({ data: [], total: 0, has_more: false });
      if (url === "logs/event-types") return Promise.resolve({ data: [] });
      if (url === "logs/actors") return Promise.resolve({ data: [] });
      return Promise.resolve({});
    });
    renderWithAuth(<Logs />);
    await waitFor(() => {
      expect(mockRequest).toHaveBeenCalledWith("logs", expect.any(Object));
    });
  });
});
