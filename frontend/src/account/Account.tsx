import { useDocumentTitle } from "../hooks";
import React, { useEffect, useState } from "react";
import { getProfile, updateProfile, changePassword } from "../api/account";
import withSidebar from "../common/base";
import {
  App,
  Form,
  Input,
  Button,
  Layout,
  Card,
  Typography,
  Tag,
  Descriptions,
  Spin,
  Divider,
} from "antd";
import {
  LockOutlined,
  UserOutlined,
  MailOutlined,
  SafetyOutlined,
  CalendarOutlined,
  LoginOutlined,
} from "@ant-design/icons";
import { useAuth } from "../auth/AuthContext";

const { Content } = Layout;
const { Text, Title } = Typography;

function Account(props: any) {
  const { message } = App.useApp();
  useDocumentTitle("QuantumPACS - Account");

  const [profile, setProfile] = useState<any>(null);
  const [profileLoading, setProfileLoading] = useState(true);
  const [emailEditing, setEmailEditing] = useState(false);
  const [emailValue, setEmailValue] = useState("");
  const [savingEmail, setSavingEmail] = useState(false);
  const [pwForm] = Form.useForm();
  const [pwLoading, setPwLoading] = useState(false);
  const { user } = useAuth();

  useEffect(() => {
    getProfile()
      .then((res) => {
        setProfile(res);
      })
      .catch((err: any) => {
        message.error("Failed to load profile");
      })
      .finally(() => {
        setProfileLoading(false);
      });
  }, []);

  const handleEmailSave = async () => {
    setSavingEmail(true);
    try {
      await updateProfile({ email: emailValue });
      message.success("Email updated");
      setEmailEditing(false);
      setProfile((prev: any) => ({ ...prev, email: emailValue }));
    } catch {
      message.error("Failed to update email");
    } finally {
      setSavingEmail(false);
    }
  };

  const handlePasswordChange = async (values: any) => {
    setPwLoading(true);
    try {
      await changePassword({
        current_password: values.current_password,
        new_password: values.new_password,
        new_password2: values.new_password2,
      });
      message.success("Password changed successfully");
      pwForm.resetFields();
    } catch (err: any) {
      message.error(err.error || err.message || "Failed to change password");
    } finally {
      setPwLoading(false);
    }
  };

  if (profileLoading) {
    return (
      <Content
        style={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          minHeight: 360,
        }}
      >
        <Spin size="large" />
      </Content>
    );
  }

  const p = profile || {};
  const permissionColors: Record<string, string> = {
    admin: "red",
    write: "blue",
    read: "green",
    delete: "orange",
  };

  return (
    <Content style={{ padding: 24, maxWidth: 640, margin: "0 auto" }}>
      <Title level={3} style={{ marginBottom: 24 }}>
        Account
      </Title>

      <Card
        title={
          <>
            <UserOutlined /> Profile
          </>
        }
        style={{ marginBottom: 24 }}
      >
        <Descriptions column={1} size="small" bordered>
          <Descriptions.Item
            label={
              <>
                <UserOutlined /> Username
              </>
            }
          >
            {p.username}
          </Descriptions.Item>
          <Descriptions.Item
            label={
              <>
                <MailOutlined /> Email
              </>
            }
          >
            {emailEditing ? (
              <Input
                value={emailValue}
                onChange={(e) => setEmailValue(e.target.value)}
                style={{ width: 240 }}
                autoFocus
              />
            ) : (
              p.email || <Text type="secondary">Not set</Text>
            )}
            <div style={{ marginTop: 4 }}>
              {emailEditing ? (
                <>
                  <Button
                    type="primary"
                    size="small"
                    loading={savingEmail}
                    onClick={handleEmailSave}
                    style={{ marginRight: 8 }}
                  >
                    Save
                  </Button>
                  <Button
                    size="small"
                    onClick={() => {
                      setEmailEditing(false);
                      setEmailValue(p.email);
                    }}
                  >
                    Cancel
                  </Button>
                </>
              ) : (
                <Button
                  type="link"
                  size="small"
                  onClick={() => {
                    setEmailEditing(true);
                    setEmailValue(p.email || "");
                  }}
                >
                  Edit
                </Button>
              )}
            </div>
          </Descriptions.Item>
          <Descriptions.Item
            label={
              <>
                <SafetyOutlined /> Role
              </>
            }
          >
            {p.role_display_name || p.role || (
              <Text type="secondary">No role</Text>
            )}
            {p.role && <Tag style={{ marginLeft: 8 }}>{p.role}</Tag>}
          </Descriptions.Item>
          {p.tenant && (
            <Descriptions.Item label="Tenant">
              {p.tenant_display_name || p.tenant}
            </Descriptions.Item>
          )}
          <Descriptions.Item
            label={
              <>
                <CalendarOutlined /> Created
              </>
            }
          >
            {p.created_at ? new Date(p.created_at).toLocaleDateString() : "-"}
          </Descriptions.Item>
          <Descriptions.Item
            label={
              <>
                <LoginOutlined /> Last Login
              </>
            }
          >
            {p.last_login ? new Date(p.last_login).toLocaleString() : "Never"}
          </Descriptions.Item>
        </Descriptions>
      </Card>

      {p.permissions && p.permissions.length > 0 && (
        <Card title="Permissions" size="small" style={{ marginBottom: 24 }}>
          {p.permissions.map((perm: string) => (
            <Tag
              key={perm}
              color={
                permissionColors[perm.split("_")[0]?.toLowerCase()] || "default"
              }
              style={{ marginBottom: 4 }}
            >
              {perm}
            </Tag>
          ))}
        </Card>
      )}

      <Card
        title={
          <>
            <LockOutlined /> Change Password
          </>
        }
        style={{ marginBottom: 24 }}
      >
        <Form form={pwForm} onFinish={handlePasswordChange} layout="vertical">
          <Form.Item
            name="current_password"
            rules={[
              { required: true, message: "Current password is required" },
            ]}
          >
            <Input.Password
              prefix={<LockOutlined />}
              placeholder="Current password"
              autoComplete="current-password"
            />
          </Form.Item>
          <Form.Item
            name="new_password"
            rules={[
              { required: true, message: "New password is required" },
              { min: 8, message: "Password must be at least 8 characters" },
            ]}
          >
            <Input.Password
              prefix={<LockOutlined />}
              placeholder="New password"
              autoComplete="new-password"
            />
          </Form.Item>
          <Form.Item
            name="new_password2"
            rules={[
              { required: true, message: "Please confirm your new password" },
              ({ getFieldValue }) => ({
                validator(_, value) {
                  if (!value || getFieldValue("new_password") === value) {
                    return Promise.resolve();
                  }
                  return Promise.reject(new Error("Passwords do not match"));
                },
              }),
            ]}
          >
            <Input.Password
              prefix={<LockOutlined />}
              placeholder="Confirm new password"
              autoComplete="new-password"
            />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" loading={pwLoading}>
              Change Password
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </Content>
  );
}

export default withSidebar(Account);
