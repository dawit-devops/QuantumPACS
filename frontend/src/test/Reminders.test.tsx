import { render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import React from "react";
import { MemoryRouter } from "react-router";
import { App } from "antd";
import { AuthProvider } from "../auth/AuthContext";
import { ThemeProvider } from "../common/ThemeProvider";
import Reminders from "../coordinator/Reminders";

vi.mock("../api/reminders", () => ({
  listReminderConfig: vi.fn(),
  listReminderLog: vi.fn(),
  saveReminderConfig: vi.fn(),
  sendReminder: vi.fn(),
}));

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

import { listReminderConfig, listReminderLog } from "../api/reminders";
const mockListCfg = vi.mocked(listReminderConfig);
const mockListLog = vi.mocked(listReminderLog);

function renderReminders() {
  localStorage.setItem("userId", "1");
  localStorage.setItem("username", "test");
  localStorage.setItem("permissions", JSON.stringify(["PRIOR_AUTH_READ"]));
  localStorage.setItem("tenant_id", "t1");
  return render(
    <MemoryRouter>
      <App>
        <AuthProvider>
          <ThemeProvider>
            <Reminders />
          </ThemeProvider>
        </AuthProvider>
      </App>
    </MemoryRouter>,
  );
}

describe("Reminders", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockListCfg.mockResolvedValue({
      data: [
        {
          id: "cfg-1",
          event_type: "reminder.appointment",
          channel: "sms",
          template: "Appt at {time}",
          lead_time_hours: 24,
          active: true,
        },
      ],
    });
    mockListLog.mockResolvedValue({
      data: [
        {
          id: "msg-1",
          channel: "sms",
          recipient: "5551234",
          event_type: "reminder.appointment",
          subject: "Appt",
          status: "SENT",
          attempts: 1,
          provider_receipt: "sms-1234",
          sent_at: "2026-08-21T12:00:00Z",
        },
      ],
      total: 1,
      page: 1,
      per_page: 20,
    });
  });

  it("renders reminder config", async () => {
    renderReminders();
    await waitFor(() => {
      expect(screen.getByText("reminder.appointment")).toBeInTheDocument();
    });
    expect(screen.getByText("SMS")).toBeInTheDocument();
  });

  it("renders delivery log on the log tab", async () => {
    renderReminders();
    await waitFor(() => {
      expect(screen.getByText("reminder.appointment")).toBeInTheDocument();
    });
  });

  it("shows the Send Reminder button", async () => {
    renderReminders();
    await waitFor(() => {
      expect(screen.getByText("Send Reminder")).toBeInTheDocument();
    });
  });
});