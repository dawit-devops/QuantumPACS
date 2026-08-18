import React, { useCallback, useEffect, useState } from "react";
import { App, Button, Popconfirm, Space, Table, Tag, Typography } from "antd";
import { ReloadOutlined, RedoOutlined } from "@ant-design/icons";
import { PageState } from "../common/PageState";
import {
  listRisExceptions,
  retryRisException,
  type RisException,
} from "../api/ris";

const { Text } = Typography;

// S3-16: the exception queue (RIS-UI-37) — FAILED messages still inside
// their retry budget, with the per-message replay action backed by
// POST /ris/interfaces/exceptions/{id}/retry (S3-03 exception queue).
function ExceptionQueue() {
  const { message } = App.useApp();
  const [exceptions, setExceptions] = useState<RisException[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [retrying, setRetrying] = useState<string | null>(null);

  const fetch = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setExceptions(await listRisExceptions());
    } catch (e) {
      setError(
        e instanceof Error ? e.message : "Failed to load the exception queue",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetch();
  }, [fetch]);

  const handleRetry = async (id: string) => {
    setRetrying(id);
    try {
      const result = await retryRisException(id);
      if (result.retried) {
        message.success("Message replayed successfully");
      } else {
        message.warning(
          "Message is not eligible for retry (unknown or over budget)",
        );
      }
      await fetch();
    } catch (e) {
      message.error(e instanceof Error ? e.message : "Retry failed");
    } finally {
      setRetrying(null);
    }
  };

  const columns = [
    {
      title: "Received",
      dataIndex: "created_at",
      render: (v: string | null) => (v ? new Date(v).toLocaleString() : "—"),
    },
    {
      title: "Retries",
      dataIndex: "retry_count",
      width: 90,
      render: (v: number) => <Tag color={v >= 3 ? "red" : "orange"}>{v}/3</Tag>,
    },
    {
      title: "Error",
      dataIndex: "error_message",
      render: (v: string | null) => (
        <Text type="danger" ellipsis={{ tooltip: v ?? undefined }}>
          {v ?? "—"}
        </Text>
      ),
    },
    {
      title: "Action",
      key: "action",
      width: 120,
      render: (_: unknown, row: RisException) => (
        <Popconfirm
          title="Replay this message?"
          description="The raw message is re-parsed and routed again."
          onConfirm={() => handleRetry(row.id)}
        >
          <Button
            size="small"
            icon={<RedoOutlined />}
            loading={retrying === row.id}
            disabled={row.retry_count >= 3}
          >
            Retry
          </Button>
        </Popconfirm>
      ),
    },
  ];

  if (error) {
    return <PageState error={error} />;
  }

  return (
    <Space direction="vertical" style={{ width: "100%" }}>
      <Space>
        <Button icon={<ReloadOutlined />} onClick={() => void fetch()}>
          Refresh
        </Button>
        <Text type="secondary">
          {exceptions.length} message{exceptions.length === 1 ? "" : "s"}{" "}
          awaiting retry
        </Text>
      </Space>
      <Table
        rowKey="id"
        size="small"
        loading={loading}
        columns={columns}
        dataSource={exceptions}
        pagination={false}
      />
    </Space>
  );
}

export default ExceptionQueue;
