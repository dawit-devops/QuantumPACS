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
    { role: "qa_officer", permissions: ["QA_READ"], expected: "qa" },
    {
      role: "pacs_admin",
      permissions: ["REPLICA_READ"],
      expected: "dashboard",
    },
    {
      role: "emr_admin",
      permissions: ["REPLICA_READ"],
      expected: "dashboard",
    },
    {
      role: "physician",
      permissions: ["REPORT_READ"],
      expected: "clinical",
    },
    {
      role: "referring_physician",
      permissions: ["REPORT_READ"],
      expected: "clinical",
    },
    {
      role: "care_coordinator",
      permissions: ["REPORT_READ"],
      // Care-coordinator review (P1-2): the coordination workspace requires
      // ORDER_READ — a coordinator without it falls through to the generic
      // reading surface.
      expected: "reading",
    },
    {
      role: "care_coordinator",
      permissions: ["ORDER_READ"],
      expected: "coordination",
    },
    { role: "patient", permissions: ["PORTAL_READ"], expected: "portal" },
    {
      role: "receptionist",
      permissions: ["REGISTRATION_READ"],
      expected: "frontdesk",
    },
    {
      role: "super_admin",
      permissions: ["USER_READ"],
      expected: "dashboard",
    },
    {
      role: "tenant_admin",
      permissions: ["USER_READ"],
      expected: "dashboard",
    },
  ])("maps the $role role to the $expected workspace", ({ role, permissions, expected }) => {
    expect(workspaceFor(user({ role, permissions }))).toBe(expected);
  });

  it.each(["cashier", "pharmacist", "medical_coder", "nurse", "scheduler", "mystery_role"])(
    "defaults the %s role to the files workspace",
    (role) => {
      expect(workspaceFor(user({ role, permissions: ["FILE_READ"] }))).toBe("files");
    }
  );

  it("lets the admin flag bypass permission gates", () => {
    expect(workspaceFor(user({ role: "radiologist", admin: true, permissions: [] }))).toBe(
      "reading"
    );
  });

  it("falls back to the first permitted workspace when the role surface is blocked", () => {
    expect(workspaceFor(user({ role: "radiologist", permissions: ["EXAM_READ"] }))).toBe(
      "acquisition"
    );
    // The DICOMweb console is admin-scoped: a clinical role holding the
    // legacy DICOMWEB_READ grant never resolves to the admin workspace.
    expect(workspaceFor(user({ role: "technologist", permissions: ["DICOMWEB_READ"] }))).toBe(
      "files"
    );
  });

  it("defaults to the files workspace when nothing is permitted", () => {
    expect(workspaceFor(user({ role: "radiologist" }))).toBe("files");
    expect(workspaceFor(user({}))).toBe("files");
  });

  it("never resolves admin-scoped roles to clinical workspaces", () => {
    // pacs_admin holds REPORT_READ (a clinical grant) but no REPLICA_READ:
    // the fallback must skip reading and resolve outside the clinical set.
    expect(workspaceFor(user({ role: "pacs_admin", permissions: ["REPORT_READ"] }))).not.toBe(
      "reading"
    );
    expect(
      workspaceFor(user({ role: "tenant_admin", permissions: ["QA_READ", "EXAM_READ"] }))
    ).not.toBe("qa");
    expect(workspaceFor(user({ role: "tenant_admin", permissions: ["EXAM_READ"] }))).not.toBe(
      "acquisition"
    );
    // The admin flag bypasses permission gates but not the role scope.
    expect(workspaceFor(user({ role: "tenant_admin", admin: true, permissions: [] }))).toBe(
      "dashboard"
    );
  });

  it("keeps clinical workspaces for non-admin roles", () => {
    expect(workspaceFor(user({ role: "radiologist", permissions: ["REPORT_READ"] }))).toBe(
      "reading"
    );
    expect(workspaceFor(user({ role: "qa_officer", permissions: ["QA_READ"] }))).toBe("qa");
  });
});

describe("landingRouteFor", () => {
  it("returns the role's primary landing route when permitted", () => {
    expect(landingRouteFor(user({ role: "radiologist", permissions: ["REPORT_READ"] }))).toBe(
      "/reading"
    );
    expect(landingRouteFor(user({ role: "technologist", permissions: ["EXAM_READ"] }))).toBe(
      "/exams"
    );
    expect(landingRouteFor(user({ role: "qa_officer", permissions: ["QA_READ"] }))).toBe(
      "/qa/queue"
    );
    expect(landingRouteFor(user({ role: "pacs_admin", permissions: ["REPLICA_READ"] }))).toBe(
      "/admin"
    );
    expect(landingRouteFor(user({ role: "physician", permissions: ["REPORT_READ"] }))).toBe(
      "/reading"
    );
    expect(landingRouteFor(user({ role: "emr_admin", permissions: ["ANALYTICS_READ"] }))).toBe(
      "/metrics"
    );
    expect(landingRouteFor(user({ role: "tenant_admin", permissions: ["USER_READ"] }))).toBe(
      "/admin"
    );
    expect(landingRouteFor(user({ role: "patient", permissions: ["STUDY_READ"] }))).toBe("/");
  });

  it("lets the admin flag bypass permission gates", () => {
    expect(landingRouteFor(user({ role: "radiologist", admin: true, permissions: [] }))).toBe(
      "/reading"
    );
  });

  it("falls back to '/' for a radiologist without REPORT_READ", () => {
    expect(landingRouteFor(user({ role: "radiologist", permissions: ["STUDY_READ"] }))).toBe("/");
  });

  it("falls back to the first permitted route in priority order", () => {
    expect(landingRouteFor(user({ role: "radiologist", permissions: ["USER_READ"] }))).toBe(
      "/users"
    );
    expect(landingRouteFor(user({ role: "qa_officer", permissions: ["ANALYTICS_READ"] }))).toBe(
      "/metrics"
    );
  });

  it("lands users without PACS permissions on /account", () => {
    expect(landingRouteFor(user({ role: "radiologist" }))).toBe("/account");
    expect(landingRouteFor(user({ role: "mystery_role" }))).toBe("/account");
  });

  it("lands admin-scoped roles on the dashboard, never clinical ones", () => {
    // pacs_admin holds REPORT_READ (a clinical grant) and USER_READ: the
    // dashboard step wins over the clinical fallback and the /users primary.
    expect(
      landingRouteFor(user({ role: "pacs_admin", permissions: ["REPORT_READ", "USER_READ"] }))
    ).toBe("/admin");
    // The admin flag bypasses gates but the role scope still excludes
    // clinical surfaces; the dashboard primary wins.
    expect(landingRouteFor(user({ role: "tenant_admin", admin: true, permissions: [] }))).toBe(
      "/admin"
    );
    // Without any dashboard permission the role surface and fallback still
    // skip clinical workspaces and degrade to the auth-only terminal.
    expect(landingRouteFor(user({ role: "tenant_admin", permissions: [] }))).toBe("/account");
    expect(landingRouteFor(user({ role: "tenant_admin", permissions: ["REPORT_READ"] }))).toBe(
      "/account"
    );
  });

  it("keeps clinical landings for non-admin roles", () => {
    expect(landingRouteFor(user({ role: "radiologist", permissions: ["REPORT_READ"] }))).toBe(
      "/reading"
    );
    expect(landingRouteFor(user({ role: "qa_officer", permissions: ["QA_READ"] }))).toBe(
      "/qa/queue"
    );
  });

  it("lands the billing persona on the billing queue (§2.6)", () => {
    expect(landingRouteFor(user({ role: "cashier", permissions: ["BILLING_READ"] }))).toBe(
      "/billing/queue"
    );
  });

  it("lands the clinical workspace roles on the reading worklist", () => {
    // physician / referring_physician hold REPORT_READ (Matrix A/B): the
    // clinical landing is /reading, never the DICOMweb console even when the
    // legacy DICOMWEB_READ grant passes.
    for (const role of ["physician", "referring_physician"]) {
      expect(landingRouteFor(user({ role, permissions: ["REPORT_READ", "DICOMWEB_READ"] }))).toBe(
        "/reading"
      );
      expect(workspaceFor(user({ role, permissions: ["REPORT_READ"] }))).toBe("clinical");
    }
  });

  it("lands the billing persona on the billing queue; EMR-only roles still terminate on /account", () => {
    // §2.6: BILLING_READ now maps to the billing-queue workspace, so the
    // cashier no longer falls through to /account.
    expect(landingRouteFor(user({ role: "cashier", permissions: ["BILLING_READ"] }))).toBe(
      "/billing/queue"
    );
    // Facility EMR roles with grants that still have no surface remain
    // terminal on /account.
    expect(landingRouteFor(user({ role: "care_assistant", permissions: ["RESULTS_READ"] }))).toBe(
      "/account"
    );
  });

  it("closes the DICOMweb console landing to clinical roles with legacy grants", () => {
    // A clinical role whose only grant is DICOMWEB_READ degrades to /account
    // instead of landing on the admin console (physician with DICOMWEB_READ
    // previously landed on /dicomweb).
    expect(landingRouteFor(user({ role: "physician", permissions: ["DICOMWEB_READ"] }))).toBe(
      "/account"
    );
    expect(workspaceFor(user({ role: "technologist", permissions: ["DICOMWEB_READ"] }))).toBe(
      "files"
    );
  });

  it("keeps workspaceFor consistent with landingRouteFor", () => {
    const cases: Array<[WorkspaceUser, Workspace, string]> = [
      [user({ role: "radiologist", permissions: ["REPORT_READ"] }), "reading", "/reading"],
      [user({ role: "technologist", permissions: ["EXAM_READ"] }), "acquisition", "/exams"],
      [user({ role: "qa_officer", permissions: ["QA_READ"] }), "qa", "/qa/queue"],
      [user({ role: "pacs_admin", permissions: ["REPLICA_READ"] }), "dashboard", "/admin"],
      [
        user({ role: "physician", permissions: ["DICOMWEB_READ"] }),
        "files",
        // The clinical workspace maps to /reading, but without REPORT_READ
        // the DICOMweb grant alone degrades to the auth-only terminal.
        "/account",
      ],
      [user({ role: "emr_admin", permissions: ["ANALYTICS_READ"] }), "analytics", "/metrics"],
      // AUDIT_READ (canonical alias of LOG_READ, spec §6) unlocks the logs
      // landing step for roles that carry only AUDIT_READ.
      [user({ role: "pacs_admin", permissions: ["AUDIT_READ"] }), "dashboard", "/admin"],
      [user({ role: "cashier", permissions: ["AUDIT_READ"] }), "admin", "/logs"],
      [user({ role: "tenant_admin", permissions: ["USER_READ"] }), "dashboard", "/admin"],
      [user({ role: "patient", permissions: ["FILE_READ"] }), "files", "/"],
      [user({ role: "patient", permissions: ["STUDY_READ"] }), "files", "/"],
      [user({ role: "patient", permissions: ["PORTAL_READ"] }), "portal", "/portal"],
      [
        user({ role: "receptionist", permissions: ["REGISTRATION_READ"] }),
        "frontdesk",
        "/frontdesk/registration",
      ],
      [
        // QUEUE_READ unlocks the privacy queue step for roles that hold it
        // without REGISTRATION_READ (navigator.ts landing steps).
        user({ role: "receptionist", permissions: ["QUEUE_READ"] }),
        "frontdesk",
        "/frontdesk/queue",
      ],
      [
        // CHART_READ alone has no landing step: the patient degrades to the
        // auth-only terminal inside the files workspace (no PORTAL_READ).
        user({ role: "patient", permissions: ["CHART_READ"] }),
        "files",
        "/account",
      ],
      [user({ role: "radiologist", permissions: [] }), "files", "/account"],
    ];
    cases.forEach(([u, workspace, route]) => {
      expect(workspaceFor(u)).toBe(workspace);
      expect(landingRouteFor(u)).toBe(route);
    });
  });
});

describe("§2.11 nursing landing (G3)", () => {
  it("keeps care_coordinator pinned to /orders when it holds ORDER_READ", () => {
    const u = user({
      role: "care_coordinator",
      permissions: ["ORDER_READ", "NURSING_READ", "NURSING_WRITE"],
    });
    expect(landingRouteFor(u)).toBe("/orders");
    expect(workspaceFor(u)).toBe("coordination");
  });

  it("falls back to the exam list for a NURSING_READ-only coordinator", () => {
    // Without ORDER_READ the coordination step fails; the acquisition step
    // now accepts NURSING_READ so a nursing-scoped coordinator still has a
    // real landing instead of degrading to /account.
    expect(landingRouteFor(user({ role: "care_coordinator", permissions: ["NURSING_READ"] }))).toBe(
      "/exams"
    );
    expect(workspaceFor(user({ role: "care_coordinator", permissions: ["NURSING_READ"] }))).toBe(
      "acquisition"
    );
  });

  it("does not open acquisition to holders of neither grant", () => {
    expect(
      landingRouteFor(user({ role: "care_coordinator", permissions: ["PATIENT_READ"] }))
    ).not.toBe("/exams");
  });
});
