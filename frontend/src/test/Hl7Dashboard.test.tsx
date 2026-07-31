import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { AuthProvider } from "../auth/AuthContext";
import { ThemeProvider } from "../common/ThemeProvider";
import Hl7Dashboard from "../hl7/Hl7Dashboard";

const mockRequest = vi.hoisted(() => vi.fn());

vi.mock("../helpers", () => ({
  request: mockRequest,
  isAdmin: () => true,
}));

vi.mock("../hooks", () => ({
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
    mockRequest.mockImplementation((url: string) => {
      if (url.startsWith("hl7/admin/messages"))
        return Promise.resolve({ messages: mockMessages, total: 2 });
      if (url.startsWith("hl7/admin/metrics"))
        return Promise.resolve(mockMetrics);
      if (url === "hl7/admin/config") return Promise.resolve(mockConfig);
      if (url === "hl7/admin/status") return Promise.resolve(mockStatus);
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

  it("renders all three tabs", async () => {
    renderWithAuth(<Hl7Dashboard />);
    await waitForMessagesTab();
    expect(screen.getByText("Messages")).toBeInTheDocument();
    expect(screen.getByText("Analytics")).toBeInTheDocument();
    expect(screen.getByText("Configuration")).toBeInTheDocument();
  });

  it("fetches messages on mount", async () => {
    renderWithAuth(<Hl7Dashboard />);
    await waitFor(() => {
      expect(mockRequest).toHaveBeenCalledWith(
        "hl7/admin/messages?limit=50&offset=0",
      );
    });
  });

  it("renders message data in table", async () => {
    renderWithAuth(<Hl7Dashboard />);
    await waitForMessagesTab();
    expect(await screen.findByText("P001")).toBeInTheDocument();
    expect(await screen.findByText("P002")).toBeInTheDocument();
  });

  it("renders filter inputs", async () => {
    renderWithAuth(<Hl7Dashboard />);
    await waitForMessagesTab();
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

  it("renders refresh button", async () => {
    renderWithAuth(<Hl7Dashboard />);
    await waitForMessagesTab();
    expect(screen.getByText("Refresh")).toBeInTheDocument();
  });

  it("shows message count", async () => {
    renderWithAuth(<Hl7Dashboard />);
    await waitForMessagesTab();
    await screen.findByText("P001");
    expect(screen.getByText("2 messages")).toBeInTheDocument();
  });
});
