import { useDocumentTitle } from "../hooks";
import React, { useState, useEffect, useMemo } from "react";
import {
  App,
  Layout,
  Table,
  Button,
  Tag,
  Modal,
  Form,
  Input,
  Popconfirm,
  Alert,
  Checkbox,
  Switch,
  Space,
  Typography,
} from "antd";
import {
  DeleteOutlined,
  CopyOutlined,
  ReloadOutlined,
} from "@ant-design/icons";
import withSidebar from "../common/base";
import PageHeader from "../common/PageHeader";
import { PageState } from "../common/PageState";
import RequirePermission from "../auth/RequirePermission";
import { useAuth } from "../auth/AuthContext";
import { listApiKeys, createApiKey, deleteApiKey } from "../api/servicekeys";

const Content = Layout.Content;

const PERMISSION_GROUPS: Record<string, string[]> = {
  Files: ["FILE_READ", "FILE_WRITE", "FILE_DELETE"],
  Patients: ["PATIENT_READ", "PATIENT_WRITE"],
  Studies: ["STUDY_READ", "STUDY_WRITE"],
  Users: ["USER_READ", "USER_WRITE", "USER_DELETE", "USER_ADMIN"],
  Replicas: ["REPLICA_READ", "REPLICA_WRITE", "REPLICA_DELETE"],
  Tenants: ["TENANT_READ", "TENANT_WRITE", "TENANT_ADMIN"],
  Roles: ["ROLE_READ", "ROLE_WRITE", "ROLE_DELETE"],
  "Service Keys": [
    "SERVICE_KEY_READ",
    "SERVICE_KEY_WRITE",
    "SERVICE_KEY_DELETE",
  ],
  Worklist: ["WORKLIST_READ", "WORKLIST_WRITE"],
  DICOMweb: ["DICOMWEB_READ", "DICOMWEB_WRITE"],
  Routing: ["ROUTING_READ", "ROUTING_WRITE"],
  Logs: ["LOG_READ"],
  Metrics: ["METRICS_READ"],
};

const ALL_PERMISSIONS = Object.values(PERMISSION_GROUPS).flat();

function ExpiryStatus({ expiresAt }: { expiresAt: string | null }) {
  if (!expiresAt) return <Tag>Permanent</Tag>;
  const ms = new Date(expiresAt).getTime() - Date.now();
  const days = ms / 86400000;
  if (ms <= 0) return <Tag color="default">Expired</Tag>;
  if (days <= 1) return <Tag color="red">≤1 day</Tag>;
  if (days <= 7) return <Tag color="orange">≤7 days</Tag>;
  return <Tag color="green">{Math.ceil(days)} days</Tag>;
}

function LastUsed({ at }: { at: string | null }) {
  if (!at) return <Typography.Text type="secondary">Never</Typography.Text>;
  const ms = Date.now() - new Date(at).getTime();
  const mins = Math.floor(ms / 60000);
  if (mins < 1) return "<1m ago";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days}d ago`;
  return new Date(at).toLocaleDateString();
}

function ServiceKeys() {
  const { message } = App.useApp();
  useDocumentTitle("QuantumPACS - Service Keys");
  const { hasPermission, user } = useAuth();

  // SERVICE_KEY_READ gates the page; issuing keys needs SERVICE_KEY_WRITE and
  // revoking needs SERVICE_KEY_DELETE (backend /api/api-keys guards match).
  const canWrite = hasPermission("SERVICE_KEY_WRITE");
  const canDelete = hasPermission("SERVICE_KEY_DELETE");

  // Mirror of api/api_keys.py _validate_key_permissions: a non-platform admin
  // may only issue a key with permissions from their own effective grant set.
  // The picker hides everything the operator could not actually grant.
  const grantablePermissions = useMemo(() => {
    if (user?.admin) return ALL_PERMISSIONS;
    const owned = new Set(user?.permissions ?? []);
    return ALL_PERMISSIONS.filter((p) => owned.has(p));
  }, [user]);

  const grantableGroups = useMemo(
    () =>
      Object.entries(PERMISSION_GROUPS)
        .map(([group, perms]) => [
          group,
          perms.filter((p) => grantablePermissions.includes(p)),
        ])
        .filter(([, perms]) => perms.length > 0) as [string, string[]][],
    [grantablePermissions],
  );

  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [visible, setVisible] = useState(false);
  const [rawKey, setRawKey] = useState<string | null>(null);
  const [showRevoked, setShowRevoked] = useState(false);
  const [form] = Form.useForm();

  const filteredData = useMemo(
    () => (showRevoked ? data : data.filter((r) => r.is_active)),
    [data, showRevoked],
  );

  const columns: any[] = [
    {
      title: "Name",
      key: "name",
      width: "18%",
      render: (_: any, r: any) => (
        <Space orientation="vertical" size={0}>
          <span>{r.name}</span>
          <Typography.Text type="secondary" style={{ fontSize: 12 }}>
            {r.prefix}
          </Typography.Text>
        </Space>
      ),
    },
    {
      title: "Permissions",
      dataIndex: "permissions",
      width: "24%",
      render: (perms: string[]) =>
        perms?.length ? (
          <Space wrap size={[2, 2]}>
            {perms.map((p) => (
              <Tag key={p} style={{ fontSize: 11 }}>
                {p}
              </Tag>
            ))}
          </Space>
        ) : (
          <Typography.Text type="secondary">None</Typography.Text>
        ),
    },
    {
      title: "Created",
      dataIndex: "created_at",
      width: "12%",
      render: (d: string) => new Date(d).toLocaleDateString(),
    },
    {
      title: "Last Used",
      dataIndex: "last_used_at",
      width: "12%",
      render: (d: string | null) => <LastUsed at={d} />,
    },
    {
      title: "Expiry",
      dataIndex: "expires_at",
      width: "12%",
      render: (d: string | null) => <ExpiryStatus expiresAt={d} />,
    },
    {
      title: "Status",
      dataIndex: "is_active",
      width: "10%",
      render: (active: boolean, r: any) =>
        !r.enabled ? (
          <Tag color="red">Revoked</Tag>
        ) : active ? (
          <Tag color="green">Active</Tag>
        ) : (
          <Tag color="default">Expired</Tag>
        ),
    },
    {
      title: "Action",
      key: "action",
      width: "12%",
      render: (_: any, record: any) =>
        canDelete && record.enabled ? (
          <Popconfirm
            title="Revoke this key?"
            description="Active integrations using this key may be affected."
            onConfirm={() => handleRevoke(record.id)}
          >
            <Button type="link" danger icon={<DeleteOutlined />} size="small">
              Revoke
            </Button>
          </Popconfirm>
        ) : null,
    },
  ];

  useEffect(() => {
    fetch();
  }, []);

  const fetch = () => {
    setLoading(true);
    setError(null);
    listApiKeys()
      .then((res) => {
        setLoading(false);
        setData(Array.isArray(res) ? res : []);
      })
      .catch((e: any) => {
        setLoading(false);
        setError(e.message);
        message.error(e.message);
      });
  };

  const handleGenerate = () => {
    form
      .validateFields()
      .then((values: any) => {
        createApiKey(values)
          .then((res) => {
            form.resetFields();
            setRawKey(res.raw_key);
            setVisible(false);
            fetch();
          })
          .catch((e: any) => {
            message.error(e.message);
          });
      })
      .catch(() => {});
  };

  const handleRevoke = (id: string) => {
    deleteApiKey(id)
      .then(() => {
        fetch();
      })
      .catch((e: any) => {
        message.error(e.message);
      });
  };

  const copyKey = () => {
    if (rawKey) {
      navigator.clipboard.writeText(rawKey);
      message.success("Key copied to clipboard");
    }
  };

  return (
    <Content style={{ padding: 24 }}>
      <PageHeader
        title="Service Keys"
        description="Issue and revoke API credentials for external integrations (RIS, EMR, modalities)."
        extra={
          <Space>
            <RequirePermission permission="SERVICE_KEY_WRITE">
              <Button
                type="primary"
                onClick={() => {
                  setRawKey(null);
                  setVisible(true);
                }}
              >
                Generate Key
              </Button>
            </RequirePermission>
            <Button icon={<ReloadOutlined />} onClick={fetch}>
              Refresh
            </Button>
            <span style={{ fontSize: 12 }}>Show revoked</span>
            <Switch checked={showRevoked} onChange={setShowRevoked} />
          </Space>
        }
      />

      {rawKey && (
        <Alert
          type="success"
          showIcon
          closable
          style={{ marginBottom: 16 }}
          onClose={() => setRawKey(null)}
          message={
            <span>
              Key generated:{" "}
              <code
                style={{
                  fontSize: 14,
                  background: "#f5f5f5",
                  padding: "2px 8px",
                  borderRadius: 4,
                }}
              >
                {rawKey}
              </code>
              <Button
                type="link"
                icon={<CopyOutlined />}
                onClick={copyKey}
                style={{ marginLeft: 8 }}
              >
                Copy
              </Button>
            </span>
          }
          description="This key will not be shown again. Copy it now."
        />
      )}

      <PageState
        loading={loading}
        error={error}
        onRetry={fetch}
        empty={!loading && !error && filteredData.length === 0}
        emptyMessage="No service keys — generate one to issue credentials."
      >
        <Table rowKey="id" columns={columns} dataSource={filteredData} />
      </PageState>

      <Modal
        title="Generate New API Key"
        open={visible}
        onCancel={() => {
          form.resetFields();
          setVisible(false);
        }}
        onOk={handleGenerate}
        okText="Generate"
        width={520}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="Name" rules={[{ required: true }]}>
            <Input placeholder="e.g., RIS Integration" />
          </Form.Item>
          <Form.Item
            name="service_name"
            label="Service Name"
            rules={[{ required: true }]}
          >
            <Input placeholder="e.g., RIS-App" />
          </Form.Item>
          <Form.Item name="expires_in_days" label="Expires In (days)">
            <Input type="number" placeholder="Leave empty for no expiry" />
          </Form.Item>
          <Form.Item name="permissions" label="Permissions" initialValue={[]}>
            <Checkbox.Group>
              <Space orientation="vertical" style={{ width: "100%" }}>
                {grantableGroups.map(([group, perms]) => (
                  <div key={group}>
                    <Typography.Text strong style={{ fontSize: 12 }}>
                      {group}
                    </Typography.Text>
                    <div style={{ paddingLeft: 12 }}>
                      {perms.map((p) => (
                        <Checkbox
                          key={p}
                          value={p}
                          style={{ marginRight: 8, fontSize: 12 }}
                        >
                          {p}
                        </Checkbox>
                      ))}
                    </div>
                  </div>
                ))}
              </Space>
            </Checkbox.Group>
            {!user?.admin && (
              <Typography.Text type="secondary" style={{ fontSize: 11 }}>
                Only permissions you hold can be granted to a key.
              </Typography.Text>
            )}
          </Form.Item>
        </Form>
      </Modal>
    </Content>
  );
}

export default withSidebar(ServiceKeys);
