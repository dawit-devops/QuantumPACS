import React, { useState, useEffect } from 'react';
import { Layout, Table, message, Tag, Divider, Popconfirm, Modal } from 'antd';
import withSidebar from '../common/base';
import { request } from '../helpers';
import { AddUser } from './EditUser';

const Content = Layout.Content;

function Users() {
  document.title = 'Users';

  let [data, setData] = useState<any[]>([]);
  let [pagination, setPagination] = useState<any>({});
  let [loading, setLoading] = useState(false);
  let [password, setPassword] = useState<string | null>(null);

  const columns: any[] = [
    {
      title: 'ID',
      dataIndex: 'id',
      sorter: true,
      width: '20%',
    },
    {
      title: 'Username',
      dataIndex: 'username',
      sorter: true,
      width: '20%',
    },
    {
      title: 'Admin',
      dataIndex: 'admin',
      render: (is_admin: boolean) => {
        const string = is_admin ? 'admin' : 'user';
        const color = is_admin ? 'green' : 'geekblue';
        return (
          <Tag color={color} key={string}>
            {string.toUpperCase()}
          </Tag>
        );
      }
    },
    {
      title: 'Status',
      dataIndex: 'status',
      render: (s: string) => {
        const color = s === 'active' ? 'green' : 'gray';
        return (
          <Tag color={color} key={s}>
            {s.toUpperCase()}
          </Tag>
        );
      }
    },
    {
      title: 'Action',
      key: 'action',
      render: (text: any, record: any) =>
        record.status === 'active' ? (
          <span>
            {/* eslint-disable-next-line */}
            <a onClick={() => resetPassword(record.id)}>Reset password</a>
            <Divider type="vertical" />
            <Popconfirm title="Sure to deactivate?" onConfirm={() => deactivate(record.id)}>
              {/* eslint-disable-next-line */}
              <a>Deactivate</a>
            </Popconfirm>
          </span>
        ) : null
    },
  ];

  useEffect(() => {
    fetch();
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

  const fetch = (params?: any) => {
    setLoading(true);
    request('users', params || {}).then((data: any) => {
      const pager = Object.assign({}, pagination, { total: data.data.length });
      setLoading(false);
      setData(data.data);
      setPagination(pager);
    }).catch((e: any) => {
      setLoading(false);
      message.error(e.message);
    });
  };

  const deactivate = (id: number) => {
    request('users/deactivate', { data: { id: id } }).then(fetch);
  };

  const resetPassword = (id: number) => {
    request('users/new_password', { data: { id: id } }).then((data: any) => {
      setPassword(data.password);
    });
  };

  return (
    <Content style={{
      alignItems: 'center',
      justifyContent: 'center',
      padding: 50
    }}>
      <AddUser style={{ marginBottom: 10 }} reload={fetch} />
      <Modal
        open={password !== null}
        footer={null}
        onCancel={() => setPassword(null)}
        title='New password'
      >
        <p>{password}</p>
      </Modal>
      <Table
        scroll={{ x: 500 }}
        columns={columns}
        rowKey={(record: any) => record.id}
        dataSource={data}
        pagination={pagination}
        loading={loading}
        onChange={handleTableChange}
      />
    </Content>
  );
}

export default withSidebar(Users);
