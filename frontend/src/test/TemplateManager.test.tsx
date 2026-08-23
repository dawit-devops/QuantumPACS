import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, waitFor, fireEvent } from "@testing-library/react";
import React from "react";

import { renderWithAuth } from "./renderWithApp";
import TemplateManager from "../admin/TemplateManager";

// antd's Drawer + Table defer their body render to async layout (motion /
// ResizeObserver) that never completes under jsdom, so the versions table
// never appears and the test hangs on waitFor. Stub both to render
// synchronously (the same per-file vi.mock pattern QAReviewForm.test.tsx
// uses for `message`). App.useApp() is stubbed too: TemplateManager toasts
// via the App context, and the real App-provided message spawns a React
// root + auto-dismiss timer that outlives jsdom and hangs the test.
vi.mock("antd", async (importOriginal) => {
  const actual = await importOriginal<typeof import("antd")>();
  const mockMessage = {
    success: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
    warning: vi.fn(),
    loading: vi.fn(),
  };
  const Drawer = ({ children, ..._props }: any) => (
    <div data-testid="versions-drawer">{children}</div>
  );
  // Minimal Table: render the first column's dataIndex text per row so the
  // test can find "v1" and the Rollback action buttons synchronously.
  const Table = ({ dataSource, columns }: any) => (
    <table data-testid="versions-table">
      <tbody>
        {(dataSource || []).map((row: any, i: number) => (
          <tr key={i}>
            {columns.map((col: any, j: number) => (
              <td key={j}>
                {col.render
                  ? col.render(row[col.dataIndex], row)
                  : String(row[col.dataIndex] ?? "")}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
  return {
    ...actual,
    Drawer,
    Table,
    App: {
      ...actual.App,
      useApp: () => ({
        message: mockMessage,
        notification: { success: vi.fn(), error: vi.fn(), info: vi.fn() },
        modal: { confirm: vi.fn() },
      }),
    },
  };
});

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
    renderWithAuth(<TemplateManager />);
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /edit/i })).toBeInTheDocument();
    });
    // fireEvent (not userEvent): the antd Modal motion transition never
    // completes under jsdom, so userEvent's pointer/visibility waits hang
    // forever. fireEvent.click opens the modal and fireEvent.change edits
    // the textarea without waiting on the transition.
    fireEvent.click(screen.getByRole("button", { name: /edit/i }));
    // Query by placeholder (antd textarea renders the placeholder role
    // immediately, before the modal motion animation completes) — avoids
    // the perma-pending waitFor inside findAllByRole("textbox").
    const findingsBox = screen.getByPlaceholderText(
      "Findings template",
    ) as HTMLTextAreaElement;
    fireEvent.change(findingsBox, { target: { value: `${findingsBox.value} updated` } });
    fireEvent.click(screen.getByRole("button", { name: /^publish$/i }));
    await waitFor(() => {
      expect(mockPublish).toHaveBeenCalled();
    });
  });

  it("rolls back to a prior version (R2-02-09)", async () => {
    renderWithAuth(<TemplateManager />);
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /history/i })).toBeInTheDocument();
    });
    fireEvent.click(screen.getByRole("button", { name: /history/i }));
    await waitFor(() => {
      expect(screen.getByText("v1")).toBeInTheDocument();
    });
    const rollbackButtons = screen.getAllByRole("button", { name: /rollback/i });
    fireEvent.click(rollbackButtons[rollbackButtons.length - 1]);
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
