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
} from "./auth/PermissionRoute";

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
const Integrations = React.lazy(() => import("./integrations/Integrations"));
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
                        <PermissionRoute permission="LOG_READ">
                          <Logs />
                        </PermissionRoute>
                      }
                    />
                    <Route
                      path="/worklist"
                      element={
                        <PermissionRoute permission="WORKLIST_READ">
                          <Worklist />
                        </PermissionRoute>
                      }
                    />
                    <Route
                      path="/schedule-board"
                      element={
                        <PermissionRoute permission="WORKLIST_READ">
                          <ScheduleBoard />
                        </PermissionRoute>
                      }
                    />
                    <Route
                      path="/exams"
                      element={
                        <PermissionRoute permission="EXAM_READ">
                          <TechnologistWorklist />
                        </PermissionRoute>
                      }
                    />
                    <Route
                      path="/exams/:id"
                      element={
                        <PermissionRoute permission="EXAM_READ">
                          <ExamConsole />
                        </PermissionRoute>
                      }
                    />
                    <Route
                      path="/reading"
                      element={
                        <PermissionRoute permission="REPORT_READ">
                          <ReadingWorklist />
                        </PermissionRoute>
                      }
                    />
                    <Route
                      path="/reading/:examId"
                      element={
                        <PermissionRoute permission="REPORT_READ">
                          <ReportEditor />
                        </PermissionRoute>
                      }
                    />
                    <Route
                      path="/peer-review"
                      element={
                        <PermissionRoute permission="PEER_REVIEW_READ">
                          <PeerReviewInbox />
                        </PermissionRoute>
                      }
                    />
                    <Route
                      path="/qa/queue"
                      element={
                        <PermissionRoute permission="QA_READ">
                          <QAQueue />
                        </PermissionRoute>
                      }
                    />
                    <Route
                      path="/qa/review/:examId"
                      element={
                        <PermissionRoute permission="QA_READ">
                          <QAReviewForm />
                        </PermissionRoute>
                      }
                    />
                    <Route
                      path="/qa/protocols"
                      element={
                        <PermissionRoute permission="QA_READ">
                          <ProtocolRegistry />
                        </PermissionRoute>
                      }
                    />
                    <Route
                      path="/qa/incidents"
                      element={
                        <PermissionRoute permission="QA_READ">
                          <Incidents />
                        </PermissionRoute>
                      }
                    />
                    <Route
                      path="/qa/actions"
                      element={
                        <PermissionRoute permission="QA_READ">
                          <CorrectiveActions />
                        </PermissionRoute>
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
                        <PermissionRoute permission="DICOMWEB_READ">
                          <DicomWebAdmin />
                        </PermissionRoute>
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
                        <PermissionRoute permission={PATIENT_ROUTE_PERMISSIONS}>
                          <Patient />
                        </PermissionRoute>
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
              <OnboardingTour onComplete={() => {}} />
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
