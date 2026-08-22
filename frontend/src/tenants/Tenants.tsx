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
  Select,
  Drawer,
  Table,
  Popconfirm,
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
  BarChartOutlined,
  PauseCircleOutlined,
  PlayCircleOutlined,
  ExclamationCircleOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  CopyOutlined,
} from "@ant-design/icons";
import withSidebar from "../common/base";
import {
  listTenants,
  createTenant,
  updateTenant,
  deleteTenant,
  getTenantHealth,
  getTenantUsage,
  type Tenant,
  type TenantUsageRow,
} from "../api/tenants";
import { PageState } from "../common/PageState";
import RequirePermission from "../auth/RequirePermission";
import { useAuth } from "../auth/AuthContext";

const { Text, Title } = Typography;
const Content = Layout.Content;

const STATUS_CONFIG: Record<string, { color: string; label: string }> = {
  provisioning: { color: "processing", label: "Provisioning" },
  active: { color: "green", label: "Active" },
  suspended: { color: "gold", label: "Suspended" },
  quarantined: { color: "orange", label: "Quarantined" },
  decommissioned: { color: "default", label: "Decommissioned" },
};

const PLAN_COLORS: Record<string, string> = {
  free: "default",
  pro: "blue",
  growth: "cyan",
  enterprise: "purple",
};

const PLAN_OPTIONS = ["free", "pro", "growth", "enterprise"];

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

// One-time panel after provisioning: the admin password exists only in the
// create response, so it must be copied here or never seen again.
function AdminPasswordPanel({
  password,
  slug,
  onDone,
}: {
  password: string;
  slug: string;
  onDone: () => void;
}) {
  const { message } = App.useApp();
  return (
    <Modal
      open
      title="Tenant Admin Credentials"
      footer={null}
      closable={false}
      maskClosable={false}
    >
      <div style={{ marginBottom: 16 }}>
        <Text>
          Tenant <Text strong>{slug}</Text> was provisioned. Share the admin
          password below with the tenant administrator.
        </Text>
      </div>
      <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
        <code
          style={{
            fontSize: 14,
            background: "#f5f5f5",
            padding: "4px 8px",
            borderRadius: 4,
          }}
        >
          {password}
        </code>
        <Button
          size="small"
          icon={<CopyOutlined />}
          onClick={() => {
            navigator.clipboard.writeText(password);
            message.success("Password copied");
          }}
        >
          Copy
        </Button>
      </div>
      <Text
        type="secondary"
        style={{ display: "block", marginTop: 12, fontSize: 12 }}
      >
        This password will not be shown again.
      </Text>
      <Button type="primary" block style={{ marginTop: 16 }} onClick={onDone}>
        I saved it
      </Button>
    </Modal>
  );
}

function Tenants() {
  const { message } = App.useApp();
  useDocumentTitle("QuantumPACS - Tenants");
  const { hasPermission } = useAuth();

  // TENANT_READ gates the page; provisioning, editing, lifecycle changes
  // and decommissioning all hit TENANT_ADMIN endpoints (backend guards).
  const canAdmin = hasPermission("TENANT_ADMIN");

  const [data, setData] = useState<Tenant[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [createVisible, setCreateVisible] = useState(false);
  const [editVisible, setEditVisible] = useState(false);
  const [editingTenant, setEditingTenant] = useState<Tenant | null>(null);
  const [createForm] = Form.useForm();
  const [editForm] = Form.useForm();
  const [provisionPassword, setProvisionPassword] = useState<{
    password: string;
    slug: string;
  } | null>(null);

  // Health probes are optional: fetch once, map by slug, and never let a
  // failure (404 before the endpoint lands) block the tenant list.
  const [health, setHealth] = useState<Record<string, { status: string }>>({});

  const [usageTenant, setUsageTenant] = useState<Tenant | null>(null);
  const [usageRows, setUsageRows] = useState<TenantUsageRow[]>([]);
  const [usageLoading, setUsageLoading] = useState(false);

  useEffect(() => {
    fetch();
    getTenantHealth()
      .then(setHealth)
      .catch(() => {});
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
        if (values.admin_email) data.admin_email = values.admin_email;
        if (values.plan) data.plan = values.plan;
        if (values.storage_quota_gb)
          data.storage_quota_bytes = values.storage_quota_gb * 1073741824;
        createTenant(data)
          .then((res: any) => {
            createForm.resetFields();
            setCreateVisible(false);
            fetch();
            // admin_password is returned exactly once; surface it before
            // anything else can steal the user's attention.
            if (res?.admin_password) {
              setProvisionPassword({
                password: res.admin_password,
                slug: values.slug,
              });
            }
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

  // Status transitions are plain PUT /tenants/{id} updates: suspended →
  // active → quarantined round-trips through the same patch endpoint.
  const handleStatusChange = (tenant: Tenant, status: string) => {
    updateTenant(tenant.id, { status })
      .then(() => {
        fetch();
      })
      .catch((e: any) => {
        message.error(e.message);
      });
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

  const openUsage = (tenant: Tenant) => {
    setUsageTenant(tenant);
    setUsageRows([]);
    setUsageLoading(true);
    getTenantUsage(tenant.id)
      .then(setUsageRows)
      .catch((e: any) => {
        message.error(e.message);
      })
      .finally(() => setUsageLoading(false));
  };

  const storageBarColor = (pct: number) => {
    if (pct > 75) return "#ef4444";
    if (pct > 50) return "#f59e0b";
    return "#22c55e";
  };

  const healthStatus = (tenant: Tenant): string | undefined =>
    health[tenant.slug || ""]?.status || health[tenant.id]?.status;

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
        <RequirePermission permission="TENANT_ADMIN">
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
        </RequirePermission>
      </div>
      <PageState
        error={error}
        onRetry={() => fetch()}
        empty={!loading && !error && data.length === 0}
        emptyMessage="No tenants provisioned"
        emptyAction={
          <RequirePermission permission="TENANT_ADMIN">
            <Button
              type="primary"
              onClick={() => {
                createForm.resetFields();
                setCreateVisible(true);
              }}
            >
              Provision Tenant
            </Button>
          </RequirePermission>
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
            const isSuspended = tenant.status === "suspended";
            const usedBytes = tenant.storage_used_bytes || 0;
            const quotaBytes = tenant.storage_quota_bytes || 0;
            const pct = quotaBytes
              ? Math.min(100, Math.round((usedBytes / quotaBytes) * 100))
              : 0;
            const hStatus = healthStatus(tenant);
            const statusPopconfirm = (
              target: string,
              label: string,
              title: string,
              desc: string,
            ) => (
              <Popconfirm
                key={target}
                title={title}
                description={desc}
                onConfirm={() => handleStatusChange(tenant, target)}
              >
                <Button type="link" size="small">
                  {label}
                </Button>
              </Popconfirm>
            );
            const lifecycleActions: React.ReactNode[] = [];
            if (canAdmin && !isProvisioning && !isDecommissioned) {
              if (isSuspended || isQuarantined) {
                lifecycleActions.push(
                  statusPopconfirm(
                    "active",
                    "Activate",
                    `Activate ${tenant.name}?`,
                    "Restores full access for this tenant.",
                  ),
                );
              } else {
                lifecycleActions.push(
                  statusPopconfirm(
                    "suspended",
                    "Suspend",
                    `Suspend ${tenant.name}?`,
                    "Tenant users will be blocked from all scoped requests.",
                  ),
                );
                lifecycleActions.push(
                  statusPopconfirm(
                    "quarantined",
                    "Quarantine",
                    `Quarantine ${tenant.name}?`,
                    "Suspicious activity detected — tenant becomes read-only.",
                  ),
                );
              }
            }

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
                          ...(canAdmin
                            ? [
                                <Button
                                  type="link"
                                  size="small"
                                  icon={<EditOutlined />}
                                  onClick={() => handleEdit(tenant)}
                                  disabled={isProvisioning || isQuarantined}
                                  key="edit"
                                >
                                  Edit
                                </Button>,
                              ]
                            : []),
                          <Button
                            type="link"
                            size="small"
                            icon={<BarChartOutlined />}
                            onClick={() => openUsage(tenant)}
                            disabled={isProvisioning}
                            key="usage"
                          >
                            Usage
                          </Button>,
                          ...lifecycleActions,
                          ...(canAdmin
                            ? [
                                <Popconfirm
                                  key="decommission"
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
                            : []),
                        ]
                  }
                >
                  {isQuarantined && (
                    <Alert
                      type="warning"
                      title="Suspicious activity detected — tenant is read-only"
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
                      description="Provisioning database..."
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
                        {hStatus ? (
                          hStatus === "ok" || hStatus === "healthy" ? (
                            <CheckCircleOutlined
                              style={{ color: "#22c55e", marginLeft: 6 }}
                              aria-label="Healthy"
                            />
                          ) : (
                            <CloseCircleOutlined
                              style={{ color: "#ef4444", marginLeft: 6 }}
                              aria-label="Unhealthy"
                            />
                          )
                        ) : null}
                        {tenant.plan && (
                          <Tag
                            color={PLAN_COLORS[tenant.plan] || "default"}
                            style={{ marginLeft: 6, fontSize: 10 }}
                          >
                            {tenant.plan}
                          </Tag>
                        )}
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
                          flexWrap: "wrap",
                        }}
                      >
                        <span>
                          <UserOutlined style={{ marginRight: 4 }} />
                          {tenant.user_count ?? "—"} users
                        </span>
                        <span>
                          <DatabaseOutlined style={{ marginRight: 4 }} />
                          {tenant.study_count ?? "—"} studies
                        </span>
                      </div>
                      {tenant.last_activity && (
                        <div
                          style={{ fontSize: 11, color: "#aaa", marginTop: 6 }}
                        >
                          Last activity:{" "}
                          {new Date(tenant.last_activity).toLocaleString()}
                        </div>
                      )}
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
          <Form.Item name="admin_email" label="Admin Email">
            <Input placeholder="e.g., admin@memorialwest.com" />
          </Form.Item>
          <Form.Item name="plan" label="Plan" initialValue="free">
            <Select
              options={PLAN_OPTIONS.map((p) => ({ value: p, label: p }))}
            />
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

      <Drawer
        title={`Usage — ${usageTenant?.name || ""}`}
        open={usageTenant !== null}
        onClose={() => setUsageTenant(null)}
        size={480}
      >
        <Table
          rowKey="date"
          size="small"
          loading={usageLoading}
          pagination={false}
          dataSource={usageRows}
          columns={[
            { title: "Date", dataIndex: "date" },
            { title: "API calls", dataIndex: "api_calls", align: "right" },
            {
              title: "MWL queries",
              dataIndex: "mwl_queries",
              align: "right",
              render: (v?: number) => v ?? 0,
            },
            {
              title: "Notifications",
              dataIndex: "notifications",
              align: "right",
              render: (v?: number) => v ?? 0,
            },
          ]}
          locale={{ emptyText: "No usage data for this tenant" }}
        />
      </Drawer>

      {provisionPassword && (
        <AdminPasswordPanel
          password={provisionPassword.password}
          slug={provisionPassword.slug}
          onDone={() => setProvisionPassword(null)}
        />
      )}
    </Content>
  );
}

export default withSidebar(Tenants);
