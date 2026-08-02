import React, { useState, useEffect } from "react";
import {
  Layout,
  Card,
  Table,
  Tag,
  Button,
  Modal,
  Form,
  Input,
  Select,
  InputNumber,
  Switch,
  Space,
  message,
  Popconfirm,
  Descriptions,
  Tabs,
  Tooltip,
} from "antd";
import {
  PlusOutlined,
  ReloadOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ApiOutlined,
  SendOutlined,
} from "@ant-design/icons";
import withRouter from "../withRouter";
import withSidebar from "../common/base";
import {
  listOauthProviders,
  createOauthProvider,
  updateOauthProvider,
  deleteOauthProvider,
  listWebhooks,
  createWebhook,
  updateWebhook,
  deleteWebhook,
  testWebhook,
} from "../api/integrations";
import { PageState } from "../common/PageState";
import "./Integrations.css";

const { Content } = Layout;
const { TextArea } = Input;

function Integrations(props: any) {
  // ---- OAuth Providers ----
  let [providers, setProviders] = useState<any[]>([]);
  let [providersLoading, setProvidersLoading] = useState(true);
  let [providerModal, setProviderModal] = useState(false);
  let [editingProvider, setEditingProvider] = useState<any>(null);
  let [providerForm] = Form.useForm();

  // ---- Webhooks ----
  let [webhooks, setWebhooks] = useState<any[]>([]);
  let [availableEvents, setAvailableEvents] = useState<string[]>([]);
  let [webhooksLoading, setWebhooksLoading] = useState(true);
  let [whModal, setWhModal] = useState(false);
  let [editingWh, setEditingWh] = useState<any>(null);
  let [whForm] = Form.useForm();
  let [testResult, setTestResult] = useState<any>(null);
  let [testing, setTesting] = useState(false);

  const fetchProviders = async () => {
    setProvidersLoading(true);
    try {
      const res = await listOauthProviders();
      setProviders(res || []);
    } catch {
    } finally {
      setProvidersLoading(false);
    }
  };

  const fetchWebhooks = async () => {
    setWebhooksLoading(true);
    try {
      const res = await listWebhooks();
      setWebhooks(res?.webhooks || []);
      setAvailableEvents(res?.available_events || []);
    } catch {
    } finally {
      setWebhooksLoading(false);
    }
  };

  useEffect(() => {
    fetchProviders();
    fetchWebhooks();
  }, []);

  // ---- OAuth Provider CRUD ----
  const openProviderModal = (provider?: any) => {
    setEditingProvider(provider || null);
    providerForm.setFieldsValue(
      provider || {
        issuer: "",
        client_id: "",
        client_secret: "",
        jwks_uri: "",
        token_url: "",
        redirect_uri: "",
        scope: "openid email profile",
        auto_provision: true,
        enabled: true,
      },
    );
    setProviderModal(true);
  };

  const handleProviderSave = async () => {
    const values = await providerForm.validateFields();
    try {
      if (editingProvider) {
        await updateOauthProvider(editingProvider.id, values);
        message.success("OAuth provider updated");
      } else {
        await createOauthProvider(values);
        message.success("OAuth provider created");
      }
      setProviderModal(false);
      fetchProviders();
    } catch (e: any) {
      message.error(e.message);
    }
  };

  const handleProviderDelete = async (id: string) => {
    try {
      await deleteOauthProvider(id);
      message.success("OAuth provider deleted");
      fetchProviders();
    } catch (e: any) {
      message.error(e.message);
    }
  };

  // ---- Webhook CRUD ----
  const openWhModal = (wh?: any) => {
    setEditingWh(wh || null);
    setTestResult(null);
    whForm.setFieldsValue(
      wh || {
        name: "",
        url: "",
        events: [],
        secret: "",
        active: true,
        retry_count: 3,
        timeout_ms: 5000,
      },
    );
    setWhModal(true);
  };

  const handleWhSave = async () => {
    const values = await whForm.validateFields();
    try {
      if (editingWh) {
        await updateWebhook(editingWh.id, values);
        message.success("Webhook updated");
      } else {
        await createWebhook(values);
        message.success("Webhook created");
      }
      setWhModal(false);
      fetchWebhooks();
    } catch (e: any) {
      message.error(e.message);
    }
  };

  const handleWhDelete = async (id: string) => {
    try {
      await deleteWebhook(id);
      message.success("Webhook deleted");
      fetchWebhooks();
    } catch (e: any) {
      message.error(e.message);
    }
  };

  const handleTestWebhook = async () => {
    const values = await whForm.validateFields();
    setTesting(true);
    setTestResult(null);
    try {
      const res = await testWebhook({
        url: values.url,
        secret: values.secret,
      });
      setTestResult(res);
    } catch (e: any) {
      setTestResult({ success: false, error: e.message, status_code: 0 });
    } finally {
      setTesting(false);
    }
  };

  const provColumns = [
    { title: "Issuer", dataIndex: "issuer", key: "issuer", ellipsis: true },
    { title: "Client ID", dataIndex: "client_id", key: "client_id" },
    { title: "Scope", dataIndex: "scope", key: "scope" },
    {
      title: "Enabled",
      dataIndex: "enabled",
      key: "enabled",
      render: (t: boolean) =>
        t ? <Tag color="green">Enabled</Tag> : <Tag color="red">Disabled</Tag>,
    },
    {
      title: "Auto-Provision",
      dataIndex: "auto_provision",
      key: "auto_provision",
      render: (t: boolean) => (t ? <Tag>Yes</Tag> : <Tag>No</Tag>),
    },
    {
      title: "Actions",
      key: "actions",
      render: (_: any, r: any) => (
        <Space>
          <Button size="small" onClick={() => openProviderModal(r)}>
            Edit
          </Button>
          <Popconfirm
            title="Delete this provider?"
            onConfirm={() => handleProviderDelete(r.id)}
          >
            <Button size="small" danger>
              Delete
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const whColumns = [
    { title: "Name", dataIndex: "name", key: "name" },
    { title: "URL", dataIndex: "url", key: "url", ellipsis: true },
    {
      title: "Events",
      dataIndex: "events",
      key: "events",
      render: (t: string[]) =>
        t?.length > 0 ? (
          t
            .slice(0, 2)
            .map((e: string) => (
              <Tag key={e} style={{ marginBottom: 2 }}>
                {e}
              </Tag>
            ))
            .concat(t.length > 2 ? [<Tag key="more">+{t.length - 2}</Tag>] : [])
        ) : (
          <Tag>All</Tag>
        ),
    },
    {
      title: "Active",
      dataIndex: "active",
      key: "active",
      render: (t: boolean) =>
        t ? <Tag color="green">Active</Tag> : <Tag color="red">Inactive</Tag>,
    },
    {
      title: "Last Trigger",
      dataIndex: "last_triggered_at",
      key: "last_triggered_at",
      render: (t: string) => (t ? new Date(t).toLocaleString() : "-"),
    },
    {
      title: "Last Status",
      dataIndex: "last_status_code",
      key: "last_status_code",
      render: (t: number, r: any) => {
        if (!t) return "-";
        const color = t < 300 ? "green" : "red";
        return (
          <Tooltip title={r.last_error}>
            <Tag color={color}>{t}</Tag>
          </Tooltip>
        );
      },
    },
    {
      title: "Actions",
      key: "actions",
      render: (_: any, r: any) => (
        <Space>
          <Button size="small" onClick={() => openWhModal(r)}>
            Edit
          </Button>
          <Popconfirm
            title="Delete this webhook?"
            onConfirm={() => handleWhDelete(r.id)}
          >
            <Button size="small" danger>
              Delete
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <Content className="integrations" style={{ padding: 24 }}>
      <Tabs
        defaultActiveKey="webhooks"
        items={[
          {
            key: "webhooks",
            label: (
              <span>
                <SendOutlined /> Webhooks
              </span>
            ),
            children: (
              <div>
                <div
                  style={{
                    marginBottom: 12,
                    display: "flex",
                    justifyContent: "space-between",
                  }}
                >
                  <span style={{ color: "var(--text-secondary)" }}>
                    {webhooks.length} webhook{webhooks.length !== 1 ? "s" : ""}{" "}
                    configured
                  </span>
                  <Space>
                    <Button icon={<ReloadOutlined />} onClick={fetchWebhooks}>
                      Refresh
                    </Button>
                    <Button
                      type="primary"
                      icon={<PlusOutlined />}
                      onClick={() => openWhModal()}
                    >
                      Add Webhook
                    </Button>
                  </Space>
                </div>
                <Table
                  dataSource={webhooks}
                  columns={whColumns}
                  rowKey="id"
                  loading={webhooksLoading}
                  pagination={false}
                  locale={{
                    emptyText:
                      "No webhooks configured. Add a webhook to receive event notifications.",
                  }}
                />
              </div>
            ),
          },
          {
            key: "oauth",
            label: (
              <span>
                <ApiOutlined /> OAuth Providers
              </span>
            ),
            children: (
              <div>
                <div
                  style={{
                    marginBottom: 12,
                    display: "flex",
                    justifyContent: "space-between",
                  }}
                >
                  <span style={{ color: "var(--text-secondary)" }}>
                    {providers.length} provider
                    {providers.length !== 1 ? "s" : ""}
                  </span>
                  <Space>
                    <Button icon={<ReloadOutlined />} onClick={fetchProviders}>
                      Refresh
                    </Button>
                    <Button
                      type="primary"
                      icon={<PlusOutlined />}
                      onClick={() => openProviderModal()}
                    >
                      Add Provider
                    </Button>
                  </Space>
                </div>
                <Table
                  dataSource={providers}
                  columns={provColumns}
                  rowKey="id"
                  loading={providersLoading}
                  pagination={false}
                  locale={{
                    emptyText:
                      "No OAuth providers configured. Add a provider to enable SSO.",
                  }}
                />
              </div>
            ),
          },
        ]}
      />

      {/* OAuth Provider Modal */}
      <Modal
        title={editingProvider ? "Edit OAuth Provider" : "Add OAuth Provider"}
        open={providerModal}
        onOk={handleProviderSave}
        onCancel={() => setProviderModal(false)}
        width={600}
      >
        <Form form={providerForm} layout="vertical">
          <Form.Item
            name="issuer"
            label="Issuer URL"
            rules={[{ required: true }]}
          >
            <Input placeholder="https://accounts.google.com" />
          </Form.Item>
          <Form.Item
            name="client_id"
            label="Client ID"
            rules={[{ required: true }]}
          >
            <Input />
          </Form.Item>
          <Form.Item
            name="client_secret"
            label="Client Secret"
            rules={[{ required: !editingProvider }]}
          >
            <Input.Password
              placeholder={editingProvider ? "(unchanged)" : ""}
            />
          </Form.Item>
          <Form.Item name="jwks_uri" label="JWKS URI">
            <Input />
          </Form.Item>
          <Form.Item name="token_url" label="Token URL">
            <Input />
          </Form.Item>
          <Form.Item name="redirect_uri" label="Redirect URI">
            <Input />
          </Form.Item>
          <Form.Item name="scope" label="Scope">
            <Input placeholder="openid email profile" />
          </Form.Item>
          <Space>
            <Form.Item name="enabled" label="Enabled" valuePropName="checked">
              <Switch />
            </Form.Item>
            <Form.Item
              name="auto_provision"
              label="Auto-Provision"
              valuePropName="checked"
            >
              <Switch />
            </Form.Item>
          </Space>
        </Form>
      </Modal>

      {/* Webhook Modal */}
      <Modal
        title={editingWh ? "Edit Webhook" : "Add Webhook"}
        open={whModal}
        onOk={handleWhSave}
        onCancel={() => {
          setWhModal(false);
          setTestResult(null);
        }}
        width={600}
      >
        <Form form={whForm} layout="vertical">
          <Form.Item name="name" label="Name" rules={[{ required: true }]}>
            <Input placeholder="e.g., Slack notifications" />
          </Form.Item>
          <Form.Item
            name="url"
            label="URL"
            rules={[{ required: true, type: "url" }]}
          >
            <Input placeholder="https://hooks.slack.com/services/..." />
          </Form.Item>
          <Form.Item name="events" label="Events">
            <Select
              mode="multiple"
              placeholder="All events"
              options={availableEvents.map((e) => ({ value: e, label: e }))}
            />
          </Form.Item>
          <Form.Item name="secret" label="Secret (for HMAC signing)">
            <Input.Password placeholder="Optional signing secret" />
          </Form.Item>
          <Space>
            <Form.Item name="active" label="Active" valuePropName="checked">
              <Switch />
            </Form.Item>
            <Form.Item name="retry_count" label="Retries">
              <InputNumber min={0} max={10} />
            </Form.Item>
            <Form.Item name="timeout_ms" label="Timeout (ms)">
              <InputNumber min={1000} max={30000} step={1000} />
            </Form.Item>
          </Space>
          <Button
            icon={<SendOutlined />}
            onClick={handleTestWebhook}
            loading={testing}
            style={{ marginTop: 8 }}
          >
            Test Webhook
          </Button>
          {testResult && (
            <Card size="small" style={{ marginTop: 8 }}>
              {testResult.success ? (
                <Space>
                  <CheckCircleOutlined style={{ color: "green" }} />
                  Delivered — {testResult.status_code}
                </Space>
              ) : (
                <Space>
                  <CloseCircleOutlined style={{ color: "red" }} />
                  Failed — {testResult.error || testResult.status_code}
                </Space>
              )}
              {testResult.body && (
                <pre style={{ fontSize: 11, maxHeight: 100, overflow: "auto" }}>
                  {testResult.body}
                </pre>
              )}
            </Card>
          )}
        </Form>
      </Modal>
    </Content>
  );
}

export default withRouter(withSidebar(Integrations));
