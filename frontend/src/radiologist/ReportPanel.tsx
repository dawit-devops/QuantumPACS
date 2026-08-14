import React from "react";
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
} from "antd";
import {
  EditOutlined,
  AuditOutlined,
  CheckCircleOutlined,
  SaveOutlined,
  RollbackOutlined,
} from "@ant-design/icons";
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

  return (
    <div className="report-panel" role="complementary" aria-label="Report">
      <Steps
        size="small"
        current={step}
        className="report-steps"
        items={steps}
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

      {submitted && (
        <Alert
          type="info"
          showIcon
          style={{ marginTop: 16 }}
          message={
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
          message="Attending returned this report"
          description={reviewFeedback}
        />
      )}

      {!isFinal && !submitted && !canWrite && (
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
