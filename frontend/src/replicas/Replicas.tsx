import { useDocumentTitle } from "../hooks";
import React, { useState, useEffect } from "react";
import {
  App,
  Layout,
  Table,
  Tag,
  Popconfirm,
  Divider,
  Form,
  Modal,
  InputNumber,
  Progress,
  Badge,
  Tooltip,
} from "antd";
import withSidebar from "../common/base";
import {
  listReplicas,
  createReplica,
  updateReplica,
  deleteReplica,
  type Replica,
} from "../api/replicas";
import { PageState } from "../common/PageState";
import { AddReplica } from "./EditReplica";

const Content = Layout.Content;

export function EditDelay(props: any) {
  const { form, replica, onCancel, onCreate } = props;
  const delay = replica ? replica.delay : 0;
  return (
    <Modal
      open={true}
      title="Edit delay"
      okText="Update"
      onCancel={onCancel}
      onOk={onCreate}
    >
      <Form form={form} layout="vertical">
        <Form.Item
          name="delay"
          label="Delay (in minutes)"
          initialValue={delay}
          rules={[{ required: true, message: "Please replica's delay!" }]}
        >
          <InputNumber />
        </Form.Item>
      </Form>
    </Modal>
  );
}

function Replicas() {
  const { message } = App.useApp();
  useDocumentTitle("QuantumPACS - Replicas");

  const [data, setData] = useState<Replica[]>([]);
  const [pagination, setPagination] = useState<any>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currReplica, setCurrReplica] = useState<Replica | null>(null);
  const [editDelayForm] = Form.useForm();

  useEffect(() => {
    // Replica status has no server push channel, so poll — but only while the
    // tab is visible and never overlapping an in-flight request. The old
    // blind 2s poll ran 1,800 req/h even in the background and stacked
    // overlapping fetches under slow responses.
    let inFlight = false;
    const refresh = () => {
      if (document.visibilityState !== "visible" || inFlight) return;
      inFlight = true;
      listReplicas()
        .then((res) => {
          setData(res);
          setPagination((p: any) =>
            Object.assign({}, p, { total: res.length }),
          );
        })
        .catch((e: any) => {
          setError(e.message);
          message.error(e.message);
        })
        .finally(() => {
          inFlight = false;
        });
    };
    const id = setInterval(refresh, 10000);
    const onWake = () => {
      if (document.visibilityState === "visible") refresh();
    };
    document.addEventListener("visibilitychange", onWake);
    window.addEventListener("focus", onWake);
    return () => {
      clearInterval(id);
      document.removeEventListener("visibilitychange", onWake);
      window.removeEventListener("focus", onWake);
    };
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

  const fetch = (showLoading?: any) => {
    if (showLoading !== false) setLoading(true);
    setError(null);
    listReplicas()
      .then((res) => {
        const pager = Object.assign({}, pagination, { total: res.length });
        if (showLoading !== false) setLoading(false);
        setData(res);
        setPagination(pager);
      })
      .catch((e: any) => {
        setLoading(false);
        setError(e.message);
        message.error(e.message);
      });
  };

  const editDelayCancel = () => {
    setCurrReplica(null);
  };

  const updateDelay = () => {
    editDelayForm
      .validateFields()
      .then((values: any) => {
        if (!currReplica) return;
        updateReplica(currReplica.id, values)
          .then(() => {
            editDelayForm.resetFields();
            setCurrReplica(null);
          })
          .then(fetch)
          .catch(() => {
            message.error("Delay failed to update");
          });
      })
      .catch(() => {});
  };

  const setMaster = (replica: any) => {
    updateReplica(replica.id, { master: true })
      .then(fetch)
      .catch(() => message.error("Failed to change master"));
  };

  const handleDelete = (replica: number) => {
    deleteReplica(replica)
      .then(fetch)
      .catch(() => {
        message.error("Deletion failed");
      });
  };

  const healthColor = (status: string) => {
    if (status === "ok") return "green";
    if (status === "degraded") return "orange";
    return "red";
  };

  const columns: any[] = [
    {
      title: "ID",
      dataIndex: "id",
      render: (id: string) => (
        <code style={{ fontSize: 12 }}>{id.slice(0, 8)}</code>
      ),
    },
    { title: "Type", dataIndex: "type" },
    {
      title: "Role",
      dataIndex: "master",
      width: "8%",
      render: (master: boolean) => {
        const label = master ? "Master" : "Replica";
        return <Tag color={master ? "green" : "geekblue"}>{label}</Tag>;
      },
    },
    {
      title: "Health",
      dataIndex: "status",
      width: "10%",
      render: (status: string) => {
        if (!status) return <Tag color="default">Unknown</Tag>;
        return (
          <Tooltip title={`Status: ${status}`}>
            <Badge
              status={
                status === "ok"
                  ? "success"
                  : status === "degraded"
                    ? "warning"
                    : "error"
              }
            />
            <Tag color={healthColor(status)} style={{ marginLeft: 4 }}>
              {status.toUpperCase()}
            </Tag>
          </Tooltip>
        );
      },
    },
    { title: "Location", dataIndex: "location" },
    {
      title: "Delay",
      dataIndex: "delay",
      render: (d: number) => (d != null ? `${d} min` : "-"),
    },
    {
      title: "Files",
      dataIndex: "files",
      width: "8%",
    },
    {
      title: "Sync Progress",
      key: "progress",
      width: "14%",
      render: (_: any, record: any) => {
        if (record.master) return <Tag color="green">Source</Tag>;
        return (
          <Progress
            percent={record.sync_progress || 0}
            size="small"
            status={record.sync_progress === 100 ? "success" : "active"}
            strokeColor={record.sync_progress === 100 ? "#22c55e" : "#0891B2"}
          />
        );
      },
    },
    {
      title: "Action",
      key: "action",
      render: (_: any, record: any) =>
        !record.master || (record.master && data.length === 1) ? (
          <span>
            {!record.master && (
              <span>
                <a onClick={() => setCurrReplica(record)}>Update delay</a>
                <Divider type="vertical" />
                <a onClick={() => setMaster(record)}>Set master</a>
                <Divider type="vertical" />
              </span>
            )}
            <Popconfirm
              title="Sure to delete?"
              onConfirm={() => handleDelete(record.id)}
            >
              <a>Delete</a>
            </Popconfirm>
          </span>
        ) : null,
    },
  ];

  return (
    <Content style={{ padding: 50 }}>
      <AddReplica style={{ marginBottom: 10 }} reload={fetch} />
      <PageState
        error={error}
        onRetry={() => fetch()}
        empty={!loading && !error && data.length === 0}
        emptyMessage="No replicas configured"
      >
        <Table
          scroll={{ x: 500 }}
          columns={columns}
          rowKey={(record: any) => record.id}
          dataSource={data}
          pagination={pagination}
          loading={loading}
          onChange={handleTableChange}
        />
      </PageState>
      {currReplica !== null && (
        <EditDelay
          form={editDelayForm}
          replica={currReplica}
          onCancel={editDelayCancel}
          onCreate={updateDelay}
        />
      )}
    </Content>
  );
}

export default withSidebar(Replicas);
