import React, { useState, useEffect } from 'react';
import { Layout, Table, message, Button, Tag, Modal, Form, Input, Popconfirm, Alert } from 'antd';
import { DeleteOutlined, CopyOutlined } from '@ant-design/icons';
import withSidebar from '../common/base';
import { request } from '../helpers';

const Content = Layout.Content;

function ServiceKeys() {
  document.title = 'QuantumPACS - Service Keys';

  let [data, setData] = useState<any[]>([]);
  let [loading, setLoading] = useState(false);
  let [visible, setVisible] = useState(false);
  let [rawKey, setRawKey] = useState<string | null>(null);
  const [form] = Form.useForm();

  const columns: any[] = [
    { title: 'Name', dataIndex: 'name', width: '20%' },
    { title: 'Service', dataIndex: 'service_name', width: '18%' },
    { title: 'Prefix', dataIndex: 'prefix', width: '14%' },
    {
      title: 'Status', dataIndex: 'enabled', width: '10%',
      render: (enabled: boolean) =>
        enabled ? <Tag color="green">Active</Tag> : <Tag color="red">Revoked</Tag>,
    },
    {
      title: 'Expires', dataIndex: 'expires_at', width: '14%',
      render: (d: string | null) => d ? new Date(d).toLocaleDateString() : 'Never',
    },
    {
      title: 'Action', key: 'action', width: '12%',
      render: (_: any, record: any) =>
        record.enabled ? (
          <Popconfirm title="Revoke this key?" onConfirm={() => handleRevoke(record.id)}>
            <DeleteOutlined
              title="Revoke"
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
    request('api-keys').then((res: any) => {
      setLoading(false);
      setData(Array.isArray(res.data) ? res.data : []);
    }).catch((e: any) => {
      setLoading(false);
      message.error(e.message);
    });
  };

  const handleGenerate = () => {
    form.validateFields().then((values: any) => {
      request('api-keys', { data: values }).then((res: any) => {
        form.resetFields();
        setRawKey(res.data.raw_key);
        setVisible(false);
        fetch();
      }).catch((e: any) => {
        message.error(e.message);
      });
    }).catch(() => {});
  };

  const handleRevoke = (id: string) => {
    request(`api-keys/${id}`, { data: undefined, method: 'DELETE' }).then(() => {
      fetch();
    }).catch((e: any) => {
      message.error(e.message);
    });
  };

  const copyKey = () => {
    if (rawKey) {
      navigator.clipboard.writeText(rawKey);
      message.success('Key copied to clipboard');
    }
  };

  return (
    <Content style={{ padding: 50 }}>
      <Button type="primary" onClick={() => { setRawKey(null); setVisible(true); }} style={{ marginBottom: 16 }}>
        Generate Key
      </Button>

      {rawKey && (
        <Alert
          type="success"
          showIcon
          closable
          style={{ marginBottom: 16 }}
          message={
            <span>
              Key generated: <code style={{ fontSize: 14, background: '#f5f5f5', padding: '2px 8px', borderRadius: 4 }}>{rawKey}</code>
              <Button type="link" icon={<CopyOutlined />} onClick={copyKey} style={{ marginLeft: 8 }}>Copy</Button>
            </span>
          }
          description="This key will not be shown again. Copy it now."
        />
      )}

      <Table
        rowKey="id"
        columns={columns}
        dataSource={data}
        loading={loading}
      />

      <Modal
        title="Generate New API Key"
        open={visible}
        onCancel={() => { form.resetFields(); setVisible(false); }}
        onOk={handleGenerate}
        okText="Generate"
      >
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="Name" rules={[{ required: true }]}>
            <Input placeholder="e.g., RIS Integration" />
          </Form.Item>
          <Form.Item name="service_name" label="Service Name" rules={[{ required: true }]}>
            <Input placeholder="e.g., RIS-App" />
          </Form.Item>
          <Form.Item name="expires_in_days" label="Expires In (days)">
            <Input type="number" placeholder="Leave empty for no expiry" />
          </Form.Item>
        </Form>
      </Modal>
    </Content>
  );
}

export default withSidebar(ServiceKeys);
