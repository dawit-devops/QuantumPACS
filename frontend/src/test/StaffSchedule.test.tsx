import React from "react";
import { render, screen, waitFor, fireEvent, within } from "@testing-library/react";
import { renderWithAuth } from "./renderWithApp";
import { describe, it, expect, vi, beforeEach } from "vitest";
import StaffSchedule from "../admin/StaffSchedule";

const mockRequest = vi.fn();

vi.mock("../helpers", () => ({
  request: (...args: any[]) => mockRequest(...args),
}));

vi.mock("../hooks", () => ({
  useDocumentTitle: vi.fn(),
}));

vi.mock("../common/base", () => ({
  __esModule: true,
  default: (Component: React.ComponentType<any>) => (props: any) => <Component {...props} />,
}));

const SCHEDULE_ROWS = [
  {
    id: "sch-1",
    patient_name: "Jane Doe",
    accession_number: "ACC-1",
    modality: "CT",
    scheduled_date: "2026-09-01",
    scheduled_time: "09:00",
    assigned_station_ae: "CT1",
    status: "scheduled",
    assigned_technologist: "Alex Kim",
  },
];

const TIME_OFF_ROWS = [
  {
    id: "to-1",
    staff_id: "s1",
    staff_name: "Terry Chen",
    modality: "CT",
    status: "REQUESTED",
    start_date: "2026-09-01",
    end_date: "2026-09-03",
    reason: "vacation",
  },
  {
    id: "to-2",
    staff_id: "s2",
    staff_name: "Mia Lopez",
    modality: "MR",
    status: "APPROVED",
    start_date: "2026-09-05",
    end_date: "2026-09-06",
    reason: "medical",
  },
];

const GAPS = [
  {
    date: "2026-09-05",
    staff_id: "s2",
    staff_name: "Mia Lopez",
    modality: "MR",
    scheduled_exams: 3,
  },
];

describe("StaffSchedule DM-07 time-off & coverage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.setItem("userId", "1");
    localStorage.setItem("username", "test");
    localStorage.setItem("permissions", JSON.stringify(["SCHEDULE_READ", "SCHEDULE_WRITE"]));
    localStorage.setItem("tenant_id", "t1");
    mockRequest.mockImplementation((url: string, opts?: any) => {
      if (url === "ris/staff-schedule") {
        return Promise.resolve({ data: SCHEDULE_ROWS });
      }
      if (url === "ris/staff-time-off") {
        if (opts?.method === "POST") {
          return Promise.resolve({ data: { ...opts.data, id: "to-3" } });
        }
        return Promise.resolve({ data: TIME_OFF_ROWS });
      }
      if (url === "ris/staff-time-off/coverage-gaps") {
        return Promise.resolve({ data: GAPS, count: 1 });
      }
      if (url.includes("ris/staff-time-off/") && opts?.method === "PATCH") {
        return Promise.resolve({ data: { ...opts.data } });
      }
      return Promise.resolve({ data: [] });
    });
  });

  it("renders the time-off tab with request rows", async () => {
    renderWithAuth(<StaffSchedule />);
    const tab = await screen.findByText("Time Off & Coverage");
    fireEvent.click(tab);
    expect(await screen.findByText("Terry Chen")).toBeInTheDocument();
    expect(screen.getByText("Mia Lopez")).toBeInTheDocument();
  });

  it("shows approved coverage gaps in an alert", async () => {
    renderWithAuth(<StaffSchedule />);
    fireEvent.click(await screen.findByText("Time Off & Coverage"));
    expect(await screen.findByText(/coverage gap/i)).toBeInTheDocument();
    expect(
      await screen.findByText(/Mia Lopez \(MR\) is on approved time-off/i)
    ).toBeInTheDocument();
  });

  it("opens the request form modal and submits", async () => {
    renderWithAuth(<StaffSchedule />);
    fireEvent.click(await screen.findByText("Time Off & Coverage"));
    fireEvent.click(await screen.findByText("Request Time Off"));
    const modal = screen.getByRole("dialog");
    expect(within(modal).getByText("Request Time Off")).toBeInTheDocument();

    fireEvent.change(within(modal).getByLabelText("Staff ID"), {
      target: { value: "s3" },
    });
    fireEvent.change(within(modal).getByLabelText("Staff Name"), {
      target: { value: "Sam Rivera" },
    });
    fireEvent.change(within(modal).getByLabelText("Start Date"), {
      target: { value: "2026-09-10" },
    });
    fireEvent.change(within(modal).getByLabelText("End Date"), {
      target: { value: "2026-09-12" },
    });
    fireEvent.click(within(modal).getByRole("button", { name: "Submit" }));

    await waitFor(() => {
      expect(mockRequest).toHaveBeenCalledWith(
        "ris/staff-time-off",
        expect.objectContaining({
          method: "POST",
          data: expect.objectContaining({
            staff_id: "s3",
            staff_name: "Sam Rivera",
            start_date: "2026-09-10",
            end_date: "2026-09-12",
          }),
        })
      );
    });
  });

  it("approves a time-off request", async () => {
    renderWithAuth(<StaffSchedule />);
    fireEvent.click(await screen.findByText("Time Off & Coverage"));
    await screen.findByText("Terry Chen");

    const approveButtons = screen.getAllByText("Approve");
    fireEvent.click(approveButtons[0]);

    await waitFor(() => {
      expect(mockRequest).toHaveBeenCalledWith(
        "ris/staff-time-off/to-1/status",
        expect.objectContaining({
          method: "PATCH",
          data: { status: "APPROVED" },
        })
      );
    });
  });

  it("rejects an invalid status change gracefully", async () => {
    mockRequest.mockImplementation((url: string, opts?: any) => {
      if (url.includes("ris/staff-time-off/") && opts?.method === "PATCH") {
        return Promise.reject(new Error("Validation failed"));
      }
      if (url === "ris/staff-time-off/coverage-gaps") {
        return Promise.resolve({ data: [], count: 0 });
      }
      if (url === "ris/staff-time-off") {
        return Promise.resolve({ data: TIME_OFF_ROWS });
      }
      return Promise.resolve({ data: [] });
    });
    renderWithAuth(<StaffSchedule />);
    fireEvent.click(await screen.findByText("Time Off & Coverage"));
    await screen.findByText("Terry Chen");
    fireEvent.click(screen.getAllByText("Approve")[0]);
    await waitFor(() => {
      expect(screen.getByText("Validation failed")).toBeInTheDocument();
    });
  });
});
