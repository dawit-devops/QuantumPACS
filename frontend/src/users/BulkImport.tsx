import { useState, useRef } from "react";
import {
  App,
  Modal,
  Button,
  Upload,
  Table,
  Tag,
  Typography,
  Progress,
} from "antd";
import { UploadOutlined, InboxOutlined } from "@ant-design/icons";
import { createUser } from "../api/users";

const { Text } = Typography;

interface ImportRow {
  username: string;
  admin: boolean;
  status?: "pending" | "success" | "error";
  error?: string;
}

interface BulkImportProps {
  reload?: () => void;
}

export function BulkImport({ reload }: BulkImportProps) {
  const { message } = App.useApp();
  const [visible, setVisible] = useState(false);
  const [rows, setRows] = useState<ImportRow[]>([]);
  const [importing, setImporting] = useState(false);
  const [progress, setProgress] = useState(0);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFile = (file: File) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      const text = e.target?.result as string;
      const lines = text.split("\n").filter(Boolean);
      const parsed: ImportRow[] = [];
      for (let i = 1; i < lines.length; i++) {
        const parts = lines[i].split(",").map((s) => s.trim());
        if (parts[0]) {
          parsed.push({
            username: parts[0],
            admin: parts[1]?.toLowerCase() === "true" || parts[1] === "1",
          });
        }
      }
      if (parsed.length === 0) {
        message.warning("No valid rows found in CSV. Format: username,admin");
        return;
      }
      setRows(parsed);
    };
    reader.readAsText(file);
  };

  const doImport = async () => {
    setImporting(true);
    setProgress(0);
    let success = 0;
    let fail = 0;
    for (let i = 0; i < rows.length; i++) {
      const row = rows[i];
      try {
        await createUser({ username: row.username, admin: row.admin });
        rows[i] = { ...row, status: "success" };
        success++;
      } catch (e: any) {
        rows[i] = { ...row, status: "error", error: e.message };
        fail++;
      }
      setProgress(Math.round(((i + 1) / rows.length) * 100));
      setRows([...rows]);
    }
    setImporting(false);
    message.success(
      `Imported ${success} users${fail > 0 ? `, ${fail} failed` : ""}`,
    );
    if (success > 0) reload?.();
  };

  const columns = [
    { title: "Username", dataIndex: "username", key: "username" },
    {
      title: "Admin",
      dataIndex: "admin",
      key: "admin",
      render: (v: boolean) =>
        v ? <Tag color="green">Yes</Tag> : <Tag color="default">No</Tag>,
    },
    {
      title: "Status",
      key: "status",
      render: (_: any, record: ImportRow) => {
        if (!record.status) return <Text type="secondary">Pending</Text>;
        if (record.status === "success")
          return <Tag color="success">Imported</Tag>;
        return (
          <Tag color="error" title={record.error}>
            Failed
          </Tag>
        );
      },
    },
  ];

  return (
    <>
      <Button onClick={() => setVisible(true)} icon={<UploadOutlined />}>
        Bulk Import
      </Button>
      <Modal
        title="Bulk Import Users"
        open={visible}
        onCancel={() => {
          setVisible(false);
          setRows([]);
        }}
        footer={
          rows.length > 0 ? (
            <Button
              type="primary"
              onClick={doImport}
              loading={importing}
              disabled={importing}
            >
              Import {rows.length} Users
            </Button>
          ) : null
        }
        width={600}
      >
        <div
          style={{
            border: "2px dashed var(--border-color, #d9d9d9)",
            borderRadius: 8,
            padding: 24,
            textAlign: "center",
            cursor: "pointer",
            marginBottom: 16,
          }}
          onClick={() => fileInputRef.current?.click()}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv"
            style={{ display: "none" }}
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) handleFile(file);
              e.target.value = "";
            }}
          />
          <InboxOutlined
            style={{
              fontSize: 36,
              color: "var(--color-primary, #0891B2)",
              marginBottom: 8,
            }}
          />
          <p style={{ margin: 0 }}>Click to select CSV file</p>
          <Text type="secondary" style={{ fontSize: 12 }}>
            Format: username,admin (one per line)
          </Text>
        </div>
        {importing && (
          <Progress
            percent={progress}
            status="active"
            style={{ marginBottom: 12 }}
          />
        )}
        {rows.length > 0 && (
          <Table
            dataSource={rows}
            columns={columns}
            rowKey="username"
            pagination={false}
            size="small"
          />
        )}
      </Modal>
    </>
  );
}
