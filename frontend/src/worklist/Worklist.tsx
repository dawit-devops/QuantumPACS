import React, { useState, useEffect } from 'react';
import { Layout, Table, message, Button, Tag, Modal, Form, Input, Select, DatePicker, TimePicker, Popconfirm } from 'antd';
import { EditOutlined, CloseCircleOutlined } from '@ant-design/icons';
import withSidebar from '../common/base';
import { request } from '../helpers';
import dayjs from 'dayjs';

const Content = Layout.Content;

const STATUS_COLORS: Record<string, string> = {
  scheduled: 'blue',
  performed: 'green',
  cancelled: 'red',
};

function Worklist() {
  document.title = 'QuantumPACS - Worklist';

  let [data, setData] = useState<any[]>([]);
  let [loading, setLoading] = useState(false);
  let [pagination, setPagination] = useState<any>({ current: 1, pageSize: 20, total: 0 });
  let [visible, setVisible] = useState(false);
  let [editingEntry, setEditingEntry] = useState<any | null>(null);
  const [form] = Form.useForm();

  const columns: any[] = [
    { title: 'Patient Name', dataIndex: 'patient_name', width: '18%' },
    { title: 'Patient ID', dataIndex: 'patient_id', width: '10%' },
    { title: 'Accession #', dataIndex: 'accession_number', width: '12%' },
    { title: 'Modality', dataIndex: 'modality', width: '8%' },
    {
      title: 'Scheduled Date', dataIndex: 'scheduled_date', width: '12%',
      render: (d: string) => d || '-',
    },
    {
      title: 'Status', dataIndex: 'status', width: '8%',
      render: (s: string) => s ? <Tag color={STATUS_COLORS[s] || 'default'}>{s}</Tag> : null,
    },
    {
      title: 'Action', key: 'action', width: '12%',
      render: (_: any, record: any) => (
        <span>
          <EditOutlined
            title="Edit"
            onClick={() => handleEdit(record)}
            style={{ cursor: 'pointer', marginRight: 12, fontSize: 16 }}
          />
          {record.status === 'scheduled' && (
            <Popconfirm title="Cancel this entry?" onConfirm={() => handleCancel(record.id)}>
              <CloseCircleOutlined
                title="Cancel"
                style={{ cursor: 'pointer', color: '#ff4d4f', fontSize: 16 }}
              />
            </Popconfirm>
          )}
        </span>
      ),
    },
  ];

  useEffect(() => {
    fetch();
  }, []);

  const fetch = (params?: any) => {
    setLoading(true);
    request('worklist', params || {}).then((res: any) => {
      setLoading(false);
      const items = Array.isArray(res.data) ? res.data : [];
      setData(items);
      setPagination((prev: any) => ({ ...prev, total: items.length }));
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
      const data: any = { ...values };
      if (data.scheduled_date) data.scheduled_date = data.scheduled_date.format('YYYY-MM-DD');
      if (data.scheduled_time) data.scheduled_time = data.scheduled_time.format('HH:mm');
      request('worklist', { data }).then(() => {
        form.resetFields();
        setVisible(false);
        fetch();
      }).catch((e: any) => {
        message.error(e.message);
      });
    }).catch(() => {});
  };

  const handleEdit = (entry: any) => {
    setEditingEntry(entry);
    form.setFieldsValue({
      ...entry,
      scheduled_date: entry.scheduled_date ? dayjs(entry.scheduled_date) : null,
      scheduled_time: entry.scheduled_time ? dayjs(entry.scheduled_time, 'HH:mm') : null,
    });
    setVisible(true);
  };

  const handleUpdate = () => {
    form.validateFields().then((values: any) => {
      const data: any = {};
      for (const key of ['patient_name', 'patient_birth_date', 'patient_sex', 'accession_number', 'requested_procedure_id', 'requested_procedure_desc', 'modality', 'station_ae_title']) {
        if (values[key] !== undefined && values[key] !== editingEntry[key]) {
          data[key] = values[key];
        }
      }
      if (values.scheduled_date) data.scheduled_date = values.scheduled_date.format('YYYY-MM-DD');
      if (values.scheduled_time) data.scheduled_time = values.scheduled_time.format('HH:mm');
      if (Object.keys(data).length === 0) {
        setVisible(false);
        setEditingEntry(null);
        return;
      }
      request(`worklist/${editingEntry.id}`, { data }).then(() => {
        form.resetFields();
        setEditingEntry(null);
        setVisible(false);
        fetch();
      }).catch((e: any) => {
        message.error(e.message);
      });
    }).catch(() => {});
  };

  const handleCancel = (id: string) => {
    request(`worklist/${id}`, { data: undefined, method: 'DELETE' }).then(() => {
      fetch();
    }).catch((e: any) => {
      message.error(e.message);
    });
  };

  const handleModalCancel = () => {
    form.resetFields();
    setEditingEntry(null);
    setVisible(false);
  };

  return (
    <Content style={{ padding: 50 }}>
      <Button type="primary" onClick={() => setVisible(true)} style={{ marginBottom: 16 }}>
        Create Entry
      </Button>
      <Table
        rowKey="id"
        columns={columns}
        dataSource={data}
        loading={loading}
        pagination={pagination}
        onChange={handleTableChange}
      />
      <Modal
        title={editingEntry ? 'Edit Worklist Entry' : 'Create Worklist Entry'}
        open={visible}
        onCancel={handleModalCancel}
        onOk={editingEntry ? handleUpdate : handleCreate}
        width={520}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="patient_id" label="Patient ID" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="patient_name" label="Patient Name">
            <Input />
          </Form.Item>
          <Form.Item name="patient_birth_date" label="Birth Date">
            <Input placeholder="YYYY-MM-DD" />
          </Form.Item>
          <Form.Item name="patient_sex" label="Sex">
            <Select allowClear>
              <Select.Option value="M">Male</Select.Option>
              <Select.Option value="F">Female</Select.Option>
              <Select.Option value="O">Other</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item name="accession_number" label="Accession #">
            <Input />
          </Form.Item>
          <Form.Item name="requested_procedure_desc" label="Procedure Description">
            <Input />
          </Form.Item>
          <Form.Item name="modality" label="Modality">
            <Input />
          </Form.Item>
          <Form.Item name="scheduled_date" label="Scheduled Date">
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="scheduled_time" label="Scheduled Time">
            <TimePicker style={{ width: '100%' }} format="HH:mm" />
          </Form.Item>
          <Form.Item name="station_ae_title" label="Station AE Title">
            <Input />
          </Form.Item>
        </Form>
      </Modal>
    </Content>
  );
}

export default withSidebar(Worklist);
