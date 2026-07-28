import React, { useState, useEffect } from 'react';
import { Layout, Table, message, Tag, Button, Modal, Form, Input, Popconfirm } from 'antd';
import { DeleteOutlined } from '@ant-design/icons';
import withSidebar from '../common/base';
import { request } from '../helpers';

const Content = Layout.Content;

const STATUS_COLORS: Record<string, string> = {
  active: 'green',
  decommissioned: 'red',
  pending: 'orange',
};

function TenantHealth({ tenantId }: { tenantId: string }) {
  const [health, setHealth] = useState<any>(null);

  useEffect(() => {
    request(`tenants/${tenantId}/stats`).then((res: any) => {
      setHealth(res.data);
    }).catch(() => {
      setHealth(null);
    });
  }, [tenantId]);

  if (!health) return <span style={{ color: '#999' }}>—</span>;

  const totalStorage = health.storage_used_bytes || 0;
  const storageColor = totalStorage > 107374182400 ? 'red' : totalStorage > 53687091200 ? 'orange' : 'green';
  const activeColor = health.last_activity ? 'green' : 'default';

  return (
    <span>
      <span className="tenant-health-dot" style={{
        display: 'inline-block', width: 8, height: 8, borderRadius: '50%',
        backgroundColor: storageColor, marginRight: 4,
      }} />
      <Tag color={activeColor}>{health.user_count || 0} users</Tag>
      <Tag color="blue">{health.study_count || 0} studies</Tag>
      <Tag color={storageColor}>
        {totalStorage > 1073741824
          ? `${(totalStorage / 1073741824).toFixed(1)} GB`
          : `${(totalStorage / 1048576).toFixed(0)} MB`}
      </Tag>
    </span>
  );
}

function Tenants() {
  document.title = 'QuantumPACS - Tenants';

  let [data, setData] = useState<any[]>([]);
  let [loading, setLoading] = useState(false);
  let [visible, setVisible] = useState(false);
  const [form] = Form.useForm();

  const columns: any[] = [
    {
      title: 'Tenant Name', dataIndex: 'name', width: '20%',
    },
    {
      title: 'Slug', dataIndex: 'slug', width: '12%',
    },
    {
      title: 'Domain', dataIndex: 'domain', width: '20%',
    },
    {
      title: 'Users', width: '10%',
      render: (_: any, record: any) => <TenantHealth tenantId={record.id} />,
    },
    {
      title: 'Status', dataIndex: 'status', width: '12%',
      render: (s: string) => (
        <Tag color={STATUS_COLORS[s] || 'default'}>
          {s?.toUpperCase() || 'UNKNOWN'}
        </Tag>
      ),
    },
    {
      title: 'Action', key: 'action', width: '12%',
      render: (_: any, record: any) =>
        record.status !== 'decommissioned' ? (
          <Popconfirm title="Decommission this tenant?" onConfirm={() => handleDecommission(record.id)}>
            <DeleteOutlined
              title="Decommission"
              style={{ cursor: 'pointer', color: '#ff4d4f', fontSize: 16 }}
            />
          </Popconfirm>
        ) : null,
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

  const handleDecommission = (id: string) => {
    request(`tenants/${id}`, { data: undefined, method: 'DELETE' }).then(() => {
      fetch();
    }).catch((e: any) => {
      message.error(e.message);
    });
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