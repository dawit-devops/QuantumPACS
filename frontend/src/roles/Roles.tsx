import { useDocumentTitle } from "../hooks";
import React, { useState, useEffect, useMemo } from "react";
import {
  App,
  Layout,
  Table,
  Tag,
  Button,
  Modal,
  Form,
  Input,
  Checkbox,
  Popconfirm,
  Space,
  Typography,
  Tooltip,
  Badge,
} from "antd";
import {
  EditOutlined,
  DeleteOutlined,
  LockOutlined,
  SearchOutlined,
  UserOutlined,
} from "@ant-design/icons";
import withSidebar from "../common/base";
import PageHeader from "../common/PageHeader";
import {
  listRoles,
  listPermissions,
  createRole,
  updateRole,
  deleteRole,
  listRoleUsers,
  roleDisplayName,
  permissionLabel,
  builtinRoleEditable,
  builtinRoleEditTooltip,
  type Role,
} from "../api/roles";
import { PageState } from "../common/PageState";
import RequirePermission from "../auth/RequirePermission";
import { useAuth } from "../auth/AuthContext";

const { Text, Paragraph } = Typography;
const Content = Layout.Content;

function Roles() {
  const { message } = App.useApp();
  useDocumentTitle("QuantumPACS - Roles");
  const { hasPermission, user } = useAuth();

  // ROLE_READ gates the page; create/edit need ROLE_WRITE, delete needs
  // ROLE_DELETE. Non-platform-admins may only assign permissions they hold
  // themselves (mirrors api_keys and the backend role validation).
  const canWrite = hasPermission("ROLE_WRITE");
  const canDelete = hasPermission("ROLE_DELETE");
  const isAdmin = user?.admin === true;

  const [data, setData] = useState<Role[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [visible, setVisible] = useState(false);
  const [editingRole, setEditingRole] = useState<Role | null>(null);
  const [selectedPerms, setSelectedPerms] = useState<string[]>([]);
  const [permSearch, setPermSearch] = useState("");
  const [permGroups, setPermGroups] = useState<Record<string, string[]>>({});
  const [form] = Form.useForm();

  useEffect(() => {
    listPermissions()
      .then(setPermGroups)
      .catch(() => {});
  }, []);

  const columns: any[] = [
    {
      title: "Role",
      key: "name",
      width: "18%",
      render: (_: any, r: any) => (
        <Space>
          {r.built_in ? <LockOutlined style={{ color: "#8c8c8c" }} /> : null}
          <Text strong={r.built_in}>{roleDisplayName(r.slug, r.name)}</Text>
          {r.built_in ? (
            <Tag color="default" style={{ fontSize: 10 }}>
              Built-in
            </Tag>
          ) : null}
        </Space>
      ),
    },
    {
      title: "Description",
      dataIndex: "description",
      width: "22%",
      render: (d: string) => d || <Text type="secondary">—</Text>,
    },
    {
      title: "Permissions",
      dataIndex: "permissions",
      width: "24%",
      render: (perms: string[]) =>
        perms?.length ? (
          <Space wrap size={[2, 2]}>
            {perms.slice(0, 4).map((p: string) => (
              <Tag
                key={p}
                color="blue"
                style={{ fontSize: 11, margin: 0 }}
                title={p}
              >
                {permissionLabel(p)}
              </Tag>
            ))}
            {perms.length > 4 ? (
              <Tag color="default" style={{ fontSize: 11, margin: 0 }}>
                +{perms.length - 4} more
              </Tag>
            ) : null}
            <Text type="secondary" style={{ fontSize: 11 }}>
              ({perms.length})
            </Text>
          </Space>
        ) : (
          <Text type="secondary">None</Text>
        ),
    },
    {
      title: "Users",
      dataIndex: "user_count",
      width: "10%",
      render: (count: number, r: any) =>
        count > 0 ? (
          <Button
            type="link"
            size="small"
            icon={<UserOutlined />}
            onClick={() => showRoleUsers(r)}
          >
            {count}
          </Button>
        ) : (
          <Text type="secondary">0</Text>
        ),
    },
    {
      title: "Action",
      key: "action",
      width: "16%",
      render: (_: any, record: any) => {
        if (!record.built_in) {
          return (
            <Space>
              {canWrite && (
                <Button
                  type="link"
                  size="small"
                  icon={<EditOutlined />}
                  onClick={() => handleEdit(record)}
                >
                  Edit
                </Button>
              )}
              {canDelete && (
                <Popconfirm
                  title="Delete this role?"
                  onConfirm={() => handleDelete(record.id)}
                >
                  <Button
                    type="link"
                    size="small"
                    danger
                    icon={<DeleteOutlined />}
                  >
                    Delete
                  </Button>
                </Popconfirm>
              )}
            </Space>
          );
        }
        // R2-16 tiers: immutable built-ins (super/tenant/pacs/emr admin,
        // patient) stay locked; teleradiologist opens only for the platform
        // admin; the remaining 8 built-ins are editable by any ROLE_WRITE
        // holder. Deletion stays blocked for every built-in.
        if (record.built_in && canWrite) {
          const editable = builtinRoleEditable(record.slug, isAdmin);
          const tip = builtinRoleEditTooltip(record.slug, isAdmin);
          return (
            <Tooltip title={tip || undefined}>
              <Button
                type="link"
                size="small"
                disabled={!editable}
                icon={<EditOutlined />}
                onClick={editable ? () => handleEdit(record) : undefined}
              >
                Edit
              </Button>
            </Tooltip>
          );
        }
        return null;
      },
    },
  ];

  useEffect(() => {
    fetch();
  }, []);

  const fetch = () => {
    setLoading(true);
    setError(null);
    listRoles()
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

  const filteredGroups = useMemo(() => {
    let groups = permGroups;
    if (!isAdmin) {
      const grantable = new Set(user?.permissions ?? []);
      const subset: Record<string, string[]> = {};
      for (const [group, perms] of Object.entries(permGroups)) {
        const held = perms.filter((p) => grantable.has(p));
        if (held.length > 0) subset[group] = held;
      }
      groups = subset;
    }
    if (!permSearch) return groups;
    const search = permSearch.toLowerCase();
    const result: Record<string, string[]> = {};
    for (const [group, perms] of Object.entries(groups)) {
      const matching = perms.filter((p) => p.toLowerCase().includes(search));
      if (matching.length > 0) result[group] = matching;
    }
    return result;
  }, [permGroups, permSearch, isAdmin, user]);

  const handleCreate = () => {
    form
      .validateFields()
      .then((values: any) => {
        createRole({ ...values, permissions: selectedPerms })
          .then(() => {
            form.resetFields();
            setSelectedPerms([]);
            setVisible(false);
            fetch();
          })
          .catch((e: any) => {
            message.error(e.message);
          });
      })
      .catch(() => {});
  };

  const handleEdit = (role: any) => {
    setEditingRole(role);
    setSelectedPerms(role.permissions || []);
    form.setFieldsValue({
      name: role.name,
      slug: role.slug,
      description: role.description,
    });
    setVisible(true);
  };

  const handleUpdate = () => {
    form
      .validateFields()
      .then((values: any) => {
        if (!editingRole) return;
        const data: any = {};
        if (values.name !== editingRole.name) data.name = values.name;
        if (values.slug !== editingRole.slug) data.slug = values.slug;
        if (values.description !== editingRole.description)
          data.description = values.description;
        data.permissions = selectedPerms;
        updateRole(editingRole.id, data)
          .then(() => {
            form.resetFields();
            setSelectedPerms([]);
            setEditingRole(null);
            setVisible(false);
            fetch();
          })
          .catch((e: any) => {
            message.error(e.message);
          });
      })
      .catch(() => {});
  };

  const handleDelete = (id: number) => {
    deleteRole(id)
      .then(() => {
        fetch();
      })
      .catch((e: any) => {
        message.error(e.message);
      });
  };

  const handleCancel = () => {
    form.resetFields();
    setSelectedPerms([]);
    setPermSearch("");
    setEditingRole(null);
    setVisible(false);
  };

  const togglePermission = (perm: string) => {
    if (!isAdmin && !(user?.permissions ?? []).includes(perm)) return;
    setSelectedPerms((prev) =>
      prev.includes(perm) ? prev.filter((p) => p !== perm) : [...prev, perm],
    );
  };

  const toggleGroup = (group: string, perms: string[]) => {
    const allSelected = perms.every((p) => selectedPerms.includes(p));
    if (allSelected) {
      setSelectedPerms((prev) => prev.filter((p) => !perms.includes(p)));
    } else {
      setSelectedPerms((prev) => {
        const next = new Set(prev);
        perms.forEach((p) => next.add(p));
        return Array.from(next);
      });
    }
  };

  const showRoleUsers = (role: any) => {
    listRoleUsers(role.id)
      .then((users) => {
        Modal.info({
          title: `Users with role "${roleDisplayName(role.slug, role.name)}"`,
          width: 500,
          content: (
            <div>
              {users.length === 0 ? (
                <Text type="secondary">No users assigned to this role</Text>
              ) : (
                <Table
                  rowKey="id"
                  dataSource={users}
                  size="small"
                  pagination={false}
                  columns={[
                    { title: "Username", dataIndex: "username" },
                    {
                      title: "Status",
                      dataIndex: "status",
                      render: (s: string) =>
                        s === "active" ? (
                          <Tag color="green">Active</Tag>
                        ) : (
                          <Tag color="default">{s}</Tag>
                        ),
                    },
                  ]}
                />
              )}
            </div>
          ),
        });
      })
      .catch((e: any) => {
        message.error(e.message);
      });
  };

  const allPerms = Object.values(permGroups).flat();

  return (
    <Content style={{ padding: 24 }}>
      <PageHeader
        title="Roles"
        description="Permission sets that scope what each role can do in the platform."
        extra={
          <RequirePermission permission="ROLE_WRITE">
            <Button type="primary" onClick={() => setVisible(true)}>
              Create Role
            </Button>
          </RequirePermission>
        }
      />
      <PageState
        error={error}
        onRetry={() => fetch()}
        empty={!loading && !error && data.length === 0}
        emptyMessage="No roles defined"
        emptyAction={
          <RequirePermission permission="ROLE_WRITE">
            <Button type="primary" onClick={() => setVisible(true)}>
              Create Role
            </Button>
          </RequirePermission>
        }
      >
        <Table
          rowKey="id"
          columns={columns}
          dataSource={Array.isArray(data) ? data : []}
          loading={loading}
          expandedRowRender={(record: any) => (
            <div style={{ padding: "8px 0" }}>
              <Text strong style={{ fontSize: 13 }}>
                Permissions ({record.permissions?.length || 0})
              </Text>
              <div
                style={{
                  marginTop: 4,
                  display: "flex",
                  flexWrap: "wrap",
                  gap: 4,
                }}
              >
                {record.permissions?.length ? (
                  record.permissions.map((p: string) => (
                    <Tag key={p} color="blue" title={p}>
                      {permissionLabel(p)}
                    </Tag>
                  ))
                ) : (
                  <Text type="secondary">No permissions</Text>
                )}
              </div>
            </div>
          )}
        />
      </PageState>

      <Modal
        title={editingRole ? "Edit Role" : "Create Role"}
        open={visible}
        onCancel={handleCancel}
        onOk={editingRole ? handleUpdate : handleCreate}
        okText={editingRole ? "Update" : "Create"}
        width={600}
        footer={(_, { OkBtn, CancelBtn }) => (
          <Space>
            <CancelBtn />
            <OkBtn />
          </Space>
        )}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="name"
            label="Role Name"
            rules={[{ required: true, max: 64 }]}
          >
            <Input />
          </Form.Item>
          <Form.Item
            name="slug"
            label="Slug"
            rules={[
              { required: true },
              {
                pattern: /^[a-z0-9_]+$/,
                message: "Only lowercase letters, numbers, and underscores",
              },
            ]}
          >
            <Input />
          </Form.Item>
          <Form.Item name="description" label="Description">
            <Input.TextArea rows={2} maxLength={255} showCount />
          </Form.Item>
          <Form.Item label="Permissions">
            <Input
              placeholder="Search permissions..."
              prefix={<SearchOutlined />}
              value={permSearch}
              onChange={(e) => setPermSearch(e.target.value)}
              style={{ marginBottom: 8 }}
              allowClear
              onClear={() => setPermSearch("")}
            />
            <div
              style={{
                maxHeight: 360,
                overflow: "auto",
                border: "1px solid #f0f0f0",
                borderRadius: 6,
                padding: 8,
              }}
            >
              {Object.entries(filteredGroups).map(([group, perms]) => {
                const selectedCount = perms.filter((p) =>
                  selectedPerms.includes(p),
                ).length;
                return (
                  <div
                    key={group}
                    style={{
                      marginBottom: 6,
                      padding: "4px 0",
                      borderBottom: "1px solid #f5f5f5",
                    }}
                  >
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 8,
                        marginBottom: 4,
                      }}
                    >
                      <Checkbox
                        indeterminate={
                          selectedCount > 0 && selectedCount < perms.length
                        }
                        checked={selectedCount === perms.length}
                        onChange={() => toggleGroup(group, perms)}
                      >
                        <Text strong style={{ fontSize: 13 }}>
                          {group}
                        </Text>
                        <Text
                          type="secondary"
                          style={{ fontSize: 11, marginLeft: 6 }}
                        >
                          ({selectedCount}/{perms.length})
                        </Text>
                      </Checkbox>
                    </div>
                    <div style={{ paddingLeft: 24 }}>
                      {perms.map((perm) => (
                        <Checkbox
                          key={perm}
                          checked={selectedPerms.includes(perm)}
                          onChange={() => togglePermission(perm)}
                          style={{
                            marginRight: 12,
                            marginBottom: 2,
                            fontSize: 12,
                          }}
                        >
                          {perm}
                        </Checkbox>
                      ))}
                    </div>
                  </div>
                );
              })}
              {Object.keys(filteredGroups).length === 0 && (
                <Text type="secondary">
                  {!isAdmin && !permSearch
                    ? "You hold no permissions you can grant to a role."
                    : `No permissions match "${permSearch}"`}
                </Text>
              )}
            </div>
            {!isAdmin && (
              <Text type="secondary" style={{ fontSize: 11 }}>
                Only permissions you hold can be assigned to a role.
              </Text>
            )}
          </Form.Item>
        </Form>
      </Modal>
    </Content>
  );
}

export default withSidebar(Roles);
