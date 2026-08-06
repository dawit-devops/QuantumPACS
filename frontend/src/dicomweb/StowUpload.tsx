import React, { useState } from "react";
import { Button, Card, List, Space, Tag, Typography, App, Result } from "antd";
import {
  InboxOutlined,
  DeleteOutlined,
  CloudUploadOutlined,
  CheckCircleOutlined,
} from "@ant-design/icons";
import withSidebar from "../common/base";
import { storeInstances, StowResult } from "../api/studies";

const { Text } = Typography;

/**
 * STOW-RS store page — upload raw DICOM files into the archive in one
 * multipart/related request (the DICOMweb native ingest path, vs. the
 * per-file /files/upload helper on the Files page).
 */
function StowUpload() {
  const { message } = App.useApp();
  const [files, setFiles] = useState<File[]>([]);
  const [storing, setStoring] = useState(false);
  const [result, setResult] = useState<StowResult | null>(null);

  const addFiles = (incoming: FileList | File[]) => {
    const list = Array.from(incoming).filter((f) => /\.dcm$/i.test(f.name));
    if (list.length === 0) {
      message.warning("Only .dcm files can be stored via STOW-RS");
      return;
    }
    setFiles((prev) => [...prev, ...list]);
    setResult(null);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    addFiles(e.dataTransfer.files);
  };

  const handleStore = async () => {
    if (files.length === 0) return;
    setStoring(true);
    setResult(null);
    try {
      const res = await storeInstances(files);
      setResult(res);
      const stored = Array.isArray(res.referenced) ? res.referenced.length : 0;
      const failed = Array.isArray(res.failed) ? res.failed.length : 0;
      message.success(
        stored > 0
          ? `Stored ${stored} instance${stored === 1 ? "" : "s"}`
          : "No instances stored",
      );
      if (failed > 0 && stored === 0) {
        message.error(`${failed} instance(s) failed to store`);
      }
    } catch (e: any) {
      message.error(e.message);
    } finally {
      setStoring(false);
    }
  };

  const storedCount = Array.isArray(result?.referenced)
    ? result!.referenced!.length
    : 0;
  const failedCount = Array.isArray(result?.failed)
    ? result!.failed!.length
    : 0;

  return (
    <div style={{ maxWidth: 720, margin: "16px auto" }}>
      <Card title="Store Studies (STOW-RS)" style={{ margin: 16 }}>
        <Text type="secondary" style={{ display: "block", marginBottom: 16 }}>
          Upload raw DICOM files directly to the archive via the DICOMweb
          STOW-RS endpoint. Files are validated and stored as a study/series.
        </Text>

        <div
          onDrop={handleDrop}
          onDragOver={(e) => e.preventDefault()}
          style={{
            border: "2px dashed var(--border-color, #d9d9d9)",
            borderRadius: 8,
            padding: "32px 16px",
            textAlign: "center",
            cursor: "pointer",
            background: "var(--bg-active, transparent)",
          }}
          onClick={() => document.getElementById("stow-file-input")?.click()}
          role="button"
          tabIndex={0}
          aria-label="Select DICOM files to store"
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ")
              document.getElementById("stow-file-input")?.click();
          }}
        >
          <input
            id="stow-file-input"
            type="file"
            multiple
            accept=".dcm,application/dicom"
            style={{ display: "none" }}
            onChange={(e) => {
              addFiles(e.target.files || []);
              e.target.value = "";
            }}
          />
          <InboxOutlined
            style={{
              fontSize: 48,
              color: "var(--color-primary, #0891B2)",
              marginBottom: 8,
            }}
          />
          <p style={{ margin: 0, fontWeight: 500 }}>
            Drag & drop .dcm files here
          </p>
          <p
            style={{
              margin: "4px 0 0",
              fontSize: 13,
              color: "var(--text-secondary, #64748b)",
            }}
          >
            or click to browse
          </p>
        </div>

        {files.length > 0 && (
          <List
            style={{ marginTop: 16 }}
            size="small"
            bordered
            dataSource={files}
            renderItem={(f, i) => (
              <List.Item
                actions={[
                  <Button
                    key="rm"
                    type="text"
                    icon={<DeleteOutlined />}
                    aria-label={`Remove ${f.name}`}
                    onClick={() =>
                      setFiles((prev) => prev.filter((_, idx) => idx !== i))
                    }
                  />,
                ]}
              >
                <Tag color="blue">.dcm</Tag>
                {f.name}
                <Text type="secondary" style={{ marginLeft: 8, fontSize: 12 }}>
                  {(f.size / 1024).toFixed(1)} KB
                </Text>
              </List.Item>
            )}
          />
        )}

        <Space style={{ marginTop: 16 }}>
          <Button
            type="primary"
            icon={<CloudUploadOutlined />}
            loading={storing}
            disabled={files.length === 0}
            onClick={handleStore}
          >
            Store to PACS
          </Button>
          {files.length > 0 && (
            <Button onClick={() => setFiles([])} disabled={storing}>
              Clear
            </Button>
          )}
        </Space>

        {result && (
          <Result
            style={{ marginTop: 8 }}
            status={failedCount > 0 && storedCount === 0 ? "error" : "success"}
            title={
              storedCount > 0
                ? `${storedCount} instance(s) stored`
                : "Nothing stored"
            }
            subTitle={
              failedCount > 0
                ? `${failedCount} instance(s) failed. Use the Files page upload for these files.`
                : undefined
            }
            extra={[
              <Button key="again" onClick={() => setFiles([])}>
                Store more files
              </Button>,
            ]}
          />
        )}
      </Card>
    </div>
  );
}

export default withSidebar(StowUpload);
