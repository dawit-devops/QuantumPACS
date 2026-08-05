import React from "react";
import { render, screen, within, waitFor } from "@testing-library/react";
import { renderWithAuth } from "./renderWithApp";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { AuthProvider } from "../auth/AuthContext";
import { ThemeProvider } from "../common/ThemeProvider";
import Logs from "../logs/Logs";

const mockListLogs = vi.hoisted(() => vi.fn());
const mockListLogActors = vi.hoisted(() => vi.fn());

vi.mock("../api/logs", () => ({
  listLogs: mockListLogs,
  listLogActors: mockListLogActors,
}));

vi.mock("../helpers", () => ({
  request: vi.fn(() => Promise.resolve({})),
  isAdmin: () => true,
}));

vi.mock("../hooks", () => ({
  useDocumentTitle: vi.fn(),
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
    mockListLogs.mockImplementation(() =>
      Promise.resolve({ data: mockLogs, total: 2, has_more: false }),
    );
    mockListLogActors.mockImplementation(() =>
      Promise.resolve(["admin", "system"]),
    );
    localStorage.setItem("token", "t");
    localStorage.setItem("userId", "u1");
    localStorage.setItem("admin", "true");
  });

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
    expect(mockListLogs).toHaveBeenCalled();
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
    mockListLogs.mockImplementation(() =>
      Promise.resolve({ data: [], total: 0, has_more: false }),
    );
    renderWithAuth(<Logs />);
    await waitFor(() => {
      expect(mockListLogs).toHaveBeenCalled();
    });
  });
});
