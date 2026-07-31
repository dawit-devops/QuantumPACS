import React, { Suspense, useEffect } from "react";
import { BrowserRouter, Routes, Route, useNavigate } from "react-router-dom";
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
                    <ProtectedRoute>
                      <Replicas />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/users"
                  element={
                    <ProtectedRoute>
                      <Users />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/roles"
                  element={
                    <ProtectedRoute>
                      <Roles />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/tenants"
                  element={
                    <ProtectedRoute>
                      <Tenants />
                    </ProtectedRoute>
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
                    <ProtectedRoute>
                      <Logs />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/worklist"
                  element={
                    <ProtectedRoute>
                      <Worklist />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/service-keys"
                  element={
                    <ProtectedRoute>
                      <ServiceKeys />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/routing"
                  element={
                    <ProtectedRoute>
                      <RoutingRules />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/fhir/config"
                  element={
                    <ProtectedRoute>
                      <FhirConfig />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/fhir/monitoring"
                  element={
                    <ProtectedRoute>
                      <FhirMonitoring />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/fhir/docs"
                  element={
                    <ProtectedRoute>
                      <FhirDocs />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/hl7"
                  element={
                    <ProtectedRoute>
                      <Hl7Dashboard />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/dicomweb"
                  element={
                    <ProtectedRoute>
                      <DicomWebAdmin />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/integrations"
                  element={
                    <ProtectedRoute>
                      <Integrations />
                    </ProtectedRoute>
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
