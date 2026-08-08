import { Page, expect } from "@playwright/test";
import { menuName } from "../helpers";

/**
 * Page object for the MWL Worklist (/worklist). The sidebar carries two
 * "Worklist" menu entries (Acquisition + Admin), so every navigation here
 * explicitly scopes to the admin submenu.
 */
export class WorklistPage {
  constructor(private readonly page: Page) {}

  async openViaAdminSidebar() {
    await this.page.getByRole("menuitem", { name: menuName("Admin") }).click();
    await this.page
      .getByRole("menuitem", { name: menuName("Worklist") })
      .filter({ visible: true })
      .click();
    await expect(this.page).toHaveURL(/\/worklist/, { timeout: 10000 });
  }

  get createEntryButton() {
    return this.page.getByRole("button", { name: "Create worklist entry" });
  }
}
