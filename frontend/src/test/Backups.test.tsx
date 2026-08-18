import React from "react";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { renderWithAuth } from "./renderWithApp";
import { describe, it, expect, vi, beforeEach } from "vitest";
import Backups from "../admin/Backups";

const mockList = vi.hoisted(() => vi.fn());
const mockCreate = vi.hoisted(() => vi.fn());
const mockDelete = vi.hoisted(() => vi.fn());
const mockVerify = vi.hoisted(() => vi.fn());
const mockDownload = vi.hoisted(() => vi.fn());

vi.mock("../api/admin", () => ({
  listBackups: mockList,
  createBackup: mockCreate,
  deleteBackup: mockDelete,
  verifyBackup: mockVerify,
  downloadBackup: mockDownload,
}));
vi.mock("../hooks", () => ({
  useDocumentTitle: vi.fn(),
}));

const completed: any = {
  id: "b1",
  status: "completed",
  kind: "metadata",
  artifact_key: "backups/b1.json",
  size_bytes: 1500,
  files_count: 42,
  bytes_count: 1048576,
  created_by: 1,
  created_at: new Date().toISOString(),
};
const running: any = { ...completed, id: "b2", status: "running", files_count: 7, bytes_count: 512, size_bytes: 51200 };
const failed: any = { ...completed, id: "b3", status: "failed", files_count: 0, bytes_count: 0, size_bytes: 0 };

describe("Backups", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockList.mockResolvedValue({ data: [completed, running, failed] });
    mockCreate.mockResolvedValue({ data: { ...completed, id: "b4" } });
    mockDelete.mockResolvedValue({ message: "ok" });
    mockVerify.mockResolvedValue({
      message: "ok",
      verification: { backup_id: "b1", files: 42, bytes: 1048576, valid: true },
    });
    mockDownload.mockResolvedValue(undefined);
  });

  it("renders the backup table with status tags and formatted sizes", async () => {
    renderWithAuth(<Backups />);
    await waitFor(() =>
      expect(screen.getByText("COMPLETED")).toBeInTheDocument(),
    );
    expect(screen.getByText("RUNNING")).toBeInTheDocument();
    expect(screen.getByText("FAILED")).toBeInTheDocument();
    expect(screen.getAllByText("42").length).toBeGreaterThan(0);
    expect(screen.getByText("1.0 MB")).toBeInTheDocument();
    expect(screen.getByText("1.5 KB")).toBeInTheDocument();
    expect(mockList).toHaveBeenCalledTimes(1);
  });

  it("shows the empty state when no backups exist", async () => {
    mockList.mockResolvedValue({ data: [] });
    renderWithAuth(<Backups />);
    await waitFor(() =>
      expect(
        screen.getByText(/No backups yet/i),
      ).toBeInTheDocument(),
    );
  });

  it("surfaces a load error and retries", async () => {
    mockList.mockRejectedValueOnce(new Error("boom"));
    mockList.mockResolvedValue({ data: [completed] });
    renderWithAuth(<Backups />);
    await waitFor(() => expect(screen.getByText("boom")).toBeInTheDocument());
    fireEvent.click(screen.getByText("Retry"));
    await waitFor(() => expect(mockList).toHaveBeenCalledTimes(2));
    expect(screen.getByText("COMPLETED")).toBeInTheDocument();
  });

  it("creates a backup on demand and refreshes the list", async () => {
    renderWithAuth(<Backups />);
    await waitFor(() =>
      expect(screen.getByText("COMPLETED")).toBeInTheDocument(),
    );
    fireEvent.click(screen.getByRole("button", { name: /back up now/i }));
    await waitFor(() => expect(mockCreate).toHaveBeenCalledTimes(1));
    expect(mockList).toHaveBeenCalledTimes(2);
  });

  it("deletes a backup after confirmation", async () => {
    renderWithAuth(<Backups />);
    await waitFor(() =>
      expect(screen.getByText("COMPLETED")).toBeInTheDocument(),
    );
    const row = screen.getByText("COMPLETED").closest("tr")!;
    fireEvent.click(row.querySelectorAll("button")[2] as HTMLElement);
    await waitFor(() =>
      expect(screen.getByText("Delete this backup?")).toBeInTheDocument(),
    );
    fireEvent.click(screen.getByRole("button", { name: "OK" }));
    await waitFor(() => expect(mockDelete).toHaveBeenCalledWith("b1"));
    expect(mockList).toHaveBeenCalledTimes(2);
  });

  it("runs a verification and shows the result", async () => {
    renderWithAuth(<Backups />);
    await waitFor(() =>
      expect(screen.getByText("COMPLETED")).toBeInTheDocument(),
    );
    fireEvent.click(screen.getAllByText("Verify")[0]);
    await waitFor(() => expect(mockVerify).toHaveBeenCalledWith("b1"));
    expect(
      screen.getByText(
        "Artifact verified — download it to recover this snapshot",
      ),
    ).toBeInTheDocument();
  });
});
