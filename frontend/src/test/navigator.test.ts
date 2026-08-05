import { describe, it, expect } from "vitest";
import { landingRouteFor, workspaceFor } from "../navigator";
import type { Workspace, WorkspaceUser } from "../navigator";

const user = (overrides: Partial<WorkspaceUser> = {}): WorkspaceUser => ({
  permissions: [],
  ...overrides,
});

describe("workspaceFor", () => {
  it.each([
    { role: "radiologist", permissions: ["REPORT_READ"], expected: "reading" },
    {
      role: "teleradiologist",
      permissions: ["REPORT_READ"],
      expected: "reading",
    },
    { role: "resident", permissions: ["REPORT_READ"], expected: "reading" },
    {
      role: "technologist",
      permissions: ["EXAM_READ"],
      expected: "acquisition",
    },
    { role: "qa_team", permissions: ["QA_READ"], expected: "qa" },
    { role: "pacs_admin", permissions: ["REPLICA_READ"], expected: "admin" },
    {
      role: "radiology_admin",
      permissions: ["REPLICA_READ"],
      expected: "admin",
    },
    {
      role: "imaging_informatics",
      permissions: ["REPLICA_READ"],
      expected: "admin",
    },
    {
      role: "department_manager",
      permissions: ["ANALYTICS_READ"],
      expected: "analytics",
    },
    {
      role: "physician",
      permissions: ["DICOMWEB_READ"],
      expected: "clinical",
    },
    {
      role: "referring_physician",
      permissions: ["DICOMWEB_READ"],
      expected: "clinical",
    },
    {
      role: "ed_physician",
      permissions: ["DICOMWEB_READ"],
      expected: "clinical",
    },
    { role: "patient", permissions: ["FILE_READ"], expected: "files" },
    { role: "super_admin", permissions: ["USER_READ"], expected: "platform" },
    { role: "tenant_admin", permissions: ["USER_READ"], expected: "platform" },
    { role: "admin", permissions: ["USER_READ"], expected: "platform" },
  ])(
    "maps the $role role to the $expected workspace",
    ({ role, permissions, expected }) => {
      expect(workspaceFor(user({ role, permissions }))).toBe(expected);
    },
  );

  it.each([
    "receptionist",
    "cashier",
    "biller",
    "scheduler",
    "front_desk",
    "nurse",
    "pharmacist",
    "lab_technician",
    "him_specialist",
    "care_coordinator",
    "emr_admin",
    "biomedical_engineer",
    "service_director",
    "hospital_staff",
    "medical_coder",
    "mystery_role",
  ])("defaults the %s role to the files workspace", (role) => {
    expect(workspaceFor(user({ role, permissions: ["FILE_READ"] }))).toBe(
      "files",
    );
  });

  it("lets the admin flag bypass permission gates", () => {
    expect(
      workspaceFor(user({ role: "radiologist", admin: true, permissions: [] })),
    ).toBe("reading");
  });

  it("falls back to the first permitted workspace when the role surface is blocked", () => {
    expect(
      workspaceFor(user({ role: "radiologist", permissions: ["EXAM_READ"] })),
    ).toBe("acquisition");
    expect(
      workspaceFor(
        user({ role: "technologist", permissions: ["DICOMWEB_READ"] }),
      ),
    ).toBe("clinical");
  });

  it("defaults to the files workspace when nothing is permitted", () => {
    expect(workspaceFor(user({ role: "radiologist" }))).toBe("files");
    expect(workspaceFor(user({}))).toBe("files");
  });
});

describe("landingRouteFor", () => {
  it("returns the role's primary landing route when permitted", () => {
    expect(
      landingRouteFor(
        user({ role: "radiologist", permissions: ["REPORT_READ"] }),
      ),
    ).toBe("/reading");
    expect(
      landingRouteFor(
        user({ role: "technologist", permissions: ["EXAM_READ"] }),
      ),
    ).toBe("/exams");
    expect(
      landingRouteFor(user({ role: "qa_team", permissions: ["QA_READ"] })),
    ).toBe("/qa/queue");
    expect(
      landingRouteFor(
        user({ role: "pacs_admin", permissions: ["REPLICA_READ"] }),
      ),
    ).toBe("/replicas");
    expect(
      landingRouteFor(
        user({ role: "physician", permissions: ["DICOMWEB_READ"] }),
      ),
    ).toBe("/dicomweb");
    expect(
      landingRouteFor(
        user({ role: "department_manager", permissions: ["METRICS_READ"] }),
      ),
    ).toBe("/metrics");
    expect(
      landingRouteFor(
        user({ role: "tenant_admin", permissions: ["USER_READ"] }),
      ),
    ).toBe("/users");
    expect(
      landingRouteFor(user({ role: "patient", permissions: ["STUDY_READ"] })),
    ).toBe("/");
  });

  it("lets the admin flag bypass permission gates", () => {
    expect(
      landingRouteFor(
        user({ role: "radiologist", admin: true, permissions: [] }),
      ),
    ).toBe("/reading");
  });

  it("falls back to '/' for a radiologist without REPORT_READ", () => {
    expect(
      landingRouteFor(
        user({ role: "radiologist", permissions: ["STUDY_READ"] }),
      ),
    ).toBe("/");
  });

  it("lands patients on '/'", () => {
    expect(
      landingRouteFor(user({ role: "patient", permissions: ["FILE_READ"] })),
    ).toBe("/");
  });

  it("falls back to the first permitted route in priority order", () => {
    expect(
      landingRouteFor(
        user({ role: "radiologist", permissions: ["USER_READ"] }),
      ),
    ).toBe("/users");
    expect(
      landingRouteFor(
        user({ role: "qa_team", permissions: ["ANALYTICS_READ"] }),
      ),
    ).toBe("/metrics");
  });

  it("lands users without PACS permissions on /account", () => {
    expect(landingRouteFor(user({ role: "radiologist" }))).toBe("/account");
    expect(landingRouteFor(user({ role: "mystery_role" }))).toBe("/account");
  });

  it("keeps workspaceFor consistent with landingRouteFor", () => {
    const cases: Array<[WorkspaceUser, Workspace, string]> = [
      [
        user({ role: "radiologist", permissions: ["REPORT_READ"] }),
        "reading",
        "/reading",
      ],
      [
        user({ role: "technologist", permissions: ["EXAM_READ"] }),
        "acquisition",
        "/exams",
      ],
      [user({ role: "qa_team", permissions: ["QA_READ"] }), "qa", "/qa/queue"],
      [
        user({ role: "pacs_admin", permissions: ["REPLICA_READ"] }),
        "admin",
        "/replicas",
      ],
      [
        user({ role: "physician", permissions: ["DICOMWEB_READ"] }),
        "clinical",
        "/dicomweb",
      ],
      [
        user({ role: "department_manager", permissions: ["ANALYTICS_READ"] }),
        "analytics",
        "/metrics",
      ],
      [
        user({ role: "tenant_admin", permissions: ["USER_READ"] }),
        "platform",
        "/users",
      ],
      [user({ role: "patient", permissions: ["FILE_READ"] }), "files", "/"],
      [user({ role: "patient", permissions: ["STUDY_READ"] }), "files", "/"],
      [user({ role: "radiologist", permissions: [] }), "files", "/account"],
    ];
    cases.forEach(([u, workspace, route]) => {
      expect(workspaceFor(u)).toBe(workspace);
      expect(landingRouteFor(u)).toBe(route);
    });
  });
});
