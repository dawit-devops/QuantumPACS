import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { AuthProvider } from "../auth/AuthContext";
import { ThemeProvider } from "../common/ThemeProvider";
import Files from "../files/Files";

const mockQidoSearch = vi.hoisted(() => vi.fn());
const mockSearchFiles = vi.hoisted(() => vi.fn());

vi.mock("../api/files", () => ({
  qidoSearch: mockQidoSearch,
  searchFiles: mockSearchFiles,
}));

vi.mock("../helpers", () => ({
  request: vi.fn(() => Promise.resolve({})),
  open: vi.fn(),
  isAdmin: () => true,
  getAccessToken: () => "t",
  setTokens: () => {},
  tryRefreshToken: () => Promise.resolve(false),
  clearTokens: () => {},
  startRefreshTimer: () => {},
  stopRefreshTimer: () => {},
}));

vi.mock("../hooks", () => ({
  useDocumentTitle: vi.fn(),
  useFetch: () => ({ exec: vi.fn() }),
}));

const mockQidoResponse = {
  data: [
    {
      "0020000D": { vr: "UI", Value: ["1.2.3"] },
      "00080050": { vr: "SH", Value: ["ACC001"] },
    },
  ],
  total: 1,
};

const mockV2Results = {
  data: [
    {
      id: "f1",
      "Patient ID": "P001",
      "Patient's Name": "Doe^John",
      "Study ID": "1.2.3",
    },
  ],
  total: 1,
};

describe("Files QIDO-RS Search", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.setItem("token", "t");
    localStorage.setItem("userId", "u1");
    localStorage.setItem("admin", "true");
  });

  function renderWithAuth(url: string, ui: React.ReactElement) {
    return render(
      <ThemeProvider>
        <AuthProvider>
          <MemoryRouter initialEntries={[url]}>{ui}</MemoryRouter>
        </AuthProvider>
      </ThemeProvider>,
    );
  }

  it("calls QIDO-RS endpoint when query param has Patient ID search", async () => {
    mockQidoSearch.mockImplementation(() => Promise.resolve(mockQidoResponse));
    mockSearchFiles.mockImplementation(() => Promise.resolve(mockV2Results));

    const originalSearch = window.location.search;
    Object.defineProperty(window, "location", {
      writable: true,
      value: { ...window.location, search: '?{"query":"P001"}' },
    } as any);

    renderWithAuth("/?%7B%22query%22%3A%22P001%22%7D", <Files />);

    await waitFor(() => {
      expect(mockQidoSearch).toHaveBeenCalled();
    });

    Object.defineProperty(window, "location", {
      writable: true,
      value: { ...window.location, search: originalSearch },
    } as any);
  });

  it("falls back to v2 search when QIDO-RS returns empty results", async () => {
    mockQidoSearch.mockImplementation(() => Promise.resolve([]));
    mockSearchFiles.mockImplementation(() => Promise.resolve(mockV2Results));

    const originalSearch = window.location.search;
    Object.defineProperty(window, "location", {
      writable: true,
      value: { ...window.location, search: '?{"query":"P001"}' },
    } as any);

    renderWithAuth("/?%7B%22query%22%3A%22P001%22%7D", <Files />);

    await waitFor(() => {
      expect(mockSearchFiles).toHaveBeenCalled();
    });

    Object.defineProperty(window, "location", {
      writable: true,
      value: { ...window.location, search: originalSearch },
    } as any);
  });

  it("falls back to v2 search when QIDO-RS request fails", async () => {
    mockQidoSearch.mockImplementation(() =>
      Promise.reject(new Error("Network error")),
    );
    mockSearchFiles.mockImplementation(() => Promise.resolve(mockV2Results));

    const originalSearch = window.location.search;
    Object.defineProperty(window, "location", {
      writable: true,
      value: { ...window.location, search: '?{"query":"P001"}' },
    } as any);

    renderWithAuth("/?%7B%22query%22%3A%22P001%22%7D", <Files />);

    await waitFor(() => {
      expect(mockSearchFiles).toHaveBeenCalled();
    });

    Object.defineProperty(window, "location", {
      writable: true,
      value: { ...window.location, search: originalSearch },
    } as any);
  });
});
