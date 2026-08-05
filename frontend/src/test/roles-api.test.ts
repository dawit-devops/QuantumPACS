import { describe, it, expect, vi, beforeEach } from "vitest";
import { request } from "../api/client";
import {
  listRoles,
  listPermissions,
  createRole,
  updateRole,
  deleteRole,
  listRoleUsers,
  roleDisplayName,
  permissionLabel,
  type Role,
} from "../api/roles";

vi.mock("../api/client", () => ({
  request: vi.fn(),
}));

const mockRequest = vi.mocked(request);

const ROLE: Role = {
  id: 7,
  name: "Night Tech",
  slug: "night_tech",
  description: "Overnight technologist",
  permissions: ["STUDY_READ", "WORKLIST_WRITE"],
  built_in: false,
  user_count: 3,
};

describe("roles api client", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("listRoles fetches GET /roles", async () => {
    mockRequest.mockResolvedValue({ data: [ROLE] });
    const result = await listRoles();
    expect(mockRequest).toHaveBeenCalledWith("roles");
    expect(result).toEqual([ROLE]);
  });

  it("listPermissions fetches GET /permissions", async () => {
    mockRequest.mockResolvedValue({ data: { Imaging: ["STUDY_READ"] } });
    const result = await listPermissions();
    expect(mockRequest).toHaveBeenCalledWith("permissions");
    expect(result).toEqual({ Imaging: ["STUDY_READ"] });
  });

  it("createRole POSTs to /roles and leaves the method to the client default", async () => {
    mockRequest.mockResolvedValue({});
    const input = { name: "Night Tech", slug: "night_tech", permissions: [] };
    await createRole(input);
    expect(mockRequest).toHaveBeenCalledWith("roles", { data: input });
    const options = mockRequest.mock.calls[0][1];
    expect(options?.method).toBeUndefined();
  });

  it("updateRole sends PUT /roles/:id (regression: missing method caused 405)", async () => {
    mockRequest.mockResolvedValue({});
    const input = { description: "Updated", permissions: [] };
    await updateRole(7, input);
    expect(mockRequest).toHaveBeenCalledWith("roles/7", {
      data: input,
      method: "PUT",
    });
  });

  it("deleteRole sends DELETE /roles/:id", async () => {
    mockRequest.mockResolvedValue({});
    await deleteRole(7);
    expect(mockRequest).toHaveBeenCalledWith("roles/7", {
      data: undefined,
      method: "DELETE",
    });
  });

  it("listRoleUsers fetches GET /roles/:id/users", async () => {
    mockRequest.mockResolvedValue({ data: [{ id: 1, username: "tech1" }] });
    const result = await listRoleUsers(7);
    expect(mockRequest).toHaveBeenCalledWith("roles/7/users");
    expect(result).toEqual([{ id: 1, username: "tech1" }]);
  });

  it("roleDisplayName falls back to canonical names and unknown slugs", () => {
    expect(roleDisplayName("super_admin")).toBe("System Admin");
    expect(roleDisplayName("admin")).toBe("Administrator");
    expect(roleDisplayName("unknown_slug", "Fallback")).toBe("Fallback");
  });

  it("permissionLabel maps known codes and passes unknown codes through", () => {
    expect(permissionLabel("STUDY_READ")).toBe("Access studies");
    expect(permissionLabel("NOT_A_CODE")).toBe("NOT_A_CODE");
  });
});
