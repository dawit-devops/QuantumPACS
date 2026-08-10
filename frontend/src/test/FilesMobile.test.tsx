import React from "react";
import {
  render,
  screen,
  waitFor,
  fireEvent,
  within,
} from "@testing-library/react";
import { renderWithAuth } from "./renderWithApp";
import { describe, it, expect, vi, beforeEach } from "vitest";
import Files from "../files/Files";

const mockQidoSearch = vi.hoisted(() => vi.fn());
const mockSearchFiles = vi.hoisted(() => vi.fn());
const mockNavigate = vi.hoisted(() => vi.fn());

vi.mock("react-router", async (importOriginal) => {
  const actual = await importOriginal<typeof import("react-router")>();
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

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
  useTenantRefetch: () => {},
}));

function makeRows(n: number) {
  return Array.from({ length: n }, (_, i) => ({
    id: String(i + 1),
    "Patient ID": `P${String(i + 1).padStart(3, "0")}`,
    "Patient's Name": `Doe^Patient${i + 1}`,
    Modality: "CT",
    "Study Description": `Study ${i + 1}`,
  }));
}

describe("Files mobile card list", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.setItem("token", "t");
    localStorage.setItem("userId", "u1");
    localStorage.setItem("admin", "true");
    Object.defineProperty(window, "innerWidth", {
      writable: true,
      configurable: true,
      value: 1024,
    });
  });

  it("paginates the mobile card list in 20-card chunks (R1-05)", async () => {
    Object.defineProperty(window, "innerWidth", {
      writable: true,
      configurable: true,
      value: 375,
    });
    mockQidoSearch.mockResolvedValue([]);
    mockSearchFiles.mockResolvedValue({ data: makeRows(25), total: 25 });

    const { container } = renderWithAuth(<Files />);

    await waitFor(() => {
      expect(container.querySelectorAll(".ant-card").length).toBe(20);
    });
    const loadMore = screen.getByRole("button", {
      name: /Load more \(5 remaining\)/,
    });
    fireEvent.click(loadMore);
    await waitFor(() => {
      expect(container.querySelectorAll(".ant-card").length).toBe(25);
    });
    expect(
      screen.queryByRole("button", { name: /Load more/ }),
    ).not.toBeInTheDocument();
  });

  it("renders mobile card titles as real links (R1-05)", async () => {
    Object.defineProperty(window, "innerWidth", {
      writable: true,
      configurable: true,
      value: 375,
    });
    mockQidoSearch.mockResolvedValue([]);
    mockSearchFiles.mockResolvedValue({ data: makeRows(2), total: 2 });

    const { container } = renderWithAuth(<Files />);
    await waitFor(() => {
      expect(container.querySelectorAll(".ant-card").length).toBe(2);
    });
    const links = container.querySelectorAll(".ant-card a");
    expect(links).toHaveLength(2);
    expect(links[0].getAttribute("href")).toBe("/files/1");
  });

  it("keeps edited values when a custom advanced field is removed (R1-05)", async () => {
    mockQidoSearch.mockResolvedValue([]);
    mockSearchFiles.mockResolvedValue({ data: [], total: 0 });

    renderWithAuth(<Files />);
    await waitFor(() => {
      expect(mockSearchFiles).toHaveBeenCalled();
    });
    fireEvent.click(screen.getByRole("button", { name: "Advanced" }));
    const dialog = await screen.findByRole("dialog");

    fireEvent.click(
      within(dialog).getByRole("button", { name: "Add search field" }),
    );
    fireEvent.change(within(dialog).getByLabelText("Field name 13"), {
      target: { value: "Study UID" },
    });
    fireEvent.change(within(dialog).getByLabelText("Field value 13"), {
      target: { value: "1.2.3" },
    });

    fireEvent.click(
      within(dialog).getByRole("button", { name: "Add search field" }),
    );
    fireEvent.click(
      within(dialog).getByRole("button", { name: "Remove field 14" }),
    );

    // Removing the later row must not mutate or drop the earlier row's values.
    expect(within(dialog).getByLabelText("Field name 13")).toHaveValue(
      "Study UID",
    );
    expect(within(dialog).getByLabelText("Field value 13")).toHaveValue(
      "1.2.3",
    );

    fireEvent.click(within(dialog).getByRole("button", { name: "Search" }));
    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith(
        "?" + encodeURIComponent(JSON.stringify({ "Study UID": ["1.2.3"] })),
      );
    });
  });
});
