import React, { Suspense, useEffect } from "react";
import { BrowserRouter, Routes, Route, useNavigate } from "react-router";
import { App as AntdApp, ConfigProvider, Spin } from "antd";
import { createRoot } from "react-dom/client";
import "./common/tokens.css";
import "./index.css";
import { init } from "./ws";
import { setNavigator } from "./navigator";
import { ThemeProvider, useTheme } from "./common/ThemeProvider";
import { lightTheme, darkTheme } from "./common/theme";
import { AuthProvider, useAuth } from "./auth/AuthContext";
import { ErrorBoundary } from "./common/ErrorBoundary";
import { renderEmpty } from "./common/EmptyState";
import { OnboardingTour } from "./common/OnboardingTour";
import { HelpButton } from "./common/HelpButton";
import ProtectedRoute from "./auth/ProtectedRoute";
import PermissionRoute, {
  VIEWER_ROUTE_PERMISSIONS,
  PATIENT_ROUTE_PERMISSIONS,
  METRICS_ROUTE_PERMISSIONS,
  ADMIN_DASHBOARD_PERMISSIONS,
} from "./auth/PermissionRoute";
import { ADMIN_SCOPED_ROLES, CLINICAL_SCOPED_ROLES } from "./navigator";

// (L8) Stable no-op: a fresh arrow per render would hand OnboardingTour a new
// onComplete reference each time ThemedApp re-renders, defeating memoization.
const NOOP = () => {};

// Clinical surfaces (Reading / Acquisition / QA) belong to clinical roles.
// Admin-scoped roles manage the platform and never work clinical queues, so
// their routes are closed to those roles even when the permission passes —
// the same scope the sidebar and navigator.ts apply. Redirects land on the
// best permitted admin/platform route via landingRouteFor.
function ClinicalRoute({
  permission,
  children,
}: {
  permission: string | string[];
  children: React.ReactNode;
}) {
  return (
    <PermissionRoute
      permission={permission}
      excludedRoles={[...ADMIN_SCOPED_ROLES]}
    >
      {children}
    </PermissionRoute>
  );
}

// Admin-console surfaces (DICOMweb server / STOW / study browser) belong to
// admin-scoped roles. Clinical roles never operate the platform, so their
// routes are closed to those roles even when the legacy permission passes
// (DICOMWEB_READ on radiologist / physician) — the symmetric counterpart of
// ClinicalRoute, matching the sidebar (adminOnly items) and navigator.ts.
function AdminConsoleRoute({
  permission,
  children,
}: {
  permission: string | string[];
  children: React.ReactNode;
}) {
  return (
    <PermissionRoute
      permission={permission}
      excludedRoles={[...CLINICAL_SCOPED_ROLES]}
    >
      {children}
    </PermissionRoute>
  );
}

const Login = React.lazy(() => import("./login/Login"));
const Account = React.lazy(() => import("./account/Account"));
const Replicas = React.lazy(() => import("./replicas/Replicas"));
const Users = React.lazy(() => import("./users/Users"));
const Logs = React.lazy(() => import("./logs/Logs"));
const Roles = React.lazy(() => import("./roles/Roles"));
const Tenants = React.lazy(() => import("./tenants/Tenants"));
const Metrics = React.lazy(() => import("./metrics/Metrics"));
const Patient = React.lazy(() => import("./patient/Patient"));
const ShareView = React.lazy(() => import("./detail/ShareView"));
const Files = React.lazy(() => import("./files/Files"));
const Detail = React.lazy(() => import("./detail/Detail"));
const Worklist = React.lazy(() => import("./worklist/Worklist"));
const ScheduleBoard = React.lazy(() => import("./schedule/ScheduleBoard"));
const FrontDeskRegistration = React.lazy(
  () => import("./frontdesk/Registration"),
);
const FrontDeskVisits = React.lazy(() => import("./frontdesk/Visits"));
const FrontDeskQueue = React.lazy(() => import("./frontdesk/WaitingQueue"));
const PatientPortal = React.lazy(() => import("./portal/Portal"));
const TechnologistWorklist = React.lazy(
  () => import("./technologist/TechnologistWorklist"),
);
const ExamConsole = React.lazy(() => import("./technologist/ExamConsole"));
const ReadingWorklist = React.lazy(
  () => import("./radiologist/ReadingWorklist"),
);
const ReportEditor = React.lazy(() => import("./radiologist/ReportEditor"));
const PeerReviewInbox = React.lazy(
  () => import("./radiologist/PeerReviewInbox"),
);
const QAQueue = React.lazy(() => import("./qa/QAQueue"));
const QAReviewForm = React.lazy(() => import("./qa/QAReviewForm"));
const ProtocolRegistry = React.lazy(() => import("./qa/ProtocolRegistry"));
const Incidents = React.lazy(() => import("./qa/Incidents"));
const CorrectiveActions = React.lazy(() => import("./qa/CorrectiveActions"));
const ServiceKeys = React.lazy(() => import("./servicekeys/ServiceKeys"));
const RoutingRules = React.lazy(() => import("./routing/RoutingRules"));
const FhirConfig = React.lazy(() => import("./fhir/FhirConfig"));
const FhirMonitoring = React.lazy(() => import("./fhir/FhirMonitoring"));
const FhirDocs = React.lazy(() => import("./fhir/FhirDocs"));
const Hl7Dashboard = React.lazy(() => import("./hl7/Hl7Dashboard"));
const DicomWebAdmin = React.lazy(() => import("./dicomweb/DicomWebAdmin"));
const StowUpload = React.lazy(() => import("./dicomweb/StowUpload"));
const StudyBrowser = React.lazy(() => import("./dicomweb/StudyBrowser"));
const Integrations = React.lazy(() => import("./integrations/Integrations"));
const AdminDashboard = React.lazy(() => import("./dashboard/AdminDashboard"));
const NotFound = React.lazy(() => import("./notfound/NotFound"));

function NavigatorSetter() {
  const navigate = useNavigate();
  useEffect(() => {
    setNavigator(navigate);
  }, [navigate]);
  return null;
}

function WsEffect() {
  const { isAuthenticated } = useAuth();
  useEffect(() => {
    // init() skips itself while unauthenticated; re-running on auth change
    // (re)connects the socket right after login instead of only on mount.
    init();
  }, [isAuthenticated]);
  return null;
}

function ThemedApp() {
  const { isDark } = useTheme();
  const params = new URLSearchParams(window.location.search);
  const tempKey = params.get("key");

  // (M1) Store the share key in an effect, not during render — effects run
  // after commit, keeping the storage write out of the render phase.
  useEffect(() => {
    if (tempKey) {
      sessionStorage.setItem("tempKey", tempKey);
    }
  }, [tempKey]);

  return (
    <ConfigProvider
      theme={isDark ? darkTheme : lightTheme}
      renderEmpty={renderEmpty}
    >
      <AntdApp>
        <BrowserRouter>
          <AuthProvider>
            <WsEffect />
            <NavigatorSetter />
            <ErrorBoundary>
              <Suspense
                fallback={
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "center",
                      alignItems: "center",
                      height: "100vh",
                    }}
                  >
                    <Spin size="large" />
                  </div>
                }
              >
                <Routes>
                  <Route path="/login" element={<Login />} />
                  <Route element={<ProtectedRoute />}>
                    <Route path="/account" element={<Account />} />
                    <Route
                      path="/admin"
                      element={
                        <PermissionRoute
                          permission={ADMIN_DASHBOARD_PERMISSIONS}
                          adminOnly
                        >
                          <AdminDashboard />
                        </PermissionRoute>
                      }
                    />
                    <Route
                      path="/replicas"
                      element={
                        <PermissionRoute permission="REPLICA_READ">
                          <Replicas />
                        </PermissionRoute>
                      }
                    />
                    <Route
                      path="/users"
                      element={
                        <PermissionRoute permission="USER_READ">
                          <Users />
                        </PermissionRoute>
                      }
                    />
                    <Route
                      path="/roles"
                      element={
                        <PermissionRoute permission="ROLE_READ">
                          <Roles />
                        </PermissionRoute>
                      }
                    />
                    <Route
                      path="/tenants"
                      element={
                        <PermissionRoute permission="TENANT_READ">
                          <Tenants />
                        </PermissionRoute>
                      }
                    />
                    <Route
                      path="/metrics"
                      element={
                        <PermissionRoute permission={METRICS_ROUTE_PERMISSIONS}>
                          <Metrics />
                        </PermissionRoute>
                      }
                    />
                    <Route
                      path="/logs"
                      element={
                        // LOG_READ or its canonical alias AUDIT_READ (spec §6):
                        // Matrix A admin roles carry only AUDIT_READ; the nav
                        // gate already accepts both and the backend resolves
                        // the alias symmetrically (rbac.py).
                        <PermissionRoute
                          permission={["LOG_READ", "AUDIT_READ"]}
                        >
                          <Logs />
                        </PermissionRoute>
                      }
                    />
                    <Route
                      path="/worklist"
                      element={
                        <ClinicalRoute permission="WORKLIST_READ">
                          <Worklist />
                        </ClinicalRoute>
                      }
                    />
                    <Route
                      path="/schedule-board"
                      element={
                        // The board is a schedule surface (view + capacity
                        // booking + cancel), so it gates on SCHEDULE_READ
                        // rather than the worklist permission: front-office
                        // roles holding SCHEDULE_READ reach it, and the
                        // SCHEDULE_WRITE grant (scheduler; receptionist via
                        // R08) unlocks the write actions inside.
                        <ClinicalRoute permission="SCHEDULE_READ">
                          <ScheduleBoard />
                        </ClinicalRoute>
                      }
                    />
                    <Route
                      path="/exams"
                      element={
                        <ClinicalRoute permission="EXAM_READ">
                          <TechnologistWorklist />
                        </ClinicalRoute>
                      }
                    />
                    <Route
                      path="/exams/:id"
                      element={
                        <ClinicalRoute permission="EXAM_READ">
                          <ExamConsole />
                        </ClinicalRoute>
                      }
                    />
                    <Route
                      path="/reading"
                      element={
                        <ClinicalRoute permission="REPORT_READ">
                          <ReadingWorklist />
                        </ClinicalRoute>
                      }
                    />
                    <Route
                      path="/reading/:examId"
                      element={
                        <ClinicalRoute permission="REPORT_READ">
                          <ReportEditor />
                        </ClinicalRoute>
                      }
                    />
                    <Route
                      path="/peer-review"
                      element={
                        <ClinicalRoute permission="PEER_REVIEW_READ">
                          <PeerReviewInbox />
                        </ClinicalRoute>
                      }
                    />
                    <Route
                      path="/qa/queue"
                      element={
                        <ClinicalRoute permission="QA_READ">
                          <QAQueue />
                        </ClinicalRoute>
                      }
                    />
                    <Route
                      path="/qa/review/:examId"
                      element={
                        <ClinicalRoute permission="QA_READ">
                          <QAReviewForm />
                        </ClinicalRoute>
                      }
                    />
                    <Route
                      path="/qa/protocols"
                      element={
                        <ClinicalRoute permission="QA_READ">
                          <ProtocolRegistry />
                        </ClinicalRoute>
                      }
                    />
                    <Route
                      path="/qa/incidents"
                      element={
                        <ClinicalRoute permission="QA_READ">
                          <Incidents />
                        </ClinicalRoute>
                      }
                    />
                    <Route
                      path="/qa/actions"
                      element={
                        <ClinicalRoute permission="QA_READ">
                          <CorrectiveActions />
                        </ClinicalRoute>
                      }
                    />
                    <Route
                      path="/frontdesk/registration"
                      element={
                        <ClinicalRoute permission="REGISTRATION_READ">
                          <FrontDeskRegistration />
                        </ClinicalRoute>
                      }
                    />
                    <Route
                      path="/frontdesk/visits"
                      element={
                        <ClinicalRoute permission="REGISTRATION_READ">
                          <FrontDeskVisits />
                        </ClinicalRoute>
                      }
                    />
                    <Route
                      path="/frontdesk/queue"
                      element={
                        <ClinicalRoute permission="QUEUE_READ">
                          <FrontDeskQueue />
                        </ClinicalRoute>
                      }
                    />
                    <Route
                      path="/portal"
                      element={
                        // The patient portal is a role-scoped surface (R19):
                        // staff/patient roles holding PORTAL_READ render their
                        // own scope-gated records. Admin-scoped roles are
                        // excluded like the front-desk surfaces — super_admin
                        // holds every grant, but "My Records" is not an admin
                        // surface.
                        <ClinicalRoute permission="PORTAL_READ">
                          <PatientPortal />
                        </ClinicalRoute>
                      }
                    />
                    <Route
                      path="/service-keys"
                      element={
                        <PermissionRoute permission="SERVICE_KEY_READ">
                          <ServiceKeys />
                        </PermissionRoute>
                      }
                    />
                    <Route
                      path="/routing"
                      element={
                        <PermissionRoute permission="ROUTING_READ">
                          <RoutingRules />
                        </PermissionRoute>
                      }
                    />
                    <Route
                      path="/fhir/config"
                      element={
                        <PermissionRoute permission="SYSTEM_ADMIN">
                          <FhirConfig />
                        </PermissionRoute>
                      }
                    />
                    <Route
                      path="/fhir/monitoring"
                      element={
                        <PermissionRoute permission="SYSTEM_ADMIN">
                          <FhirMonitoring />
                        </PermissionRoute>
                      }
                    />
                    <Route
                      path="/fhir/docs"
                      element={
                        <PermissionRoute permission="SYSTEM_ADMIN">
                          <FhirDocs />
                        </PermissionRoute>
                      }
                    />
                    <Route
                      path="/hl7"
                      element={
                        <PermissionRoute permission="HL7_READ">
                          <Hl7Dashboard />
                        </PermissionRoute>
                      }
                    />
                    <Route
                      path="/dicomweb"
                      element={
                        <AdminConsoleRoute permission="DICOMWEB_READ">
                          <DicomWebAdmin />
                        </AdminConsoleRoute>
                      }
                    />
                    <Route
                      path="/dicomweb/store"
                      element={
                        <AdminConsoleRoute permission="DICOMWEB_READ">
                          <StowUpload />
                        </AdminConsoleRoute>
                      }
                    />
                    <Route
                      path="/dicomweb/browser"
                      element={
                        <AdminConsoleRoute permission="DICOMWEB_READ">
                          <StudyBrowser />
                        </AdminConsoleRoute>
                      }
                    />
                    <Route
                      path="/integrations"
                      element={
                        <PermissionRoute permission="SYSTEM_ADMIN">
                          <Integrations />
                        </PermissionRoute>
                      }
                    />
                    <Route
                      path="/patients/:id"
                      element={
                        <ClinicalRoute permission={PATIENT_ROUTE_PERMISSIONS}>
                          <Patient />
                        </ClinicalRoute>
                      }
                    />
                    <Route
                      path="/files/:id"
                      element={
                        <PermissionRoute permission={VIEWER_ROUTE_PERMISSIONS}>
                          <Detail />
                        </PermissionRoute>
                      }
                    />
                    <Route
                      path="/"
                      element={
                        <PermissionRoute permission={VIEWER_ROUTE_PERMISSIONS}>
                          <Files />
                        </PermissionRoute>
                      }
                    />
                  </Route>
                  <Route path="/view/:key" element={<ShareView />} />
                  <Route path="*" element={<NotFound />} />
                </Routes>
              </Suspense>
              <OnboardingTour onComplete={NOOP} />
              <HelpButton />
            </ErrorBoundary>
          </AuthProvider>
        </BrowserRouter>
      </AntdApp>
    </ConfigProvider>
  );
}

function App() {
  return (
    <ThemeProvider>
      <ThemedApp />
    </ThemeProvider>
  );
}

const rootEl = document.getElementById("root")!;
createRoot(rootEl).render(<App />);
