import React from "react";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { renderWithAuth } from "./renderWithApp";
import { describe, it, expect, vi, beforeEach } from "vitest";
import InterfaceDashboard from "../admin/InterfaceDashboard";

const mockListInterfaces = vi.hoisted(() => vi.fn());
const mockListMessages = vi.hoisted(() => vi.fn());
const mockGetMetrics = vi.hoisted(() => vi.fn());
const mockListExceptions = vi.hoisted(() => vi.fn());
const mockRetry = vi.hoisted(() => vi.fn());

vi.mock("../api/ris", () => ({
  listRisInterfaces: mockListInterfaces,
  listRisInterfaceMessages: mockListMessages,
  getRisInterfaceMetrics: mockGetMetrics,
  listRisExceptions: mockListExceptions,
  retryRisException: mockRetry,
}));
vi.mock("../hooks", () => ({
  useDocumentTitle: vi.fn(),
}));
vi.mock("../common/base", () => ({
  default: (c: React.ComponentType) => c,
}));

const iface: any = {
  id: "11111111-1111-1111-1111-111111111111",
  name: "HIS Order Feed",
  interface_type: "HL7_ORM",
  protocol: "HL7V2",
  is_active: true,
  last_message_at: new Date().toISOString(),
  message_count: 5,
  error_count: 1,
  status_counts: { PROCESSED: 4, FAILED: 1 },
};

describe("InterfaceDashboard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockListInterfaces.mockResolvedValue([iface]);
    mockListMessages.mockResolvedValue({
      messages: [
        {
          id: "m1",
          message_type: "ORM",
          trigger_event: "O01",
          control_id: "MSG004",
          status: "FAILED",
          error_message: "Unparseable message",
          created_at: new Date().toISOString(),
        },
      ],
      total: 1,
    });
    mockGetMetrics.mockResolvedValue({
      endpoint_id: iface.id,
      period: "24h",
      total: 5,
      failed: 1,
      avg_latency_ms: 12.5,
    });
    mockListExceptions.mockResolvedValue([
      {
        id: "m1",
        retry_count: 1,
        error_message: "Unparseable message",
        created_at: new Date().toISOString(),
      },
    ]);
    mockRetry.mockResolvedValue({ retried: true });
  });

  it("renders interfaces with counts and latency metrics", async () => {
    renderWithAuth(<InterfaceDashboard />);
    expect(await screen.findByText("HIS Order Feed")).toBeTruthy();
    await waitFor(() => {
      expect(screen.getByText("12.5 ms")).toBeTruthy();
    });
    expect(mockGetMetrics).toHaveBeenCalledWith(iface.id, "24h");
  });

  it("lists the exception queue with the retry action", async () => {
    renderWithAuth(<InterfaceDashboard />);
    fireEvent.click(await screen.findByText("Exception Queue"));
    expect(await screen.findByText("Unparseable message")).toBeTruthy();
    fireEvent.click(screen.getByText("Retry"));
    const confirm = await screen.findByRole("button", { name: "OK" });
    fireEvent.click(confirm);
    await waitFor(() => {
      expect(mockRetry).toHaveBeenCalledWith("m1");
    });
  });
});
