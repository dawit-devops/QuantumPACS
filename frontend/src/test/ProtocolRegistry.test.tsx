import React from "react";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { AuthProvider } from "../auth/AuthContext";
import { ThemeProvider } from "../common/ThemeProvider";
import ProtocolRegistry from "../qa/ProtocolRegistry";

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

function renderRegistry() {
  return render(
    <ThemeProvider>
      <AuthProvider>
        <MemoryRouter initialEntries={["/qa/protocols"]}>
          <ProtocolRegistry />
        </MemoryRouter>
      </AuthProvider>
    </ThemeProvider>,
  );
}

const mockProtocols = [
  {
    id: "p1",
    protocol_code: "CTHEAD",
    name: "CT Head (Routine)",
    modality: "CT",
    body_part: "Head",
    sequences: [{ name: "Axial", required: true }],
    acr_benchmark_dlp: 930,
    acr_benchmark_ctdivol: 57,
  },
  {
    id: "p2",
    protocol_code: "MRBRAIN",
    name: "MR Brain",
    modality: "MR",
    body_part: "Brain",
    sequences: [],
    acr_benchmark_dlp: null,
  },
];

describe("ProtocolRegistry", () => {
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
    mockRequest.mockResolvedValue({ data: mockProtocols });
  });

  it("renders the seeded protocols", async () => {
    renderRegistry();
    expect(await screen.findByText("CT Head (Routine)")).toBeInTheDocument();
    expect(screen.getByText("MR Brain")).toBeInTheDocument();
    expect(screen.getByText("CTHEAD")).toBeInTheDocument();
  });

  it("shows the ACR benchmark and sequence counts", async () => {
    renderRegistry();
    await screen.findByText("CT Head (Routine)");
    expect(screen.getByText("930 mGy·cm")).toBeInTheDocument();
    expect(screen.getByText("1 required")).toBeInTheDocument();
  });

  it("opens the create modal on Add Protocol", async () => {
    renderRegistry();
    await screen.findByText("CT Head (Routine)");
    fireEvent.click(screen.getByText("Add Protocol"));
    expect(await screen.findByText("Create")).toBeInTheDocument();
  });

  it("submits a new protocol with sequences", async () => {
    renderRegistry();
    await screen.findByText("CT Head (Routine)");
    fireEvent.click(screen.getByText("Add Protocol"));
    await screen.findByText("Create");
    fireEvent.change(screen.getByLabelText("Protocol name"), {
      target: { value: "CT Abdomen" },
    });
    fireEvent.change(screen.getByLabelText("Protocol code"), {
      target: { value: "CTABD" },
    });
    fireEvent.click(screen.getByText("Create"));
    await waitFor(() => {
      const postCall = mockRequest.mock.calls.find(
        (c: any[]) => c[0] === "qa/protocols" && c[1].method === "POST",
      );
      expect(postCall).toBeTruthy();
      expect(postCall![1].data.name).toBe("CT Abdomen");
      expect(postCall![1].data.protocol_code).toBe("CTABD");
    });
  });

  it("opens the edit modal and sends a PUT on save", async () => {
    renderRegistry();
    await screen.findByText("CT Head (Routine)");
    const editButtons = screen.getAllByText("Edit");
    fireEvent.click(editButtons[0]);
    await screen.findByText("Save");
    fireEvent.click(screen.getByText("Save"));
    await waitFor(() => {
      const putCall = mockRequest.mock.calls.find(
        (c: any[]) => c[0] === "qa/protocols/p1" && c[1].method === "PUT",
      );
      expect(putCall).toBeTruthy();
      expect(putCall![1].data.name).toBe("CT Head (Routine)");
    });
  });
});
