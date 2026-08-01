import React, { useState, useEffect } from "react";
import {
  Layout,
  Card,
  Switch,
  Input,
  InputNumber,
  Button,
  Table,
  Modal,
  Form,
  Tag,
  message,
  Space,
  Alert,
  Tooltip,
  Spin,
  Descriptions,
} from "antd";
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  PlusOutlined,
  KeyOutlined,
  WarningOutlined,
} from "@ant-design/icons";
import withRouter from "../withRouter";
import withSidebar from "../common/base";
import {
  getFhirConfig,
  updateFhirConfig,
  listFhirClients,
  createFhirClient,
  updateFhirClient,
  deleteFhirClient,
  testFhirConnection,
} from "../api/fhir";
import { PageState } from "../common/PageState";
import "./Fhir.css";

const { Content } = Layout;

function FhirConfig(props: any) {
  let [config, setConfig] = useState<any>(null);
  let [loading, setLoading] = useState(true);
  let [saving, setSaving] = useState(false);
  let [error, setError] = useState<string | null>(null);
  let [clients, setClients] = useState<any[]>([]);
  let [clientsLoading, setClientsLoading] = useState(false);
  let [modalOpen, setModalOpen] = useState(false);
  let [newClient, setNewClient] = useState<any>({
    name: "",
    description: "",
    redirect_uris: "",
  });
  let [secretModal, setSecretModal] = useState<any>(null);
  let [testResult, setTestResult] = useState<any>(null);
  let [testing, setTesting] = useState(false);

  const fetchConfig = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getFhirConfig();
      setConfig(res);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const fetchClients = async () => {
    setClientsLoading(true);
    try {
      const res = await listFhirClients();
      setClients(res);
    } catch {
    } finally {
      setClientsLoading(false);
    }
  };

  useEffect(() => {
    fetchConfig();
    fetchClients();
  }, []);

  const handleToggle = async (checked: boolean) => {
    setSaving(true);
    try {
      const res = await updateFhirConfig({ enabled: String(checked) });
      setConfig(res);
      message.success(`FHIR ${checked ? "enabled" : "disabled"}`);
    } catch (e: any) {
      message.error(e.message);
    } finally {
      setSaving(false);
    }
  };

  const handleSaveConfig = async () => {
    setSaving(true);
    try {
      const res = await updateFhirConfig({
        base_url: config.base_url,
        publisher: config.publisher,
        max_search_results: config.max_search_results,
        log_retention_days: config.log_retention_days,
      });
      setConfig(res);
      message.success("Configuration saved");
    } catch (e: any) {
      message.error(e.message);
    } finally {
      setSaving(false);
    }
  };

  const handleTestConnection = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const res = await testFhirConnection();
      setTestResult(res);
    } catch (e: any) {
      setTestResult({ reachable: false, error: e.message });
    } finally {
      setTesting(false);
    }
  };

  const handleCreateClient = async () => {
    if (!newClient.name.trim()) {
      message.warning("Client name is required");
      return;
    }
    try {
      const res = await createFhirClient(newClient);
      setSecretModal(res);
      setModalOpen(false);
      setNewClient({ name: "", description: "", redirect_uris: "" });
      fetchClients();
    } catch (e: any) {
      message.error(e.message);
    }
  };

  const handleDeactivateClient = async (id: string, active: boolean) => {
    try {
      await updateFhirClient(id, { active });
      message.success(active ? "Client activated" : "Client deactivated");
      fetchClients();
    } catch (e: any) {
      message.error(e.message);
    }
  };

  const handleDeleteClient = (id: string) => {
    Modal.confirm({
      title: "Delete client?",
      content:
        "This action cannot be undone. Integrations using this client will stop working.",
      onOk: async () => {
        try {
          await deleteFhirClient(id);
          message.success("Client deleted");
          fetchClients();
        } catch (e: any) {
          message.error(e.message);
        }
      },
    });
  };

  const clientColumns = [
    { title: "Name", dataIndex: "name", key: "name" },
    {
      title: "Client ID",
      dataIndex: "client_id",
      key: "client_id",
      render: (t: string) => <code>{t}</code>,
    },
    {
      title: "Grant Type",
      dataIndex: "grant_type",
      key: "grant_type",
      render: (t: string) => <Tag>{t}</Tag>,
    },
    {
      title: "Active",
      dataIndex: "active",
      key: "active",
      render: (t: boolean) =>
        t ? <Tag color="green">Active</Tag> : <Tag color="red">Inactive</Tag>,
    },
    {
      title: "Last Used",
      dataIndex: "last_used",
      key: "last_used",
      render: (t: string) => (t ? new Date(t).toLocaleDateString() : "Never"),
    },
    {
      title: "Actions",
      key: "actions",
      render: (_: any, record: any) => (
        <Space>
          {record.active ? (
            <Button
              size="small"
              onClick={() => handleDeactivateClient(record.id, false)}
            >
              Deactivate
            </Button>
          ) : (
            <Button
              size="small"
              onClick={() => handleDeactivateClient(record.id, true)}
            >
              Activate
            </Button>
          )}
          <Button
            size="small"
            danger
            onClick={() => handleDeleteClient(record.id)}
          >
            Delete
          </Button>
        </Space>
      ),
    },
  ];

  if (loading) {
    return (
      <Content className="fhir-config" style={{ padding: 24 }}>
        <Spin size="large" style={{ display: "block", margin: "80px auto" }} />
      </Content>
    );
  }

  if (error) {
    return (
      <Content className="fhir-config" style={{ padding: 24 }}>
        <PageState error={error} onRetry={fetchConfig} />
      </Content>
    );
  }

  return (
    <Content className="fhir-config" style={{ padding: 24 }}>
      {/* Status Banner */}
      <Card style={{ marginBottom: 16 }}>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <Space size="large">
            <span style={{ fontWeight: 600, fontSize: 16 }}>
              FHIR R4 Server
            </span>
            {config?.enabled ? (
              <Tag icon={<CheckCircleOutlined />} color="green">
                Enabled
              </Tag>
            ) : (
              <Tag icon={<CloseCircleOutlined />} color="red">
                Disabled
              </Tag>
            )}
          </Space>
          <Switch
            checked={config?.enabled}
            onChange={handleToggle}
            loading={saving}
          />
        </div>
        {!config?.enabled && (
          <Alert
            style={{ marginTop: 12 }}
            type="warning"
            showIcon
            message="FHIR server is disabled. All FHIR endpoints will return 503. Enable it to allow EHR integrations."
          />
        )}
      </Card>

      {/* Configuration */}
      <Card title="Server Configuration" style={{ marginBottom: 16 }}>
        <Descriptions column={2} size="small">
          <Descriptions.Item label="Base URL">
            <Input
              value={config?.base_url || ""}
              onChange={(e) =>
                setConfig({ ...config, base_url: e.target.value })
              }
              style={{ width: 400 }}
              disabled={saving}
            />
          </Descriptions.Item>
          <Descriptions.Item label="Publisher">
            <Input
              value={config?.publisher || ""}
              onChange={(e) =>
                setConfig({ ...config, publisher: e.target.value })
              }
              style={{ width: 300 }}
              disabled={saving}
            />
          </Descriptions.Item>
          <Descriptions.Item label="Max Search Results">
            <InputNumber
              value={config?.max_search_results}
              min={1}
              max={1000}
              onChange={(v) => setConfig({ ...config, max_search_results: v })}
              disabled={saving}
            />
          </Descriptions.Item>
          <Descriptions.Item label="Log Retention (days)">
            <InputNumber
              value={config?.log_retention_days}
              min={1}
              max={365}
              onChange={(v) => setConfig({ ...config, log_retention_days: v })}
              disabled={saving}
            />
          </Descriptions.Item>
        </Descriptions>
        <Space style={{ marginTop: 12 }}>
          <Button type="primary" onClick={handleSaveConfig} loading={saving}>
            Save
          </Button>
          <Button onClick={handleTestConnection} loading={testing}>
            {testing ? "Testing..." : "Test Connection"}
          </Button>
        </Space>
        {testResult && (
          <Card size="small" style={{ marginTop: 12 }}>
            {testResult.reachable ? (
              <Space>
                <CheckCircleOutlined style={{ color: "green" }} />
                Reachable — FHIR {testResult.fhir_version} (
                {testResult.response_time_ms}ms)
              </Space>
            ) : (
              <Space>
                <CloseCircleOutlined style={{ color: "red" }} />
                Unreachable — {testResult.error} ({testResult.response_time_ms}
                ms)
              </Space>
            )}
          </Card>
        )}
      </Card>

      {/* SMART Clients */}
      <Card
        title={
          <Space>
            <KeyOutlined />
            <span>SMART-on-FHIR Clients</span>
          </Space>
        }
        extra={
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => setModalOpen(true)}
          >
            Register Client
          </Button>
        }
      >
        <Table
          dataSource={clients}
          columns={clientColumns}
          rowKey="id"
          loading={clientsLoading}
          pagination={false}
          locale={{
            emptyText:
              "No clients configured. Register a SMART-on-FHIR client to enable EHR integrations.",
          }}
        />
      </Card>

      {/* Create Client Modal */}
      <Modal
        title="Register SMART-on-FHIR Client"
        open={modalOpen}
        onOk={handleCreateClient}
        onCancel={() => setModalOpen(false)}
      >
        <Form layout="vertical">
          <Form.Item label="Client Name" required>
            <Input
              value={newClient.name}
              onChange={(e) =>
                setNewClient({ ...newClient, name: e.target.value })
              }
              placeholder="e.g., Epic Hyperspace"
            />
          </Form.Item>
          <Form.Item label="Description">
            <Input.TextArea
              value={newClient.description}
              onChange={(e) =>
                setNewClient({ ...newClient, description: e.target.value })
              }
              rows={2}
            />
          </Form.Item>
          <Form.Item label="Redirect URIs">
            <Input.TextArea
              value={newClient.redirect_uris}
              onChange={(e) =>
                setNewClient({ ...newClient, redirect_uris: e.target.value })
              }
              rows={2}
              placeholder="One per line"
            />
          </Form.Item>
        </Form>
      </Modal>

      {/* Secret Modal */}
      <Modal
        title="Client Credentials"
        open={!!secretModal}
        onCancel={() => setSecretModal(null)}
        footer={[
          <Button
            key="copy"
            type="primary"
            onClick={() => {
              navigator.clipboard.writeText(
                `Client ID: ${secretModal?.client_id}\nClient Secret: ${secretModal?.client_secret}`,
              );
              message.success("Copied");
            }}
          >
            Copy Credentials
          </Button>,
          <Button key="close" onClick={() => setSecretModal(null)}>
            Close
          </Button>,
        ]}
      >
        <Alert
          type="warning"
          showIcon
          icon={<WarningOutlined />}
          message="These credentials will not be shown again. Save them now."
          style={{ marginBottom: 12 }}
        />
        <Descriptions column={1} size="small">
          <Descriptions.Item label="Client ID">
            <code>{secretModal?.client_id}</code>
          </Descriptions.Item>
          <Descriptions.Item label="Client Secret">
            <code>{secretModal?.client_secret}</code>
          </Descriptions.Item>
        </Descriptions>
      </Modal>
    </Content>
  );
}

export default withRouter(withSidebar(FhirConfig));
