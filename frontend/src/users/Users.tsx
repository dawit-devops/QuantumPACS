import { useDocumentTitle } from "../hooks";
import React, { useState, useEffect } from "react";
import {
  App,
  Layout,
  Table,
  Tag,
  Divider,
  Popconfirm,
  Modal,
  Select,
  Tooltip,
  Button,
  Space,
  Typography,
} from "antd";
import { InfoCircleOutlined, CopyOutlined } from "@ant-design/icons";
import { useAuth } from "../auth/AuthContext";

const { Text } = Typography;
import withSidebar from "../common/base";
import {
  listUsers,
  assignRole,
  deactivateUser,
  resetPassword,
  type User,
} from "../api/users";
import { listRoles, type Role } from "../api/roles";
import { PageState } from "../common/PageState";
import PageHeader from "../common/PageHeader";
import RequirePermission from "../auth/RequirePermission";
import { AddUser } from "./EditUser";
import { BulkImport } from "./BulkImport";

const Content = Layout.Content;

function Users() {
  const { message } = App.useApp();
  useDocumentTitle("QuantumPACS - Users");
  const { hasPermission } = useAuth();

  // USER_READ gates the page (route); every mutating control — role change,
  // reset password, deactivate, create — is a USER_WRITE action and is hidden
  // for read-only holders (backend /api/users guards match).
  const canWrite = hasPermission("USER_WRITE");

  const [data, setData] = useState<User[]>([]);
  const [pagination, setPagination] = useState<any>({
    current: 1,
    pageSize: 10,
    total: 0,
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [password, setPassword] = useState<string | null>(null);
  const [roles, setRoles] = useState<Role[]>([]);
  const [changingRole, setChangingRole] = useState<{
    userId: number;
    roleId: number | null;
  } | null>(null);

  useEffect(() => {
    listRoles()
      .then(setRoles)
      .catch(() => {});
  }, []);

  const columns: any[] = [
    {
      title: "ID",
      dataIndex: "id",
      sorter: true,
      width: "8%",
    },
    {
      title: "Username",
      dataIndex: "username",
      sorter: true,
      width: "18%",
    },
    {
      title: "Role",
      dataIndex: "role_name",
      render: (name: string, record: any) => {
        if (!name) return null;
        return (
          <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
            <Select
              value={record.role_id}
              style={{ width: 160 }}
              onChange={(roleId) => handleRoleChange(record.id, roleId)}
              options={roles.map((r: any) => ({ value: r.id, label: r.name }))}
              size="small"
              loading={changingRole?.userId === record.id}
              disabled={changingRole?.userId === record.id || !canWrite}
              aria-label={`Change role for ${record.username}`}
            />
            <Tooltip
              title={`Role: ${name}\nPermissions: ${roles.find((r: any) => r.id === record.role_id)?.permissions?.join(", ") || "N/A"}`}
            >
              <InfoCircleOutlined
                style={{
                  color: "var(--text-secondary, #94a3b8)",
                  cursor: "pointer",
                }}
              />
            </Tooltip>
          </span>
        );
      },
    },
    {
      title: "Tenant",
      dataIndex: "tenant",
      width: "14%",
      render: (t: string | null) =>
        t ? <Tag color="blue">{t}</Tag> : <Text type="secondary">—</Text>,
    },
    {
      title: "Admin",
      dataIndex: "admin",
      render: (is_admin: boolean) => {
        const string = is_admin ? "admin" : "user";
        const color = is_admin ? "success" : "geekblue";
        return <Tag color={color}>{string.toUpperCase()}</Tag>;
      },
    },
    {
      title: "Status",
      dataIndex: "status",
      render: (s: string) => {
        const color = s === "active" ? "success" : "gray";
        return <Tag color={color}>{s.toUpperCase()}</Tag>;
      },
    },
    {
      title: "Action",
      key: "action",
      render: (_: any, record: any) => {
        if (!canWrite || record.status !== "active") return null;
        return (
          <span>
            <a onClick={() => handleResetPassword(record.id)}>Reset password</a>
            <Divider orientation="vertical" />
            <Popconfirm
              title="Sure to deactivate?"
              onConfirm={() => deactivate(record.id)}
            >
              <a>Deactivate</a>
            </Popconfirm>
          </span>
        );
      },
    },
  ];

  useEffect(() => {
    fetch();
  }, []);

  const handleTableChange = (pag: any, _filters: any, _sorter: any) => {
    setPagination(Object.assign({}, pag, { current: pag.current }));
    fetch({
      offset: (pag.current - 1) * pag.pageSize,
      limit: pag.pageSize,
    });
  };

  const fetch = (params?: { offset?: number; limit?: number }) => {
    setLoading(true);
    setError(null);
    // Explicit 1st-page size keeps dataSource length aligned with pageSize, so
    // antd's pagination heuristic (length < total && length > pageSize) never
    // fires on the initial unfiltered load.
    listUsers(params || { offset: 0, limit: 10 })
      .then((res) => {
        const pager = Object.assign({}, pagination, { total: res.total });
        setLoading(false);
        setData(res.data);
        setPagination(pager);
      })
      .catch((e: any) => {
        setLoading(false);
        setError(e.message);
        message.error(e.message);
      });
  };

  const handleRoleChange = (userId: number, roleId: number) => {
    setChangingRole({ userId, roleId });
    assignRole(userId, roleId)
      .then(() => {
        setChangingRole(null);
        fetch();
      })
      .catch((e: any) => {
        setChangingRole(null);
        message.error(e.message);
      });
  };

  const deactivate = (id: number) => {
    // Same error surfacing as role changes; the table refetches on success.
    deactivateUser(id)
      .then(() => fetch())
      .catch((e: any) => message.error(e.message));
  };

  const handleResetPassword = (id: number) => {
    resetPassword(id).then((res) => {
      setPassword(res.password);
    });
  };

  return (
    <Content style={{ padding: 24 }}>
      <PageHeader
        title="Users"
        description="User accounts and role assignments."
        extra={
          <RequirePermission permission="USER_WRITE">
            <div style={{ display: "flex", gap: 8 }}>
              <AddUser reload={fetch} />
              <BulkImport reload={fetch} />
            </div>
          </RequirePermission>
        }
      />
      <Modal
        open={password !== null}
        footer={null}
        onCancel={() => setPassword(null)}
        title="Password Reset"
      >
        <div style={{ marginBottom: 16 }}>
          <Text>New password for this user:</Text>
        </div>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <code
            style={{
              fontSize: 16,
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
              navigator.clipboard.writeText(password || "");
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
          Share this password with the user. It will not be shown again.
        </Text>
      </Modal>
      <PageState
        error={error}
        onRetry={() => fetch()}
        empty={!loading && !error && data.length === 0}
        emptyMessage="No users found"
        emptyAction={
          <RequirePermission permission="USER_WRITE">
            <AddUser reload={fetch} />
          </RequirePermission>
        }
      >
        <Table
          scroll={{ x: 600 }}
          columns={columns}
          rowKey={(record: any) => record.id}
          dataSource={data}
          pagination={pagination}
          loading={loading}
          onChange={handleTableChange}
        />
      </PageState>
    </Content>
  );
}

export default withSidebar(Users);
