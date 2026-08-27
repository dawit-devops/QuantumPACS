import React from "react";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router";
import { describe, it, expect, beforeEach, vi } from "vitest";
import { AuthProvider } from "../auth/AuthContext";
import PermissionRoute, {
  VIEWER_ROUTE_PERMISSIONS,
  PATIENT_ROUTE_PERMISSIONS,
  METRICS_ROUTE_PERMISSIONS,
  ADMIN_DASHBOARD_PERMISSIONS,
} from "../auth/PermissionRoute";
import { landingRouteFor, ADMIN_SCOPED_ROLES, CLINICAL_SCOPED_ROLES } from "../navigator";

const { landingRouteForMock } = vi.hoisted(() => ({
  landingRouteForMock: vi.fn(() => "/account"),
}));

// Keep the real role-scope constants (ADMIN_SCOPED_ROLES) but stub the
// landing resolver, which the tests control to assert redirect targets.
vi.mock("../navigator", async () => {
  const actual = await vi.importActual<typeof import("../navigator")>("../navigator");
  return {
    ...actual,
    landingRouteFor: landingRouteForMock,
    navigate: vi.fn(),
    setNavigator: vi.fn(),
  };
});

function seedUser({
  role,
  admin,
  permissions,
}: {
  role: string;
  admin: boolean;
  permissions: string[];
}) {
  localStorage.setItem("userId", "u1");
  localStorage.setItem("username", "test-user");
  localStorage.setItem("admin", String(admin));
  localStorage.setItem("role", role);
  localStorage.setItem("permissions", JSON.stringify(permissions));
}

// Mirrors the route table in src/index.tsx: the four PACS workspace routes
// wrap their pages in PermissionRoute using the shared gate sets. Kept in
// sync by importing those constants rather than restating the keys. The
// patient page mirrors the ClinicalRoute wrapper (index.tsx) like the reading
// surface: closed to admin-scoped role slugs even when the permission passes.
function WorkspaceRouteTable() {
  return (
    <Routes>
      <Route path="/login" element={<div data-testid="login-page" />} />
      <Route path="/account" element={<div data-testid="account-page" />} />
      {/* Mirrors the index.tsx /admin route: permission union PLUS adminOnly —
          the dashboard is the operational home of admin-scoped roles only. */}
      <Route
        path="/admin"
        element={
          <PermissionRoute permission={ADMIN_DASHBOARD_PERMISSIONS} adminOnly>
            <div data-testid="dashboard-page" />
          </PermissionRoute>
        }
      />
      <Route
        path="/"
        element={
          <PermissionRoute permission={VIEWER_ROUTE_PERMISSIONS}>
            <div data-testid="files-page" />
          </PermissionRoute>
        }
      />
      <Route
        path="/files/:id"
        element={
          <PermissionRoute permission={VIEWER_ROUTE_PERMISSIONS}>
            <div data-testid="viewer-page" />
          </PermissionRoute>
        }
      />
      <Route
        path="/patients/:id"
        element={
          <PermissionRoute
            permission={PATIENT_ROUTE_PERMISSIONS}
            excludedRoles={[...ADMIN_SCOPED_ROLES]}
          >
            <div data-testid="patient-page" />
          </PermissionRoute>
        }
      />
      <Route
        path="/metrics"
        element={
          <PermissionRoute permission={METRICS_ROUTE_PERMISSIONS}>
            <div data-testid="metrics-page" />
          </PermissionRoute>
        }
      />
      {/* Mirrors the index.tsx /logs route: LOG_READ or its canonical alias
          AUDIT_READ (spec §6) — Matrix A admin roles carry only AUDIT_READ. */}
      <Route
        path="/logs"
        element={
          <PermissionRoute permission={["LOG_READ", "AUDIT_READ"]}>
            <div data-testid="logs-page" />
          </PermissionRoute>
        }
      />
      {/* Mirrors the ClinicalRoute wrapper in src/index.tsx: clinical surfaces
          are closed to admin-scoped role slugs even when the permission passes. */}
      <Route
        path="/reading"
        element={
          <PermissionRoute permission="REPORT_READ" excludedRoles={[...ADMIN_SCOPED_ROLES]}>
            <div data-testid="reading-page" />
          </PermissionRoute>
        }
      />
      {/* Mirrors the PermissionRoute wrapper in src/index.tsx: the DICOMweb
          console is reachable for clinical roles holding legacy DICOMWEB_READ
          (user decision 2026-08-27 — no longer admin-scoped); the backend
          re-checks DICOMWEB_WRITE on the STOW endpoint itself. */}
      <Route
        path="/dicomweb"
        element={
          <PermissionRoute permission="DICOMWEB_READ">
            <div data-testid="dicomweb-page" />
          </PermissionRoute>
        }
      />
    </Routes>
  );
}

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AuthProvider>
        <WorkspaceRouteTable />
      </AuthProvider>
    </MemoryRouter>
  );
}

describe("PACS workspace route gates", () => {
  beforeEach(() => {
    localStorage.clear();
    landingRouteForMock.mockImplementation(() => "/account");
  });

  it("defines the workspace gates with the spec permission keys", () => {
    expect(VIEWER_ROUTE_PERMISSIONS).toEqual(["FILE_READ", "STUDY_READ", "VIEWER_READ"]);
    expect(PATIENT_ROUTE_PERMISSIONS).toEqual(["PATIENT_READ"]);
    expect(METRICS_ROUTE_PERMISSIONS).toEqual(["METRICS_READ", "ANALYTICS_READ"]);
    expect(ADMIN_DASHBOARD_PERMISSIONS).toEqual([
      "USER_READ",
      "LOG_READ",
      "AUDIT_READ",
      "INTERFACE_MONITOR",
      "METRICS_READ",
      "REPLICA_READ",
      "DICOMWEB_READ",
    ]);
  });

  it("lets a radiologist open the study browser and viewer but not patients or metrics", () => {
    seedUser({
      role: "radiologist",
      admin: false,
      permissions: ["REPORT_READ", "VIEWER_READ", "STUDY_READ"],
    });
    landingRouteForMock.mockImplementation(() => "/account");

    const first = renderAt("/");
    expect(screen.getByTestId("files-page")).toBeInTheDocument();
    first.unmount();

    const second = renderAt("/files/123");
    expect(screen.getByTestId("viewer-page")).toBeInTheDocument();
    second.unmount();

    const third = renderAt("/patients/123");
    expect(screen.getByTestId("account-page")).toBeInTheDocument();
    expect(screen.queryByTestId("patient-page")).toBeNull();
    third.unmount();

    const fourth = renderAt("/metrics");
    expect(screen.getByTestId("account-page")).toBeInTheDocument();
    expect(screen.queryByTestId("metrics-page")).toBeNull();
    fourth.unmount();
  });

  it("blocks a patient-role user from the whole PACS workspace", () => {
    seedUser({
      role: "patient",
      admin: false,
      permissions: ["PORTAL_READ"],
    });

    const first = renderAt("/");
    expect(screen.getByTestId("account-page")).toBeInTheDocument();
    expect(screen.queryByTestId("files-page")).toBeNull();
    first.unmount();

    const second = renderAt("/files/123");
    expect(screen.getByTestId("account-page")).toBeInTheDocument();
    expect(screen.queryByTestId("viewer-page")).toBeNull();
    second.unmount();

    const third = renderAt("/patients/123");
    expect(screen.getByTestId("account-page")).toBeInTheDocument();
    expect(screen.queryByTestId("patient-page")).toBeNull();
    third.unmount();
  });

  it("blocks a billing-only billing clerk from files, viewer and patients", () => {
    seedUser({
      role: "billing_clerk",
      admin: false,
      permissions: ["BILLING_READ", "METERING_READ"],
    });

    const first = renderAt("/");
    expect(screen.getByTestId("account-page")).toBeInTheDocument();
    expect(screen.queryByTestId("files-page")).toBeNull();
    first.unmount();

    const second = renderAt("/files/123");
    expect(screen.getByTestId("account-page")).toBeInTheDocument();
    expect(screen.queryByTestId("viewer-page")).toBeNull();
    second.unmount();

    const third = renderAt("/patients/123");
    expect(screen.getByTestId("account-page")).toBeInTheDocument();
    expect(screen.queryByTestId("patient-page")).toBeNull();
    third.unmount();

    // METERING_READ is a distinct code: it must NOT unlock /metrics.
    const fourth = renderAt("/metrics");
    expect(screen.getByTestId("account-page")).toBeInTheDocument();
    expect(screen.queryByTestId("metrics-page")).toBeNull();
    fourth.unmount();
  });

  it("lets a billing clerk with ANALYTICS_READ open metrics", () => {
    seedUser({
      role: "billing_clerk",
      admin: false,
      permissions: ["BILLING_READ", "ANALYTICS_READ"],
    });

    const result = renderAt("/metrics");
    expect(screen.getByTestId("metrics-page")).toBeInTheDocument();
    result.unmount();
  });

  it("lets an admin-scoped role with AUDIT_READ open the audit logs", () => {
    seedUser({
      role: "emr_admin",
      admin: false,
      permissions: ["AUDIT_READ", "INTERFACE_MONITOR"],
    });

    const result = renderAt("/logs");
    expect(screen.getByTestId("logs-page")).toBeInTheDocument();
    result.unmount();
  });

  it("blocks a user without LOG_READ or AUDIT_READ from the logs", () => {
    seedUser({
      role: "technologist",
      admin: false,
      permissions: ["WORKLIST_READ", "EXAM_READ"],
    });
    landingRouteForMock.mockImplementation(() => "/account");

    const result = renderAt("/logs");
    expect(screen.getByTestId("account-page")).toBeInTheDocument();
    expect(screen.queryByTestId("logs-page")).toBeNull();
    result.unmount();
  });

  it("lets a FILE_READ-only legacy user open files routes but not patients", () => {
    seedUser({
      role: "technologist",
      admin: false,
      permissions: ["FILE_READ", "WORKLIST_READ"],
    });

    const first = renderAt("/");
    expect(screen.getByTestId("files-page")).toBeInTheDocument();
    first.unmount();

    const second = renderAt("/files/123");
    expect(screen.getByTestId("viewer-page")).toBeInTheDocument();
    second.unmount();

    const third = renderAt("/patients/123");
    expect(screen.getByTestId("account-page")).toBeInTheDocument();
    expect(screen.queryByTestId("patient-page")).toBeNull();
    third.unmount();
  });

  it("lets an admin open the file browser and viewer but not patients", () => {
    seedUser({ role: "admin", admin: true, permissions: [] });

    for (const path of ["/", "/files/123", "/metrics"]) {
      const result = renderAt(path);
      const visible = [
        screen.queryByTestId("files-page"),
        screen.queryByTestId("viewer-page"),
        screen.queryByTestId("metrics-page"),
      ].filter(Boolean);
      expect(visible).toHaveLength(1);
      result.unmount();
    }
  });

  it("closes the patient page to an admin-scoped role even with the permission", () => {
    seedUser({
      role: "tenant_admin",
      admin: true,
      permissions: ["PATIENT_READ"],
    });
    landingRouteForMock.mockImplementation(() => "/account");

    const result = renderAt("/patients/123");
    expect(screen.getByTestId("account-page")).toBeInTheDocument();
    expect(screen.queryByTestId("patient-page")).toBeNull();
    result.unmount();
  });

  it("closes clinical routes to an excluded admin role even with the permission", () => {
    seedUser({
      role: "tenant_admin",
      admin: true,
      permissions: ["REPORT_READ"],
    });
    landingRouteForMock.mockImplementation(() => "/account");

    const result = renderAt("/reading");
    expect(screen.getByTestId("account-page")).toBeInTheDocument();
    expect(screen.queryByTestId("reading-page")).toBeNull();
    result.unmount();
  });

  it("lets a clinical role open an excludedRoles route when permitted", () => {
    seedUser({
      role: "radiologist",
      admin: false,
      permissions: ["REPORT_READ"],
    });

    const result = renderAt("/reading");
    expect(screen.getByTestId("reading-page")).toBeInTheDocument();
    result.unmount();
  });

  it("lets a clinical role with DICOMWEB_READ open the DICOMweb console", () => {
    // Legacy grants give radiologist and physician DICOMWEB_READ; the console
    // is now reachable for them (user decision 2026-08-27 — the sidebar and
    // route gate use a plain PermissionRoute, no adminOnly/excludedRoles).
    seedUser({
      role: "radiologist",
      admin: false,
      permissions: ["DICOMWEB_READ"],
    });
    landingRouteForMock.mockImplementation(() => "/account");

    const result = renderAt("/dicomweb");
    expect(screen.getByTestId("dicomweb-page")).toBeInTheDocument();
    result.unmount();
  });

  it("lets an admin-scoped role open the DICOMweb console with DICOMWEB_READ", () => {
    seedUser({
      role: "pacs_admin",
      admin: false,
      permissions: ["DICOMWEB_READ"],
    });

    const result = renderAt("/dicomweb");
    expect(screen.getByTestId("dicomweb-page")).toBeInTheDocument();
    result.unmount();
  });

  it("lets an admin-scoped role open the dashboard", () => {
    seedUser({ role: "pacs_admin", admin: false, permissions: ["USER_READ"] });

    const result = renderAt("/admin");
    expect(screen.getByTestId("dashboard-page")).toBeInTheDocument();
    result.unmount();
  });

  it("closes the dashboard to a clinical role even with a dashboard permission", () => {
    seedUser({
      role: "radiologist",
      admin: false,
      permissions: ["USER_READ", "LOG_READ"],
    });
    landingRouteForMock.mockImplementation(() => "/account");

    const result = renderAt("/admin");
    expect(screen.getByTestId("account-page")).toBeInTheDocument();
    expect(screen.queryByTestId("dashboard-page")).toBeNull();
    result.unmount();
  });

  it("closes the dashboard to an admin-scoped role without any dashboard permission", () => {
    seedUser({ role: "tenant_admin", admin: false, permissions: [] });
    landingRouteForMock.mockImplementation(() => "/account");

    const result = renderAt("/admin");
    expect(screen.getByTestId("account-page")).toBeInTheDocument();
    expect(screen.queryByTestId("dashboard-page")).toBeNull();
    result.unmount();
  });

  it("lets a dept_manager open the dashboard with a dashboard permission", () => {
    // S12-34: dept_manager is admin-scoped (ADMIN_SCOPED_ROLES) with read-only
    // operational analytics — METRICS_READ satisfies the dashboard gate.
    seedUser({ role: "dept_manager", admin: false, permissions: ["METRICS_READ"] });

    const result = renderAt("/admin");
    expect(screen.getByTestId("dashboard-page")).toBeInTheDocument();
    result.unmount();
  });

  it("closes clinical routes to a dept_manager even with the permission", () => {
    // dept_manager carries REPORT_READ (RIS dashboard gate) but is
    // admin-scoped — the clinical reading surface must stay closed.
    seedUser({ role: "dept_manager", admin: false, permissions: ["REPORT_READ"] });
    landingRouteForMock.mockImplementation(() => "/account");

    const result = renderAt("/reading");
    expect(screen.getByTestId("account-page")).toBeInTheDocument();
    expect(screen.queryByTestId("reading-page")).toBeNull();
    result.unmount();
  });
});
