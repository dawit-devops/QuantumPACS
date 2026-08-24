import React, { useCallback, useState } from "react";
import {
  Card,
  Descriptions,
  Tag,
  Input,
  Select,
  Button,
  Steps,
  Alert,
  Divider,
  Space,
  Spin,
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
  const step = isFinal
    ? 2
    : submitted
      ? 1
      : isResident
        ? 0
        : status === "preliminary"
          ? 1
          : 0;

  // R-06: version history + pairwise diff, restored via the console (the
  // console owns report state; restoring reloads it there).
  const [showVersions, setShowVersions] = useState(false);
  const [versionsLoading, setVersionsLoading] = useState(false);
  const [versions, setVersions] = useState<any[]>([]);
  const [diffV1, setDiffV1] = useState<number | undefined>();
  const [diffV2, setDiffV2] = useState<number | undefined>();
  const [diff, setDiff] = useState<any>(null);
  const [restoringVersion, setRestoringVersion] = useState<number | null>(
    null,
  );

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
      const res = await request(
        `reports/${report.id}/versions?v1=${diffV1}&v2=${diffV2}`,
      );
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
      Promise.resolve(onRestoreVersion?.(version)).finally(() =>
        setRestoringVersion(null),
      );
    },
    [onRestoreVersion],
  );

  return (
    <div className="report-panel" role="complementary" aria-label="Report">
      <Steps
        size="small"
        current={step}
        className="report-steps"
        items={steps}
      />

      <Divider />

      {report?.id && (
        <div style={{ marginBottom: 12 }}>
          <Button
            size="small"
            icon={<HistoryOutlined />}
            onClick={toggleVersions}
            aria-expanded={showVersions}
          >
            Version history
          </Button>
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
                      No saved versions yet — every content change is
                      snapshotted automatically.
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
                        {v.created_at
                          ? new Date(v.created_at).toLocaleString()
                          : ""}
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
        </div>
      )}

      {!isFinal && !submitted && canWrite && (
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
      )}

      {isFinal && (
        <Alert
          type="success"
          showIcon
          style={{ marginTop: 16 }}
          title="This report is FINAL."
          description={`Signed by ${
            report?.signed_by_name || report?.signed_by || "radiologist"
          } · ${
            report?.signed_at ? new Date(report.signed_at).toLocaleString() : ""
          }`}
        />
      )}

      {submitted && (
        <Alert
          type="info"
          showIcon
          style={{ marginTop: 16 }}
          title={
            isResident
              ? "Submitted for attending review"
              : "Awaiting attending review"
          }
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
            signedBy={
              report?.signed_by_name || report?.signed_by || undefined
            }
            signedAt={report?.signed_at}
          />
        </div>
      ) : null}

      {canWrite && !submitted && !isFinal && (
        <>
          {canWrite && !submitted && (
            <Card
              title="Report Template"
              size="small"
              style={{ marginTop: 16 }}
              extra={
                <Select
                  placeholder="Apply a template"
                  style={{ width: 260 }}
                  onChange={onApplyTemplate}
                  options={templates.map((t) => ({
                    value: t.name,
                    label: t.name,
                  }))}
                  showSearch={{ optionFilterProp: "label" }}
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
              onChange={(e) => onFindingsChange(e.target.value)}
              readOnly={!canWrite || submitted}
              placeholder="Structured findings — per template or free text…"
            />
          </Card>

          <Card title="Impression" size="small" style={{ marginTop: 16 }}>
            <Input.TextArea
              rows={4}
              value={impression}
              onChange={(e) => onImpressionChange(e.target.value)}
              readOnly={!canWrite || submitted}
              placeholder="Impression / conclusion (required before signing)…"
              status={!impression.trim() ? "warning" : ""}
            />
          </Card>

          <Card title="Recommendations" size="small" style={{ marginTop: 16 }}>
            <Input.TextArea
              rows={2}
              value={recommendations}
              onChange={(e) => onRecommendationsChange(e.target.value)}
              readOnly={!canWrite || submitted}
              placeholder="Optional recommendations for follow-up…"
            />
          </Card>

          {canWrite && !submitted && (
            <div className="report-actions">
              <Button
                icon={<SaveOutlined />}
                onClick={onSaveDraft}
                disabled={!dirty}
              >
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
          )}

          {submitted && canSign && (
            <div className="report-actions">
              <Button
                type="primary"
                icon={<CheckCircleOutlined />}
                onClick={onRequestSign}
              >
                Approve & Co-sign
              </Button>
              <Button icon={<RollbackOutlined />} onClick={onReturnClick}>
                Return for revision
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
