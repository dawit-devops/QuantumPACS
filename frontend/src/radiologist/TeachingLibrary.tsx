import React, { useCallback, useEffect, useState } from "react";
import {
  Card,
  Tag,
  Select,
  Input,
  Button,
  Drawer,
  Spin,
  Alert,
  Space,
} from "antd";
import { BookOutlined } from "@ant-design/icons";
import { useDocumentTitle } from "../hooks";
import { request } from "../helpers";
import withSidebar from "../common/base";
import "./TeachingLibrary.css";

const DIFFICULTY_COLORS: Record<string, string> = {
  easy: "green",
  medium: "gold",
  hard: "red",
};

// RES-03 / R-11: the teaching file library — curated cases submitted from
// the reading console, browsable by modality / body part / diagnosis /
// difficulty. REPORT_READ-gated like every reading surface.
function TeachingLibrary() {
  useDocumentTitle("QuantumPACS - Teaching Library");
  const [files, setFiles] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [modalityFilter, setModalityFilter] = useState<string>("");
  const [difficultyFilter, setDifficultyFilter] = useState<string>("");
  const [diagnosisSearch, setDiagnosisSearch] = useState("");
  const [detail, setDetail] = useState<any | null>(null);

  const fetchList = useCallback(() => {
    setLoading(true);
    setError(null);
    const q = new URLSearchParams();
    if (modalityFilter) q.set("modality", modalityFilter);
    if (difficultyFilter) q.set("difficulty", difficultyFilter);
    if (diagnosisSearch) q.set("diagnosis", diagnosisSearch);
    request(`teaching-files${q.toString() ? `?${q.toString()}` : ""}`)
      .then((res: any) => {
        setFiles(Array.isArray(res.data) ? res.data : []);
        setLoading(false);
      })
      .catch((e: any) => {
        setError(e.message);
        setLoading(false);
      });
  }, [modalityFilter, difficultyFilter, diagnosisSearch]);

  useEffect(() => {
    fetchList();
  }, [fetchList]);

  const openDetail = useCallback(
    (id: string) => {
      setDetail({ loading: true });
      request(`teaching-files/${id}`)
        .then((res: any) => setDetail(res?.data ?? {}))
        .catch(() => setDetail({}));
    },
    [],
  );

  return (
    <div style={{ padding: 24 }} role="main">
      <div className="teaching-filters" style={{ marginBottom: 16 }}>
        <Input.Search
          aria-label="Diagnosis"
          placeholder="Search diagnosis…"
          allowClear
          style={{ width: 260 }}
          onSearch={(v: string) => setDiagnosisSearch(v)}
        />
        <Select
          aria-label="Modality filter"
          allowClear
          placeholder="Modality"
          style={{ width: 130 }}
          value={modalityFilter || undefined}
          onChange={(v: string) => setModalityFilter(v || "")}
          options={["CT", "MR", "PET", "DX", "US", "MG"].map((m) => ({
            value: m,
            label: m,
          }))}
        />
        <Select
          aria-label="Difficulty filter"
          allowClear
          placeholder="Difficulty"
          style={{ width: 140 }}
          value={difficultyFilter || undefined}
          onChange={(v: string) => setDifficultyFilter(v || "")}
          options={["easy", "medium", "hard"].map((d) => ({
            value: d,
            label: d,
          }))}
        />
      </div>

      {error && (
        <Alert type="error" title="Failed to load teaching library" description={error} showIcon />
      )}

      <Spin spinning={loading}>
        {files.length === 0 && !loading && !error ? (
          <Card>
            <span className="report-template-hint">
              No curated teaching cases yet — submit one from the reading
              console.
            </span>
          </Card>
        ) : (
          <div className="teaching-grid">
            {files.map((f: any) => (
              <Card
                key={f.id}
                size="small"
                title={f.title}
                extra={
                  <Tag color={DIFFICULTY_COLORS[f.difficulty] || "default"}>
                    {f.difficulty}
                  </Tag>
                }
                style={{ marginBottom: 12 }}
              >
                <Space size="small" wrap style={{ marginBottom: 8 }}>
                  {f.modality && <Tag>{f.modality}</Tag>}
                  {f.body_part && <Tag>{f.body_part}</Tag>}
                </Space>
                <div style={{ fontSize: 13, marginBottom: 8 }}>
                  <strong>DX:</strong> {f.diagnosis || "—"}
                </div>
                <Button
                  size="small"
                  icon={<BookOutlined />}
                  aria-label={`Open ${f.title}`}
                  onClick={() => openDetail(f.id)}
                >
                  Open case
                </Button>
              </Card>
            ))}
          </div>
        )}
      </Spin>

      <Drawer
        title={detail?.title || "Teaching case"}
        width={520}
        open={!!detail}
        onClose={() => setDetail(null)}
      >
        {detail?.loading ? (
          <Spin />
        ) : detail ? (
          <>
            <p>
              <strong>Diagnosis:</strong> {detail.diagnosis || "—"}
            </p>
            <p>
              <strong>Differential diagnosis:</strong>{" "}
              {(detail.differential_diagnosis || []).join(", ") || "—"}
            </p>
            <p>
              <strong>Teaching points:</strong>
            </p>
            <ul>
              {(detail.teaching_points || []).map((tp: string, i: number) => (
                <li key={i}>{tp}</li>
              ))}
              {(detail.teaching_points || []).length === 0 && <li>—</li>}
            </ul>
            {detail.findings_text && (
              <p style={{ whiteSpace: "pre-wrap" }}>{detail.findings_text}</p>
            )}
          </>
        ) : null}
      </Drawer>
    </div>
  );
}

export default withSidebar(TeachingLibrary);
