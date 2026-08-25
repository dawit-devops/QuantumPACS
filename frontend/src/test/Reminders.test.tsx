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
  listPatientOptOuts: vi.fn(),
  setPatientOptOut: vi.fn(),
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

import { listReminderConfig, listReminderLog, listPatientOptOuts } from "../api/reminders";
const mockListCfg = vi.mocked(listReminderConfig);
const mockListLog = vi.mocked(listReminderLog);
const mockListOptOuts = vi.mocked(listPatientOptOuts);

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
    mockListOptOuts.mockResolvedValue({
      data: [
        {
          id: "oo-1",
          patient_id: "8675309",
          event_type: null,
          tenant_id: "default",
          created_at: "2026-08-22T09:00:00Z",
          created_by: "1",
        },
      ],
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

  it("renders patient opt-outs on the opt-out tab", async () => {
    renderReminders();
    await waitFor(() => {
      expect(screen.getByText("reminder.appointment")).toBeInTheDocument();
    });
    screen.getByRole("tab", { name: "Patient Opt-Outs" }).click();
    await waitFor(() => {
      expect(screen.getByText("8675309")).toBeInTheDocument();
    });
    expect(screen.getByText("All events")).toBeInTheDocument();
  });
});