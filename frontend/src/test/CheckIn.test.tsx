import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

vi.mock("../api/checkin", () => ({
  getCheckIn: vi.fn(),
  confirmCheckIn: vi.fn(),
}));

import CheckIn from "../kiosk/CheckIn";
import { getCheckIn, confirmCheckIn } from "../api/checkin";

const mockedGet = vi.mocked(getCheckIn);
const mockedConfirm = vi.mocked(confirmCheckIn);

const pushToken = () =>
  window.history.pushState({}, "", "/checkin?token=tok-1");

describe("CheckIn kiosk", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    pushToken();
  });

  it("shows the visit summary from the token", async () => {
    mockedGet.mockResolvedValue({
      patient_name: "John Doe",
      start_time: "2026-08-25T09:30:00Z",
      status: "SCHEDULED",
    });
    render(<CheckIn />);
    await waitFor(() =>
      expect(screen.getByTestId("checkin-summary")).toBeTruthy(),
    );
    expect(screen.getByText(/John Doe/)).toBeTruthy();
    expect(screen.getByTestId("checkin-status").textContent).toContain(
      "SCHEDULED",
    );
  });

  it("confirms arrival via POST and shows success", async () => {
    mockedGet.mockResolvedValue({
      patient_name: "John Doe",
      start_time: "2026-08-25T09:30:00Z",
      status: "SCHEDULED",
    });
    mockedConfirm.mockResolvedValue({ id: "appt-1", status: "ARRIVED" });
    const user = userEvent.setup();
    render(<CheckIn />);
    await waitFor(() => screen.getByRole("button"));
    await user.click(screen.getByRole("button"));
    await waitFor(() =>
      expect(screen.getByText(/checked in/i)).toBeTruthy(),
    );
    expect(mockedConfirm).toHaveBeenCalledWith("tok-1");
  });

  it("renders an error screen for invalid tokens", async () => {
    mockedGet.mockRejectedValue(
      Object.assign(new Error("Token invalid or expired"), { status: 403 }),
    );
    render(<CheckIn />);
    await waitFor(() =>
      expect(screen.getByText(/Cannot check in/i)).toBeTruthy(),
    );
  });
});
