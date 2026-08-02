import { useState, useCallback, useRef } from "react";
import { message } from "antd";
import { InboxOutlined } from "@ant-design/icons";
import { API_URL } from "../config";
import { getAccessToken } from "../helpers";
import { UploadProgress } from "./UploadProgress";
import type { UploadFileItem, UploadStatus } from "./UploadProgress";

let fileIdCounter = 0;

function nextFileId(): string {
  fileIdCounter += 1;
  return `upload-${Date.now()}-${fileIdCounter}`;
}

function uploadFile(
  file: File,
  onProgress: (pct: number) => void,
  signal: AbortSignal,
): Promise<Response> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    const formData = new FormData();
    formData.append("file", file);

    xhr.upload.addEventListener("progress", (e) => {
      if (e.lengthComputable) {
        onProgress(Math.round((e.loaded / e.total) * 100));
      }
    });

    xhr.addEventListener("load", () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(new Response(xhr.responseText, { status: xhr.status }));
      } else {
        reject(new Error(`Upload failed (${xhr.status})`));
      }
    });

    xhr.addEventListener("error", () => reject(new Error("Network error")));
    xhr.addEventListener("abort", () => reject(new Error("Cancelled")));

    signal.addEventListener("abort", () => {
      xhr.abort();
      reject(new Error("Cancelled"));
    });

    xhr.open("POST", `${API_URL}/files/upload`);
    xhr.setRequestHeader("X-Auth-Pacs", getAccessToken() || "");
    xhr.setRequestHeader("X-CSRF-Token", "1");
    xhr.send(formData);
  });
}

interface UploadZoneProps {
  reload?: () => void;
}

export function UploadZone({ reload }: UploadZoneProps) {
  const [queue, setQueue] = useState<UploadFileItem[]>([]);
  const queueRef = useRef<UploadFileItem[]>(queue);

  const updateFile = useCallback(
    (id: string, patch: Partial<UploadFileItem>) => {
      setQueue((prev) => {
        const next = prev.map((f) => (f.id === id ? { ...f, ...patch } : f));
        queueRef.current = next;
        return next;
      });
    },
    [],
  );

  const removeFile = useCallback((id: string) => {
    setQueue((prev) => prev.filter((f) => f.id !== id));
  }, []);

  const fileRefs = useRef<Map<string, File>>(new Map());

  const startUpload = useCallback(
    (file: File) => {
      const id = nextFileId();
      fileRefs.current.set(id, file);
      const controller = new AbortController();
      const entry: UploadFileItem = {
        id,
        name: file.name,
        size: file.size,
        status: "pending",
        progress: 0,
        controller,
      };
      setQueue((prev) => {
        const next = [...prev, entry];
        queueRef.current = next;
        return next;
      });

      updateFile(id, { status: "uploading" });

      uploadFile(
        file,
        (pct) => updateFile(id, { progress: pct }),
        controller.signal,
      )
        .then(async (resp) => {
          try {
            const json = await resp.json();
            if (json.duplicate) {
              updateFile(id, {
                status: "done",
                progress: 100,
                error: "File already exists",
              });
            } else if (json.error) {
              updateFile(id, {
                status: "error",
                error: json.error,
                progress: 0,
              });
              return;
            }
          } catch {
            // Unparseable server response — treat as a failed upload instead
            // of silently marking the file done (Q-18).
            updateFile(id, { status: "error", error: "Bad server response", progress: 0 });
            return;
          }
          updateFile(id, { status: "done", progress: 100 });
          reload?.();
          setTimeout(() => removeFile(id), 3000);
        })
        .catch((err: Error) => {
          if (err.message === "Cancelled") {
            updateFile(id, { status: "cancelled", progress: 0 });
            setTimeout(() => removeFile(id), 2000);
          } else {
            updateFile(id, {
              status: "error",
              error: err.message,
              progress: 0,
            });
          }
        });
    },
    [updateFile, removeFile, reload],
  );

  const MAX_UPLOAD_BYTES = 500 * 1024 * 1024;

  const enqueueFile = useCallback(
    (file: File) => {
      if (file.size > MAX_UPLOAD_BYTES) {
        const id = nextFileId();
        const entry: UploadFileItem = {
          id,
          name: file.name,
          size: file.size,
          status: "error",
          progress: 0,
          error: "File exceeds 500MB limit",
        };
        setQueue((prev) => {
          const next = [...prev, entry];
          queueRef.current = next;
          return next;
        });
        setTimeout(() => removeFile(id), 5000);
        return;
      }
      startUpload(file);
    },
    [startUpload, removeFile],
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      const files = Array.from(e.dataTransfer.files);
      for (const file of files) {
        enqueueFile(file);
      }
    },
    [enqueueFile],
  );

  const handleFileSelect = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const files = Array.from(e.target.files || []);
      for (const file of files) {
        enqueueFile(file);
      }
      e.target.value = "";
    },
    [enqueueFile],
  );

  const handleCancel = useCallback(
    (id: string) => {
      const file = queueRef.current.find((f) => f.id === id);
      file?.controller?.abort();
      updateFile(id, { status: "cancelled", progress: 0 });
      setTimeout(() => removeFile(id), 2000);
    },
    [updateFile, removeFile],
  );

  const handleRetry = useCallback(
    (id: string) => {
      const entry = queueRef.current.find((f) => f.id === id);
      if (!entry) return;
      const originalFile = fileRefs.current.get(id);
      if (!originalFile) {
        updateFile(id, {
          status: "error",
          error: "Original file not available",
        });
        return;
      }
      const newController = new AbortController();
      updateFile(id, {
        status: "pending",
        progress: 0,
        error: undefined,
        controller: newController,
      });
      setTimeout(() => {
        const current = queueRef.current.find((f) => f.id === id);
        if (!current || current.status !== "pending") return;
        updateFile(id, { status: "uploading" });
        uploadFile(
          originalFile,
          (pct) => updateFile(id, { progress: pct }),
          newController.signal,
        )
          .then(async (resp) => {
            try {
              const json = await resp.json();
              if (json.error) {
                updateFile(id, {
                  status: "error",
                  error: json.error,
                  progress: 0,
                });
                return;
              }
            } catch {
              updateFile(id, { status: "error", error: "Bad server response", progress: 0 });
              return;
            }
            updateFile(id, { status: "done", progress: 100 });
            reload?.();
            setTimeout(() => removeFile(id), 3000);
          })
          .catch((err: Error) => {
            if (err.message === "Cancelled") {
              updateFile(id, { status: "cancelled", progress: 0 });
              setTimeout(() => removeFile(id), 2000);
            } else {
              updateFile(id, {
                status: "error",
                error: err.message,
                progress: 0,
              });
            }
          });
      }, 100);
    },
    [updateFile, removeFile, reload],
  );

  const handleCancelAll = useCallback(() => {
    for (const file of queueRef.current) {
      if (file.status === "pending" || file.status === "uploading") {
        file.controller?.abort();
      }
    }
    setQueue([]);
    queueRef.current = [];
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
  }, []);

  const activeCount = queue.filter(
    (f) => f.status === "pending" || f.status === "uploading",
  ).length;

  return (
    <div>
      <div
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        style={{
          border: "2px dashed var(--border-color, #d9d9d9)",
          borderRadius: 8,
          padding: "32px 16px",
          textAlign: "center",
          cursor: "pointer",
          transition: "border-color 0.2s, background 0.2s",
          background:
            activeCount > 0 ? "var(--bg-active, #f0fdfa)" : "transparent",
        }}
        onClick={() => document.getElementById("upload-file-input")?.click()}
        role="button"
        tabIndex={0}
        aria-label="Upload DICOM files"
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ")
            document.getElementById("upload-file-input")?.click();
        }}
      >
        <input
          id="upload-file-input"
          type="file"
          multiple
          accept=".dcm,application/dicom"
          onChange={handleFileSelect}
          style={{ display: "none" }}
        />
        <InboxOutlined
          style={{
            fontSize: 48,
            color: "var(--color-primary, #0891B2)",
            marginBottom: 8,
          }}
        />
        <p style={{ margin: 0, fontWeight: 500 }}>
          Drag & drop DICOM files here
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
      <UploadProgress
        files={queue}
        onCancel={handleCancel}
        onRetry={handleRetry}
        onCancelAll={handleCancelAll}
      />
    </div>
  );
}
