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
import {
  listRoles,
  listPermissions,
  createRole,
  updateRole,
  deleteRole,
  listRoleUsers,
  type Role,
} from "../api/roles";
import { PageState } from "../common/PageState";

const { Text, Paragraph } = Typography;
const Content = Layout.Content;

const SUPER_ADMIN_SLUG = "super_admin";

function Roles() {
  const { message } = App.useApp();
  useDocumentTitle("QuantumPACS - Roles");

  const [data, setData] = useState<Role[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [visible, setVisible] = useState(false);
  const [editingRole, setEditingRole] = useState<Role | null>(null);
  const [selectedPerms, setSelectedPerms] = useState<string[]>([]);
  const [permSearch, setPermSearch] = useState("");
  const [permGroups, setPermGroups] = useState<Record<string, string[]>>({});
  const [form] = Form.useForm();

  const isEditingSuperAdmin = editingRole?.slug === SUPER_ADMIN_SLUG;

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
          <Text strong={r.built_in}>{r.name}</Text>
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
              <Tag key={p} color="blue" style={{ fontSize: 11, margin: 0 }}>
                {p}
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
              <Button
                type="link"
                size="small"
                icon={<EditOutlined />}
                onClick={() => handleEdit(record)}
              >
                Edit
              </Button>
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
            </Space>
          );
        }
        if (record.slug === SUPER_ADMIN_SLUG) {
          return (
            <Tooltip title="Immutable built-in role">
              <Button type="link" size="small" disabled icon={<EditOutlined />}>
                Edit
              </Button>
            </Tooltip>
          );
        }
        return (
          <Tooltip title="Built-in roles cannot be deleted">
            <Button
              type="link"
              size="small"
              icon={<EditOutlined />}
              onClick={() => handleEdit(record)}
            >
              Edit
            </Button>
          </Tooltip>
        );
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
    if (!permSearch) return permGroups;
    const search = permSearch.toLowerCase();
    const result: Record<string, string[]> = {};
    for (const [group, perms] of Object.entries(permGroups)) {
      const matching = perms.filter((p) => p.toLowerCase().includes(search));
      if (matching.length > 0) result[group] = matching;
    }
    return result;
  }, [permGroups, permSearch]);

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
          title: `Users with role "${role.name}"`,
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
                      dataIndex: "active",
                      render: (a: boolean) =>
                        a ? (
                          <Tag color="green">Active</Tag>
                        ) : (
                          <Tag color="default">Inactive</Tag>
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
    <Content style={{ padding: 50 }}>
      <Button
        type="primary"
        onClick={() => setVisible(true)}
        style={{ marginBottom: 16 }}
      >
        Create Role
      </Button>
      <PageState
        error={error}
        onRetry={() => fetch()}
        empty={!loading && !error && data.length === 0}
        emptyMessage="No roles defined"
        emptyAction={
          <Button type="primary" onClick={() => setVisible(true)}>
            Create Role
          </Button>
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
                    <Tag key={p} color="blue">
                      {p}
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
        onOk={
          isEditingSuperAdmin
            ? undefined
            : editingRole
              ? handleUpdate
              : handleCreate
        }
        okText={
          isEditingSuperAdmin ? "Close" : editingRole ? "Update" : "Create"
        }
        width={600}
        footer={(_, { OkBtn, CancelBtn }) => (
          <Space>
            <CancelBtn />
            {!isEditingSuperAdmin && <OkBtn />}
          </Space>
        )}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="name"
            label="Role Name"
            rules={[{ required: true, max: 64 }]}
          >
            <Input disabled={isEditingSuperAdmin} />
          </Form.Item>
          <Form.Item name="slug" label="Slug" rules={[{ required: true }]}>
            <Input disabled={isEditingSuperAdmin} />
          </Form.Item>
          <Form.Item name="description" label="Description">
            <Input.TextArea
              rows={2}
              maxLength={255}
              showCount
              disabled={isEditingSuperAdmin}
            />
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
                        disabled={isEditingSuperAdmin}
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
                          disabled={isEditingSuperAdmin}
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
                  No permissions match "{permSearch}"
                </Text>
              )}
            </div>
          </Form.Item>
        </Form>
      </Modal>
    </Content>
  );
}

export default withSidebar(Roles);
