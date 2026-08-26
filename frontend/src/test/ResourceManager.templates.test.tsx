import React from "react";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";
import ResourceManager from "../schedule/ResourceManager";
import { renderWithAuth } from "./renderWithApp";

const mocks = vi.hoisted(() => ({
  resources: vi.fn(),
  schedules: vi.fn(),
  templates: vi.fn(),
  createTemplate: vi.fn(),
  applyTemplate: vi.fn(),
}));

vi.mock("../api/scheduling", async () => {
  const actual = await import("../api/scheduling");
  return {
    ...actual,
    listRisResources: mocks.resources,
    listRisSchedules: mocks.schedules,
    listScheduleTemplates: mocks.templates,
    createScheduleTemplate: mocks.createTemplate,
    applyScheduleTemplate: mocks.applyTemplate,
    createRisResource: vi.fn(),
    createRisSchedule: vi.fn(),
  };
});

vi.mock("../hooks", () => ({
  useDocumentTitle: vi.fn(),
  useTenantRefetch: () => {},
}));

const RESOURCE = {
  id: "r1",
  name: "CT Room 1",
  resource_type: "MODALITY",
  modality: "CT",
  status: "ACTIVE",
};

const WINDOWS = [
  { id: "s1", resource_id: "r1", day_of_week: 0, start_time: "08:00:00", end_time: "16:00:00" },
];

beforeEach(() => {
  vi.clearAllMocks();
  localStorage.clear();
  localStorage.setItem("token", "t");
  localStorage.setItem("userId", "u2");
  localStorage.setItem("admin", "false");
  localStorage.setItem("role", "care_coordinator");
  localStorage.setItem("permissions", JSON.stringify(["SCHEDULE_READ", "SCHEDULE_WRITE"]));
  mocks.resources.mockResolvedValue([RESOURCE]);
  mocks.schedules.mockResolvedValue(WINDOWS);
  mocks.templates.mockResolvedValue([
    {
      id: "tpl-1",
      name: "Standard weekday",
      slots: [{ day_of_week: 0, start_time: "08:00", end_time: "16:00" }],
    },
  ]);
  mocks.createTemplate.mockResolvedValue({ id: "tpl-2", name: "Mine", slots: [] });
});

async function openScheduleDrawer() {
  const user = userEvent.setup();
  renderWithAuth(<ResourceManager />);
  await screen.findByText("CT Room 1");
  await user.click(await screen.findByRole("button", { name: /manage schedules for ct room 1/i }));
  await screen.findByText(/weekly windows/i);
  return user;
}

describe("ResourceManager schedule templates (S-05)", () => {
  it("saves the resource's current windows as a named template", async () => {
    const user = await openScheduleDrawer();

    await user.click(screen.getByRole("button", { name: /save as template/i }));
    const dlg = await screen.findByTestId("template-save-dialog");
    await user.type(screen.getByLabelText(/template name/i), "My CT week");

    const { fireEvent } = await import("@testing-library/react");
    fireEvent.click(dlg.querySelector(".ant-btn-primary") as HTMLElement);

    await vi.waitFor(() =>
      expect(mocks.createTemplate).toHaveBeenCalledWith({
        name: "My CT week",
        slots: [{ day_of_week: 0, start_time: "08:00:00", end_time: "16:00:00" }],
      })
    );
  });

  it("applies a chosen template to the resource and reloads its windows", async () => {
    const user = await openScheduleDrawer();

    await user.click(screen.getByRole("combobox", { name: /choose template/i }));
    await user.click(await screen.findByTitle("Standard weekday"));
    await user.click(screen.getByRole("button", { name: /^Apply$/i }));

    await vi.waitFor(() => expect(mocks.applyTemplate).toHaveBeenCalledWith("tpl-1", "r1"));
    // Windows reload after apply.
    await vi.waitFor(() => expect(mocks.schedules).toHaveBeenCalledTimes(2));
  });
});
