import React, { useState, useEffect } from 'react';
import { Layout, Table, message, Tag, Popconfirm, Divider, Form, Modal, InputNumber } from 'antd';
import withSidebar from '../common/base';
import { request } from '../helpers';
import { AddReplica } from './EditReplica';

const Content = Layout.Content;

export function EditDelay(props: any) {
  const { form, replica, onCancel, onCreate } = props;
  const delay = replica ? replica.delay : 0;

  return (
    <Modal
      open={true}
      title='Edit delay'
      okText='Update'
      onCancel={onCancel}
      onOk={onCreate}
    >
      <Form form={form} layout="vertical">
        <Form.Item name="delay" label="Delay (in minutes)" initialValue={delay} rules={[{ required: true, message: "Please replica's delay!" }]}>
          <InputNumber />
        </Form.Item>
      </Form>
    </Modal>
  );
}

function Replicas() {
  document.title = 'QuantumPACS - Replicas';

  let [data, setData] = useState<any[]>([]);
  let [pagination, setPagination] = useState<any>({});
  let [loading, setLoading] = useState(false);
  let [currReplica, setCurrReplica] = useState<any>(null);
  let [editDelayForm] = Form.useForm();

  useEffect(() => {
    fetch();
    // eslint-disable-next-line
  }, []);

  const handleDelete = (replica: number) => {
    request(`replicas/${replica}`, { method: 'DELETE' })
      .then(fetch).catch(() => {
        message.error('Deletion failed');
      });
  };

  const updateDelay = () => {
    editDelayForm.validateFields().then((values: any) => {
      request(`replicas/${currReplica.id}`, { data: values })
        .then(() => {
          editDelayForm.resetFields();
          setCurrReplica(null);
        })
        .then(fetch).catch(() => {
          message.error('Delay failed to update');
        });
    }).catch(() => {});
  };

  const setMaster = (replica: any) => {
    request(`replicas/${replica.id}`, { data: { master: true } })
      .then(fetch).catch(() => message.error('Failed to change master'));
  };

  useEffect(() => {
    const id = setInterval(() => {
      fetch(false);
      setLoading(false);
    }, 2000);
    return () => clearInterval(id);
    // eslint-disable-next-line
  }, []);

  const handleTableChange = (pagination: any, filters: any, sorter: any) => {
    const pager = { ...pagination };
    pager.current = pagination.current;
    setPagination(Object.assign({}, pagination, { current: pagination.current }));
    fetch({
      results: pagination.pageSize,
      page: pagination.current,
      sortField: sorter.field,
      sortOrder: sorter.order,
      ...filters,
    });
  };

  const fetch = (showLoading?: any) => {
    if (showLoading !== false) setLoading(true);
    request('replicas').then((data: any) => {
      const pager = Object.assign({}, pagination, { total: data.data.length });
      if (showLoading !== false) setLoading(false);
      setData(data.data);
      setPagination(pager);
    }).catch((e: any) => {
      setLoading(false);
      message.error(e.message);
    });
  };

  const editDelayCancel = () => {
    setCurrReplica(null);
  };

  const columns: any[] = [
    {
      title: 'ID',
      dataIndex: 'id',
    },
    {
      title: 'Type',
      dataIndex: 'type',
    },
    {
      title: 'Replication',
      dataIndex: 'master',
      render: (master: boolean) => {
        const mstr = master ? 'master' : 'replica';
        const color = master ? 'green' : 'geekblue';
        return (
          <Tag color={color} key={mstr}>
            {mstr.toUpperCase()}
          </Tag>
        );
      }
    },
    {
      title: 'Location',
      dataIndex: 'location',
    },
    {
      title: 'Delay',
      dataIndex: 'delay',
    },
    {
      title: 'Status',
      dataIndex: 'status',
      sorter: true,
      render: (status: string) => {
        let color;
        if (status === 'ok') {
          color = 'green';
        } else {
          color = 'orange';
        }
        return (
          <Tag color={color} key={status}>
            {status.toUpperCase()}
          </Tag>
        );
      }
    },
    {
      title: 'Files',
      dataIndex: 'files',
    },
    {
      title: 'Action',
      key: 'action',
      render: (text: any, record: any) =>
        (!record.master || (record.master && data.length === 1)) ? (
          <span>
            {!record.master &&
              <span>
                {/* eslint-disable-next-line */}
                <a onClick={() => setCurrReplica(record)}>Update delay</a>
                <Divider type="vertical" />
                {/* eslint-disable-next-line */}
                <a onClick={() => setMaster(record)}>Set master</a>
                <Divider type="vertical" />
              </span>
            }
            <Popconfirm title="Sure to delete?" onConfirm={() => handleDelete(record.id)}>
              {/* eslint-disable-next-line */}
              <a>Delete</a>
            </Popconfirm>
          </span>
        ) : null,
    },
  ];

  return (
    <Content style={{
      alignItems: 'center',
      justifyContent: 'center',
      padding: 50
    }}>
      <AddReplica style={{ marginBottom: 10 }} reload={fetch} />
      <Table
        scroll={{ x: 500 }}
        columns={columns}
        rowKey={(record: any) => record.id}
        dataSource={data}
        pagination={pagination}
        loading={loading}
        onChange={handleTableChange}
      />
      {
        currReplica !== null &&
        <EditDelay
          form={editDelayForm}
          replica={currReplica}
          onCancel={editDelayCancel}
          onCreate={updateDelay}
        ></EditDelay>
      }
    </Content>
  );
}

export default withSidebar(Replicas);
