import { useDocumentTitle } from "../hooks";
import React, { useState, useEffect, useCallback, useRef } from "react";
import {
  Layout,
  Card,
  Descriptions,
  Button,
  Tag,
  Input,
  Select,
  Steps,
  message,
  Alert,
  Spin,
  Space,
  Divider,
  Modal,
} from "antd";
import {
  FileTextOutlined,
  CheckCircleOutlined,
  SaveOutlined,
  EditOutlined,
  AuditOutlined,
} from "@ant-design/icons";
import { useParams, useNavigate } from "react-router";
import withSidebar from "../common/base";
import { request } from "../helpers";
import { useAuth } from "../auth/AuthContext";
import "./ReportEditor.css";

const Content = Layout.Content;

const PRIORITY_COLORS: Record<string, string> = {
  stat: "red",
  urgent: "orange",
  routine: "default",
};

// NFR-R12-10: report autosave cadence ≤ 10s; drafts must never be lost.
const AUTOSAVE_MS = 3000;

function ReportEditor() {
  useDocumentTitle("QuantumPACS - Report Editor");
  const { examId } = useParams<{ examId: string }>();
  const navigate = useNavigate();

  // REPORT_WRITE gates editing (draft save, mark preliminary, template
  // application); REPORT_SIGN gates finalizing. A REPORT_READ-only user
  // (referring physician, care coordinator, nurse) gets a read-only view, and
  // a resident (REPORT_WRITE without REPORT_SIGN) drafts without the sign
  // affordance — the attending cosigns.
  const { hasPermission } = useAuth();
  const canWrite = hasPermission("REPORT_WRITE");
  const canSign = hasPermission("REPORT_SIGN");

  const [exam, setExam] = useState<any | null>(null);
  const [report, setReport] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [templates, setTemplates] = useState<any[]>([]);
  const [findings, setFindings] = useState("");
  const [impression, setImpression] = useState("");
  const [recommendations, setRecommendations] = useState("");
  const [templateName, setTemplateName] = useState("");
  const [status, setStatus] = useState("draft");
  const [savedAt, setSavedAt] = useState<Date | null>(null);
  const [dirty, setDirty] = useState(false);
  const [signOpen, setSignOpen] = useState(false);
  const [signing, setSigning] = useState(false);

  const saveTimer = useRef<ReturnType<typeof setInterval> | null>(null);
  // The autosave interval is registered once; read the live dirty flag AND the
  // latest saveDraft via refs so the interval closure never sees a stale value
  // (NFR-R12-10 — zero drafts lost).
  const dirtyRef = useRef(false);
  const saveDraftRef = useRef<() => void>(() => {});

  const load = useCallback(() => {
    setLoading(true);
    request(`reports/${examId}`)
      .then((res: any) => {
        setLoading(false);
        setExam(res.data.exam);
        const r = res.data.report;
        setReport(r);
        setFindings(r?.findings || "");
        setImpression(r?.impression || "");
        setRecommendations(r?.recommendations || "");
        setTemplateName(r?.template_name || "");
        setStatus(r?.status || "draft");
        setSavedAt(r?.updated_at ? new Date(r.updated_at) : null);
        setError(null);
      })
      .catch((e: any) => {
        setLoading(false);
        setError(e.message);
      });
  }, [examId]);

  // Keep the interval closure pointing at the latest saveDraft after every render.
  useEffect(() => {
    saveDraftRef.current = () => saveDraft();
  });

  useEffect(() => {
    load();
    // Autosave loop: flush the local draft on an interval (FR-R12-09 / NFR-R12-10).
    saveTimer.current = setInterval(() => {
      if (dirtyRef.current) {
        saveDraftRef.current();
      }
    }, AUTOSAVE_MS);
    return () => {
      if (saveTimer.current) clearInterval(saveTimer.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    request("reports/templates", {
      query: { modality: exam?.modality || "" },
    })
      .then((res: any) => setTemplates(Array.isArray(res.data) ? res.data : []))
      .catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [exam?.modality]);

  const saveDraft = useCallback(
    async (silent = true): Promise<boolean> => {
      // Read-only viewers never save: the guard also makes the autosave
      // interval a no-op for them.
      if (!canWrite) return true;
      dirtyRef.current = false;
      setDirty(false);
      try {
        await request(`reports/${examId}`, {
          data: {
            findings,
            impression,
            recommendations,
            template_name: templateName,
            status: status === "final" ? "preliminary" : status,
          },
        });
        setSavedAt(new Date());
        if (!silent) message.success("Draft saved");
        return true;
      } catch (e: any) {
        // Never lose the draft on a transient failure — mark dirty again so the
        // autosave loop retries (NFR-R12-10).
        dirtyRef.current = true;
        setDirty(true);
        if (!silent) message.error(e.message || "Save failed");
        return false;
      }
    },
    [canWrite, examId, findings, impression, recommendations, status, templateName],
  );

  const applyTemplate = (name: string) => {
    const t = templates.find((x) => x.name === name);
    if (!t) return;
    setFindings(t.findings_template || "");
    setImpression(t.impression_template || "");
    setRecommendations("");
    setTemplateName(name);
    dirtyRef.current = true;
    setDirty(true);
    message.info(`Template "${name}" applied`);
  };

  const signReport = async () => {
    if (!impression.trim()) {
      message.error("Impression is required before signing");
      return;
    }
    setSigning(true);
    try {
      // Flush any pending edits first, then sign. Abort the sign if the flush
      // failed so we never finalize a report missing the last keystrokes.
      const saved = await saveDraft(true);
      if (!saved) {
        message.error("Could not save the draft — sign aborted. Try again.");
        return;
      }
      const res = await request(`reports/${examId}/sign`, {
        data: { confirm: true },
      });
      setReport(res.data);
      setStatus("final");
      setSavedAt(new Date());
      setSignOpen(false);
      message.success("Report signed — status is now FINAL");
    } catch (e: any) {
      message.error(e.message || "Sign failed");
    } finally {
      setSigning(false);
    }
  };

  if (loading && !exam) {
    return (
      <Content style={{ padding: 24 }}>
        <div className="report-loading">
          <Spin size="large" />
        </div>
      </Content>
    );
  }

  if (error && !exam) {
    return (
      <Content style={{ padding: 24 }}>
        <Alert
          type="error"
          message="Failed to load exam"
          description={error}
          showIcon
        />
        <Button style={{ marginTop: 12 }} onClick={() => navigate("/reading")}>
          Back to worklist
        </Button>
      </Content>
    );
  }

  if (!exam) return null;

  const isFinal = status === "final";
  const step = isFinal ? 2 : status === "preliminary" ? 1 : 0;

  return (
    <Content style={{ padding: 24 }} role="main" id="main-content">
      <div className="report-header">
        <Button onClick={() => navigate("/reading")} className="report-back">
          ← Back to worklist
        </Button>
        <div className="report-header-title">
          <h2>
            <FileTextOutlined /> Report —{" "}
            {exam.accession_number || exam.id.slice(0, 8)}
            <Tag
              color={PRIORITY_COLORS[exam.priority]}
              className={exam.priority === "stat" ? "report-stat-tag" : ""}
            >
              {(exam.priority || "routine").toUpperCase()}
            </Tag>
            <Tag
              color={
                isFinal ? "green" : status === "preliminary" ? "purple" : "gold"
              }
            >
              {status.toUpperCase()}
            </Tag>
          </h2>
          <span className="report-subtitle">
            {exam.patient_name || exam.patient_id} · {exam.modality} ·{" "}
            {exam.protocol_name || "No protocol"}
          </span>
        </div>
        <Space>
          {savedAt && (
            <span className="report-saved">
              <SaveOutlined /> saved {savedAt.toLocaleTimeString()}
            </span>
          )}
          {!isFinal && canSign && (
            <Button
              type="primary"
              icon={<CheckCircleOutlined />}
              onClick={() => setSignOpen(true)}
            >
              Sign Report
            </Button>
          )}
        </Space>
      </div>

      <Steps
        size="small"
        current={step}
        className="report-steps"
        items={[
          { title: "Draft", icon: <EditOutlined /> },
          { title: "Preliminary", icon: <AuditOutlined /> },
          { title: "Final", icon: <CheckCircleOutlined /> },
        ]}
      />

      <Divider />

      <Card title="Patient & Exam" size="small">
        <Descriptions size="small" column={3} bordered>
          <Descriptions.Item label="Patient Name">
            {exam.patient_name || "—"}
          </Descriptions.Item>
          <Descriptions.Item label="Patient ID">
            {exam.patient_id || "—"}
          </Descriptions.Item>
          <Descriptions.Item label="DOB">
            {exam.patient_birth_date || "—"}
          </Descriptions.Item>
          <Descriptions.Item label="Sex">
            {exam.patient_sex || "—"}
          </Descriptions.Item>
          <Descriptions.Item label="Accession">
            {exam.accession_number || "—"}
          </Descriptions.Item>
          <Descriptions.Item label="Completed">
            {exam.completed_at
              ? new Date(exam.completed_at).toLocaleString()
              : "—"}
          </Descriptions.Item>
        </Descriptions>
      </Card>

      {isFinal && (
        <Alert
          type="success"
          showIcon
          style={{ marginTop: 16 }}
          message="This report is FINAL."
          description={`Signed by ${report?.signed_by || "radiologist"} · ${
            report?.signed_at ? new Date(report.signed_at).toLocaleString() : ""
          }`}
        />
      )}

      {!isFinal && !canWrite && (
        <Alert
          type="info"
          showIcon
          style={{ marginTop: 16 }}
          message="Read-only report"
          description="You have view access to this report. Editing requires the REPORT_WRITE permission — only the assigned radiologist can draft or sign."
        />
      )}

      {!isFinal && (
        <>
          {canWrite && (
            <Card
              title="Report Template"
              size="small"
              style={{ marginTop: 16 }}
              extra={
                <Select
                  placeholder="Apply a template"
                  style={{ width: 260 }}
                  onChange={applyTemplate}
                  options={templates.map((t) => ({
                    value: t.name,
                    label: t.name,
                  }))}
                  showSearch
                  optionFilterProp="label"
                />
              }
            >
              <span className="report-template-hint">
                Templates seed the findings and impression sections — always
                review and tailor the text before signing.
              </span>
            </Card>
          )}

          <Card title="Findings" size="small" style={{ marginTop: 16 }}>
            <Input.TextArea
              rows={8}
              value={findings}
              onChange={(e) => {
                setFindings(e.target.value);
                dirtyRef.current = true;
                setDirty(true);
              }}
              readOnly={!canWrite}
              placeholder="Structured findings — per template or free text…"
            />
          </Card>

          <Card title="Impression" size="small" style={{ marginTop: 16 }}>
            <Input.TextArea
              rows={4}
              value={impression}
              onChange={(e) => {
                setImpression(e.target.value);
                dirtyRef.current = true;
                setDirty(true);
              }}
              readOnly={!canWrite}
              placeholder="Impression / conclusion (required before signing)…"
              status={!impression.trim() ? "warning" : ""}
            />
          </Card>

          <Card title="Recommendations" size="small" style={{ marginTop: 16 }}>
            <Input.TextArea
              rows={2}
              value={recommendations}
              onChange={(e) => {
                setRecommendations(e.target.value);
                dirtyRef.current = true;
                setDirty(true);
              }}
              readOnly={!canWrite}
              placeholder="Optional recommendations for follow-up…"
            />
          </Card>

          {canWrite && (
            <div className="report-actions">
              <Button
                icon={<SaveOutlined />}
                onClick={() => saveDraft(false)}
                disabled={!dirty}
              >
                Save Draft
              </Button>
              <Button
                onClick={() => {
                  setStatus("preliminary");
                  saveDraft(true).then(() =>
                    message.success("Marked preliminary"),
                  );
                }}
                disabled={isFinal}
              >
                Mark Preliminary
              </Button>
              {canSign && (
                <Button
                  type="primary"
                  icon={<CheckCircleOutlined />}
                  onClick={() => setSignOpen(true)}
                  disabled={!impression.trim()}
                >
                  Sign Report
                </Button>
              )}
            </div>
          )}
        </>
      )}

      <Modal
        title="Sign Report"
        open={signOpen}
        onCancel={() => setSignOpen(false)}
        onOk={signReport}
        okText="Sign & Finalize"
        okButtonProps={{ loading: signing, disabled: !impression.trim() }}
        destroyOnHidden
      >
        <Alert
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
          message="Signing makes this report FINAL and records you as the signing radiologist."
        />
        <p>
          Impression preview:{" "}
          <em>{impression || "(empty — required to sign)"}</em>
        </p>
      </Modal>
    </Content>
  );
}

export default withSidebar(ReportEditor);
