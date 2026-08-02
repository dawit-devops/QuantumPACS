import React from "react";
import { render, screen, within, waitFor } from "@testing-library/react";
import { renderWithApp } from "./renderWithApp";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { AuthProvider } from "../auth/AuthContext";
import { ThemeProvider } from "../common/ThemeProvider";
import Integrations from "../integrations/Integrations";

const mockListOauthProviders = vi.hoisted(() => vi.fn());
const mockListWebhooks = vi.hoisted(() => vi.fn());
const mockCreateWebhook = vi.hoisted(() => vi.fn());
const mockDeleteWebhook = vi.hoisted(() => vi.fn());

vi.mock("../api/integrations", () => ({
  listOauthProviders: mockListOauthProviders,
  createOauthProvider: vi.fn(),
  updateOauthProvider: vi.fn(),
  deleteOauthProvider: vi.fn(),
  listWebhooks: mockListWebhooks,
  createWebhook: mockCreateWebhook,
  updateWebhook: vi.fn(),
  deleteWebhook: mockDeleteWebhook,
  testWebhook: vi.fn(() => Promise.resolve({})),
}));

vi.mock("../helpers", () => ({
  request: vi.fn(() => Promise.resolve({})),
  isAdmin: () => true,
}));

vi.mock("../hooks", () => ({
  useDocumentTitle: vi.fn(),
  useFetch: () => ({ exec: vi.fn() }),
}));

const mockWebhooks = [
  {
    id: 1,
    name: "Slack",
    url: "https://hooks.slack.com/abc",
    events: ["study.read"],
    active: true,
    last_triggered_at: "2026-07-01T12:00:00Z",
    last_status_code: 200,
  },
  {
    id: 2,
    name: "PagerDuty",
    url: "https://events.pagerduty.com/xyz",
    events: [],
    active: false,
    last_triggered_at: null,
    last_status_code: null,
  },
];
const mockProviders = [
  {
    id: "p1",
    issuer: "https://accounts.google.com",
    client_id: "g-client",
    scope: "openid email",
    enabled: true,
    auto_provision: true,
  },
  {
    id: "p2",
    issuer: "https://idp.example.com",
    client_id: "e-client",
    scope: "openid",
    enabled: false,
    auto_provision: false,
  },
];
const mockEvents = ["study.read", "study.created", "user.created"];

async function waitForTabs() {
  await screen.findByText("Webhooks");
}

describe("Integrations", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockListWebhooks.mockResolvedValue({
      webhooks: mockWebhooks,
      available_events: mockEvents,
    });
    mockListOauthProviders.mockResolvedValue(mockProviders);
    mockCreateWebhook.mockResolvedValue({} as any);
    mockDeleteWebhook.mockResolvedValue(undefined);
    localStorage.setItem("token", "t");
    localStorage.setItem("userId", "u1");
    localStorage.setItem("admin", "true");
  });

  function renderWithAuth(ui: React.ReactElement) {
    return renderWithApp(
      <ThemeProvider>
        <AuthProvider>
          <MemoryRouter>{ui}</MemoryRouter>
        </AuthProvider>
      </ThemeProvider>,
    );
  }

  it("renders both tabs", async () => {
    renderWithAuth(<Integrations />);
    await waitForTabs();
    expect(screen.getByText("Webhooks")).toBeInTheDocument();
    expect(screen.getByText("OAuth Providers")).toBeInTheDocument();
  });

  it("renders webhook names in table", async () => {
    renderWithAuth(<Integrations />);
    await waitForTabs();
    expect(await screen.findByText("Slack")).toBeInTheDocument();
    expect(await screen.findByText("PagerDuty")).toBeInTheDocument();
  });

  it("renders OAuth provider table on tab switch", async () => {
    const user = userEvent.setup();
    renderWithAuth(<Integrations />);
    await waitForTabs();
    await user.click(screen.getByText("OAuth Providers"));
    expect(
      await screen.findByText("https://accounts.google.com"),
    ).toBeInTheDocument();
    expect(
      await screen.findByText("https://idp.example.com"),
    ).toBeInTheDocument();
  });

  it("shows webhook count", async () => {
    renderWithAuth(<Integrations />);
    await waitForTabs();
    expect(
      await screen.findByText("2 webhooks configured"),
    ).toBeInTheDocument();
  });

  it("opens add webhook modal", async () => {
    const user = userEvent.setup();
    renderWithAuth(<Integrations />);
    await waitForTabs();
    await user.click(screen.getByText("Add Webhook"));
    const modal = screen.getByRole("dialog");
    expect(within(modal).getByLabelText("Name")).toBeInTheDocument();
    expect(within(modal).getByLabelText("URL")).toBeInTheDocument();
  });

  it("creates a webhook via modal", async () => {
    const user = userEvent.setup();
    mockCreateWebhook.mockResolvedValue({} as any);
    renderWithAuth(<Integrations />);
    await waitForTabs();
    await user.click(screen.getByText("Add Webhook"));
    const modal = screen.getByRole("dialog");
    await user.type(within(modal).getByLabelText("Name"), "New Hook");
    await user.type(
      within(modal).getByLabelText("URL"),
      "https://example.com/hook",
    );
    await user.click(within(modal).getByText("OK"));
    await waitFor(() => {
      expect(mockCreateWebhook).toHaveBeenCalled();
    });
  });

  it("deletes a webhook", async () => {
    const user = userEvent.setup();
    renderWithAuth(<Integrations />);
    await waitForTabs();
    const deleteBtns = screen.getAllByText("Delete");
    await user.click(deleteBtns[0]);
    await screen.findByText("Delete this webhook?");
    await user.click(screen.getByText("OK"));
    await waitFor(() => {
      expect(mockDeleteWebhook).toHaveBeenCalledWith(1);
    });
  });

  it("opens add OAuth provider modal", async () => {
    const user = userEvent.setup();
    renderWithAuth(<Integrations />);
    await waitForTabs();
    await user.click(screen.getByText("OAuth Providers"));
    await screen.findByText("https://accounts.google.com");
    await user.click(screen.getByText("Add Provider"));
    const modal = screen.getByRole("dialog");
    expect(within(modal).getByLabelText("Issuer URL")).toBeInTheDocument();
    expect(within(modal).getByLabelText("Client ID")).toBeInTheDocument();
  });

  it("calls endpoints on mount", async () => {
    renderWithAuth(<Integrations />);
    await waitForTabs();
    expect(mockListWebhooks).toHaveBeenCalled();
    expect(mockListOauthProviders).toHaveBeenCalled();
  });
});
