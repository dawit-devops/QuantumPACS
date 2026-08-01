import { test, expect, Page, APIRequestContext } from '@playwright/test';
import { BASE, loginAs } from './helpers';

// Users seeded by backend/management/seed_rbac.py (dev + CI).
// Permissions come from BUILT_IN_ROLES in backend/api/permissions.py.
const SEED_PASSWORD = process.env.SEED_RBAC_PASSWORD || 'pa55w0rd';
const API_BASE = process.env.E2E_API_URL || 'http://localhost:8080';

const SUPER_ADMIN = { username: 'admin', password: 'pa55w0rd' };
const ROLES = {
  admin: { username: 'role_admin', permissions: 'admin' },
  technologist: { username: 'role_technologist', permissions: 'technologist' },
  radiologist: { username: 'role_radiologist', permissions: 'radiologist' },
  physician: { username: 'role_physician', permissions: 'physician' },
  cashier: { username: 'role_cashier', permissions: 'cashier' },
  receptionist: { username: 'role_receptionist', permissions: 'receptionist' },
} as const;

async function loginAsRole(page: Page, role: keyof typeof ROLES) {
  const { username } = ROLES[role];
  await loginAs(page, username, SEED_PASSWORD);
}

async function apiToken(request: APIRequestContext, username: string, password: string): Promise<string> {
  const resp = await request.post(`${API_BASE}/api/login`, {
    data: { username, password },
  });
  expect(resp.status()).toBe(200);
  const body = await resp.json();
  return body.token as string;
}

test.describe('RBAC: sidebar visibility', () => {
  test('super admin sees Admin submenu incl. Tenants', async ({ page }) => {
    await loginAs(page, SUPER_ADMIN.username, SUPER_ADMIN.password);
    await expect(page.getByText('Admin').first()).toBeVisible({ timeout: 10000 });
    await page.getByText('Admin').first().click();
    await expect(page.getByText('Tenants').first()).toBeVisible({ timeout: 5000 });
  });

  // The Admin submenu shows for any user with an admin-family permission
  // (USER_READ, REPLICA_READ, TENANT_READ, ROLE_READ, LOG_READ,
  // SERVICE_KEY_READ, WORKLIST_READ, HL7_READ); its items are gated per item.
  for (const role of ['radiologist', 'physician', 'cashier'] as const) {
    test(`role ${role}: Admin submenu hidden without admin-family permission`, async ({ page }) => {
      await loginAsRole(page, role);
      await expect(page.getByText('Admin').first()).toHaveCount(0, { timeout: 10000 });
    });
  }

  test('role admin: Admin submenu shown but Tenants hidden', async ({ page }) => {
    await loginAsRole(page, 'admin');
    await page.getByText('Admin').first().click();
    await expect(page.getByText('Users').first()).toBeVisible({ timeout: 5000 });
    await expect(page.getByText('Tenants').first()).toHaveCount(0);
  });

  test('role technologist: Admin submenu shown via WORKLIST_READ, Users item hidden', async ({ page }) => {
    await loginAsRole(page, 'technologist');
    await page.getByText('Admin').first().click();
    await expect(page.getByText('Worklist').first()).toBeVisible({ timeout: 5000 });
    await expect(page.getByText('Users').first()).toHaveCount(0);
  });

  test('role receptionist: Admin submenu shown via WORKLIST_READ', async ({ page }) => {
    await loginAsRole(page, 'receptionist');
    await page.getByText('Admin').first().click();
    await expect(page.getByText('Worklist').first()).toBeVisible({ timeout: 5000 });
  });
});

test.describe('RBAC: role-based page routes', () => {
  test('unauthenticated access to /users redirects to /login', async ({ page }) => {
    await page.goto(`${BASE}/users`, { waitUntil: 'networkidle' });
    await expect(page).toHaveURL(/\/login/, { timeout: 15000 });
  });

  test('role without USER_READ can open /users page but API denies', async ({ page }) => {
    await loginAsRole(page, 'technologist');
    await page.goto(`${BASE}/users`, { waitUntil: 'domcontentloaded' });
    await expect(page).toHaveURL(/\/users/, { timeout: 10000 });
    const resp = await page.request.get(`${API_BASE}/api/users`, {
      headers: { Authorization: `Bearer ${await apiToken(page.request, ROLES.technologist.username, SEED_PASSWORD)}` },
    });
    expect(resp.status()).toBe(403);
  });

  test('admin opens /users page and API allows', async ({ page }) => {
    await loginAsRole(page, 'admin');
    await page.goto(`${BASE}/users`, { waitUntil: 'domcontentloaded' });
    await expect(page).toHaveURL(/\/users/, { timeout: 10000 });
    const resp = await page.request.get(`${API_BASE}/api/users`, {
      headers: { Authorization: `Bearer ${await apiToken(page.request, ROLES.admin.username, SEED_PASSWORD)}` },
    });
    expect(resp.status()).toBe(200);
  });

  test('files page loads for radiologist (FILE_READ)', async ({ page }) => {
    await loginAsRole(page, 'radiologist');
    await expect(page.getByText('Search Studies').first()).toBeVisible({ timeout: 10000 });
  });

  test('files page renders for cashier without FILE_READ (no crash)', async ({ page }) => {
    await loginAsRole(page, 'cashier');
    await expect(page.getByText('Search Studies').first()).toBeVisible({ timeout: 10000 });
  });
});

// Expected statuses per endpoint, keyed by BUILT_IN_ROLES permissions:
//   FILE_READ: all but cashier | USER_READ: admin/super | LOG_READ: admin/super
//   REPLICA_READ: admin/super | TENANT_READ: super only | WORKLIST_READ: admin/techno/recept
test.describe('RBAC: API permission matrix', () => {
  const cases: Array<[keyof typeof ROLES | 'super_admin', string, number, string]> = [
    ['super_admin', '/api/files', 200, 'FILE_READ'],
    ['admin', '/api/files', 200, 'FILE_READ'],
    ['technologist', '/api/files', 200, 'FILE_READ'],
    ['radiologist', '/api/files', 200, 'FILE_READ'],
    ['physician', '/api/files', 200, 'FILE_READ'],
    ['cashier', '/api/files', 403, 'no FILE_READ'],
    ['receptionist', '/api/files', 200, 'FILE_READ'],
    ['super_admin', '/api/users', 200, 'USER_READ'],
    ['admin', '/api/users', 200, 'USER_READ'],
    ['technologist', '/api/users', 403, 'no USER_READ'],
    ['radiologist', '/api/users', 403, 'no USER_READ'],
    ['cashier', '/api/users', 403, 'no USER_READ'],
    ['receptionist', '/api/users', 403, 'no USER_READ'],
    ['super_admin', '/api/logs', 200, 'LOG_READ'],
    ['admin', '/api/logs', 200, 'LOG_READ'],
    ['technologist', '/api/logs', 403, 'no LOG_READ'],
    ['super_admin', '/api/replicas', 200, 'REPLICA_READ'],
    ['admin', '/api/replicas', 200, 'REPLICA_READ'],
    ['technologist', '/api/replicas', 403, 'no REPLICA_READ'],
    ['super_admin', '/api/tenants', 200, 'TENANT_READ'],
    ['admin', '/api/tenants', 403, 'no TENANT_READ'],
    ['super_admin', '/api/worklist', 200, 'WORKLIST_READ'],
    ['admin', '/api/worklist', 200, 'WORKLIST_READ'],
    ['technologist', '/api/worklist', 200, 'WORKLIST_READ'],
    ['radiologist', '/api/worklist', 403, 'no WORKLIST_READ'],
    ['physician', '/api/worklist', 403, 'no WORKLIST_READ'],
    ['cashier', '/api/worklist', 403, 'no WORKLIST_READ'],
    ['receptionist', '/api/worklist', 200, 'WORKLIST_READ'],
  ];

  for (const [role, path, expected, note] of cases) {
    test(`GET ${path} → ${expected} as ${role} (${note})`, async ({ page }) => {
      const username = role === 'super_admin' ? SUPER_ADMIN.username : ROLES[role].username;
      const token = await apiToken(page.request, username, SEED_PASSWORD);
      const resp = await page.request.get(`${API_BASE}${path}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      expect(resp.status()).toBe(expected);
    });
  }
});
