import { useDocumentTitle } from "../hooks";
import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  App,
  Layout,
  Card,
  Form,
  Input,
  InputNumber,
  Switch,
  Button,
  Space,
  Typography,
  Tag,
  Alert,
} from "antd";
import { SettingOutlined, SaveOutlined } from "@ant-design/icons";
import withSidebar from "../common/base";
import PageHeader from "../common/PageHeader";
import { PageState } from "../common/PageState";
import {
  getAdminConfig,
  updateAdminConfig,
  type ConfigSetting,
} from "../api/admin";

const { Content } = Layout;
const { Text } = Typography;

const LABELS: Record<string, string> = {
  max_upload_size_mb: "Max file upload size (MB)",
  max_stow_size_mb: "Max STOW-RS store size (MB)",
  tenant_usage_retention_days: "Tenant usage retention (days)",
  token_expiry_days: "Access token lifetime (days)",
  allowed_hosts: "Allowed hosts",
  cors_origins: "CORS origins",
  cookie_secure: "Secure cookies (HTTPS only)",
};

const GROUPS: { key: string; title: string; keys: string[] }[] = [
  {
    key: "storage",
    title: "Storage & Upload",
    keys: ["max_upload_size_mb", "max_stow_size_mb"],
  },
  {
    key: "session",
    title: "Auth & Retention",
    keys: ["token_expiry_days", "tenant_usage_retention_days"],
  },
  {
    key: "security",
    title: "Security & Hosting",
    keys: ["allowed_hosts", "cors_origins", "cookie_secure"],
  },
];

function Settings() {
  const { message } = App.useApp();
  useDocumentTitle("QuantumPACS - System Settings");
  const [settings, setSettings] = useState<Record<
    string,
    ConfigSetting
  > | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState<string | null>(null);
  const [form] = Form.useForm();

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    getAdminConfig()
      .then((res) => {
        setSettings(res.settings);
        const initial: Record<string, unknown> = {};
        for (const [k, v] of Object.entries(res.settings)) {
          initial[k] = v.value;
        }
        form.setFieldsValue(initial);
      })
      .catch((e: any) => setError(e.message))
      .finally(() => setLoading(false));
  }, [form]);

  useEffect(() => {
    load();
  }, [load]);

  const saveGroup = async (groupKey: string, keys: string[]) => {
    setSaving(groupKey);
    try {
      const values = await form.validateFields(keys);
      const payload: Record<string, { value: string | number | boolean }> = {};
      for (const k of keys) payload[k] = { value: values[k] };
      const res = await updateAdminConfig(payload);
      message.success(`Saved ${res.updated.length} setting(s)`);
      load();
    } catch (e: any) {
      if (e?.errorFields) {
        message.error("Please fix the highlighted fields");
      } else {
        message.error(e.message);
      }
    } finally {
      setSaving(null);
    }
  };

  const restartKeys = useMemo(
    () =>
      settings
        ? Object.entries(settings)
            .filter(([, s]) => s.restart)
            .map(([k]) => k)
        : [],
    [settings],
  );

  return (
    <Content style={{ padding: 24 }}>
      <PageHeader
        title="System Settings"
        description="Whitelisted platform settings. Changes are audited as system.config_changed. Secrets are never shown here."
      />

      {restartKeys.length > 0 && (
        <Alert
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
          title={`Some settings need a restart to take effect: ${restartKeys.join(", ")}`}
        />
      )}

      <PageState loading={loading} error={error} onRetry={load}>
        {settings && (
          <Space vertical style={{ width: "100%" }} size={16}>
            {GROUPS.map((group) => (
              <Card
                key={group.key}
                size="small"
                title={
                  <span>
                    <SettingOutlined /> {group.title}
                  </span>
                }
                extra={
                  <Button
                    type="primary"
                    size="small"
                    icon={<SaveOutlined />}
                    loading={saving === group.key}
                    onClick={() => saveGroup(group.key, group.keys)}
                  >
                    Save
                  </Button>
                }
              >
                <Form form={form} layout="vertical">
                  {group.keys.map((key) => {
                    const spec = settings[key];
                    if (!spec) return null;
                    return (
                      <Form.Item
                        key={key}
                        name={key}
                        label={
                          <Space size={6}>
                            <span>{LABELS[key] ?? key}</span>
                            {spec.restart && (
                              <Tag color="orange">restart required</Tag>
                            )}
                          </Space>
                        }
                      >
                        {spec.type === "bool" ? (
                          <Switch
                            checkedChildren="ON"
                            unCheckedChildren="OFF"
                          />
                        ) : spec.type === "int" ? (
                          <InputNumber min={1} style={{ width: 200 }} />
                        ) : (
                          <Input placeholder={key} />
                        )}
                      </Form.Item>
                    );
                  })}
                </Form>
              </Card>
            ))}
            <Text type="secondary" style={{ fontSize: 12 }}>
              Editable values are applied to the running platform for
              runtime-safe keys; restart-required keys apply on the next backend
              restart.
            </Text>
          </Space>
        )}
      </PageState>
    </Content>
  );
}

export default withSidebar(Settings);
