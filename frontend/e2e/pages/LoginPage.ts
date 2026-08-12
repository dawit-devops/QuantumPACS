import { Page, expect } from "@playwright/test";
import { clearAndGo, waitForShell, adminCredentials } from "../helpers";

export class LoginPage {
  constructor(private readonly page: Page) {}

  async open() {
    await clearAndGo(this.page);
  }

  async fillCredentials(username: string, password: string) {
    await this.page.getByPlaceholder("Username").fill(username);
    await this.page.getByPlaceholder("Password").fill(password);
  }

  async submit() {
    await this.page.getByRole("button", { name: /sign in/i }).click();
  }

  async login(username: string, password: string) {
    await this.fillCredentials(username, password);
    await this.submit();
  }

  /** Full admin flow: open login, sign in, wait for the authenticated shell.
   * Credentials come from adminCredentials() — CI exports E2E_ADMIN_PASS from
   * SUPERADMIN_PASS (the value the backend seeds admin with) so specs share
   * one constant; pa55w0rd is only the local-dev fallback. */
  async loginAsAdmin() {
    await this.open();
    await this.login(adminCredentials().username, adminCredentials().password);
    await waitForShell(this.page);
  }

  async expectVisible() {
    await expect(this.page.getByText("Sign in to your account")).toBeVisible({
      timeout: 15000,
    });
  }
}
