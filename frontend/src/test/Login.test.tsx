import React from "react";
import { screen } from "@testing-library/react";
import { renderWithAuth } from "./renderWithApp";
import { describe, it, expect, vi, beforeEach } from "vitest";
import LoginForm from "../login/Login";

const mockListLoginProviders = vi.hoisted(() => vi.fn());

vi.mock("../api/auth", () => ({
  listLoginProviders: mockListLoginProviders,
}));

vi.mock("../helpers", () => ({
  request: vi.fn(() => Promise.resolve({})),
  isAdmin: () => true,
  setTokens: () => {},
  clearTokens: () => {},
  startRefreshTimer: () => {},
  stopRefreshTimer: () => {},
}));

vi.mock("../hooks", () => ({
  useDocumentTitle: vi.fn(),
  useFetch: () => ({
    exec: vi.fn(),
    showLoading: false,
    loading: false,
    data: null,
    error: null,
  }),
}));

const mockProviders = [
  { id: "1", name: "Google", slug: "google", icon: null },
  { id: "2", name: "Microsoft", slug: "microsoft", icon: null },
];

describe("LoginForm", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockListLoginProviders.mockResolvedValue(mockProviders);
  });

  it("renders login form", () => {
    renderWithAuth(<LoginForm />);
    expect(screen.getByText(/Sign in to your account/)).toBeInTheDocument();
    expect(screen.getByText("Sign In")).toBeInTheDocument();
  });

  // (R1-05) Accessible names come from aria-label, not the placeholder.
  it("labels the username and password inputs (R1-05)", () => {
    renderWithAuth(<LoginForm />);
    expect(screen.getByLabelText("Username")).toBeInTheDocument();
    expect(screen.getByLabelText("Password")).toBeInTheDocument();
  });

  it("renders SSO section with provider buttons", async () => {
    renderWithAuth(<LoginForm />);

    const googleBtns = await screen.findAllByText("Sign in with Google");
    expect(googleBtns.length).toBeGreaterThanOrEqual(1);
    const msBtns = await screen.findAllByText("Sign in with Microsoft");
    expect(msBtns.length).toBeGreaterThanOrEqual(1);
  });

  it("offers a demo-user datalist with test-role usernames", () => {
    renderWithAuth(<LoginForm />);

    const datalist = document.getElementById("demo-usernames");
    expect(datalist).not.toBeNull();
    const values = Array.from(
      (datalist as HTMLDataListElement).querySelectorAll("option"),
    ).map((o) => o.getAttribute("value"));
    expect(values).toContain("test.radiologist");
    expect(values).toContain("test.technologist");
    expect(values).toContain("test.pacs_admin");
    expect(values).toContain("test.patient");
  });
});
