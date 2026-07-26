import React, { useState, useEffect } from 'react';
import { Layout, Table, message, Tag, Button, Modal, Form, Input, Popconfirm } from 'antd';
import withSidebar from '../common/base';
import { request } from '../helpers';

const Content = Layout.Content;

function Tenants() {
  document.title = 'QuantumPACS - Tenants';

  let [data, setData] = useState<any[]>([]);
  let [loading, setLoading] = useState(false);
  let [visible, setVisible] = useState(false);
  const [form] = Form.useForm();

  const columns: any[] = [
    {
      title: 'Tenant Name',
      dataIndex: 'name',
      width: '25%',
    },
    {
      title: 'Slug',
      dataIndex: 'slug',
      width: '15%',
    },
    {
      title: 'Domain',
      dataIndex: 'domain',
      width: '25%',
    },
    {
      title: 'Status',
      dataIndex: 'status',
      render: (s: string) => (
        <Tag color={s === 'active' ? 'green' : s === 'decommissioned' ? 'red' : 'orange'}>
          {s?.toUpperCase() || 'UNKNOWN'}
        </Tag>
      ),
    },
  ];

  useEffect(() => {
    fetch();
  }, []);

  const fetch = () => {
    setLoading(true);
    request('tenants').then((data: any) => {
      setLoading(false);
      setData(data.data || []);
    }).catch((e: any) => {
      setLoading(false);
      message.error(e.message);
    });
  };

  const handleProvision = () => {
    form.validateFields().then((values: any) => {
      request('tenants', { data: values }).then(() => {
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
        Provision Tenant
      </Button>
      <Table
        rowKey="id"
        columns={columns}
        dataSource={data}
        loading={loading}
      />
      <Modal
        title="Provision Tenant"
        open={visible}
        onCancel={() => setVisible(false)}
        onOk={handleProvision}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="Tenant Name" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="slug" label="Slug" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="domain" label="Domain">
            <Input />
          </Form.Item>
          <Form.Item name="admin_email" label="Admin Email">
            <Input type="email" />
          </Form.Item>
        </Form>
      </Modal>
    </Content>
  );
}

export default withSidebar(Tenants);
