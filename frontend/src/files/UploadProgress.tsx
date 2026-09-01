import { Button, Progress, Tag, Typography } from "antd";
import {
  CloseCircleOutlined,
  CloseOutlined,
  ReloadOutlined,
} from "@ant-design/icons";

const { Text } = Typography;

export type UploadStatus =
  "pending" | "uploading" | "done" | "error" | "cancelled";

export interface UploadFileItem {
  id: string;
  name: string;
  size: number;
  status: UploadStatus;
  progress: number;
  error?: string;
  info?: string;
  controller?: AbortController;
}

interface UploadProgressProps {
  files: UploadFileItem[];
  onCancel: (id: string) => void;
  onRetry: (id: string) => void;
  onCancelAll: () => void;
}

const STATUS_LABELS: Record<UploadStatus, { label: string; color: string }> = {
  pending: { label: "Pending", color: "default" },
  uploading: { label: "Uploading", color: "processing" },
  done: { label: "Done", color: "success" },
  error: { label: "Error", color: "error" },
  cancelled: { label: "Cancelled", color: "warning" },
};

function formatSize(bytes: number): string {
  if (!bytes) return "0 B";
  const units = ["B", "KB", "MB"];
  let i = 0;
  let val = bytes;
  while (val >= 1024 && i < units.length - 1) {
    val /= 1024;
    i++;
  }
  return `${val.toFixed(i === 0 ? 0 : 1)} ${units[i]}`;
}

export function UploadProgress({
  files,
  onCancel,
  onRetry,
  onCancelAll,
}: UploadProgressProps) {
  const total = files.length;
  const done = files.filter((f) => f.status === "done").length;
  const hasActive = files.some(
    (f) => f.status === "pending" || f.status === "uploading",
  );

  if (total === 0) return null;

  return (
    <div style={{ marginTop: 16 }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 8,
        }}
      >
        <Text strong>
          Uploading {done} of {total} files
        </Text>
        {hasActive && (
          <Button
            size="small"
            icon={<CloseOutlined />}
            onClick={onCancelAll}
            danger
          >
            Cancel All
          </Button>
        )}
      </div>
      <div
        style={{
          maxHeight: 240,
          overflowY: "auto",
          display: "flex",
          flexDirection: "column",
          gap: 8,
        }}
      >
        {files.map((file) => (
          <div
            key={file.id}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              padding: "6px 8px",
              borderRadius: 6,
              background:
                file.status === "error"
                  ? "var(--bg-error, #fef2f2)"
                  : "var(--bg-muted, #f8fafc)",
            }}
          >
            <div style={{ flex: 1, minWidth: 0 }}>
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  marginBottom: 2,
                }}
              >
                <Text ellipsis style={{ fontSize: 13, maxWidth: 200 }}>
                  {file.name}
                </Text>
                <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
                  <Tag
                    color={STATUS_LABELS[file.status].color}
                    style={{ margin: 0, fontSize: 11, lineHeight: "18px" }}
                  >
                    {STATUS_LABELS[file.status].label}
                  </Tag>
                  <Text type="secondary" style={{ fontSize: 11 }}>
                    {formatSize(file.size)}
                  </Text>
                </span>
              </div>
              {(file.status === "uploading" || file.status === "pending") && (
                <Progress
                  percent={file.progress}
                  size="small"
                  showInfo={false}
                  strokeColor="var(--color-primary, #0891B2)"
                />
              )}
              {file.status === "error" && file.error && (
                <Text type="danger" style={{ fontSize: 11, display: "block" }}>
                  {file.error}
                </Text>
              )}
              {file.info && (
                <Text
                  type={file.status === "error" ? "danger" : "secondary"}
                  style={{ fontSize: 11, display: "block" }}
                >
                  {file.info}
                </Text>
              )}
            </div>
            <div style={{ display: "flex", gap: 4, flexShrink: 0 }}>
              {(file.status === "pending" || file.status === "uploading") && (
                <Button
                  size="small"
                  type="text"
                  icon={<CloseCircleOutlined />}
                  onClick={() => onCancel(file.id)}
                  aria-label={`Cancel ${file.name}`}
                />
              )}
              {file.status === "error" && (
                <Button
                  size="small"
                  type="text"
                  icon={<ReloadOutlined />}
                  onClick={() => onRetry(file.id)}
                  aria-label={`Retry ${file.name}`}
                />
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
