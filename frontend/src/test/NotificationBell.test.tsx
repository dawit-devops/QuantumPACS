import React from "react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  render,
  screen,
  waitFor,
  fireEvent,
  within,
} from "@testing-library/react";
import { App } from "antd";
import NotificationBell from "../notifications/NotificationBell";
import * as notifApi from "../api/notifications";
import * as ws from "../ws";
import { MemoryRouter } from "react-router";

vi.mock("../api/notifications", () => ({
  getUnreadCount: vi.fn(),
  listNotifications: vi.fn(),
  markRead: vi.fn(),
  markAllRead: vi.fn(),
  deleteNotification: vi.fn(),
  clearNotifications: vi.fn(),
}));

vi.mock("../ws", () => ({
  addEventListener: vi.fn(),
  removeEventListener: vi.fn(),
}));

const { mockNavigate } = vi.hoisted(() => ({
  mockNavigate: vi.fn(),
}));

vi.mock("react-router", async (importOriginal) => {
  const actual = await importOriginal<typeof import("react-router")>();
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

const renderBell = () =>
  render(
    <App>
      <MemoryRouter>
        <NotificationBell />
      </MemoryRouter>
    </App>,
  );

async function openDrawer() {
  await waitFor(() => {
    expect(notifApi.getUnreadCount).toHaveBeenCalled();
  });
  fireEvent.click(screen.getByLabelText("bell"));
}

describe("NotificationBell", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(notifApi.getUnreadCount).mockResolvedValue(0);
    vi.mocked(notifApi.listNotifications).mockResolvedValue({
      data: [],
      total: 0,
    });
  });

  afterEach(() => {});

  it("shows the unread badge count", async () => {
    vi.mocked(notifApi.getUnreadCount).mockResolvedValue(3);
    renderBell();
    await waitFor(() => {
      expect(screen.getByText("3")).toBeInTheDocument();
    });
  });

  it("lists notifications when opened", async () => {
    vi.mocked(notifApi.listNotifications).mockResolvedValue({
      data: [
        {
          id: "1",
          event_type: "study.arrived",
          title: "Study arrived",
          body: "P001",
          read: false,
        },
      ],
      total: 1,
    });
    renderBell();
    await openDrawer();
    expect(await screen.findByText("Study arrived")).toBeInTheDocument();
    expect(screen.getByText("P001")).toBeInTheDocument();
  });

  it("shows the empty state when there are no notifications", async () => {
    renderBell();
    await openDrawer();
    expect(await screen.findByText("No notifications")).toBeInTheDocument();
  });

  it("marks a single notification as read and decrements the badge", async () => {
    vi.mocked(notifApi.getUnreadCount).mockResolvedValue(1);
    vi.mocked(notifApi.listNotifications).mockResolvedValue({
      data: [
        { id: "1", event_type: "system.alert", title: "Hello", read: false },
      ],
      total: 1,
    });
    vi.mocked(notifApi.markRead).mockResolvedValue(undefined);
    renderBell();
    await openDrawer();
    const row = await screen.findByText("Hello");
    fireEvent.click(row);
    await waitFor(() => {
      expect(notifApi.markRead).toHaveBeenCalledWith("1");
    });
  });

  it("surfaces an error when markRead fails", async () => {
    vi.mocked(notifApi.getUnreadCount).mockResolvedValue(1);
    vi.mocked(notifApi.listNotifications).mockResolvedValue({
      data: [
        { id: "1", event_type: "system.alert", title: "Hello", read: false },
      ],
      total: 1,
    });
    vi.mocked(notifApi.markRead).mockRejectedValue(new Error("network down"));
    renderBell();
    await openDrawer();
    fireEvent.click(await screen.findByText("Hello"));
    await waitFor(() => {
      expect(
        screen.getByText(/Failed to mark read: network down/),
      ).toBeInTheDocument();
    });
  });

  it("surfaces an error when markAllRead fails", async () => {
    vi.mocked(notifApi.getUnreadCount).mockResolvedValue(1);
    vi.mocked(notifApi.listNotifications).mockResolvedValue({
      data: [
        { id: "1", event_type: "system.alert", title: "Hello", read: false },
      ],
      total: 1,
    });
    vi.mocked(notifApi.markAllRead).mockRejectedValue(new Error("boom"));
    renderBell();
    await openDrawer();
    fireEvent.click(screen.getByText("Read all"));
    await waitFor(() => {
      expect(
        screen.getByText(/Failed to mark all read: boom/),
      ).toBeInTheDocument();
    });
  });

  it("surfaces an error when dismiss fails", async () => {
    vi.mocked(notifApi.listNotifications).mockResolvedValue({
      data: [
        { id: "1", event_type: "system.alert", title: "Hello", read: true },
      ],
      total: 1,
    });
    vi.mocked(notifApi.deleteNotification).mockRejectedValue(new Error("gone"));
    renderBell();
    await openDrawer();
    // The per-row dismiss renders DeleteOutlined (role="img" aria-label
    // "delete") inside the list item's actions; the header "Dismiss all"
    // button uses the same icon, so scope the lookup to the row.
    const row = await screen.findByText("Hello");
    const rowContainer = row.closest(".ant-list-item") as HTMLElement;
    const dismissIcon = within(rowContainer).getByRole("img", {
      name: "delete",
    });
    fireEvent.click(dismissIcon.parentElement!);
    await waitFor(() => {
      expect(screen.getByText(/Failed to dismiss: gone/)).toBeInTheDocument();
    });
  });

  it("surfaces an error when dismissAll fails", async () => {
    vi.mocked(notifApi.listNotifications).mockResolvedValue({
      data: [
        { id: "1", event_type: "system.alert", title: "Hello", read: true },
      ],
      total: 1,
    });
    vi.mocked(notifApi.clearNotifications).mockRejectedValue(new Error("nope"));
    renderBell();
    await openDrawer();
    // Dismiss all is disabled until the list fetch sets total > 0.
    await waitFor(() => {
      expect(screen.getByText(/Notifications \(1\)/)).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText("Dismiss all"));
    await waitFor(() => {
      expect(
        screen.getByText(/Failed to dismiss all: nope/),
      ).toBeInTheDocument();
    });
  });

  it("clears all notifications and shows success on dismissAll", async () => {
    vi.mocked(notifApi.getUnreadCount).mockResolvedValue(2);
    vi.mocked(notifApi.listNotifications).mockResolvedValue({
      data: [
        { id: "1", event_type: "system.alert", title: "Hello", read: true },
      ],
      total: 1,
    });
    vi.mocked(notifApi.clearNotifications).mockResolvedValue(undefined);
    renderBell();
    await openDrawer();
    await waitFor(() => {
      expect(screen.getByText(/Notifications \(1\)/)).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText("Dismiss all"));
    await waitFor(() => {
      expect(
        screen.getByText("All notifications dismissed"),
      ).toBeInTheDocument();
    });
    await waitFor(() => {
      expect(screen.getByText("No notifications")).toBeInTheDocument();
    });
  });

  it("refreshes the unread count on a WS notifications event", async () => {
    const listeners: Array<(data: any) => void> = [];
    vi.mocked(ws.addEventListener).mockImplementation((fn: any) => {
      listeners.push(fn);
    });
    vi.mocked(notifApi.getUnreadCount).mockResolvedValue(0);
    renderBell();
    await waitFor(() => {
      expect(notifApi.getUnreadCount).toHaveBeenCalledTimes(1);
    });
    vi.mocked(notifApi.getUnreadCount).mockResolvedValue(5);
    listeners.forEach((fn) => fn({ type: "notifications" }));
    await waitFor(() => {
      expect(notifApi.getUnreadCount).toHaveBeenCalledTimes(2);
    });
  });

  it("unsubscribes the WS listener on unmount", async () => {
    const listeners: Array<(data: any) => void> = [];
    vi.mocked(ws.addEventListener).mockImplementation((fn: any) => {
      listeners.push(fn);
    });
    const { unmount } = renderBell();
    await waitFor(() => {
      expect(listeners).toHaveLength(1);
    });
    unmount();
    expect(ws.removeEventListener).toHaveBeenCalledWith(listeners[0]);
  });

  it("navigates when the notification link is a same-origin path (M4)", async () => {
    vi.mocked(notifApi.listNotifications).mockResolvedValue({
      data: [
        {
          id: "1",
          event_type: "study.arrived",
          title: "Open study",
          link: "/files?study=1",
          read: true,
        },
      ],
      total: 1,
    });
    renderBell();
    await openDrawer();
    fireEvent.click(await screen.findByText("Open study"));
    expect(mockNavigate).toHaveBeenCalledWith("/files?study=1");
  });

  it("refuses external and javascript: links (M4)", async () => {
    vi.mocked(notifApi.listNotifications).mockResolvedValue({
      data: [
        {
          id: "1",
          event_type: "system.alert",
          title: "Evil one",
          link: "https://evil.example/phish",
          read: true,
        },
        {
          id: "2",
          event_type: "system.alert",
          title: "Evil two",
          link: "javascript:alert(1)",
          read: true,
        },
        {
          id: "3",
          event_type: "system.alert",
          title: "Safe",
          link: "/files",
          read: true,
        },
      ],
      total: 3,
    });
    renderBell();
    await openDrawer();
    fireEvent.click(await screen.findByText("Evil one"));
    fireEvent.click(screen.getByText("Evil two"));
    expect(mockNavigate).not.toHaveBeenCalled();
    fireEvent.click(screen.getByText("Safe"));
    expect(mockNavigate).toHaveBeenCalledWith("/files");
  });
});
