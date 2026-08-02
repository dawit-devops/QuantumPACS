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

  // (M1) Store the share key in an effect, not during render — effects run
  // after commit, keeping the storage write out of the render phase.
  useEffect(() => {
    if (tempKey) {
      sessionStorage.setItem("tempKey", tempKey);
    }
  }, [tempKey]);
  useEffect(() => {
    init();
  }, []);

  return (
    <ConfigProvider
      theme={isDark ? darkTheme : lightTheme}
      renderEmpty={renderEmpty}
    >
      <AntdApp>
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
                  <Route element={<ProtectedRoute />}>
                    <Route path="/account" element={<Account />} />
                    <Route path="/replicas" element={<Replicas />} />
                    <Route path="/users" element={<Users />} />
                    <Route path="/roles" element={<Roles />} />
                    <Route path="/tenants" element={<Tenants />} />
                    <Route path="/metrics" element={<Metrics />} />
                    <Route path="/logs" element={<Logs />} />
                    <Route path="/worklist" element={<Worklist />} />
                    <Route path="/service-keys" element={<ServiceKeys />} />
                    <Route path="/routing" element={<RoutingRules />} />
                    <Route path="/fhir/config" element={<FhirConfig />} />
                    <Route
                      path="/fhir/monitoring"
                      element={<FhirMonitoring />}
                    />
                    <Route path="/fhir/docs" element={<FhirDocs />} />
                    <Route path="/hl7" element={<Hl7Dashboard />} />
                    <Route path="/dicomweb" element={<DicomWebAdmin />} />
                    <Route path="/integrations" element={<Integrations />} />
                    <Route path="/patients/:id" element={<Patient />} />
                    <Route path="/files/:id" element={<Detail />} />
                    <Route path="/" element={<Files />} />
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
