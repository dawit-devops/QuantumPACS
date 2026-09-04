import React from "react";
import { render, screen } from "@testing-library/react";
import { renderWithAuth } from "./renderWithApp";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { AuthProvider } from "../auth/AuthContext";
import { ThemeProvider } from "../common/ThemeProvider";
import Sidebar from "../common/Sidebar";

vi.mock("../hooks", () => ({
  useDocumentTitle: vi.fn(),
  useFetch: () => ({ exec: vi.fn() }),
}));

const { requestMock } = vi.hoisted(() => ({
  requestMock: vi.fn().mockResolvedValue({}),
}));

const { mockLogout } = vi.hoisted(() => ({
  mockLogout: vi.fn().mockResolvedValue(undefined),
}));

vi.mock("../api/auth", () => ({
  logout: mockLogout,
}));

vi.mock("../helpers", () => ({
  isAdmin: () => true,
  request: requestMock,
  clearTokens: () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
  },
  setTokens: () => {},
  startRefreshTimer: () => {},
  stopRefreshTimer: () => {},
}));

function setSession(opts: { role?: string; admin?: boolean; permissions?: string[] }) {
  localStorage.setItem("token", "t");
  localStorage.setItem("userId", "u1");
  localStorage.setItem("admin", String(opts.admin ?? false));
  localStorage.setItem("role", opts.role ?? "user");
  localStorage.setItem("permissions", JSON.stringify(opts.permissions ?? []));
}

describe("Sidebar", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("renders Files nav item", () => {
    setSession({
      role: "referring_physician",
      permissions: ["FILE_READ"],
    });
    renderWithAuth(<Sidebar />);
    expect(screen.getByText("Files")).toBeInTheDocument();
  });

  it("hides the Files item from a referring_physician with only STUDY_READ/VIEWER_READ", () => {
    // referring_physician walk F2: the role holds STUDY_READ/VIEWER_READ which
    // pass the Files route gate, but the backend /api/files* endpoints require
    // FILE_READ → the page would 403 on every data load. Gate the nav item on
    // FILE_READ so the dead item is hidden (route stays deep-linkable).
    setSession({
      role: "referring_physician",
      permissions: ["STUDY_READ", "VIEWER_READ", "REPORT_READ"],
    });
    renderWithAuth(<Sidebar />);
    expect(screen.queryByText("Files")).not.toBeInTheDocument();
    expect(screen.getByText("Account")).toBeInTheDocument();
  });

  it("hides the Acquisition section from a referring_physician with WORKLIST_READ/SCHEDULE_READ", () => {
    // referring_physician walk (sidebar refinement): the Acquisition section is
    // the technologist/scheduler's operational surface. The referring physician
    // holds WORKLIST_READ/SCHEDULE_READ but does not operate the acquisition
    // workflow — hide the section while keeping Reading + Coordination.
    setSession({
      role: "referring_physician",
      permissions: ["REPORT_READ", "WORKLIST_READ", "SCHEDULE_READ", "ORDER_READ", "PATIENT_READ"],
    });
    renderWithAuth(<Sidebar />);
    expect(screen.getByText("Reading")).toBeInTheDocument();
    expect(screen.queryByText("Acquisition")).not.toBeInTheDocument();
    expect(screen.getByText("Coordination")).toBeInTheDocument();
  });

  it("renders Account nav item", () => {
    localStorage.setItem("token", "t");
    localStorage.setItem("userId", "u1");
    renderWithAuth(<Sidebar />);
    expect(screen.getByText("Account")).toBeInTheDocument();
  });

  it("renders Logout nav item", () => {
    localStorage.setItem("token", "t");
    localStorage.setItem("userId", "u1");
    renderWithAuth(<Sidebar />);
    expect(screen.getByText("Logout")).toBeInTheDocument();
  });

  it("shows Admin submenu and items for user with admin-level permission", async () => {
    const user = userEvent.setup();
    localStorage.setItem("token", "t");
    localStorage.setItem("userId", "u1");
    localStorage.setItem("admin", "false");
    localStorage.setItem("role", "tenant_admin");
    localStorage.setItem("permissions", JSON.stringify(["TENANT_READ", "USER_READ"]));
    renderWithAuth(<Sidebar />);
    expect(screen.getByText("Admin")).toBeInTheDocument();
    await user.click(screen.getByText("Admin"));
    expect(screen.getByText("Dashboard")).toBeInTheDocument();
    expect(screen.getByText("Tenants")).toBeInTheDocument();
    expect(screen.getByText("Users")).toBeInTheDocument();
    expect(screen.queryByText("Replicas")).not.toBeInTheDocument();
  });

  it("hides Admin submenu for user without any admin permission", () => {
    localStorage.setItem("token", "t");
    localStorage.setItem("userId", "u1");
    localStorage.setItem("admin", "false");
    localStorage.setItem("role", "cashier");
    localStorage.setItem("permissions", JSON.stringify(["PATIENT_READ", "PATIENT_WRITE"]));
    renderWithAuth(<Sidebar />);
    expect(screen.queryByText("Admin")).not.toBeInTheDocument();
  });

  it("shows Admin submenu for admin user", () => {
    localStorage.setItem("token", "t");
    localStorage.setItem("userId", "u1");
    localStorage.setItem("admin", "true");
    renderWithAuth(<Sidebar />);
    expect(screen.getByText("Admin")).toBeInTheDocument();
  });

  it("renders QuantumLogo", () => {
    localStorage.setItem("token", "t");
    localStorage.setItem("userId", "u1");
    renderWithAuth(<Sidebar />);
    const svg = document.querySelector("svg");
    expect(svg?.textContent).toContain("Quantum");
  });

  it("logout calls the logout endpoint and clears session via signOut", async () => {
    const user = userEvent.setup();
    localStorage.setItem("token", "t");
    localStorage.setItem("userId", "u1");
    localStorage.setItem("access_token", "a");
    localStorage.setItem("refresh_token", "r");
    sessionStorage.setItem("tempKey", "share-temp");
    renderWithAuth(<Sidebar />);

    await user.click(screen.getByText("Logout"));

    expect(mockLogout).toHaveBeenCalled();
    expect(localStorage.getItem("userId")).toBeNull();
    expect(localStorage.getItem("access_token")).toBeNull();
    expect(localStorage.getItem("refresh_token")).toBeNull();
    expect(sessionStorage.getItem("tempKey")).toBeNull();
  });

  it("renders Reading section items for a radiologist and hides Acquisition/QA/Admin", async () => {
    const user = userEvent.setup();
    setSession({
      role: "radiologist",
      permissions: ["REPORT_READ", "PEER_REVIEW_READ"],
    });
    renderWithAuth(<Sidebar />);
    expect(screen.getByText("Reading")).toBeInTheDocument();
    expect(screen.queryByText("Acquisition")).not.toBeInTheDocument();
    expect(screen.queryByText("QA")).not.toBeInTheDocument();
    expect(screen.queryByText("Admin")).not.toBeInTheDocument();
    expect(screen.queryByText("Analytics")).not.toBeInTheDocument();
    await user.click(screen.getByText("Reading"));
    expect(screen.getByText("Reading Worklist")).toBeInTheDocument();
    expect(screen.getByText("Peer Review")).toBeInTheDocument();
    expect(screen.queryByText("Exams")).not.toBeInTheDocument();
    expect(screen.queryByText("QA Queue")).not.toBeInTheDocument();
  });

  it("renders only Portal and Account sections for a patient role", () => {
    // patient walk R1: the patient portal is the only workspace — hide the
    // Acquisition and Front Desk sections that leak via SCHEDULE_READ.
    setSession({
      role: "patient",
      permissions: ["PORTAL_READ", "SCHEDULE_READ", "RESULTS_READ", "CHART_READ"],
    });
    renderWithAuth(<Sidebar />);
    expect(screen.getAllByText("My Records").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("Account")).toBeInTheDocument();
    expect(screen.queryByText("Files")).not.toBeInTheDocument();
    expect(screen.queryByText("Reading")).not.toBeInTheDocument();
    expect(screen.queryByText("Acquisition")).not.toBeInTheDocument();
    expect(screen.queryByText("QA")).not.toBeInTheDocument();
    expect(screen.queryByText("Admin")).not.toBeInTheDocument();
    expect(screen.queryByText("Front Desk")).not.toBeInTheDocument();
    expect(screen.queryByText("Analytics")).not.toBeInTheDocument();
    expect(screen.queryByText("Metrics")).not.toBeInTheDocument();
  });

  it("shows the Admin section for a user with only LOG_READ", async () => {
    const user = userEvent.setup();
    setSession({ role: "user", permissions: ["LOG_READ"] });
    renderWithAuth(<Sidebar />);
    expect(screen.getByText("Admin")).toBeInTheDocument();
    await user.click(screen.getByText("Admin"));
    expect(screen.getByText("Logs")).toBeInTheDocument();
    expect(screen.queryByText("Users")).not.toBeInTheDocument();
    expect(screen.queryByText("Replicas")).not.toBeInTheDocument();
  });

  it("hides clinical sections for a tenant_admin even with clinical grants", () => {
    setSession({
      role: "tenant_admin",
      permissions: ["REPORT_READ", "EXAM_READ", "QA_READ", "WORKLIST_READ", "USER_READ"],
    });
    renderWithAuth(<Sidebar />);
    expect(screen.queryByText("Reading")).not.toBeInTheDocument();
    expect(screen.queryByText("Acquisition")).not.toBeInTheDocument();
    expect(screen.queryByText("QA")).not.toBeInTheDocument();
    expect(screen.getByText("Admin")).toBeInTheDocument();
  });

  it("hides the Dashboard item from a clinical role even with a dashboard permission", async () => {
    const user = userEvent.setup();
    setSession({ role: "radiologist", permissions: ["USER_READ"] });
    renderWithAuth(<Sidebar />);
    expect(screen.getByText("Admin")).toBeInTheDocument();
    await user.click(screen.getByText("Admin"));
    expect(screen.getByText("Users")).toBeInTheDocument();
    expect(screen.queryByText("Dashboard")).not.toBeInTheDocument();
  });

  it("hides clinical sections for an admin-scoped role", () => {
    setSession({ role: "tenant_admin", admin: true, permissions: [] });
    renderWithAuth(<Sidebar />);
    expect(screen.queryByText("Reading")).not.toBeInTheDocument();
    expect(screen.queryByText("Acquisition")).not.toBeInTheDocument();
    expect(screen.queryByText("QA")).not.toBeInTheDocument();
    expect(screen.getByText("Admin")).toBeInTheDocument();
  });

  it("hides Front Desk and My Records from a tenant_admin even with the grants", () => {
    // The most dangerous NON_ADMIN_WORKSPACES drift: an admin-scoped role
    // that DOES hold the R08/R19 grants. The nav must still hide the
    // front-office and patient surfaces — admins manage the platform.
    setSession({
      role: "tenant_admin",
      permissions: [
        "REGISTRATION_READ",
        "REGISTRATION_WRITE",
        "QUEUE_READ",
        "PORTAL_READ",
        "SCHEDULE_READ",
        "USER_READ",
      ],
    });
    renderWithAuth(<Sidebar />);
    expect(screen.queryByText("Front Desk")).not.toBeInTheDocument();
    expect(screen.queryByText("My Records")).not.toBeInTheDocument();
  });

  it("hides Front Desk and My Records from super_admin (worst case)", () => {
    // super_admin holds every permission, so the filter is the only thing
    // standing between the platform roles and the front-office/patient UIs.
    setSession({
      role: "super_admin",
      admin: true,
      permissions: ["REGISTRATION_READ", "PORTAL_READ"],
    });
    renderWithAuth(<Sidebar />);
    expect(screen.queryByText("Front Desk")).not.toBeInTheDocument();
    expect(screen.queryByText("My Records")).not.toBeInTheDocument();
  });

  it("shows the Front Desk section for a receptionist with R08 grants", async () => {
    const user = userEvent.setup();
    setSession({
      role: "receptionist",
      permissions: [
        "REGISTRATION_READ",
        "REGISTRATION_WRITE",
        "QUEUE_READ",
        "SCHEDULE_READ",
        "SCHEDULE_WRITE",
        "PATIENT_READ",
      ],
    });
    renderWithAuth(<Sidebar />);
    expect(screen.getByText("Front Desk")).toBeInTheDocument();
    await user.click(screen.getByText("Front Desk"));
    expect(screen.getByText("Registration")).toBeInTheDocument();
    expect(screen.getByText("Today's Schedule")).toBeInTheDocument();
    expect(screen.getByText("Waiting Queue")).toBeInTheDocument();
    expect(screen.getByText("Patient Search")).toBeInTheDocument();
    // No PORTAL_READ: the patient surface stays hidden.
    expect(screen.queryByText("My Records")).not.toBeInTheDocument();
  });

  it("hides Acquisition but keeps Coordination for a receptionist with WORKLIST_READ/ORDER_READ", () => {
    // receptionist walk R1: the Acquisition section (MWL/Tracking/Schedule/
    // Calendar/Resources) is the technologist's operational surface, not the
    // front-office workspace. Coordination (Orders/Care Plans/Communications)
    // stays visible — the receptionist uses Orders during registration flow.
    setSession({
      role: "receptionist",
      permissions: [
        "REGISTRATION_READ", "REGISTRATION_WRITE", "QUEUE_READ",
        "SCHEDULE_READ", "SCHEDULE_WRITE", "PATIENT_READ",
        "WORKLIST_READ", "ORDER_READ",
      ],
    });
    renderWithAuth(<Sidebar />);
    expect(screen.getByText("Front Desk")).toBeInTheDocument();
    expect(screen.queryByText("Acquisition")).not.toBeInTheDocument();
    expect(screen.getByText("Coordination")).toBeInTheDocument();
  });

  it("hides Front Desk and My Records from a physician even with SCHEDULE_READ/PATIENT_READ", async () => {
    // physician walk R1: clinical-scoped roles hold SCHEDULE_READ and
    // PATIENT_READ (they open clinical and coordination surfaces), but the
    // front-office/patient UIs are not their workspace — hide the sections
    // while keeping the underlying routes deep-linkable.
    const user = userEvent.setup();
    setSession({
      role: "physician",
      permissions: ["SCHEDULE_READ", "PATIENT_READ", "PORTAL_READ", "REPORT_READ"],
    });
    renderWithAuth(<Sidebar />);
    expect(screen.getByText("Reading")).toBeInTheDocument();
    expect(screen.queryByText("Front Desk")).not.toBeInTheDocument();
    expect(screen.queryByText("My Records")).not.toBeInTheDocument();
  });

  it("shows the Metrics item for a custom role holding only ANALYTICS_READ", () => {
    setSession({
      role: "analytics_officer",
      permissions: ["ANALYTICS_READ", "AUDIT_READ", "INTERFACE_MONITOR"],
    });
    renderWithAuth(<Sidebar />);
    // "Metrics" appears twice: the Analytics section title and its item.
    expect(screen.getAllByText("Metrics").length).toBeGreaterThanOrEqual(1);
  });

  it("does not advertise Routing or DICOMweb to INTERFACE_ADMIN/STORAGE_ADMIN holders", async () => {
    const user = userEvent.setup();
    setSession({
      role: "tenant_admin",
      permissions: ["INTERFACE_ADMIN", "STORAGE_ADMIN", "USER_READ"],
    });
    renderWithAuth(<Sidebar />);
    expect(screen.getByText("Admin")).toBeInTheDocument();
    await user.click(screen.getByText("Admin"));
    // The /api/routing and /api/dicomweb* guards require ROUTING_READ /
    // DICOMWEB_READ; tenant_admin holds neither, so the nav must not
    // advertise pages the route and backend both reject.
    expect(screen.queryByText("Routing")).not.toBeInTheDocument();
    expect(screen.queryByText("DICOMweb")).not.toBeInTheDocument();
  });

  it("shows the Logs item for an admin-scoped role with AUDIT_READ", async () => {
    const user = userEvent.setup();
    setSession({
      role: "emr_admin",
      permissions: ["AUDIT_READ", "INTERFACE_MONITOR"],
    });
    renderWithAuth(<Sidebar />);
    expect(screen.getByText("Admin")).toBeInTheDocument();
    await user.click(screen.getByText("Admin"));
    expect(screen.getByText("Logs")).toBeInTheDocument();
  });

  it("shows the DICOMweb console to a clinical role with DICOMWEB_READ", async () => {
    const user = userEvent.setup();
    // radiologist and physician carry legacy DICOMWEB_READ; the console is
    // reachable for them (user decision 2026-08-27 — the submenu is no longer
    // adminOnly) and the backend re-checks DICOMWEB_WRITE on STOW itself.
    setSession({
      role: "radiologist",
      permissions: ["DICOMWEB_READ", "REPORT_READ"],
    });
    renderWithAuth(<Sidebar />);
    expect(screen.getByText("Reading")).toBeInTheDocument();
    expect(screen.getByText("Admin")).toBeInTheDocument();
    await user.click(screen.getByText("Admin"));
    expect(screen.getByText("DICOMweb")).toBeInTheDocument();
    expect(user).toBeDefined();
  });

  it("shows the DICOMweb console to an admin-scoped role holding DICOMWEB_READ", async () => {
    const user = userEvent.setup();
    setSession({
      role: "pacs_admin",
      permissions: ["DICOMWEB_READ", "REPLICA_READ"],
    });
    renderWithAuth(<Sidebar />);
    expect(screen.getByText("Admin")).toBeInTheDocument();
    await user.click(screen.getByText("Admin"));
    expect(screen.getByText("DICOMweb")).toBeInTheDocument();
  });

  it("hides the Files item from a role without any viewer permission", () => {
    // an EMR-only custom role (cf. the retired pharmacist/lab_technician
    // built-ins) holds no viewer grants; the Files route gate (FILE_READ |
    // STUDY_READ | VIEWER_READ) would bounce them, so the nav item must not
    // advertise a dead link.
    setSession({
      role: "emr_clerk",
      permissions: ["RESULTS_READ", "MED_VERIFY"],
    });
    renderWithAuth(<Sidebar />);
    expect(screen.queryByText("Files")).not.toBeInTheDocument();
    expect(screen.getByText("Account")).toBeInTheDocument();
  });

  it("keeps the Files item for a technologist with FILE_READ", () => {
    setSession({
      role: "technologist",
      permissions: ["FILE_READ", "EXAM_READ", "WORKLIST_READ"],
    });
    renderWithAuth(<Sidebar />);
    expect(screen.getByText("Files")).toBeInTheDocument();
    expect(screen.getByText("Acquisition")).toBeInTheDocument();
  });

  it("labels the Acquisition items My Exams and Modality Worklist", async () => {
    const user = userEvent.setup();
    setSession({
      role: "technologist",
      permissions: ["EXAM_READ", "WORKLIST_READ"],
    });
    renderWithAuth(<Sidebar />);
    expect(screen.getByText("Acquisition")).toBeInTheDocument();
    await user.click(screen.getByText("Acquisition"));
    // C10: the R06 assignment list and the DICOM worklist read distinctly.
    expect(screen.getByText("My Exams")).toBeInTheDocument();
    expect(screen.getByText("Modality Worklist")).toBeInTheDocument();
  });
});
