import React, { useCallback, useState } from "react";
import {
  Card,
  Descriptions,
  Tag,
  Select,
  Button,
  Steps,
  Alert,
  Divider,
  Space,
  Spin,
  Drawer,
} from "antd";
import {
  EditOutlined,
  AuditOutlined,
  CheckCircleOutlined,
  SaveOutlined,
  RollbackOutlined,
  HistoryOutlined,
} from "@ant-design/icons";
import { request } from "../helpers";
import ReportDocument from "../common/ReportDocument";
import "./ReportPanel.css";
import RichTextEditor from "./RichTextEditor";

interface ReportPanelProps {
  exam: any;
  report: any;
  role: string;
  canWrite: boolean;
  canSign: boolean;
  status: string;
  findings: string;
  impression: string;
  recommendations: string;
  templates: any[];
  templateName?: string;
  dirty: boolean;
  reviewFeedback?: string;
  onFindingsChange: (v: string) => void;
  onImpressionChange: (v: string) => void;
  onRecommendationsChange: (v: string) => void;
  onApplyTemplate: (name: string) => void;
  onSaveDraft: () => void;
  onMarkPreliminary: () => void;
  onSubmitDraft: () => void;
  onRequestSign: () => void;
  onReturnClick: () => void;
  onRestoreVersion?: (version: number) => void;
  distribution?: any[] | null;
}

// Report content extracted from the old ReportEditor route shell — the
// reading console owns the report state (autosave, sign) and feeds this
// controlled panel. REPORT_WRITE gates editing; REPORT_SIGN gates
// finalizing; a REPORT_READ-only user gets a read-only view.
//
// R13 supervision: residents see a Draft → Submitted → Co-signed lifecycle
// (submit instead of sign); a submitted report locks editing everywhere and
// hands the attending Approve & Co-sign / Return for revision actions.
// Returned reports reopen as drafts carrying review_feedback.
export default function ReportPanel({
  exam,
  report,
  role,
  canWrite,
  canSign,
  status,
  findings,
  impression,
  recommendations,
  templates,
  templateName,
  dirty,
  reviewFeedback,
  onFindingsChange,
  onImpressionChange,
  onRecommendationsChange,
  onApplyTemplate,
  onSaveDraft,
  onMarkPreliminary,
  onSubmitDraft,
  onRequestSign,
  onReturnClick,
  onRestoreVersion,
  distribution,
}: ReportPanelProps) {
  const isFinal = status === "final";
  const isResident = role === "resident";
  const submitted = status === "submitted";
  // Resident lifecycle has no Preliminary step; the attending supervising a
  // submitted report sees it between Draft and Final.
  const steps = isResident
    ? [
        { title: "Draft", icon: <EditOutlined /> },
        { title: "Submitted", icon: <AuditOutlined /> },
        { title: "Co-signed", icon: <CheckCircleOutlined /> },
      ]
    : [
        { title: "Draft", icon: <EditOutlined /> },
        { title: "Preliminary", icon: <AuditOutlined /> },
        { title: "Final", icon: <CheckCircleOutlined /> },
      ];
  const step = isFinal ? 2 : submitted ? 1 : isResident ? 0 : status === "preliminary" ? 1 : 0;

  // R-06: version history + pairwise diff, restored via the console (the
  // console owns report state; restoring reloads it there).
  const [showVersions, setShowVersions] = useState(false);
  const [versionsLoading, setVersionsLoading] = useState(false);
  const [versions, setVersions] = useState<any[]>([]);
  const [diffV1, setDiffV1] = useState<number | undefined>();
  const [diffV2, setDiffV2] = useState<number | undefined>();
  const [diff, setDiff] = useState<any>(null);
  const [restoringVersion, setRestoringVersion] = useState<number | null>(null);

  const loadVersions = useCallback(() => {
    if (!report?.id) return;
    setVersionsLoading(true);
    request(`reports/${report.id}/versions`)
      .then((res: any) => {
        setVersions(Array.isArray(res.data) ? res.data : []);
      })
      .catch(() => setVersions([]))
      .finally(() => setVersionsLoading(false));
  }, [report?.id]);

  const toggleVersions = useCallback(() => {
    const next = !showVersions;
    setShowVersions(next);
    if (next) loadVersions();
  }, [showVersions, loadVersions]);

  const compareVersions = useCallback(async () => {
    if (!report?.id || !diffV1 || !diffV2) return;
    setVersionsLoading(true);
    try {
      const res = await request(`reports/${report.id}/versions?v1=${diffV1}&v2=${diffV2}`);
      setDiff(res?.data ?? null);
    } catch {
      setDiff(null);
    } finally {
      setVersionsLoading(false);
    }
  }, [report?.id, diffV1, diffV2]);

  const restore = useCallback(
    (version: number) => {
      setRestoringVersion(version);
      Promise.resolve(onRestoreVersion?.(version)).finally(() => setRestoringVersion(null));
    },
    [onRestoreVersion]
  );

  // R-07: prior reports quick-view — the patient's earlier reports for the
  // same modality, compared without leaving the console.
  const [showPriors, setShowPriors] = useState(false);
  const [priorsLoading, setPriorsLoading] = useState(false);
  const [priors, setPriors] = useState<any[]>([]);
  const [priorDetail, setPriorDetail] = useState<any | null>(null);

  const togglePriors = useCallback(() => {
    const next = !showPriors;
    setShowPriors(next);
    if (next && exam?.patient_id) {
      setPriorsLoading(true);
      const q = new URLSearchParams({
        patient_id: String(exam.patient_id),
        modality: String(exam.modality || ""),
        exclude_exam_id: String(exam.id || ""),
      });
      request(`reports/priors?${q.toString()}`)
        .then((res: any) => setPriors(Array.isArray(res.data) ? res.data : []))
        .catch(() => setPriors([]))
        .finally(() => setPriorsLoading(false));
    }
  }, [showPriors, exam?.patient_id, exam?.modality, exam?.id]);

  const openPrior = useCallback((examId: string) => {
    setPriorDetail({ loading: true });
    request(`reports/${examId}`)
      .then((res: any) => setPriorDetail(res?.data?.report ?? {}))
      .catch(() => setPriorDetail({}));
  }, []);

  // Single-page ergonomic editor: the editable state fills the pane height
  // (flex column) so viewer + report editor share one viewport with no page
  // scroll — the textareas flex-fill the remaining space after the compact
  // header rows, and each field scrolls internally instead.
  const editable = canWrite && !submitted && !isFinal;

  const versionPriorButtons = report?.id ? (
    <Space size="small" wrap>
      <Button
        size="small"
        icon={<HistoryOutlined />}
        onClick={toggleVersions}
        aria-expanded={showVersions}
      >
        Version history
      </Button>
      {exam?.patient_id && (
        <Button
          size="small"
          icon={<AuditOutlined />}
          onClick={togglePriors}
          aria-expanded={showPriors}
        >
          Prior reports
        </Button>
      )}
    </Space>
  ) : null;

  return (
    <div
      className={`report-panel${editable ? " report-panel-editor" : ""}`}
      role="complementary"
      aria-label="Report"
    >
      {!editable && <Steps size="small" current={step} className="report-steps" items={steps} />}

      {editable ? (
        <div className="report-editor">
          <div className="report-editor-toolbar">
            <span className="report-editor-status" title={steps[step]?.title}>
              {steps.map((s, i) => (
                <span
                  key={s.title}
                  className={`report-editor-status-dot${i === step ? " current" : i < step ? " done" : ""}`}
                  aria-hidden="true"
                />
              ))}
              <span className="report-editor-status-label">{steps[step]?.title}</span>
            </span>
            <Select
              placeholder="Apply a template"
              style={{ width: 220, flexShrink: 0 }}
              value={templateName || undefined}
              onChange={onApplyTemplate}
              options={templates.map((t) => ({
                value: t.name,
                label: t.name,
              }))}
              showSearch={{ optionFilterProp: "label" }}
            />
          </div>
          <div className="report-editor-meta">
            <span className="report-editor-patient">
              <strong className="report-editor-patient-name">{exam.patient_name || "—"}</strong>
              <span className="report-editor-patient-detail">
                {" "}
                · {exam.patient_id || "—"} · {exam.patient_birth_date || "—"} ·{" "}
                {exam.patient_sex || "—"} · {exam.accession_number || "—"}
                {exam.completed_at ? ` · ${new Date(exam.completed_at).toLocaleString()}` : ""}
              </span>
            </span>
            {versionPriorButtons}
          </div>

          {!submitted && !isFinal && reviewFeedback && (
            <Alert
              type="warning"
              showIcon
              title="Attending returned this report"
              description={reviewFeedback}
            />
          )}
          {showPriors && (
            <Card title="Prior Reports" size="small" style={{ marginTop: 8 }}>
              <Spin spinning={priorsLoading}>
                {priors.length === 0 && !priorsLoading && (
                  <span className="report-template-hint">
                    No prior reports for this patient / modality.
                  </span>
                )}
                {priors.map((p: any) => (
                  <div
                    key={p.report_id}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 8,
                      padding: "4px 0",
                    }}
                  >
                    <Tag>{p.status}</Tag>
                    <strong>{p.accession_number || p.exam_id}</strong>
                    <span style={{ flex: 1, fontSize: 12 }}>
                      {p.impression_excerpt || "(no impression)"}
                    </span>
                    <Button
                      size="small"
                      aria-label={`Open prior ${p.accession_number || p.exam_id}`}
                      onClick={() => openPrior(p.exam_id)}
                    >
                      Open
                    </Button>
                  </div>
                ))}
              </Spin>
            </Card>
          )}

          {showVersions && (
            <Card title="Versions" size="small" style={{ marginTop: 8 }}>
              <Spin spinning={versionsLoading}>
                <Space size="small" wrap style={{ marginBottom: 8 }}>
                  <Select
                    placeholder="From v"
                    style={{ width: 90 }}
                    value={diffV1}
                    onChange={setDiffV1}
                    options={versions.map((v: any) => ({
                      value: v.version_number,
                      label: `v${v.version_number}`,
                    }))}
                  />
                  <Select
                    placeholder="To v"
                    style={{ width: 90 }}
                    value={diffV2}
                    onChange={setDiffV2}
                    options={versions.map((v: any) => ({
                      value: v.version_number,
                      label: `v${v.version_number}`,
                    }))}
                  />
                  <Button onClick={compareVersions} disabled={!diffV1 || !diffV2}>
                    Compare
                  </Button>
                </Space>
                {diff && (
                  <div className="report-version-diff">
                    <Tag color={diff.findings_changed ? "orange" : "default"}>
                      findings {diff.findings_changed ? "changed" : "same"}
                    </Tag>
                    <Tag color={diff.impression_changed ? "orange" : "default"}>
                      impression {diff.impression_changed ? "changed" : "same"}
                    </Tag>
                    <pre style={{ whiteSpace: "pre-wrap", fontSize: 12 }}>
                      {`— v${diff.v1?.version_number} —\n${
                        diff.v1?.impression || diff.v1?.findings || "(empty)"
                      }\n\n+ v${diff.v2?.version_number} +\n${
                        diff.v2?.impression || diff.v2?.findings || "(empty)"
                      }`}
                    </pre>
                  </div>
                )}
                <div>
                  {versions.length === 0 && !versionsLoading && (
                    <span className="report-template-hint">
                      No saved versions yet — every content change is snapshotted automatically.
                    </span>
                  )}
                  {versions.map((v: any) => (
                    <div
                      key={v.version_number}
                      className="report-version-row"
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 8,
                        padding: "4px 0",
                      }}
                    >
                      <strong>v{v.version_number}</strong>
                      <span style={{ flex: 1, fontSize: 12 }}>
                        {(v.edited_by || "—") + " · "}
                        {v.created_at ? new Date(v.created_at).toLocaleString() : ""}
                      </span>
                      {canWrite && !submitted && !isFinal && onRestoreVersion && (
                        <Button
                          size="small"
                          icon={<RollbackOutlined />}
                          loading={restoringVersion === v.version_number}
                          aria-label={`Restore version ${v.version_number}`}
                          onClick={() => restore(v.version_number)}
                        >
                          Restore
                        </Button>
                      )}
                    </div>
                  ))}
                </div>
              </Spin>
            </Card>
          )}

          <div className="report-editor-fields">
            <div className="report-field report-field-findings">
              <span className="report-field-label">Findings</span>
              <RichTextEditor
                value={findings}
                onChange={onFindingsChange}
                readOnly={!canWrite || submitted}
                placeholder="Structured findings — per template or free text…"
              />
            </div>

            <div className="report-field report-field-impression">
              <span className="report-field-label">Impression</span>
              <RichTextEditor
                value={impression}
                onChange={onImpressionChange}
                readOnly={!canWrite || submitted}
                placeholder="Impression / conclusion (required before signing)…"
                status={!impression.trim() ? "warning" : ""}
              />
            </div>

            <div className="report-field report-field-recommendations">
              <span className="report-field-label">Recommendations</span>
              <RichTextEditor
                value={recommendations}
                onChange={onRecommendationsChange}
                readOnly={!canWrite || submitted}
                placeholder="Optional recommendations for follow-up…"
              />
            </div>
          </div>

          <div className="report-actions">
            <Button icon={<SaveOutlined />} onClick={onSaveDraft} disabled={!dirty}>
              Save Draft
            </Button>
            {!isResident && (
              <Button onClick={onMarkPreliminary} disabled={isFinal}>
                Mark Preliminary
              </Button>
            )}
            {isResident && (
              <Button
                type="primary"
                icon={<AuditOutlined />}
                onClick={onSubmitDraft}
                disabled={!impression.trim()}
              >
                Submit for Review
              </Button>
            )}
            {canSign && !isResident && (
              <Button
                type="primary"
                icon={<CheckCircleOutlined />}
                onClick={onRequestSign}
                disabled={!impression.trim()}
              >
                Sign Report
              </Button>
            )}
          </div>
        </div>
      ) : (
        <>
          {versionPriorButtons}

          {!isFinal && !submitted && canWrite && (
            <Card title="Patient & Exam" size="small">
              <Descriptions size="small" column={3} bordered>
                <Descriptions.Item label="Patient Name">
                  {exam.patient_name || "—"}
                </Descriptions.Item>
                <Descriptions.Item label="Patient ID">{exam.patient_id || "—"}</Descriptions.Item>
                <Descriptions.Item label="DOB">{exam.patient_birth_date || "—"}</Descriptions.Item>
                <Descriptions.Item label="Sex">{exam.patient_sex || "—"}</Descriptions.Item>
                <Descriptions.Item label="Accession">
                  {exam.accession_number || "—"}
                </Descriptions.Item>
                <Descriptions.Item label="Completed">
                  {exam.completed_at ? new Date(exam.completed_at).toLocaleString() : "—"}
                </Descriptions.Item>
              </Descriptions>
            </Card>
          )}

          {isFinal && (
            <Alert
              type="success"
              showIcon
              style={{ marginTop: 16 }}
              title="This report is FINAL."
              description={`Signed by ${
                report?.signed_by_name || report?.signed_by || "radiologist"
              } · ${report?.signed_at ? new Date(report.signed_at).toLocaleString() : ""}`}
            />
          )}

          {/* R-16: distribution confirmation — per-recipient ORU receipts. */}
          {isFinal && distribution && (
            <Card title="Distribution" size="small" style={{ marginTop: 12 }}>
              {distribution.length === 0 ? (
                <span className="report-template-hint">
                  No distribution records yet — the results engine delivers the signed report to the
                  ordering physician.
                </span>
              ) : (
                <>
                  <div style={{ marginBottom: 6, fontSize: 13 }}>
                    Report distributed to {distribution.length} recipient
                    {distribution.length === 1 ? "" : "s"}:
                  </div>
                  {distribution.map((d: any) => (
                    <div
                      key={d.id}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 8,
                        padding: "2px 0",
                      }}
                    >
                      <Tag color={d.status === "SENT" ? "green" : "red"}>{d.status}</Tag>
                      <span style={{ fontSize: 12 }}>
                        {d.accession_number || d.report_id}
                        {d.delivered_at
                          ? ` · delivered ${new Date(d.delivered_at).toLocaleTimeString()}`
                          : ` · ${d.attempts ?? 1} attempt(s) — retry pending`}
                      </span>
                    </div>
                  ))}
                </>
              )}
            </Card>
          )}

          {submitted && (
            <Alert
              type="info"
              showIcon
              style={{ marginTop: 16 }}
              title={isResident ? "Submitted for attending review" : "Awaiting attending review"}
              description={
                isResident
                  ? "Your draft is with the supervising attending — it is locked until they co-sign it FINAL or return it for revision."
                  : "This report was submitted for your review. Co-sign it to finalize, or return it to the resident for revision."
              }
            />
          )}

          {!submitted && !isFinal && reviewFeedback && (
            <Alert
              type="warning"
              showIcon
              style={{ marginTop: 16 }}
              title="Attending returned this report"
              description={reviewFeedback}
            />
          )}

          {!isFinal && !submitted && !canWrite && (
            <Alert
              type="info"
              showIcon
              style={{ marginTop: 16 }}
              title="Read-only report"
              description="You have view access to this report. Editing requires the REPORT_WRITE permission — only the assigned radiologist can draft or sign."
            />
          )}

          {/* Branded report document — read-only, submitted, or final surfaces
          use the design-system REPORT-TEMPLATE.html layout. */}
          {isFinal || submitted || !canWrite ? (
            <div style={{ marginTop: 16 }}>
              <ReportDocument
                meta={{
                  patient_name: exam.patient_name,
                  patient_id: exam.patient_id,
                  patient_birth_date: exam.patient_birth_date,
                  patient_sex: exam.patient_sex,
                  accession_number: exam.accession_number,
                  modality: exam.modality,
                  requested_procedure_desc: exam.requested_procedure_desc,
                  referring_physician: exam.referring_physician,
                  priority: exam.priority,
                  protocol_name: exam.protocol_name,
                }}
                findings={findings}
                impression={impression}
                recommendations={recommendations}
                signedBy={report?.signed_by_name || report?.signed_by || undefined}
                signedAt={report?.signed_at}
              />
            </div>
          ) : null}

          {submitted && canSign && (
            <div className="report-actions">
              <Button type="primary" icon={<CheckCircleOutlined />} onClick={onRequestSign}>
                Approve & Co-sign
              </Button>
              <Button icon={<RollbackOutlined />} onClick={onReturnClick}>
                Return for revision
              </Button>
            </div>
          )}
        </>
      )}

      {/* R-07: read-only preview of a prior report, in-console. */}
      <Drawer
        title={priorDetail ? `Prior report — ${exam?.accession_number || ""} comparison` : null}
        width={520}
        open={!!priorDetail}
        onClose={() => setPriorDetail(null)}
      >
        {priorDetail?.loading ? (
          <Spin />
        ) : (
          <div>
            <p>
              <strong>Impression:</strong>
            </p>
            <p style={{ whiteSpace: "pre-wrap" }}>
              {priorDetail?.impression || "(no impression recorded)"}
            </p>
            <p>
              <strong>Findings:</strong>
            </p>
            <p style={{ whiteSpace: "pre-wrap" }}>
              {priorDetail?.findings || "(no findings recorded)"}
            </p>
          </div>
        )}
      </Drawer>
    </div>
  );
}
