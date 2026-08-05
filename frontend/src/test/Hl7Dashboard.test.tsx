import React from "react";
import { render, screen } from "@testing-library/react";
import { renderWithAuth } from "./renderWithApp";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { AuthProvider } from "../auth/AuthContext";
import { ThemeProvider } from "../common/ThemeProvider";
import Hl7Dashboard from "../hl7/Hl7Dashboard";

const mockListHl7Messages = vi.hoisted(() => vi.fn());
const mockGetHl7Metrics = vi.hoisted(() => vi.fn());
const mockGetHl7Config = vi.hoisted(() => vi.fn());
const mockUpdateHl7Config = vi.hoisted(() => vi.fn());
const mockGetHl7Status = vi.hoisted(() => vi.fn());
const mockGetHl7Message = vi.hoisted(() => vi.fn());

vi.mock("../api/hl7", () => ({
  listHl7Messages: mockListHl7Messages,
  getHl7Metrics: mockGetHl7Metrics,
  getHl7Config: mockGetHl7Config,
  updateHl7Config: mockUpdateHl7Config,
  getHl7Status: mockGetHl7Status,
  getHl7Message: mockGetHl7Message,
}));

vi.mock("../helpers", () => ({
  request: vi.fn(() => Promise.resolve({})),
  isAdmin: () => true,
}));

vi.mock("../hooks", () => ({
  useDocumentTitle: vi.fn(),
  useFetch: () => ({ exec: vi.fn() }),
}));

const mockMessages = [
  {
    id: "m1",
    created_at: "2026-07-01T12:00:00Z",
    message_type: "ADT",
    event_type: "A01",
    parse_status: "ok",
    patient_id: "P001",
    accession_number: "ACC001",
    sending_facility: "Hospital A",
  },
  {
    id: "m2",
    created_at: "2026-07-01T12:05:00Z",
    message_type: "ORM",
    event_type: "O01",
    parse_status: "failed",
    patient_id: "P002",
    accession_number: "ACC002",
    sending_facility: "Hospital B",
  },
];
const mockMetrics = {
  total: 50,
  by_status: [
    { parse_status: "ok", count: 35 },
    { parse_status: "failed", count: 15 },
  ],
  by_type: [{ message_type: "ADT", event_type: "A01", count: 30 }],
  by_facility: [{ sending_facility: "Hospital A", count: 30 }],
};
const mockConfig = { mllp_port: 12579, allowed_ips: ["10.0.0.0/24"] };
const mockStatus = { listening: true, host: "0.0.0.0", response_time_ms: 12 };

async function waitForMessagesTab() {
  await screen.findByText("Messages");
}

describe("Hl7Dashboard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockListHl7Messages.mockResolvedValue({
      messages: mockMessages,
      total: 2,
    });
    mockGetHl7Metrics.mockResolvedValue(mockMetrics);
    mockGetHl7Config.mockResolvedValue(mockConfig);
    mockGetHl7Status.mockResolvedValue(mockStatus);
    mockUpdateHl7Config.mockResolvedValue({ updated: [] });
    mockGetHl7Message.mockResolvedValue({} as any);
    localStorage.setItem("token", "t");
    localStorage.setItem("userId", "u1");
    localStorage.setItem("admin", "true");
  });

  it("renders tabs, fetches messages, and shows refresh/count", async () => {
    renderWithAuth(<Hl7Dashboard />);
    expect(await screen.findByText("P001")).toBeInTheDocument();
    expect(screen.getByText("Messages")).toBeInTheDocument();
    expect(screen.getByText("Analytics")).toBeInTheDocument();
    expect(screen.getByText("Configuration")).toBeInTheDocument();
    expect(mockListHl7Messages).toHaveBeenCalledWith(
      expect.objectContaining({ limit: 50, offset: 0 }),
    );
    expect(screen.getByText("Refresh")).toBeInTheDocument();
    expect(screen.getByText("2 messages")).toBeInTheDocument();
  });

  it("renders message data and filter inputs", async () => {
    renderWithAuth(<Hl7Dashboard />);
    await waitForMessagesTab();
    expect(await screen.findByText("P001")).toBeInTheDocument();
    expect(await screen.findByText("P002")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("Patient ID")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("Facility")).toBeInTheDocument();
  });

  it("shows analytics tab with metrics", async () => {
    const user = userEvent.setup();
    renderWithAuth(<Hl7Dashboard />);
    await waitForMessagesTab();
    await user.click(screen.getByText("Analytics"));
    expect(await screen.findByText("Total Messages")).toBeInTheDocument();
  });

  it("shows config tab with server status", async () => {
    const user = userEvent.setup();
    renderWithAuth(<Hl7Dashboard />);
    await waitForMessagesTab();
    await user.click(screen.getByText("Configuration"));
    expect(await screen.findByText("Listening")).toBeInTheDocument();
    expect(screen.getByDisplayValue("12579")).toBeInTheDocument();
  });

  it("disables Save and shows an alert when config fails to load", async () => {
    const user = userEvent.setup();
    mockGetHl7Config.mockRejectedValue(new Error("connection refused"));
    mockListHl7Messages.mockResolvedValue({
      messages: mockMessages,
      total: 2,
    });
    mockGetHl7Status.mockResolvedValue(mockStatus);
    mockUpdateHl7Config.mockResolvedValue({ updated: [] });
    mockGetHl7Message.mockResolvedValue({} as any);
    renderWithAuth(<Hl7Dashboard />);
    await waitForMessagesTab();
    await user.click(screen.getByText("Configuration"));

    expect(
      await screen.findByText("Failed to load configuration"),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Save" })).toBeDisabled();
  });
});
