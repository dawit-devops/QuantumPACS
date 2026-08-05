import React from "react";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router";
import { describe, it, expect, beforeEach, vi } from "vitest";
import { AuthProvider } from "../auth/AuthContext";
import PermissionRoute, {
  VIEWER_ROUTE_PERMISSIONS,
  PATIENT_ROUTE_PERMISSIONS,
  METRICS_ROUTE_PERMISSIONS,
} from "../auth/PermissionRoute";
import { landingRouteFor } from "../navigator";

const { landingRouteForMock } = vi.hoisted(() => ({
  landingRouteForMock: vi.fn(() => "/account"),
}));

vi.mock("../navigator", () => ({
  landingRouteFor: landingRouteForMock,
  navigate: vi.fn(),
  setNavigator: vi.fn(),
}));

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
// sync by importing those constants rather than restating the keys.
function WorkspaceRouteTable() {
  return (
    <Routes>
      <Route path="/login" element={<div data-testid="login-page" />} />
      <Route path="/account" element={<div data-testid="account-page" />} />
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
          <PermissionRoute permission={PATIENT_ROUTE_PERMISSIONS}>
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
    </Routes>
  );
}

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AuthProvider>
        <WorkspaceRouteTable />
      </AuthProvider>
    </MemoryRouter>,
  );
}

describe("PACS workspace route gates", () => {
  beforeEach(() => {
    localStorage.clear();
    landingRouteForMock.mockImplementation(() => "/account");
  });

  it("defines the workspace gates with the spec permission keys", () => {
    expect(VIEWER_ROUTE_PERMISSIONS).toEqual([
      "FILE_READ",
      "STUDY_READ",
      "VIEWER_READ",
    ]);
    expect(PATIENT_ROUTE_PERMISSIONS).toEqual(["PATIENT_READ"]);
    expect(METRICS_ROUTE_PERMISSIONS).toEqual([
      "METRICS_READ",
      "ANALYTICS_READ",
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

  it("blocks a billing-only biller from files, viewer and patients", () => {
    seedUser({
      role: "biller",
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

  it("lets a biller with ANALYTICS_READ open metrics", () => {
    seedUser({
      role: "biller",
      admin: false,
      permissions: ["BILLING_READ", "ANALYTICS_READ"],
    });

    const result = renderAt("/metrics");
    expect(screen.getByTestId("metrics-page")).toBeInTheDocument();
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

  it("lets an admin open every workspace route", () => {
    seedUser({ role: "admin", admin: true, permissions: [] });

    for (const path of ["/", "/files/123", "/patients/123", "/metrics"]) {
      const result = renderAt(path);
      const visible = [
        screen.queryByTestId("files-page"),
        screen.queryByTestId("viewer-page"),
        screen.queryByTestId("patient-page"),
        screen.queryByTestId("metrics-page"),
      ].filter(Boolean);
      expect(visible).toHaveLength(1);
      result.unmount();
    }
  });
});
