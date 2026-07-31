import React, { useEffect, useState, useRef } from "react";
import withRouter from "../withRouter";
import { useFetch, useDocumentTitle } from "../hooks";
import { request } from "../helpers";
import {
  Form,
  Input,
  Button,
  message,
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
import "./Login.css";
const { Content } = Layout;
const { Text } = Typography;

const LOGIN_RETRY_KEY = "loginAttempts";

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

function recordFailedAttempt() {
  const raw = localStorage.getItem(LOGIN_RETRY_KEY);
  let count = 1;
  if (raw) {
    try {
      count = JSON.parse(raw).count + 1;
    } catch {}
  }
  const delay = Math.min(30, Math.pow(2, count - 1));
  localStorage.setItem(
    LOGIN_RETRY_KEY,
    JSON.stringify({
      count,
      nextAllowed: Date.now() + delay * 1000,
    }),
  );
}

function clearAttempts() {
  localStorage.removeItem(LOGIN_RETRY_KEY);
}

function LoginForm(props: any) {
  useDocumentTitle("QuantumPACS - Login");

  const [form] = Form.useForm();
  const { exec, showLoading, loading, data, error } = useFetch("login");
  const [lockoutSeconds, setLockoutSeconds] = useState(getLoginDelay);
  const [shareKeyError, setShareKeyError] = useState<string | null>(null);
  const [providers, setProviders] = useState<any[]>([]);
  const { signIn } = useAuth();
  const { isDark } = useTheme();

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
    request("oauth/providers")
      .then((res: any) => {
        if (res?.data) setProviders(res.data);
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
      },
      data.refresh_token,
    );
    props.history.push("/");
  }, [data]);

  const errorRef = React.useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!loading && error) {
      if (error.status !== 429) recordFailedAttempt();
      setLockoutSeconds(getLoginDelay());
      const msg =
        error.status === 429
          ? "Too many login attempts. Please wait before trying again."
          : error.error || error;
      message.error(msg);
      setTimeout(() => {
        const btn = document.querySelector(
          ".login-form-button",
        ) as HTMLButtonElement;
        btn?.focus();
      }, 100);
    }
  }, [loading, error]);

  useEffect(() => {
    if (lockoutSeconds <= 0) return;
    const id = setInterval(() => {
      const remaining = getLoginDelay();
      setLockoutSeconds(remaining);
      if (remaining <= 0) clearInterval(id);
    }, 1000);
    return () => clearInterval(id);
  }, [lockoutSeconds]);

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
                size="large"
                autoComplete="username"
              />
            </Form.Item>
            <Form.Item
              name="password"
              rules={[
                { required: true, message: "Please input your password!" },
              ]}
            >
              <Input.Password
                prefix={<LockOutlined style={{ color: prefixColor }} />}
                placeholder="Password"
                size="large"
                autoComplete="current-password"
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

export default withRouter(LoginForm);
