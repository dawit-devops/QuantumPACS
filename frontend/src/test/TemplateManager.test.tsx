import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { renderWithAuth } from "./renderWithApp";
import TemplateManager from "../admin/TemplateManager";

const mockListTemplates = vi.hoisted(() => vi.fn());
const mockListVersions = vi.hoisted(() => vi.fn());
const mockPublish = vi.hoisted(() => vi.fn());
const mockRollback = vi.hoisted(() => vi.fn());

vi.mock("../api/reports-ris", async (importOriginal) => {
  const actual = await importOriginal<
    typeof import("../api/reports-ris")
  >();
  return {
    ...actual,
    listReportTemplates: mockListTemplates,
    listTemplateVersions: mockListVersions,
    publishTemplateVersion: mockPublish,
    rollbackTemplateVersion: mockRollback,
  };
});

const tpl = {
  id: "tpl-1",
  name: "CT Chest Routine",
  modality: "CT",
  findings_template: "Lungs clear.",
  impression_template: "No acute findings.",
};

describe("TemplateManager", () => {
  beforeEach(() => {
    localStorage.setItem("token", "t");
    localStorage.setItem("userId", "u1");
    localStorage.setItem("admin", "true");
    localStorage.setItem(
      "permissions",
      JSON.stringify(["REPORT_READ", "REPORT_WRITE"]),
    );
    mockListTemplates.mockResolvedValue([tpl]);
    mockListVersions.mockResolvedValue([
      { version_number: 2, findings_template: "v2", published_by: "7" },
      { version_number: 1, findings_template: "v1", published_by: "7" },
    ]);
    mockPublish.mockResolvedValue({ id: "tpl-1", version_number: 3 });
    mockRollback.mockResolvedValue({ id: "tpl-1", version_number: 2 });
  });

  it("lists templates by modality", async () => {
    renderWithAuth(<TemplateManager />);
    await waitFor(() => {
      expect(screen.getByText(/CT Chest Routine/)).toBeInTheDocument();
    });
  });

  it("publishes a new version from the editor", async () => {
    const user = userEvent.setup();
    renderWithAuth(<TemplateManager />);
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /edit/i })).toBeInTheDocument();
    });
    await user.click(screen.getByRole("button", { name: /edit/i }));
    const boxes = await screen.findAllByRole("textbox");
    await user.type(boxes[0], " updated");
    await user.click(screen.getByRole("button", { name: /^publish$/i }));
    await waitFor(() => {
      expect(mockPublish).toHaveBeenCalled();
    });
  });

  it("rolls back to a prior version (R2-02-09)", async () => {
    const user = userEvent.setup();
    renderWithAuth(<TemplateManager />);
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /history/i })).toBeInTheDocument();
    });
    await user.click(screen.getByRole("button", { name: /history/i }));
    await waitFor(() => {
      expect(screen.getByText("v1")).toBeInTheDocument();
    });
    const rollbackButtons = screen.getAllByRole("button", { name: /rollback/i });
    await user.click(rollbackButtons[rollbackButtons.length - 1]);
    await waitFor(() => {
      expect(mockRollback).toHaveBeenCalledWith("tpl-1", 1);
    });
  });
  it("passes WCAG 2.1 AA automated scan (F3)", async () => {
    renderWithAuth(<TemplateManager />)
    await waitFor(() => {
      expect(screen.getByText("Report Templates")).toBeTruthy();
    });
    const { scanA11y, seriousViolations } = await import("./axe");
    const results = await scanA11y(document.body);
    expect(seriousViolations(results)).toEqual([]);
  });

});
