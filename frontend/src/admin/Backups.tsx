import { useDocumentTitle } from "../hooks";
import React, { useCallback, useEffect, useState } from "react";
import {
  App,
  Layout,
  Card,
  Table,
  Button,
  Space,
  Tag,
  Typography,
  Popconfirm,
  Alert,
  Modal,
  Descriptions,
} from "antd";
import {
  CloudUploadOutlined,
  DownloadOutlined,
  DeleteOutlined,
  SafetyCertificateOutlined,
  ReloadOutlined,
} from "@ant-design/icons";
import withSidebar from "../common/base";
import PageHeader from "../common/PageHeader";
import { PageState } from "../common/PageState";
import {
  listBackups,
  createBackup,
  deleteBackup,
  downloadBackup,
  verifyBackup,
  type Backup,
} from "../api/admin";

const { Content } = Layout;
const { Text } = Typography;

function formatBytes(bytes: number): string {
  if (!bytes) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB"];
  let i = 0;
  let val = bytes;
  while (val >= 1024 && i < units.length - 1) {
    val /= 1024;
    i += 1;
  }
  return `${val.toFixed(1)} ${units[i]}`;
}

function Backups() {
  const { message } = App.useApp();
  useDocumentTitle("QuantumPACS - Backups");
  const [data, setData] = useState<Backup[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [verifyOpen, setVerifyOpen] = useState(false);
  const [verification, setVerification] = useState<any>(null);
  const [verifying, setVerifying] = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    listBackups()
      .then((res) => setData(Array.isArray(res.data) ? res.data : []))
      .catch((e: any) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const runBackup = async () => {
    setCreating(true);
    try {
      const res = await createBackup();
      message.success(`Backup created (${res.data.files_count} files)`);
      load();
    } catch (e: any) {
      message.error(e.message);
    } finally {
      setCreating(false);
    }
  };

  const removeBackup = async (id: string) => {
    try {
      await deleteBackup(id);
      message.success("Backup deleted");
      load();
    } catch (e: any) {
      message.error(e.message);
    }
  };

  const openVerify = async (record: Backup) => {
    setVerifyOpen(true);
    setVerifying(true);
    setVerification(null);
    try {
      const res = await verifyBackup(record.id);
      setVerification(res.verification);
    } catch (e: any) {
      message.error(e.message);
      setVerifyOpen(false);
    } finally {
      setVerifying(false);
    }
  };

  const newest = data.find((b) => b.status === "completed");
  const stale = newest && new Date(newest.created_at).getTime() < Date.now() - 7 * 86400000;

  return (
    <Content style={{ padding: 24 }}>
      <PageHeader
        title="Backups"
        description="Point-in-time metadata snapshots of the archive, stored on the master replica. Download an artifact as the recovery path."
        extra={
          <Space>
            <Button
              type="primary"
              icon={<CloudUploadOutlined />}
              loading={creating}
              onClick={runBackup}
            >
              Back up now
            </Button>
            <Button icon={<ReloadOutlined />} onClick={load}>
              Refresh
            </Button>
          </Space>
        }
      />

      {stale && (
        <Alert
          type="warning"
          showIcon
          style={{ marginBottom: 16 }}
          message={`Newest backup is older than 7 days (${new Date(newest!.created_at).toLocaleString()})`}
        />
      )}

      <PageState
        loading={loading}
        error={error}
        onRetry={load}
        empty={!loading && !error && data.length === 0}
        emptyMessage="No backups yet — run your first backup to snapshot the archive metadata."
      >
        <Table
          rowKey="id"
          dataSource={data}
          loading={loading}
          columns={[
            {
              title: "Created",
              dataIndex: "created_at",
              render: (t: string) => (t ? new Date(t).toLocaleString() : "—"),
            },
            {
              title: "Status",
              dataIndex: "status",
              render: (s: string) =>
                s === "completed" ? (
                  <Tag color="green">COMPLETED</Tag>
                ) : s === "failed" ? (
                  <Tag color="red">FAILED</Tag>
                ) : (
                  <Tag color="orange">RUNNING</Tag>
                ),
            },
            {
              title: "Files",
              dataIndex: "files_count",
              render: (n: number) => n ?? "—",
            },
            {
              title: "Archive bytes",
              dataIndex: "bytes_count",
              render: (n: number) => formatBytes(n ?? 0),
            },
            {
              title: "Artifact size",
              dataIndex: "size_bytes",
              render: (n: number) => formatBytes(n ?? 0),
            },
            {
              title: "Action",
              key: "action",
              width: 260,
              render: (_: unknown, record: Backup) =>
                record.status === "completed" ? (
                  <Space size={4}>
                    <Button
                      size="small"
                      icon={<SafetyCertificateOutlined />}
                      onClick={() => openVerify(record)}
                    >
                      Verify
                    </Button>
                    <Button
                      size="small"
                      icon={<DownloadOutlined />}
                      onClick={() => downloadBackup(record.id).catch((e) => message.error(e.message))}
                    >
                      Download
                    </Button>
                    <Popconfirm
                      title="Delete this backup?"
                      description="Removes the artifact from storage. This cannot be undone."
                      onConfirm={() => removeBackup(record.id)}
                    >
                      <Button size="small" danger icon={<DeleteOutlined />} />
                    </Popconfirm>
                  </Space>
                ) : null,
            },
          ]}
        />
      </PageState>

      <Modal
        title="Backup verification"
        open={verifyOpen}
        onCancel={() => setVerifyOpen(false)}
        footer={
          <Button type="primary" onClick={() => setVerifyOpen(false)}>
            Close
          </Button>
        }
      >
        {verifying ? (
          <Text type="secondary">Verifying artifact…</Text>
        ) : (
          verification && (
            <Descriptions column={1} size="small">
              <Descriptions.Item label="Backup ID">
                <Text code>{verification.backup_id}</Text>
              </Descriptions.Item>
              <Descriptions.Item label="Kind">
                {verification.kind ?? "—"}
              </Descriptions.Item>
              <Descriptions.Item label="Generated at">
                {verification.generated_at ?? "—"}
              </Descriptions.Item>
              <Descriptions.Item label="Files">{verification.files}</Descriptions.Item>
              <Descriptions.Item label="Archive bytes">
                {formatBytes(verification.bytes)}
              </Descriptions.Item>
              <Descriptions.Item label="Master replica">
                {verification.master_replica ?? "—"}
              </Descriptions.Item>
            </Descriptions>
          )
        )}
        {verification?.valid && (
          <Alert
            style={{ marginTop: 12 }}
            type="success"
            showIcon
            message="Artifact verified — download it to recover this snapshot"
          />
        )}
      </Modal>
    </Content>
  );
}

export default withSidebar(Backups);
