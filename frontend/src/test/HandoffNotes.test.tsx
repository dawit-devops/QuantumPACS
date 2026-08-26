import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import React from "react";
import { MemoryRouter } from "react-router";
import { App } from "antd";
import { AuthProvider } from "../auth/AuthContext";
import { ThemeProvider } from "../common/ThemeProvider";
import HandoffNotes from "../coordinator/HandoffNotes";

vi.mock("../api/ris", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api/ris")>();
  return {
    ...actual,
    listHandoffNotes: vi.fn(),
    createHandoffNote: vi.fn(),
    markHandoffNoteRead: vi.fn(),
  };
});

vi.mock("../hooks", () => ({
  useDocumentTitle: vi.fn(),
  useTenantRefetch: vi.fn(),
}));

vi.mock("../auth/AuthContext", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../auth/AuthContext")>();
  return {
    ...actual,
    useAuth: () => ({ hasPermission: () => true }),
  };
});

import { listHandoffNotes, createHandoffNote, markHandoffNoteRead } from "../api/ris";
const mockList = vi.mocked(listHandoffNotes);
const mockCreate = vi.mocked(createHandoffNote);
const mockMarkRead = vi.mocked(markHandoffNoteRead);

function renderHandoffNotes() {
  localStorage.setItem("userId", "1");
  localStorage.setItem("username", "test");
  localStorage.setItem("permissions", JSON.stringify(["PATIENT_READ", "PATIENT_WRITE"]));
  localStorage.setItem("tenant_id", "t1");
  return render(
    <MemoryRouter>
      <App>
        <AuthProvider>
          <ThemeProvider>
            <HandoffNotes />
          </ThemeProvider>
        </AuthProvider>
      </App>
    </MemoryRouter>
  );
}

const mockNote: import("../api/ris").HandoffNote = {
  id: "hn-1",
  patient_id: "8675309",
  note: "Patient needs follow-up call before discharge.",
  priority: "high",
  is_read: false,
  tenant_id: "t1",
  created_by: "1",
  created_at: "2026-08-22T10:00:00Z",
};

describe("HandoffNotes", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockList.mockResolvedValue([mockNote]);
  });

  it("renders handoff notes with priority and unread status", async () => {
    renderHandoffNotes();
    await waitFor(() => {
      expect(screen.getByText(/Patient needs follow-up call/i)).toBeInTheDocument();
    });
    expect(screen.getByText("HIGH")).toBeInTheDocument();
    expect(screen.getByText("Unread")).toBeInTheDocument();
  });

  it("lists notes via listHandoffNotes", async () => {
    renderHandoffNotes();
    await waitFor(() => {
      expect(mockList).toHaveBeenCalled();
    });
  });

  it("marks a note as read from the row action", async () => {
    mockMarkRead.mockResolvedValue(undefined);
    renderHandoffNotes();
    await waitFor(() => {
      expect(screen.getByText("Mark Read")).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText("Mark Read"));
    await waitFor(() => {
      expect(mockMarkRead).toHaveBeenCalledWith("hn-1");
    });
  });

  it("creates a new handoff note from the modal", async () => {
    mockCreate.mockResolvedValue(mockNote);
    renderHandoffNotes();
    await waitFor(() => {
      expect(screen.getByText("New Note")).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText("New Note"));
    await waitFor(() => {
      expect(screen.getByText("New Handoff Note")).toBeInTheDocument();
    });

    fireEvent.change(screen.getByLabelText(/Patient ID/), {
      target: { value: "8675309" },
    });
    fireEvent.change(screen.getByLabelText(/Note/), {
      target: { value: "Urgent handoff for the next shift." },
    });
    fireEvent.click(screen.getByRole("button", { name: /create note/i }));

    await waitFor(() => {
      expect(mockCreate).toHaveBeenCalledWith({
        patient_id: "8675309",
        note: "Urgent handoff for the next shift.",
        priority: "normal",
      });
    });
  });

  it("shows read status for read notes", async () => {
    mockList.mockResolvedValue([{ ...mockNote, is_read: true, priority: "high" as const }]);
    renderHandoffNotes();
    await waitFor(() => {
      expect(screen.getByText("Read")).toBeInTheDocument();
    });
    expect(screen.queryByText("Mark Read")).not.toBeInTheDocument();
  });

  it("renders empty state when no notes exist", async () => {
    mockList.mockResolvedValue([]);
    renderHandoffNotes();
    await waitFor(() => {
      expect(screen.getByText(/No handoff notes yet/i)).toBeInTheDocument();
    });
  });
});
