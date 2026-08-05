import React, { useState, useEffect } from 'react';
import { Layout, Table, message } from 'antd';
import withSidebar from '../common/base';
import { request } from '../helpers';

const Content = Layout.Content;

const columns: any[] = [
  {
    title: 'Time',
    dataIndex: 'created',
    width: '20%',
    render: (data: number) => new Date(data * 1000).toUTCString(),
  },
  {
    title: 'Log',
    dataIndex: 'log',
    render: (data: string) => {
      const lines = data.split('\n');
      return lines.slice(-2);
    }
  }
];

function Logs() {
  document.title = 'QuantumPACS - Logs';

  let [data, setData] = useState<any[]>([]);
  let [pagination, setPagination] = useState<any>({});
  let [loading, setLoading] = useState(false);

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
    request('logs', params || {}).then((data: any) => {
      const pager = Object.assign({}, pagination, { total: data.data.length });
      setLoading(false);
      setData(data.data);
      setPagination(pager);
    }).catch((e: any) => {
      setLoading(false);
      message.error(e.message);
    });
  };

  return (
    <Content style={{
      alignItems: 'center',
      justifyContent: 'center',
      padding: 50
    }}>
      <Table
        columns={columns}
        rowKey={(record: any) => record.id}
        expandedRowRender={(record: any) => <p style={{ margin: 0 }}>{record.log}</p>}
        dataSource={data}
        pagination={pagination}
        loading={loading}
        onChange={handleTableChange}
      />
    </Content>
  );
}

export default withSidebar(Logs);
