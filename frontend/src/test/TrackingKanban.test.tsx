import React from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";
import TrackingKanban, {
  ROLE_KANBAN_COLUMNS,
  DEFAULT_KANBAN_COLUMNS,
  canTransition,
} from "../worklist/TrackingKanban";

vi.mock("../auth/AuthContext", () => ({
  useAuth: () => ({
    user: { role: localStorage.getItem("role") || "" },
    hasPermission: (p: string) =>
      (JSON.parse(localStorage.getItem("permissions") || "[]") as string[]).includes(p),
  }),
}));

const ENTRY = (over: Partial<Record<string, unknown>> = {}) =>
  ({
    id: "t1",
    patient_name: "Jane Doe",
    patient_id: "P1",
    accession_number: "ACC1",
    modality: "CT",
    status: "arrived",
    station_ae_title: "CT1",
    scheduled_time: "10:30",
    requested_procedure_priority: "ROUTINE",
    ...over,
  }) as any;

beforeEach(() => {
  localStorage.clear();
  localStorage.setItem("role", "technologist");
  localStorage.setItem("permissions", JSON.stringify(["WORKLIST_WRITE"]));
});

describe("TrackingKanban (§6)", () => {
  it("maps roles onto the real exam-status lifecycle", () => {
    // Technologists never see 'performed'; coordinators do.
    expect(ROLE_KANBAN_COLUMNS.technologist).not.toContain("performed");
    expect(ROLE_KANBAN_COLUMNS.care_coordinator).toContain("performed");
    for (const cols of Object.values(ROLE_KANBAN_COLUMNS)) {
      for (const c of cols) expect(DEFAULT_KANBAN_COLUMNS).toContain(c);
    }
  });

  it("gates transitions: no self-moves and cancellation stays explicit", () => {
    expect(canTransition("arrived", "in_progress")).toBe(true);
    expect(canTransition("arrived", "scheduled")).toBe(false);
    expect(canTransition("completed", "completed")).toBe(false);
    expect(canTransition("scheduled", "cancelled")).toBe(false);
  });

  it("renders role columns and places entries in their status column", () => {
    render(
      <TrackingKanban
        entries={[
          ENTRY({ id: "a", status: "arrived" }),
          ENTRY({ id: "b", status: "in_progress", patient_name: "John Roe" }),
        ]}
        onStatusChange={vi.fn()}
        onOpenDetail={vi.fn()}
      />
    );
    expect(screen.getByTestId("kanban-col-scheduled")).toBeInTheDocument();
    expect(screen.getByTestId("kanban-col-in_progress")).toBeInTheDocument();
    // Technologist columns exclude performed.
    expect(screen.queryByTestId("kanban-col-performed")).not.toBeInTheDocument();
    expect(screen.getByText("Jane Doe")).toBeInTheDocument();
  });

  it("opens the exam detail from a card click", async () => {
    const onOpenDetail = vi.fn();
    const user = userEvent.setup();
    render(
      <TrackingKanban entries={[ENTRY()]} onStatusChange={vi.fn()} onOpenDetail={onOpenDetail} />
    );
    await user.click(screen.getByTestId("kanban-card-t1"));
    expect(onOpenDetail).toHaveBeenCalledTimes(1);
  });
});
