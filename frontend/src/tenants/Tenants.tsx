import { useDocumentTitle } from "../hooks";
import React, { useState, useEffect } from "react";
import {
  App,
  Layout,
  Card,
  Row,
  Col,
  Tag,
  Progress,
  Button,
  Modal,
  Form,
  Input,
  Popconfirm,
  Space,
  Typography,
  Spin,
  Alert,
} from "antd";
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  UserOutlined,
  DatabaseOutlined,
  HddOutlined,
} from "@ant-design/icons";
import withSidebar from "../common/base";
import {
  listTenants,
  createTenant,
  updateTenant,
  deleteTenant,
  type Tenant,
} from "../api/tenants";
import { PageState } from "../common/PageState";

const { Text, Title } = Typography;
const Content = Layout.Content;

const STATUS_CONFIG: Record<string, { color: string; label: string }> = {
  provisioning: { color: "processing", label: "Provisioning" },
  active: { color: "green", label: "Active" },
  quarantined: { color: "orange", label: "Quarantined" },
  decommissioned: { color: "default", label: "Decommissioned" },
};

function formatBytes(bytes: number): string {
  if (!bytes) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB"];
  let i = 0;
  let val = bytes;
  while (val >= 1024 && i < units.length - 1) {
    val /= 1024;
    i++;
  }
  return `${val.toFixed(1)} ${units[i]}`;
}

function Tenants() {
  const { message } = App.useApp();
  useDocumentTitle("QuantumPACS - Tenants");

  const [data, setData] = useState<Tenant[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [createVisible, setCreateVisible] = useState(false);
  const [editVisible, setEditVisible] = useState(false);
  const [editingTenant, setEditingTenant] = useState<Tenant | null>(null);
  const [createForm] = Form.useForm();
  const [editForm] = Form.useForm();

  useEffect(() => {
    fetch();
  }, []);

  const fetch = () => {
    setLoading(true);
    setError(null);
    listTenants()
      .then((res) => {
        setLoading(false);
        setData(res);
      })
      .catch((e: any) => {
        setLoading(false);
        setError(e.message);
        message.error(e.message);
      });
  };

  const handleProvision = () => {
    createForm
      .validateFields()
      .then((values: any) => {
        const data: any = { name: values.name, slug: values.slug };
        if (values.domain) data.domain = values.domain;
        if (values.storage_quota_gb)
          data.storage_quota_bytes = values.storage_quota_gb * 1073741824;
        createTenant(data)
          .then(() => {
            createForm.resetFields();
            setCreateVisible(false);
            fetch();
          })
          .catch((e: any) => {
            message.error(e.message);
          });
      })
      .catch(() => {});
  };

  const handleEdit = (tenant: any) => {
    setEditingTenant(tenant);
    editForm.setFieldsValue({
      name: tenant.name,
      domain: tenant.domain,
      storage_quota_gb: tenant.storage_quota_bytes
        ? Math.round(tenant.storage_quota_bytes / 1073741824)
        : undefined,
    });
    setEditVisible(true);
  };

  const handleUpdate = () => {
    if (!editingTenant) return;
    editForm
      .validateFields()
      .then((values: any) => {
        const data: any = {};
        if (values.name !== editingTenant.name) data.name = values.name;
        if (values.domain !== editingTenant.domain)
          data.domain = values.domain || null;
        const newQuota = values.storage_quota_gb
          ? values.storage_quota_gb * 1073741824
          : null;
        if (newQuota !== editingTenant.storage_quota_bytes)
          data.storage_quota_bytes = newQuota;
        if (Object.keys(data).length === 0) {
          setEditVisible(false);
          return;
        }
        updateTenant(editingTenant.id, data)
          .then(() => {
            setEditingTenant(null);
            setEditVisible(false);
            fetch();
          })
          .catch((e: any) => {
            message.error(e.message);
          });
      })
      .catch(() => {});
  };

  const handleDecommission = (tenant: any) => {
    deleteTenant(tenant.id)
      .then(() => {
        fetch();
      })
      .catch((e: any) => {
        message.error(e.message);
      });
  };

  const storageBarColor = (pct: number) => {
    if (pct > 75) return "#ef4444";
    if (pct > 50) return "#f59e0b";
    return "#22c55e";
  };

  return (
    <Content style={{ padding: 50 }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          marginBottom: 16,
          alignItems: "center",
        }}
      >
        <Title level={4} style={{ margin: 0 }}>
          Tenants
        </Title>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => {
            createForm.resetFields();
            setCreateVisible(true);
          }}
        >
          Provision Tenant
        </Button>
      </div>
      <PageState
        error={error}
        onRetry={() => fetch()}
        empty={!loading && !error && data.length === 0}
        emptyMessage="No tenants provisioned"
        emptyAction={
          <Button
            type="primary"
            onClick={() => {
              createForm.resetFields();
              setCreateVisible(true);
            }}
          >
            Provision Tenant
          </Button>
        }
      >
        <Row gutter={[16, 16]}>
          {data.map((tenant) => {
            const statusCfg = STATUS_CONFIG[tenant.status ?? "active"] || {
              color: "default",
              label: tenant.status || "Unknown",
            };
            const isDecommissioned = tenant.status === "decommissioned";
            const isProvisioning = tenant.status === "provisioning";
            const isQuarantined = tenant.status === "quarantined";
            const usedBytes = tenant.storage_used_bytes || 0;
            const quotaBytes = tenant.storage_quota_bytes || 0;
            const pct = quotaBytes
              ? Math.min(100, Math.round((usedBytes / quotaBytes) * 100))
              : 0;

            return (
              <Col xs={24} sm={12} lg={8} xl={6} key={tenant.id}>
                <Card
                  style={{
                    opacity: isDecommissioned ? 0.5 : 1,
                    borderLeft: isQuarantined ? "3px solid #faad14" : undefined,
                  }}
                  actions={
                    isDecommissioned
                      ? undefined
                      : [
                          <Button
                            type="link"
                            size="small"
                            icon={<EditOutlined />}
                            onClick={() => handleEdit(tenant)}
                            disabled={isProvisioning || isQuarantined}
                          >
                            Edit
                          </Button>,
                          <Popconfirm
                            title="Decommission this tenant?"
                            description="Data will be retained for 90 days per retention policy. This action is not reversible without manual DBA intervention."
                            onConfirm={() => handleDecommission(tenant)}
                            disabled={isProvisioning}
                          >
                            <Button
                              type="link"
                              size="small"
                              danger
                              icon={<DeleteOutlined />}
                              disabled={isProvisioning}
                            >
                              Decommission
                            </Button>
                          </Popconfirm>,
                        ]
                  }
                >
                  {isQuarantined && (
                    <Alert
                      type="warning"
                      message="Suspicious activity detected — tenant is read-only"
                      style={{
                        marginBottom: 12,
                        fontSize: 12,
                        padding: "4px 8px",
                      }}
                      showIcon
                    />
                  )}
                  {isProvisioning ? (
                    <Spin
                      tip="Provisioning database..."
                      style={{
                        display: "block",
                        textAlign: "center",
                        padding: "24px 0",
                      }}
                    >
                      <div style={{ padding: 24 }} />
                    </Spin>
                  ) : (
                    <>
                      <div style={{ marginBottom: 8 }}>
                        <Text strong style={{ fontSize: 16 }}>
                          {tenant.name}
                        </Text>
                        <Tag style={{ marginLeft: 6, fontSize: 10 }}>
                          {tenant.slug}
                        </Tag>
                      </div>
                      {tenant.domain && (
                        <div style={{ marginBottom: 8 }}>
                          <Text type="secondary" style={{ fontSize: 12 }}>
                            {tenant.domain}
                          </Text>
                        </div>
                      )}
                      <div style={{ marginBottom: 8 }}>
                        <Tag color={statusCfg.color}>{statusCfg.label}</Tag>
                      </div>
                      {quotaBytes > 0 && (
                        <div style={{ marginBottom: 8 }}>
                          <div
                            style={{
                              display: "flex",
                              justifyContent: "space-between",
                              fontSize: 12,
                              marginBottom: 2,
                            }}
                          >
                            <Text type="secondary" style={{ fontSize: 11 }}>
                              <HddOutlined style={{ marginRight: 4 }} />
                              {formatBytes(usedBytes)} /{" "}
                              {formatBytes(quotaBytes)}
                            </Text>
                            <Text
                              style={{
                                fontSize: 11,
                                color: storageBarColor(pct),
                              }}
                            >
                              {pct}%
                            </Text>
                          </div>
                          <Progress
                            percent={pct}
                            size="small"
                            strokeColor={storageBarColor(pct)}
                            showInfo={false}
                          />
                        </div>
                      )}
                      <div
                        style={{
                          display: "flex",
                          gap: 12,
                          fontSize: 12,
                          color: "#888",
                        }}
                      >
                        <span>
                          <UserOutlined style={{ marginRight: 4 }} />
                          {tenant.user_count ?? "?"} users
                        </span>
                        <span>
                          <DatabaseOutlined style={{ marginRight: 4 }} />
                          {tenant.study_count ?? "?"} studies
                        </span>
                      </div>
                    </>
                  )}
                </Card>
              </Col>
            );
          })}
        </Row>
      </PageState>

      <Modal
        title="Provision Tenant"
        open={createVisible}
        onCancel={() => setCreateVisible(false)}
        onOk={handleProvision}
        okText="Provision"
      >
        <Form form={createForm} layout="vertical">
          <Form.Item
            name="name"
            label="Tenant Name"
            rules={[{ required: true }]}
          >
            <Input placeholder="e.g., Memorial Hospital West" />
          </Form.Item>
          <Form.Item name="slug" label="Slug" rules={[{ required: true }]}>
            <Input placeholder="e.g., memorial-west" />
          </Form.Item>
          <Form.Item name="domain" label="Custom Domain">
            <Input placeholder="e.g., pacs.memorialwest.com" />
          </Form.Item>
          <Form.Item name="storage_quota_gb" label="Storage Quota (GB)">
            <Input type="number" placeholder="Leave empty for system default" />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="Edit Tenant"
        open={editVisible}
        onCancel={() => {
          setEditingTenant(null);
          setEditVisible(false);
        }}
        onOk={handleUpdate}
        okText="Save"
      >
        <Form form={editForm} layout="vertical">
          <Form.Item
            name="name"
            label="Tenant Name"
            rules={[{ required: true }]}
          >
            <Input />
          </Form.Item>
          <Form.Item name="domain" label="Custom Domain">
            <Input placeholder="Leave empty to clear" />
          </Form.Item>
          <Form.Item name="storage_quota_gb" label="Storage Quota (GB)">
            <Input type="number" placeholder="Current: unchanged" />
          </Form.Item>
        </Form>
      </Modal>
    </Content>
  );
}

export default withSidebar(Tenants);
