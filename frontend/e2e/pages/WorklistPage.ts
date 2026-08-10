import { Page, expect } from "@playwright/test";
import { openWorklist } from "../helpers";

/**
 * Page object for the MWL Worklist (/worklist). The Worklist menu entry lives
 * in the Acquisition group (d4abc25 workspace restructure) — Reading's
 * "Reading Worklist" shares the substring, so navigation uses exact names via
 * openWorklist.
 */
export class WorklistPage {
  constructor(private readonly page: Page) {}

  async openViaAdminSidebar() {
    await openWorklist(this.page);
    await expect(this.page).toHaveURL(/\/worklist/, { timeout: 10000 });
  }

  get createEntryButton() {
    return this.page.getByRole("button", { name: "Create worklist entry" });
  }
}
