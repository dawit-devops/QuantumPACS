import React from "react";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { renderWithAuth } from "./renderWithApp";
import { describe, it, expect, vi, beforeEach } from "vitest";
import Settings from "../admin/Settings";

const mockGet = vi.hoisted(() => vi.fn());
const mockUpdate = vi.hoisted(() => vi.fn());

vi.mock("../api/admin", () => ({
  getAdminConfig: mockGet,
  updateAdminConfig: mockUpdate,
}));
vi.mock("../hooks", () => ({
  useDocumentTitle: vi.fn(),
}));

const baseSettings = {
  max_upload_size_mb: { value: 200, type: "int", restart: false },
  max_stow_size_mb: { value: 400, type: "int", restart: false },
  token_expiry_days: { value: 14, type: "int", restart: true },
  tenant_usage_retention_days: { value: 90, type: "int", restart: false },
  allowed_hosts: { value: "localhost", type: "str", restart: true },
  cors_origins: { value: "*", type: "str", restart: false },
  cookie_secure: { value: false, type: "bool", restart: false },
};

describe("Settings", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGet.mockResolvedValue({ settings: baseSettings });
    mockUpdate.mockResolvedValue({ updated: ["max_upload_size_mb"] });
  });

  it("renders grouped setting cards with labels and values", async () => {
    renderWithAuth(<Settings />);
    await waitFor(() =>
      expect(screen.getByText("Storage & Upload")).toBeInTheDocument(),
    );
    expect(screen.getByText("Auth & Retention")).toBeInTheDocument();
    expect(screen.getByText("Security & Hosting")).toBeInTheDocument();
    expect(screen.getByText("Max file upload size (MB)")).toBeInTheDocument();
    expect(screen.getByText("Secure cookies (HTTPS only)")).toBeInTheDocument();
    expect(mockGet).toHaveBeenCalledTimes(1);
  });

  it("flags restart-required settings", async () => {
    renderWithAuth(<Settings />);
    await waitFor(() =>
      expect(screen.getByText("Storage & Upload")).toBeInTheDocument(),
    );
    expect(screen.getAllByText("restart required").length).toBe(2);
    expect(
      screen.getByText(/Some settings need a restart to take effect/),
    ).toBeInTheDocument();
  });

  it("saves a group and reports how many settings changed", async () => {
    renderWithAuth(<Settings />);
    await waitFor(() =>
      expect(screen.getByText("Storage & Upload")).toBeInTheDocument(),
    );
    const storageCard = screen
      .getByText("Storage & Upload")
      .closest(".ant-card")!;
    fireEvent.click(
      storageCard.querySelector("button")!,
    );
    await waitFor(() => expect(mockUpdate).toHaveBeenCalledTimes(1));
    expect(mockUpdate.mock.calls[0][0]).toEqual({
      max_upload_size_mb: { value: 200 },
      max_stow_size_mb: { value: 400 },
    });
    await waitFor(() =>
      expect(screen.getByText("Saved 1 setting(s)")).toBeInTheDocument(),
    );
  });

  it("surfaces a load error and retries", async () => {
    mockGet.mockRejectedValueOnce(new Error("config boom"));
    renderWithAuth(<Settings />);
    await waitFor(() => expect(screen.getByText("config boom")).toBeInTheDocument());
    fireEvent.click(screen.getByText("Retry"));
    await waitFor(() => expect(mockGet).toHaveBeenCalledTimes(2));
    expect(screen.getByText("Storage & Upload")).toBeInTheDocument();
  });
});
