import React, { useState, useEffect } from 'react';
import { Layout, Table, message, Tag, Button, Modal, Form, Input, Checkbox, Select } from 'antd';
import withSidebar from '../common/base';
import { request } from '../helpers';

const Content = Layout.Content;

function Roles() {
  document.title = 'QuantumPACS - Roles';

  let [data, setData] = useState<any[]>([]);
  let [loading, setLoading] = useState(false);
  let [visible, setVisible] = useState(false);
  const [form] = Form.useForm();

  const columns: any[] = [
    {
      title: 'Role Name',
      dataIndex: 'name',
      width: '25%',
    },
    {
      title: 'Slug',
      dataIndex: 'slug',
      width: '20%',
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
      request('roles', { data: values }).then(() => {
        form.resetFields();
        setVisible(false);
        fetch();
      }).catch((e: any) => {
        message.error(e.message);
      });
    }).catch(() => {});
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
        title="Create Role"
        open={visible}
        onCancel={() => setVisible(false)}
        onOk={handleCreate}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="Role Name" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="slug" label="Slug" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
        </Form>
      </Modal>
    </Content>
  );
}

export default withSidebar(Roles);
