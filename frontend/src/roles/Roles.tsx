import React, { useState, useEffect } from 'react';
import { Layout, Table, message, Tag, Button, Modal, Form, Input, Checkbox, Popconfirm } from 'antd';
import { EditOutlined, DeleteOutlined } from '@ant-design/icons';
import withSidebar from '../common/base';
import { request } from '../helpers';

const Content = Layout.Content;

const PERMISSION_GROUPS: { label: string; keys: string[] }[] = [
  { label: 'Files', keys: ['FILE_READ', 'FILE_WRITE', 'FILE_DELETE'] },
  { label: 'Patients', keys: ['PATIENT_READ', 'PATIENT_WRITE'] },
  { label: 'Studies', keys: ['STUDY_READ', 'STUDY_WRITE'] },
  { label: 'Users', keys: ['USER_READ', 'USER_WRITE', 'USER_DELETE', 'USER_ADMIN'] },
  { label: 'Replicas', keys: ['REPLICA_READ', 'REPLICA_WRITE', 'REPLICA_DELETE'] },
  { label: 'Logs', keys: ['LOG_READ'] },
  { label: 'Tenants', keys: ['TENANT_READ', 'TENANT_WRITE', 'TENANT_ADMIN'] },
  { label: 'Roles', keys: ['ROLE_READ', 'ROLE_WRITE', 'ROLE_DELETE'] },
  { label: 'Service Keys', keys: ['SERVICE_KEY_READ', 'SERVICE_KEY_WRITE', 'SERVICE_KEY_DELETE'] },
  { label: 'Worklist', keys: ['WORKLIST_READ', 'WORKLIST_WRITE'] },
  { label: 'DICOMweb', keys: ['DICOMWEB_READ', 'DICOMWEB_WRITE'] },
  { label: 'Routing', keys: ['ROUTING_READ', 'ROUTING_WRITE'] },
  { label: 'Metrics', keys: ['METRICS_READ'] },
];

function Roles() {
  document.title = 'QuantumPACS - Roles';

  let [data, setData] = useState<any[]>([]);
  let [loading, setLoading] = useState(false);
  let [visible, setVisible] = useState(false);
  let [editingRole, setEditingRole] = useState<any | null>(null);
  let [selectedPerms, setSelectedPerms] = useState<string[]>([]);
  const [form] = Form.useForm();

  const columns: any[] = [
    {
      title: 'Role Name',
      dataIndex: 'name',
      width: '20%',
    },
    {
      title: 'Slug',
      dataIndex: 'slug',
      width: '15%',
    },
    {
      title: 'Permissions',
      dataIndex: 'permissions',
      render: (perms: string[]) =>
        perms && perms.length > 0 ? (
          <span>
            {perms.slice(0, 3).map((p: string) => (
              <Tag key={p} color="blue" style={{ marginBottom: 2 }}>{p}</Tag>
            ))}
            {perms.length > 3 && <Tag color="default">+{perms.length - 3}</Tag>}
          </span>
        ) : null,
    },
    {
      title: 'Built-in',
      dataIndex: 'built_in',
      render: (builtIn: boolean) =>
        builtIn ? <Tag color="green">Yes</Tag> : <Tag color="orange">Custom</Tag>,
    },
    {
      title: 'Action',
      key: 'action',
      render: (_: any, record: any) =>
        record.built_in ? null : (
          <span>
            <EditOutlined
              title="Edit"
              onClick={() => handleEdit(record)}
              style={{ cursor: 'pointer', marginRight: 12, fontSize: 16 }}
            />
            <Popconfirm title="Delete this role?" onConfirm={() => handleDelete(record.id)}>
              <DeleteOutlined
                title="Delete"
                style={{ cursor: 'pointer', color: '#ff4d4f', fontSize: 16 }}
              />
            </Popconfirm>
          </span>
        ),
    },
  ];

  useEffect(() => {
    fetch();
  }, []);

  const fetch = () => {
    setLoading(true);
    request('roles').then((data: any) => {
      setLoading(false);
      setData(data.data || []);
    }).catch((e: any) => {
      setLoading(false);
      message.error(e.message);
    });
  };

  const handleCreate = () => {
    form.validateFields().then((values: any) => {
      request('roles', { data: { ...values, permissions: selectedPerms } }).then(() => {
        form.resetFields();
        setSelectedPerms([]);
        setVisible(false);
        fetch();
      }).catch((e: any) => {
        message.error(e.message);
      });
    }).catch(() => {});
  };

  const handleEdit = (role: any) => {
    setEditingRole(role);
    setSelectedPerms(role.permissions || []);
    form.setFieldsValue({ name: role.name, slug: role.slug });
    setVisible(true);
  };

  const handleUpdate = () => {
    form.validateFields().then((values: any) => {
      const data: any = {};
      if (values.name !== editingRole.name) data.name = values.name;
      if (values.slug !== editingRole.slug) data.slug = values.slug;
      data.permissions = selectedPerms;
      request(`roles/${editingRole.id}`, { data }).then(() => {
        form.resetFields();
        setSelectedPerms([]);
        setEditingRole(null);
        setVisible(false);
        fetch();
      }).catch((e: any) => {
        message.error(e.message);
      });
    }).catch(() => {});
  };

  const handleDelete = (id: number) => {
    request(`roles/${id}`, { data: undefined, method: 'DELETE' }).then(() => {
      fetch();
    }).catch((e: any) => {
      message.error(e.message);
    });
  };

  const handleCancel = () => {
    form.resetFields();
    setSelectedPerms([]);
    setEditingRole(null);
    setVisible(false);
  };

  const togglePermission = (perm: string) => {
    setSelectedPerms((prev) =>
      prev.includes(perm) ? prev.filter((p) => p !== perm) : [...prev, perm],
    );
  };

  return (
    <Content style={{ padding: 50 }}>
      <Button type="primary" onClick={() => setVisible(true)} style={{ marginBottom: 16 }}>
        Create Role
      </Button>
      <Table
        rowKey="id"
        columns={columns}
        dataSource={data}
        loading={loading}
      />
      <Modal
        title={editingRole ? 'Edit Role' : 'Create Role'}
        open={visible}
        onCancel={handleCancel}
        onOk={editingRole ? handleUpdate : handleCreate}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="Role Name" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="slug" label="Slug" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item label="Permissions">
            {PERMISSION_GROUPS.map((group) => (
              <div key={group.label} style={{ marginBottom: 8 }}>
                <div style={{ fontWeight: 600, marginBottom: 4, fontSize: 13 }}>{group.label}</div>
                <div>
                  {group.keys.map((perm) => (
                    <Checkbox
                      key={perm}
                      checked={selectedPerms.includes(perm)}
                      onChange={() => togglePermission(perm)}
                      style={{ marginRight: 12, marginBottom: 4 }}
                    >
                      {perm}
                    </Checkbox>
                  ))}
                </div>
              </div>
            ))}
          </Form.Item>
        </Form>
      </Modal>
    </Content>
  );
}

export default withSidebar(Roles);