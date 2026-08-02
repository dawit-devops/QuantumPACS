import React, { Suspense, useEffect } from "react";
import { BrowserRouter, Routes, Route, useNavigate } from "react-router";
import { ConfigProvider, Spin } from "antd";
import { createRoot } from "react-dom/client";
import "./common/tokens.css";
import "./index.css";
import { init } from "./ws";
import { setNavigator } from "./navigator";
import { ThemeProvider, useTheme } from "./common/ThemeProvider";
import { lightTheme, darkTheme } from "./common/theme";
import { AuthProvider } from "./auth/AuthContext";
import { ErrorBoundary } from "./common/ErrorBoundary";
import { renderEmpty } from "./common/EmptyState";
import { OnboardingTour } from "./common/OnboardingTour";
import { HelpButton } from "./common/HelpButton";
import ProtectedRoute from "./auth/ProtectedRoute";
import PermissionRoute from "./auth/PermissionRoute";

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

function ThemedApp() {
  const { isDark } = useTheme();
  const params = new URLSearchParams(window.location.search);
  const tempKey = params.get("key");

  if (tempKey) {
    localStorage.setItem("tempKey", tempKey);
  }
  useEffect(() => {
    init();
  }, []);

  return (
    <ConfigProvider
      theme={isDark ? darkTheme : lightTheme}
      renderEmpty={renderEmpty}
    >
      <BrowserRouter>
        <AuthProvider>
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
                <Route
                  path="/account"
                  element={
                    <ProtectedRoute>
                      <Account />
                    </ProtectedRoute>
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
                    <ProtectedRoute>
                      <Metrics />
                    </ProtectedRoute>
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
                    <ProtectedRoute>
                      <Patient />
                    </ProtectedRoute>
                  }
                />
                <Route path="/view/:key" element={<ShareView />} />
                <Route
                  path="/files/:id"
                  element={
                    <ProtectedRoute>
                      <Detail />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/"
                  element={
                    <ProtectedRoute>
                      <Files />
                    </ProtectedRoute>
                  }
                />
                <Route path="*" element={<NotFound />} />
              </Routes>
            </Suspense>
            <OnboardingTour onComplete={() => {}} />
            <HelpButton />
          </ErrorBoundary>
        </AuthProvider>
      </BrowserRouter>
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
