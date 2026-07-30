import React, { useState, useEffect } from 'react';
import { Layout, Table, message, Tag, Divider, Popconfirm, Modal, Select, Tooltip, Button, Space, Typography } from 'antd';
import { InfoCircleOutlined, CopyOutlined } from '@ant-design/icons';

const { Text } = Typography;
import withSidebar from '../common/base';
import { request } from '../helpers';
import { PageState } from '../common/PageState';
import { AddUser } from './EditUser';
import { BulkImport } from './BulkImport';

const Content = Layout.Content;

function Users() {
  document.title = 'QuantumPACS - Users';

  let [data, setData] = useState<any[]>([]);
  let [pagination, setPagination] = useState<any>({});
  let [loading, setLoading] = useState(false);
  let [error, setError] = useState<string | null>(null);
  let [password, setPassword] = useState<string | null>(null);
  let [roles, setRoles] = useState<any[]>([]);
  let [changingRole, setChangingRole] = useState<{ userId: number; roleId: number | null } | null>(null);

  useEffect(() => {
    request('roles').then((res: any) => {
      setRoles(res.data || []);
    }).catch(() => {});
  }, []);

  const columns: any[] = [
    {
      title: 'ID',
      dataIndex: 'id',
      sorter: true,
      width: '8%',
    },
    {
      title: 'Username',
      dataIndex: 'username',
      sorter: true,
      width: '18%',
    },
    {
      title: 'Role',
      dataIndex: 'role_name',
      render: (name: string, record: any) => {
        if (!name) return null;
        return (
          <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <Select
              value={record.role_id}
              style={{ width: 160 }}
              onChange={(roleId) => handleRoleChange(record.id, roleId)}
              options={roles.map((r: any) => ({ value: r.id, label: r.name }))}
              size="small"
            />
            <Tooltip title={`Role: ${name}\nPermissions: ${roles.find((r: any) => r.id === record.role_id)?.permissions?.join(', ') || 'N/A'}`}>
              <InfoCircleOutlined style={{ color: 'var(--text-secondary, #94a3b8)', cursor: 'pointer' }} />
            </Tooltip>
          </span>
        );
      },
    },
    {
      title: 'Admin',
      dataIndex: 'admin',
      render: (is_admin: boolean) => {
        const string = is_admin ? 'admin' : 'user';
        const color = is_admin ? 'green' : 'geekblue';
        return <Tag color={color}>{string.toUpperCase()}</Tag>;
      },
    },
    {
      title: 'Status',
      dataIndex: 'status',
      render: (s: string) => {
        const color = s === 'active' ? 'green' : 'gray';
        return <Tag color={color}>{s.toUpperCase()}</Tag>;
      },
    },
    {
      title: 'Action',
      key: 'action',
      render: (_: any, record: any) =>
        record.status === 'active' ? (
          <span>
            <a onClick={() => resetPassword(record.id)}>Reset password</a>
            <Divider type="vertical" />
            <Popconfirm title="Sure to deactivate?" onConfirm={() => deactivate(record.id)}>
              <a>Deactivate</a>
            </Popconfirm>
          </span>
        ) : null,
    },
  ];

  useEffect(() => {
    fetch();
  }, []);

  const handleTableChange = (pag: any, _filters: any, sorter: any) => {
    const pager = { ...pag };
    setPagination(Object.assign({}, pag, { current: pag.current }));
    fetch({ results: pag.pageSize, page: pag.current, sortField: sorter.field, sortOrder: sorter.order });
  };

  const fetch = (params?: any) => {
    setLoading(true);
    setError(null);
    request('users', params || {}).then((res: any) => {
      const pager = Object.assign({}, pagination, { total: res.data.length });
      setLoading(false);
      setData(res.data);
      setPagination(pager);
    }).catch((e: any) => {
      setLoading(false);
      setError(e.message);
      message.error(e.message);
    });
  };

  const handleRoleChange = (userId: number, roleId: number) => {
    setChangingRole({ userId, roleId });
    request('users/role', { data: { user_id: userId, role_id: roleId } }).then(() => {
      setChangingRole(null);
      fetch();
    }).catch((e: any) => {
      setChangingRole(null);
      message.error(e.message);
    });
  };

  const deactivate = (id: number) => {
    request('users/deactivate', { data: { id } }).then(fetch);
  };

  const resetPassword = (id: number) => {
    request('users/new_password', { data: { id } }).then((data: any) => {
      setPassword(data.password);
    });
  };

  return (
    <Content style={{ padding: 50 }}>
      <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
        <AddUser reload={fetch} />
        <BulkImport reload={fetch} />
      </div>
      <Modal
        open={password !== null}
        footer={null}
        onCancel={() => setPassword(null)}
        title="Password Reset"
      >
        <div style={{ marginBottom: 16 }}>
          <Text>New password for this user:</Text>
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <code style={{ fontSize: 16, background: '#f5f5f5', padding: '4px 8px', borderRadius: 4 }}>
            {password}
          </code>
          <Button
            size="small"
            icon={<CopyOutlined />}
            onClick={() => {
              navigator.clipboard.writeText(password || '');
              message.success('Password copied');
            }}
          >
            Copy
          </Button>
        </div>
        <Text type="secondary" style={{ display: 'block', marginTop: 12, fontSize: 12 }}>
          Share this password with the user. It will not be shown again.
        </Text>
      </Modal>
      <PageState error={error} onRetry={() => fetch()}
        empty={!loading && !error && data.length === 0}
        emptyMessage="No users found"
        emptyAction={<AddUser reload={fetch} />}
      >
        <Table
          scroll={{ x: 600 }}
          columns={columns}
          rowKey={(record: any) => record.id}
          dataSource={data}
          pagination={pagination}
          loading={loading}
          onChange={handleTableChange}
        />
      </PageState>
    </Content>
  );
}

export default withSidebar(Users);
