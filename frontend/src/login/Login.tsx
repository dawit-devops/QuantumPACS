import React, { useEffect, useState, useRef } from "react";
import { useLocation, useNavigate } from "react-router";
import { useFetch, useDocumentTitle } from "../hooks";
import { listLoginProviders } from "../api/auth";
import {
  App,
  Form,
  Input,
  Button,
  Layout,
  Card,
  Typography,
  Divider,
  Alert,
} from "antd";
import { UserOutlined, LockOutlined, LoginOutlined } from "@ant-design/icons";
import { useAuth } from "../auth/AuthContext";
import { useTheme } from "../common/ThemeProvider";
import QuantumLogo from "../common/QuantumLogo";
import MaintenanceBanner from "../common/MaintenanceBanner";
import { landingRouteFor } from "../navigator";
import { NAME_MAP } from "../api/roles";
import "./Login.css";
const { Content } = Layout;
const { Text } = Typography;

const LOGIN_RETRY_KEY = "loginAttempts";

// Dev-only quick-fill: every canonical role slug becomes a `test.`-prefixed
// username so testers can sign in as any persona without typing credentials.
// (R1-05) Gated on DEV so the demo-user catalog never ships in prod builds.
const demoUsernames = import.meta.env.DEV
  ? Object.keys(NAME_MAP).map((slug) => `test.${slug}`)
  : [];

function getLoginDelay(): number {
  try {
    const raw = localStorage.getItem(LOGIN_RETRY_KEY);
    if (!raw) return 0;
    const { count, nextAllowed } = JSON.parse(raw);
    if (Date.now() < nextAllowed) {
      return Math.ceil((nextAllowed - Date.now()) / 1000);
    }
  } catch {
    localStorage.removeItem(LOGIN_RETRY_KEY);
  }
  return 0;
}

function recordFailedAttempt(): number {
  const raw = localStorage.getItem(LOGIN_RETRY_KEY);
  let count = 1;
  if (raw) {
    try {
      count = JSON.parse(raw).count + 1;
    } catch {}
  }
  const delay = Math.min(30, Math.pow(2, count - 1));
  const nextAllowed = Date.now() + delay * 1000;
  localStorage.setItem(
    LOGIN_RETRY_KEY,
    JSON.stringify({
      count,
      nextAllowed,
    }),
  );
  return nextAllowed;
}

function clearAttempts() {
  localStorage.removeItem(LOGIN_RETRY_KEY);
}

function LoginForm(props: any) {
  const { message } = App.useApp();
  useDocumentTitle("QuantumPACS - Login");
  const navigate = useNavigate();
  const location = useLocation();

  const [form] = Form.useForm();
  const { exec, showLoading, loading, data, error } = useFetch("login");
  const [lockoutSeconds, setLockoutSeconds] = useState(getLoginDelay);
  const [shareKeyError, setShareKeyError] = useState<string | null>(null);
  const [providers, setProviders] = useState<any[]>([]);
  const { signIn } = useAuth();
  const { isDark } = useTheme();
  // (R1-05) Single absolute lockout deadline; the countdown interval below
  // derives remaining seconds from it instead of recreating itself on every
  // tick (the old `[lockoutSeconds]` dependency re-armed setInterval 1/sec).
  const lockoutEndRef = useRef<number | null>(null);

  useEffect(() => {
    const err = sessionStorage.getItem("shareKeyError");
    if (err) {
      sessionStorage.removeItem("shareKeyError");
      setShareKeyError(
        "This share link has expired or is invalid. Please request a new one from the sender.",
      );
    }
  }, []);

  useEffect(() => {
    listLoginProviders()
      .then((res) => {
        setProviders(res);
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (!data) return;
    clearAttempts();
    signIn(
      data.access_token || data.token,
      {
        id: data.id,
        username: data.username || "",
        admin: data.admin === true || data.admin === "true",
        role: data.role || (data.admin ? "admin" : "user"),
        permissions: data.permissions || [],
        tenant_id: data.tenant_id,
        tenant_name: data.tenant_name,
      },
      data.refresh_token,
    );
    // A-7: ProtectedRoute records the pre-login URL in location.state.from so
    // users land back where they were headed instead of always the root.
    // The root is not a deep link: logging in from "/" must still reach the
    // role-scoped landing (admin home is the dashboard, not the files page).
    const from = (location.state as { from?: { pathname?: string } } | null)
      ?.from?.pathname;
    // Role-scoped landing: the user shape mirrors the one handed to signIn()
    // above, so the redirect matches the workspace the session exposes.
    navigate(
      from && from !== "/"
        ? from
        : landingRouteFor({
            role: data.role || (data.admin ? "admin" : "user"),
            admin: data.admin === true || data.admin === "true",
            permissions: data.permissions || [],
          }),
    );
  }, [data, location.state]);

  useEffect(() => {
    if (!loading && error) {
      if (error.status !== 429) {
        lockoutEndRef.current = recordFailedAttempt();
      }
      setLockoutSeconds(getLoginDelay());
      const msg =
        error.status === 429
          ? "Too many login attempts. Please wait before trying again."
          : error.message || error;
      message.error(msg);
      setTimeout(() => {
        const btn = document.querySelector(
          ".login-form-button",
        ) as HTMLButtonElement;
        btn?.focus();
      }, 100);
    }
  }, [loading, error]);

  // Seed the deadline from storage on mount so a reload during a lockout
  // keeps counting down.
  useEffect(() => {
    try {
      const raw = localStorage.getItem(LOGIN_RETRY_KEY);
      if (raw) {
        const { nextAllowed } = JSON.parse(raw);
        if (nextAllowed > Date.now()) lockoutEndRef.current = nextAllowed;
      }
    } catch {}
  }, []);

  // One interval for the whole mount; remaining time is always derived from
  // the absolute deadline, so ticks never re-create the timer.
  useEffect(() => {
    const id = setInterval(() => {
      const end = lockoutEndRef.current;
      if (end == null) return;
      const remaining = Math.max(0, Math.ceil((end - Date.now()) / 1000));
      setLockoutSeconds(remaining);
      if (remaining <= 0) lockoutEndRef.current = null;
    }, 1000);
    return () => clearInterval(id);
  }, []);

  const handleSubmit = (values: any) => {
    if (lockoutSeconds > 0) {
      message.warning(`Too many attempts. Try again in ${lockoutSeconds}s.`);
      return;
    }
    exec(true, {
      method: "POST",
      body: JSON.stringify({
        username: values.username,
        password: values.password,
      }),
    });
  };

  const prefixColor = isDark ? "rgba(255,255,255,0.3)" : "rgba(0,0,0,0.25)";
  const dividerColor = isDark ? "rgba(255,255,255,0.2)" : "rgba(0,0,0,0.35)";

  return (
    <Layout
      style={{
        alignItems: "center",
        justifyContent: "center",
        height: "100%",
        background:
          "linear-gradient(135deg, var(--login-gradient-start) 0%, var(--login-gradient-mid) 50%, var(--login-gradient-end) 100%)",
      }}
    >
      <div style={{ position: "absolute", top: 0, left: 0, right: 0 }}>
        <MaintenanceBanner />
      </div>
      <Content>
        <Card
          className="animate-scale-in"
          style={{
            width: 380,
            borderRadius: 12,
            boxShadow: "0 8px 32px rgba(0,0,0,0.3)",
          }}
          styles={{ body: { padding: "40px 32px" } }}
        >
          <div style={{ textAlign: "center", marginBottom: 32 }}>
            <QuantumLogo size={48} />
          </div>
          {shareKeyError && (
            <Alert
              message="Expired Share Link"
              description={shareKeyError}
              type="warning"
              showIcon
              closable
              onClose={() => setShareKeyError(null)}
              style={{ marginBottom: 16, borderRadius: 8 }}
            />
          )}
          <Text
            type="secondary"
            style={{
              display: "block",
              textAlign: "center",
              marginBottom: 24,
              fontSize: 13,
            }}
          >
            Sign in to your account
          </Text>
          <Form form={form} onFinish={handleSubmit} className="login-form">
            <Form.Item
              name="username"
              rules={[
                { required: true, message: "Please input your username!" },
              ]}
            >
              <Input
                prefix={<UserOutlined style={{ color: prefixColor }} />}
                placeholder="Username"
                aria-label="Username"
                size="large"
                autoComplete="username"
                list={import.meta.env.DEV ? "demo-usernames" : undefined}
                maxLength={128}
              />
            </Form.Item>
            {/* Dev/demo helper: a datalist of `test.`-prefixed role usernames
                so testers can impersonate any persona from the role catalog
                without typing credentials by hand. (R1-05) Dev-only. */}
            {import.meta.env.DEV && (
              <datalist id="demo-usernames">
                {demoUsernames.map((username) => (
                  <option key={username} value={username} />
                ))}
              </datalist>
            )}
            {import.meta.env.DEV && (
              <Text
                type="secondary"
                style={{
                  display: "block",
                  textAlign: "center",
                  fontSize: 11,
                  marginBottom: 16,
                }}
              >
                Demo users (dev only): pick a role username, e.g.
                test.radiologist
              </Text>
            )}
            <Form.Item
              name="password"
              rules={[
                { required: true, message: "Please input your password!" },
              ]}
            >
              <Input.Password
                prefix={<LockOutlined style={{ color: prefixColor }} />}
                placeholder="Password"
                aria-label="Password"
                size="large"
                autoComplete="current-password"
                maxLength={256}
              />
            </Form.Item>
            <Form.Item>
              <Button
                type="primary"
                htmlType="submit"
                className="login-form-button animate-fade-in-up"
                size="large"
                loading={showLoading}
                disabled={lockoutSeconds > 0}
                style={{ animationDelay: "100ms" }}
              >
                {lockoutSeconds > 0 ? `Retry in ${lockoutSeconds}s` : "Sign In"}
              </Button>
            </Form.Item>
          </Form>
          {providers.length > 0 && (
            <>
              <Divider
                plain
                style={{ fontSize: 12, color: dividerColor, margin: "16px 0" }}
              >
                or continue with SSO
              </Divider>
              {providers.map((p: any) => (
                <Button
                  key={p.slug}
                  block
                  icon={<LoginOutlined />}
                  style={{ marginBottom: 8 }}
                  onClick={() => {
                    window.location.href = `${window.location.origin}/api/oauth/login?idp=${p.slug}`;
                  }}
                >
                  Sign in with {p.name}
                </Button>
              ))}
            </>
          )}
          <Text
            type="secondary"
            style={{
              display: "block",
              textAlign: "center",
              fontSize: 11,
              marginTop: 16,
            }}
          >
            QuantumPACS v1.0 — Diagnostic Clarity, Quantum Fast
          </Text>
        </Card>
      </Content>
    </Layout>
  );
}

export default LoginForm;
