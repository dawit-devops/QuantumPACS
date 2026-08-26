import { App as AntdApp, ConfigProvider, Spin } from "antd";
import React, { Suspense, useEffect } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Routes, Route, useNavigate } from "react-router";

import "./common/tokens.css";
import "./common/report.css";
import "./index.css";

import { AuthProvider, useAuth } from "./auth/AuthContext";
import PermissionRoute, {
  VIEWER_ROUTE_PERMISSIONS,
  PATIENT_ROUTE_PERMISSIONS,
  METRICS_ROUTE_PERMISSIONS,
  ADMIN_DASHBOARD_PERMISSIONS,
} from "./auth/PermissionRoute";
import ProtectedRoute from "./auth/ProtectedRoute";
import { renderEmpty } from "./common/EmptyState";
import { ErrorBoundary } from "./common/ErrorBoundary";
import { HelpButton } from "./common/HelpButton";
import { OnboardingTour } from "./common/OnboardingTour";
import { lightTheme, darkTheme } from "./common/theme";
import { ThemeProvider, useTheme } from "./common/ThemeProvider";
import { setNavigator, ADMIN_SCOPED_ROLES, CLINICAL_SCOPED_ROLES } from "./navigator";
import { init } from "./ws";

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
    <PermissionRoute permission={permission} excludedRoles={[...ADMIN_SCOPED_ROLES]}>
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
    <PermissionRoute permission={permission} excludedRoles={[...CLINICAL_SCOPED_ROLES]}>
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
const TrackingBoard = React.lazy(() => import("./worklist/TrackingBoard"));
const ScheduleBoard = React.lazy(() => import("./schedule/ScheduleBoard"));
const ResourceManager = React.lazy(() => import("./schedule/ResourceManager"));
const CalendarView = React.lazy(() => import("./schedule/CalendarView"));
const Orders = React.lazy(() => import("./coordinator/Orders"));
const PriorAuthPanel = React.lazy(() => import("./coordinator/PriorAuthPanel"));
const Reminders = React.lazy(() => import("./coordinator/Reminders"));
const CarePlans = React.lazy(() => import("./coordinator/CarePlans"));
const NursingPrepList = React.lazy(() => import("./nursing/NursingPrepList"));
const Communications = React.lazy(() => import("./coordinator/Communications"));
const FrontDeskRegistration = React.lazy(() => import("./frontdesk/Registration"));
const FrontDeskVisits = React.lazy(() => import("./frontdesk/Visits"));
const FrontDeskQueue = React.lazy(() => import("./frontdesk/WaitingQueue"));
const FrontDeskSchedule = React.lazy(() => import("./frontdesk/ScheduleToday"));
const PatientPortal = React.lazy(() => import("./portal/PortalHome"));
const PatientProfile = React.lazy(() => import("./portal/PatientProfile"));
const AppointmentList = React.lazy(() => import("./portal/AppointmentList"));
const ReportList = React.lazy(() => import("./portal/ReportList"));
const ReportDetail = React.lazy(() => import("./portal/ReportDetail"));
const FollowUpHub = React.lazy(() => import("./portal/FollowUpHub"));
const TechnologistWorklist = React.lazy(() => import("./technologist/TechnologistWorklist"));
const ExamConsole = React.lazy(() => import("./technologist/ExamConsole"));
const ReadingWorklist = React.lazy(() => import("./radiologist/ReadingWorklist"));
const ResidentHome = React.lazy(() => import("./radiologist/ResidentHome"));
const ResidentProgress = React.lazy(() => import("./radiologist/ResidentProgress"));
const TeachingLibrary = React.lazy(() => import("./radiologist/TeachingLibrary"));
const ReadingConsole = React.lazy(() => import("./radiologist/ReadingConsole"));
const PeerReviewInbox = React.lazy(() => import("./radiologist/PeerReviewInbox"));
const CriticalResultsList = React.lazy(() => import("./radiologist/CriticalResults"));
const QAQueue = React.lazy(() => import("./qa/QAQueue"));
const QAReviewForm = React.lazy(() => import("./qa/QAReviewForm"));
const ProtocolRegistry = React.lazy(() => import("./qa/ProtocolRegistry"));
const Incidents = React.lazy(() => import("./qa/Incidents"));
const CorrectiveActions = React.lazy(() => import("./qa/CorrectiveActions"));
const QAAnalyticsDashboard = React.lazy(() => import("./qa/QAAnalyticsDashboard"));
const BillingQueue = React.lazy(() => import("./billing/BillingQueue"));
const ClaimsStatus = React.lazy(() => import("./billing/ClaimsStatus"));
const RevenueDashboard = React.lazy(() => import("./billing/RevenueDashboard"));
const DenialRework = React.lazy(() => import("./billing/DenialRework"));
const TemplateManager = React.lazy(() => import("./admin/TemplateManager"));
const UnbilledAging = React.lazy(() => import("./billing/UnbilledAging"));
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
const NotificationPreferences = React.lazy(() => import("./notifications/NotificationPreferences"));
const UserDashboard = React.lazy(() => import("./dashboard/UserDashboard"));
const Maintenance = React.lazy(() => import("./maintenance/Maintenance"));
const Backups = React.lazy(() => import("./admin/Backups"));
const Settings = React.lazy(() => import("./admin/Settings"));
const InterfaceDashboard = React.lazy(() => import("./admin/InterfaceDashboard"));
const RisDashboard = React.lazy(() => import("./admin/RISDashboard"));
const StaffSchedule = React.lazy(() => import("./admin/StaffSchedule"));
const NotFound = React.lazy(() => import("./notfound/NotFound"));
const CheckIn = React.lazy(() => import("./kiosk/CheckIn"));

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
    <ConfigProvider theme={isDark ? darkTheme : lightTheme} renderEmpty={renderEmpty}>
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
                  {/* RIS-REG-04: kiosk check-in is a public surface. */}
                  <Route path="/checkin" element={<CheckIn />} />
                  <Route element={<ProtectedRoute />}>
                    <Route path="/account" element={<Account />} />
                    {/* Per-user notification subscriptions (P1-1). */}
                    <Route path="/account/notifications" element={<NotificationPreferences />} />
                    {/* §3 configurable widget dashboard — widgets self-filter
                        by permission; the page is plain authenticated. */}
                    <Route path="/dashboard" element={<UserDashboard />} />
                    {/* Platform-ops surfaces (super_admin review) — only the
                        platform admin holds SYSTEM_ADMIN. */}
                    <Route
                      path="/admin/maintenance"
                      element={
                        <PermissionRoute permission="SYSTEM_ADMIN">
                          <Maintenance />
                        </PermissionRoute>
                      }
                    />
                    <Route
                      path="/admin/backups"
                      element={
                        <PermissionRoute permission="SYSTEM_ADMIN">
                          <Backups />
                        </PermissionRoute>
                      }
                    />
                    <Route
                      path="/admin/settings"
                      element={
                        <PermissionRoute permission="SYSTEM_ADMIN">
                          <Settings />
                        </PermissionRoute>
                      }
                    />
                    <Route
                      path="/admin/interfaces"
                      element={
                        <PermissionRoute permission="HL7_READ">
                          <InterfaceDashboard />
                        </PermissionRoute>
                      }
                    />
                    <Route
                      path="/admin/ris-dashboard"
                      element={
                        <AdminConsoleRoute permission="REPORT_READ">
                          <RisDashboard />
                        </AdminConsoleRoute>
                      }
                    />
                    <Route
                      path="/admin/staff-schedule"
                      element={
                        <AdminConsoleRoute permission="SCHEDULE_READ">
                          <StaffSchedule />
                        </AdminConsoleRoute>
                      }
                    />
                    <Route
                      path="/admin"
                      element={
                        <PermissionRoute permission={ADMIN_DASHBOARD_PERMISSIONS} adminOnly>
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
                        <PermissionRoute permission={["LOG_READ", "AUDIT_READ"]}>
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
                      path="/tracking"
                      element={
                        <ClinicalRoute permission="WORKLIST_READ">
                          <TrackingBoard />
                        </ClinicalRoute>
                      }
                    />
                    <Route
                      path="/schedule-board"
                      element={
                        // The board loads day data from GET /api/worklist
                        // (WORKLIST_READ) and supports capacity booking
                        // (SCHEDULE_READ/WRITE). Accept either permission
                        // so both physician/resident (WORKLIST_READ) and
                        // scheduler/receptionist (SCHEDULE_READ) reach the
                        // page without a dead-end redirect.
                        <ClinicalRoute permission={["WORKLIST_READ", "SCHEDULE_READ"]}>
                          <ScheduleBoard />
                        </ClinicalRoute>
                      }
                    />
                    <Route
                      path="/schedule"
                      element={
                        // S4-16 day view: the RIS-native schedule surface.
                        // Gated on SCHEDULE_READ like the board; SCHEDULE_WRITE
                        // unlocks book/reschedule/cancel inside.
                        <ClinicalRoute permission="SCHEDULE_READ">
                          <CalendarView />
                        </ClinicalRoute>
                      }
                    />
                    <Route
                      path="/schedule/resources"
                      element={
                        <ClinicalRoute permission="SCHEDULE_READ">
                          <ResourceManager />
                        </ClinicalRoute>
                      }
                    />
                    <Route
                      path="/exams"
                      element={
                        <ClinicalRoute permission={["EXAM_READ", "NURSING_READ"]}>
                          <TechnologistWorklist />
                        </ClinicalRoute>
                      }
                    />
                    <Route
                      path="/exams/:id"
                      element={
                        <ClinicalRoute permission={["EXAM_READ", "NURSING_READ"]}>
                          <ExamConsole />
                        </ClinicalRoute>
                      }
                    />
                    {/* §2.11 nursing prep queue: the coordinator/nurse entry
                        surface that deep-links into exam consoles. */}
                    <Route
                      path="/nursing"
                      element={
                        <ClinicalRoute permission="NURSING_READ">
                          <NursingPrepList />
                        </ClinicalRoute>
                      }
                    />
                    <Route
                      path="/orders"
                      element={
                        // Care-coordinator review (P0-2/P1-2): the coordination
                        // surface. ORDER_READ is the read gate; write actions
                        // (status updates) will require ORDER_WRITE when shipped.
                        <ClinicalRoute permission="ORDER_READ">
                          <Orders />
                        </ClinicalRoute>
                      }
                    />
                    <Route
                      path="/prior-auth"
                      element={
                        // R2-01: prior authorization management. PRIOR_AUTH_READ
                        // gates the list; submit/decide are PRIOR_AUTH_WRITE
                        // actions surfaced inline (the API enforces them).
                        <ClinicalRoute permission="PRIOR_AUTH_READ">
                          <PriorAuthPanel />
                        </ClinicalRoute>
                      }
                    />
                    <Route
                      path="/reminders"
                      element={
                        // R2-02: reminders — config, delivery log, manual send.
                        <ClinicalRoute permission="PRIOR_AUTH_READ">
                          <Reminders />
                        </ClinicalRoute>
                      }
                    />
                    <Route
                      path="/care-plans"
                      element={
                        // CC-02: care-plan board. Browse is PATIENT_READ so
                        // coordinator (and any chart-reader) can see plans;
                        // create/edit gates on CARE_PLAN_WRITE in the UI.
                        <ClinicalRoute permission="PATIENT_READ">
                          <CarePlans />
                        </ClinicalRoute>
                      }
                    />
                    <Route
                      path="/communications"
                      element={
                        // CC-04: communication log — patient-scoped search;
                        // logging gates on ENCOUNTER_WRITE server-side.
                        <ClinicalRoute permission="PATIENT_READ">
                          <Communications />
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
                      path="/reading/home"
                      element={
                        <ClinicalRoute permission="REPORT_READ">
                          <ResidentHome />
                        </ClinicalRoute>
                      }
                    />
                    {/* RES-04: must register before /reading/:examId. */}
                    <Route
                      path="/reading/progress"
                      element={
                        <ClinicalRoute permission="REPORT_READ">
                          <ResidentProgress />
                        </ClinicalRoute>
                      }
                    />
                    {/* R-11/RES-03: teaching file library. */}
                    <Route
                      path="/teaching"
                      element={
                        <ClinicalRoute permission="REPORT_READ">
                          <TeachingLibrary />
                        </ClinicalRoute>
                      }
                    />
                    <Route
                      path="/reading/:examId"
                      element={
                        <ClinicalRoute permission="REPORT_READ">
                          <ReadingConsole />
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
                      path="/critical"
                      element={
                        // CR-6: dedicated critical-results surface. GET
                        // /api/notifications/critical is REPORT_READ-gated
                        // (notifications.py), so the route gate matches.
                        <ClinicalRoute permission="REPORT_READ">
                          <CriticalResultsList />
                        </ClinicalRoute>
                      }
                    />
                    <Route
                      path="/billing/queue"
                      element={
                        <ClinicalRoute permission="BILLING_READ">
                          <BillingQueue />
                        </ClinicalRoute>
                      }
                    />
                    {/* B-06: claim lifecycle tracking. */}
                    <Route
                      path="/billing/claims"
                      element={
                        <ClinicalRoute permission="BILLING_READ">
                          <ClaimsStatus />
                        </ClinicalRoute>
                      }
                    />
                    {/* B-07: revenue trends + AR aging. */}
                    <Route
                      path="/billing/revenue"
                      element={
                        <ClinicalRoute permission="BILLING_READ">
                          <RevenueDashboard />
                        </ClinicalRoute>
                      }
                    />
                    <Route
                      path="/admin/report-templates"
                      element={
                        <ClinicalRoute permission="REPORT_WRITE">
                          <TemplateManager />
                        </ClinicalRoute>
                      }
                    />
                    <Route
                      path="/billing/denials"
                      element={
                        <ClinicalRoute permission="BILLING_READ">
                          <DenialRework />
                        </ClinicalRoute>
                      }
                    />
                    <Route
                      path="/billing/unbilled"
                      element={
                        <ClinicalRoute permission="BILLING_READ">
                          <UnbilledAging />
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
                      path="/qa/analytics"
                      element={
                        <ClinicalRoute permission="QA_READ">
                          <QAAnalyticsDashboard />
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
                      path="/frontdesk/schedule"
                      element={
                        <ClinicalRoute permission="SCHEDULE_READ">
                          <FrontDeskSchedule />
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
                      path="/portal/profile"
                      element={
                        <ClinicalRoute permission="PORTAL_READ">
                          <PatientProfile />
                        </ClinicalRoute>
                      }
                    />
                    <Route
                      path="/portal/appointments"
                      element={
                        <ClinicalRoute permission="PORTAL_READ">
                          <AppointmentList />
                        </ClinicalRoute>
                      }
                    />
                    <Route
                      path="/portal/results"
                      element={
                        <ClinicalRoute permission="PORTAL_READ">
                          <ReportList />
                        </ClinicalRoute>
                      }
                    />
                    <Route
                      path="/portal/results/:reportId"
                      element={
                        <ClinicalRoute permission="PORTAL_READ">
                          <ReportDetail />
                        </ClinicalRoute>
                      }
                    />
                    <Route
                      path="/portal/follow-ups"
                      element={
                        <ClinicalRoute permission="PORTAL_READ">
                          <FollowUpHub />
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
