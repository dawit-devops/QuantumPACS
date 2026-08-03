import { useDocumentTitle } from "../hooks";
import React, { useState, useEffect, useCallback } from "react";
import {
  Layout,
  Card,
  Descriptions,
  Radio,
  InputNumber,
  Input,
  Checkbox,
  Button,
  Alert,
  Spin,
  message,
  Tag,
  Space,
} from "antd";
import {
  ArrowLeftOutlined,
  SaveOutlined,
  EyeOutlined,
} from "@ant-design/icons";
import { useNavigate, useParams } from "react-router";
import withSidebar from "../common/base";
import { useAuth } from "../auth/AuthContext";
import { request } from "../helpers";
import "./QAReviewForm.css";

const Content = Layout.Content;

// 44×44px touch targets per FR-R05-02.
const RADIO_STYLE: React.CSSProperties = {
  minHeight: 44,
  lineHeight: "44px",
  padding: "0 12px",
};

function QAReviewForm() {
  useDocumentTitle("QuantumPACS - QA Review");
  const navigate = useNavigate();
  const { examId } = useParams<{ examId: string }>();
  const { hasPermission } = useAuth();
  const canWrite = hasPermission("QA_WRITE");
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [passFail, setPassFail] = useState<"pass" | "fail">("pass");
  const [discrepancy, setDiscrepancy] = useState("none");
  const [dose, setDose] = useState({ dlp: 0, ctdivol: 0, kvp: 0, mas: 0 });
  const [sequenceCompliance, setSequenceCompliance] = useState<
    Record<string, boolean>
  >({});
  const [comments, setComments] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const fetchReview = useCallback(() => {
    if (!examId) return;
    setLoading(true);
    request(`qa/reviews/${examId}`)
      .then((res: any) => {
        setData(res.data);
        setLoading(false);
        const score = res.data?.score;
        if (score) {
          setPassFail(score.pass_fail === "fail" ? "fail" : "pass");
          setDiscrepancy(score.discrepancy_level);
          setDose({
            dlp: score.dose_dlp || 0,
            ctdivol: score.dose_ctdivol || 0,
            kvp: score.dose_kvp || 0,
            mas: score.dose_mas || 0,
          });
          setSequenceCompliance(score.sequence_compliance || {});
          setComments(score.comments || "");
        }
      })
      .catch((e: any) => {
        setLoading(false);
        setError(e.message);
      });
  }, [examId]);

  useEffect(() => {
    fetchReview();
  }, [fetchReview]);

  const exam = data?.exam;
  const protocol = data?.protocol;
  const sequences: any[] = protocol?.sequences || [];
  const existingScore = data?.score;

  const toggleSequence = (name: string) => {
    setSequenceCompliance((prev) => ({ ...prev, [name]: !prev[name] }));
  };

  const submit = async () => {
    setSubmitting(true);
    try {
      await request("qa/reviews", {
        method: "POST",
        data: {
          exam_id: examId,
          protocol_id: protocol?.id,
          pass_fail: passFail,
          discrepancy_level: discrepancy,
          dose_dlp: dose.dlp,
          dose_ctdivol: dose.ctdivol,
          dose_kvp: dose.kvp,
          dose_mas: dose.mas,
          sequence_compliance: sequenceCompliance,
          comments,
        },
      });
      message.success(
        existingScore ? "QA score updated" : "QA score submitted",
      );
      navigate("/qa/queue");
    } catch (e: any) {
      message.error(e.message || "Failed to submit QA score");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <Content
        style={{ display: "flex", justifyContent: "center", padding: 48 }}
      >
        <Spin size="large" />
      </Content>
    );
  }

  if (error || !exam) {
    return (
      <Content style={{ padding: 16 }}>
        <Alert
          type="error"
          showIcon
          message={error || "Exam not found"}
          action={
            <Button onClick={() => navigate("/qa/queue")}>Back to queue</Button>
          }
        />
      </Content>
    );
  }

  return (
    <Content style={{ padding: "16px" }}>
      <Button
        type="text"
        icon={<ArrowLeftOutlined />}
        onClick={() => navigate("/qa/queue")}
      >
        Back to QA Queue
      </Button>
      <div className="qa-review-grid">
        <Card
          title={`QA Review — ${exam.accession_number || exam.patient_id}`}
          className="qa-review-exam"
          extra={
            <Button
              type="primary"
              ghost
              icon={<EyeOutlined />}
              onClick={() => window.open(`/files/${exam.id}`, "_blank")}
            >
              Open in Viewer
            </Button>
          }
        >
          <Descriptions column={2} size="small" bordered>
            <Descriptions.Item label="Patient">
              {exam.patient_name || exam.patient_id}
            </Descriptions.Item>
            <Descriptions.Item label="MRN">{exam.patient_id}</Descriptions.Item>
            <Descriptions.Item label="Modality">
              <Tag>{exam.modality}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="Priority">
              <Tag
                color={
                  exam.priority === "stat"
                    ? "red"
                    : exam.priority === "urgent"
                      ? "orange"
                      : "default"
                }
              >
                {(exam.priority || "routine").toUpperCase()}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="Protocol">
              {exam.protocol_name || "-"}
            </Descriptions.Item>
            <Descriptions.Item label="Technologist">
              {exam.assigned_technologist || "-"}
            </Descriptions.Item>
            <Descriptions.Item label="Completed" span={2}>
              {exam.completed_at
                ? new Date(exam.completed_at).toLocaleString()
                : "-"}
            </Descriptions.Item>
          </Descriptions>
        </Card>

        <Card title="QA Findings" className="qa-review-form">
          {existingScore && (
            <Alert
              type="info"
              showIcon
              message={`Already reviewed as "${existingScore.pass_fail}" — submitting will update it.`}
              style={{ marginBottom: 12 }}
            />
          )}
          <div className="qa-field">
            <label>Overall assessment</label>
            <Radio.Group
              value={passFail}
              onChange={(e) => setPassFail(e.target.value)}
              aria-label="Overall assessment"
            >
              <Radio.Button value="pass" style={RADIO_STYLE}>
                ✓ Pass
              </Radio.Button>
              <Radio.Button value="fail" style={RADIO_STYLE}>
                ✗ Fail
              </Radio.Button>
            </Radio.Group>
          </div>
          <div className="qa-field">
            <label>Discrepancy level</label>
            <Radio.Group
              value={discrepancy}
              onChange={(e) => setDiscrepancy(e.target.value)}
            >
              {["none", "minor", "major", "critical"].map((d) => (
                <Radio.Button key={d} value={d} style={RADIO_STYLE}>
                  {d}
                </Radio.Button>
              ))}
            </Radio.Group>
          </div>

          <div className="qa-field">
            <label>Dose (CT)</label>
            <div className="qa-dose-grid">
              <div>
                <span>DLP (mGy·cm)</span>
                <InputNumber
                  min={0}
                  value={dose.dlp}
                  onChange={(v) => setDose((d) => ({ ...d, dlp: v || 0 }))}
                  aria-label="DLP mGy cm"
                />
              </div>
              <div>
                <span>CTDIvol (mGy)</span>
                <InputNumber
                  min={0}
                  value={dose.ctdivol}
                  onChange={(v) => setDose((d) => ({ ...d, ctdivol: v || 0 }))}
                  aria-label="CTDIvol mGy"
                />
              </div>
              <div>
                <span>kVp</span>
                <InputNumber
                  min={0}
                  value={dose.kvp}
                  onChange={(v) => setDose((d) => ({ ...d, kvp: v || 0 }))}
                  aria-label="kVp"
                />
              </div>
              <div>
                <span>mAs</span>
                <InputNumber
                  min={0}
                  value={dose.mas}
                  onChange={(v) => setDose((d) => ({ ...d, mas: v || 0 }))}
                  aria-label="mAs"
                />
              </div>
            </div>
          </div>

          <div className="qa-field">
            <label>Sequence checklist</label>
            {sequences.length === 0 ? (
              <span className="qa-muted">
                No required sequences configured for this protocol.
              </span>
            ) : (
              <Space direction="vertical">
                {sequences.map((s: any) => (
                  <Checkbox
                    key={s.name}
                    checked={Boolean(sequenceCompliance[s.name])}
                    onChange={() => toggleSequence(s.name)}
                  >
                    {s.name}
                    {s.required === false ? " (optional)" : ""}
                  </Checkbox>
                ))}
              </Space>
            )}
          </div>

          <div className="qa-field">
            <label>Comments</label>
            <Input.TextArea
              rows={3}
              maxLength={500}
              showCount
              value={comments}
              onChange={(e) => setComments(e.target.value)}
              placeholder="Findings, follow-up, retake justification..."
              aria-label="Comments"
            />
          </div>

          {canWrite ? (
            <Button
              type="primary"
              size="large"
              icon={<SaveOutlined />}
              loading={submitting}
              onClick={submit}
              className="qa-submit"
            >
              {existingScore ? "Update QA score" : "Submit QA score"}
            </Button>
          ) : (
            <Alert
              type="info"
              showIcon
              message="Read-only: you need QA_WRITE to submit scores."
            />
          )}
        </Card>
      </div>
    </Content>
  );
}

export default withSidebar(QAReviewForm);
