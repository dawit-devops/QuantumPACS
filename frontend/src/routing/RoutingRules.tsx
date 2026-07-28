import React, { useState, useEffect } from 'react';
import { Layout, Table, message, Button, Tag, Modal, Form, Input, InputNumber, Switch, Popconfirm } from 'antd';
import { DeleteOutlined } from '@ant-design/icons';
import withSidebar from '../common/base';
import { request } from '../helpers';

const Content = Layout.Content;

function RoutingRules() {
  document.title = 'QuantumPACS - Routing Rules';

  let [data, setData] = useState<any[]>([]);
  let [loading, setLoading] = useState(false);
  let [pagination, setPagination] = useState<any>({ current: 1, pageSize: 50, total: 0, pages: 0 });
  let [visible, setVisible] = useState(false);
  let [editingRule, setEditingRule] = useState<any | null>(null);
  const [form] = Form.useForm();

  const columns: any[] = [
    { title: 'Name', dataIndex: 'name', width: '20%' },
    {
      title: 'Status', dataIndex: 'enabled', width: '10%',
      render: (enabled: boolean) =>
        enabled ? <Tag color="green">Active</Tag> : <Tag color="default">Disabled</Tag>,
    },
    { title: 'Destination', dataIndex: 'destination', width: '18%' },
    { title: 'Priority', dataIndex: 'priority', width: '8%' },
    {
      title: 'Conditions', dataIndex: 'conditions', width: '24%',
      render: (c: any) => c ? JSON.stringify(c) : '-',
    },
    {
      title: 'Action', key: 'action', width: '12%',
      render: (_: any, record: any) => (
        <span>
          <Popconfirm title="Delete this rule?" onConfirm={() => handleDelete(record.id)}>
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
    fetch({ page: 1, per_page: 50 });
  }, []);

  const fetch = (params: any) => {
    setLoading(true);
    request('routing', params).then((res: any) => {
      setLoading(false);
      setData(Array.isArray(res.data) ? res.data : []);
      if (res.pagination) setPagination(res.pagination);
    }).catch((e: any) => {
      setLoading(false);
      message.error(e.message);
    });
  };

  const handleTableChange = (pag: any) => {
    setPagination(pag);
    fetch({ page: pag.current, per_page: pag.pageSize });
  };

  const handleCreate = () => {
    form.validateFields().then((values: any) => {
      const data: any = {
        name: values.name,
        destination: values.destination,
        priority: values.priority || 0,
        enabled: values.enabled !== undefined ? values.enabled : true,
        description: values.description || '',
      };
      try {
        if (values.conditions) data.conditions = JSON.parse(values.conditions);
      } catch {
        data.conditions = values.conditions || {};
      }
      request('routing', { data }).then(() => {
        form.resetFields();
        setVisible(false);
        fetch({ page: 1, per_page: 50 });
      }).catch((e: any) => {
        message.error(e.message);
      });
    }).catch(() => {});
  };

  const handleEdit = (rule: any) => {
    setEditingRule(rule);
    form.setFieldsValue({
      ...rule,
      conditions: typeof rule.conditions === 'object' ? JSON.stringify(rule.conditions, null, 2) : rule.conditions,
    });
    setVisible(true);
  };

  const handleUpdate = () => {
    form.validateFields().then((values: any) => {
      const data: any = {};
      const fields = ['name', 'destination', 'description'];
      for (const key of fields) {
        if (values[key] !== undefined && values[key] !== editingRule[key]) data[key] = values[key];
      }
      if (values.priority !== undefined && values.priority !== editingRule.priority) data.priority = values.priority;
      if (values.enabled !== undefined && values.enabled !== editingRule.enabled) data.enabled = values.enabled;
      if (values.conditions) {
        try { data.conditions = JSON.parse(values.conditions); } catch { data.conditions = values.conditions; }
      }
      if (Object.keys(data).length === 0) {
        setVisible(false);
        setEditingRule(null);
        return;
      }
      request(`routing/${editingRule.id}`, { data }).then(() => {
        form.resetFields();
        setEditingRule(null);
        setVisible(false);
        fetch({ page: 1, per_page: 50 });
      }).catch((e: any) => {
        message.error(e.message);
      });
    }).catch(() => {});
  };

  const handleDelete = (id: string) => {
    request(`routing/${id}`, { data: undefined, method: 'DELETE' }).then(() => {
      fetch({ page: 1, per_page: 50 });
    }).catch((e: any) => {
      message.error(e.message);
    });
  };

  const handleModalCancel = () => {
    form.resetFields();
    setEditingRule(null);
    setVisible(false);
  };

  return (
    <Content style={{ padding: 50 }}>
      <Button type="primary" onClick={() => setVisible(true)} style={{ marginBottom: 16 }}>
        Create Rule
      </Button>
      <Table
        rowKey="id"
        columns={columns}
        dataSource={data}
        loading={loading}
        pagination={{ current: pagination.page, pageSize: pagination.per_page, total: pagination.total }}
        onChange={handleTableChange}
      />
      <Modal
        title={editingRule ? 'Edit Routing Rule' : 'Create Routing Rule'}
        open={visible}
        onCancel={handleModalCancel}
        onOk={editingRule ? handleUpdate : handleCreate}
        width={600}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="Name" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="destination" label="Destination" rules={[{ required: true }]}>
            <Input placeholder="e.g., replica_2" />
          </Form.Item>
          <Form.Item name="priority" label="Priority">
            <InputNumber min={0} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="enabled" label="Enabled" valuePropName="checked">
            <Switch defaultChecked />
          </Form.Item>
          <Form.Item name="description" label="Description">
            <Input.TextArea rows={2} />
          </Form.Item>
          <Form.Item name="conditions" label="Conditions (JSON)">
            <Input.TextArea rows={4} placeholder='{"modality": "CT", "study_description": {"contains": "CHEST"}}' />
          </Form.Item>
        </Form>
      </Modal>
    </Content>
  );
}

export default withSidebar(RoutingRules);
