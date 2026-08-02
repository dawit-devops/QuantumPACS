import React, { useState, useEffect } from "react";
import { Table, message, Tag } from "antd";
import { listFileChanges } from "../api/files";

const columns = [
  {
    title: "time",
    dataIndex: "created",
    width: "30%",
    render: (data: number) => new Date(data * 1000).toUTCString(),
  },
  {
    title: "username",
    dataIndex: "username",
    width: "10%",
  },
  {
    title: "change",
    dataIndex: "type",
    width: "70%",
    render: (data: string) => {
      return <Tag color="orange">{data}</Tag>;
    },
  },
];

function Changes(props: any) {
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
    setPagination(
      Object.assign({}, pagination, { current: pagination.current }),
    );
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
    listFileChanges(props.file.id, params || {})
      .then((data: any) => {
        const pager = Object.assign({}, pagination, {
          total: data.data.length,
        });
        setLoading(false);
        setData(data.data);
        setPagination(pager);
      })
      .catch((e: any) => {
        setLoading(false);
        message.error(e.message);
      });
  };

  return (
    <Table
      scroll={{ x: 500 }}
      columns={columns}
      rowKey={(record: any) => record.id}
      dataSource={data}
      pagination={pagination}
      loading={loading}
      onChange={handleTableChange}
    />
  );
}

export default Changes;
