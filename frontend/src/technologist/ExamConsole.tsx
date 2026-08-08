import { useDocumentTitle } from "../hooks";
import React, { useState, useEffect, useCallback, useMemo } from "react";
import {
  Layout,
  Card,
  Descriptions,
  Button,
  Tag,
  Modal,
  Form,
  Select,
  Input,
  Steps,
  message,
  Alert,
  Spin,
  Table,
  Progress,
  Divider,
  Space,
} from "antd";
import {
  CheckCircleOutlined,
  SafetyCertificateOutlined,
  ThunderboltOutlined,
  ExperimentOutlined,
  BugOutlined,
  ExclamationCircleOutlined,
  FlagOutlined,
} from "@ant-design/icons";
import { useParams, useNavigate } from "react-router";
import withSidebar from "../common/base";
import { request } from "../helpers";
import { useAuth } from "../auth/AuthContext";
import SimulatedPreview from "./SimulatedPreview";
import "./ExamConsole.css";

const Content = Layout.Content;

const PRIORITY_COLORS: Record<string, string> = {
  stat: "red",
  urgent: "orange",
  routine: "default",
};

const STATUS_COLORS: Record<string, string> = {
  ready: "blue",
  in_progress: "gold",
  completed: "green",
  cancelled: "red",
};

// Modality-specific acquisition workflows (FR-R06-10). These drive the
// sequence list shown in the acquisition panel.
const MODALITY_WORKFLOWS: Record<
  string,
  { name: string; sequences: string[] }
> = {
  CT: {
    name: "CT workflow",
    sequences: ["Localizer", "Contrast (if ordered)", "Diagnostic series"],
  },
  MR: {
    name: "MRI workflow",
    sequences: ["Localizer", "Axial T1", "Axial T2", "FLAIR", "DWI"],
  },
  PET: {
    name: "PET workflow",
    sequences: ["Dose calibration", "Uptake period", "Emission scan"],
  },
  US: {
    name: "Ultrasound workflow",
    sequences: ["Real-time capture", "Annotation & measurement"],
  },
  MG: {
    name: "Mammography workflow",
    sequences: ["CC view", "MLO view"],
  },
  DX: {
    name: "Radiography workflow",
    sequences: ["PA", "Lateral"],
  },
};

const INCIDENT_TYPES = [
  "patient_motion",
  "equipment_malfunction",
  "contrast_reaction",
  "positioning_error",
  "other",
];

const SAFETY_CHECK_ITEMS = [
  { check_item: "No known contrast allergies", key: "allergies" },
  {
    check_item: "Not pregnant (or documented radiation risk accepted)",
    key: "pregnancy",
  },
  { check_item: "Creatinine/recent lab values reviewed", key: "renal" },
];

function ExamConsole() {
  useDocumentTitle("QuantumPACS - Exam Console");
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  // Every write here (identity confirm, protocol, acquisitions, safety
  // checks, incidents, overrides, complete) is gated EXAM_WRITE on the
  // backend (api/exams.py). View-only holders (EXAM_READ — nurse, resident)
  // watch the exam progression without the acquisition affordances.
  const { hasPermission } = useAuth();
  const canWrite = hasPermission("EXAM_WRITE");

  const [exam, setExam] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [protocols, setProtocols] = useState<any[]>([]);
  const [selectedProtocol, setSelectedProtocol] = useState<string>("");

  // Acquisition state.
  const [seriesNumber, setSeriesNumber] = useState(1);
  const [pendingPreviews, setPendingPreviews] = useState<any[]>([]);

  // Modals.
  const [incidentOpen, setIncidentOpen] = useState(false);
  const [overrideOpen, setOverrideOpen] = useState(false);
  const [rejectOpen, setRejectOpen] = useState<string | null>(null); // acquisition id
  const [completing, setCompleting] = useState(false);

  const [incidentForm] = Form.useForm();
  const [overrideForm] = Form.useForm();
  const [rejectForm] = Form.useForm();

  const fetchExam = useCallback(() => {
    setLoading(true);
    request(`exams/${id}`)
      .then((res: any) => {
        setLoading(false);
        setExam(res.data);
        setError(null);
      })
      .catch((e: any) => {
        setLoading(false);
        setError(e.message);
      });
  }, [id]);

  useEffect(() => {
    fetchExam();
    // Modal worklist updates are handled by the 30s refresh on the worklist
    // screen; here we only load once per exam id.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  useEffect(() => {
    request("protocols", {
      query: { modality: exam?.modality },
    })
      .then((res: any) => {
        setProtocols(Array.isArray(res.data) ? res.data : []);
        if (!selectedProtocol && res.data?.length && !exam?.protocol_name) {
          const def = res.data.find((p: any) => p.is_default) || res.data[0];
          setSelectedProtocol(def.name);
        }
      })
      .catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [exam?.modality]);

  const workflow = useMemo(
    () => MODALITY_WORKFLOWS[exam?.modality || ""] || null,
    [exam?.modality],
  );

  const doRequest = useCallback(
    async (url: string, data: any, okMsg: string) => {
      try {
        await request(url, { data });
        message.success(okMsg);
        await fetchExam();
        return true;
      } catch (e: any) {
        message.error(e.message || "Request failed");
        return false;
      }
    },
    [fetchExam],
  );

  const confirmIdentity = async () => {
    const ok = await doRequest(
      `exams/${id}/identity-confirm`,
      { confirmed: true },
      "Patient identity confirmed",
    );
    if (ok) message.success("Exam is now in progress");
  };

  const startProtocol = async () => {
    const ok = await doRequest(
      `exams/${id}/protocol`,
      { protocol_name: selectedProtocol || exam?.protocol_name || "" },
      "Protocol started",
    );
    if (ok) message.info("Acquisition ready — acquire images below");
  };

  const acquireImage = async () => {
    // Record a simulated acquisition with plausible dose parameters for the
    // modality, then show it in the pending QA queue (FR-R06-04/05).
    const dose =
      exam?.modality === "CT"
        ? { kvp: 120, mas: 210, dlp: 520, ctdivol: 12.5 }
        : exam?.modality === "MR"
          ? { kvp: 0, mas: 0, dlp: 0, ctdivol: 0, exposure_time: 3200 }
          : exam?.modality === "PET"
            ? { kvp: 140, mas: 120, dlp: 0, ctdivol: 0, exposure_time: 1800 }
            : { kvp: 75, mas: 8, dlp: 0, ctdivol: 0, exposure_time: 40 };
    try {
      const res = await request(`exams/${id}/acquisitions`, {
        data: {
          series_number: seriesNumber,
          description:
            workflow?.sequences[
              Math.min(seriesNumber - 1, (workflow?.sequences.length || 1) - 1)
            ] || `Series ${seriesNumber}`,
          ...dose,
        },
      });
      message.success("Image acquired");
      setPendingPreviews((p) => [...p, res.data]);
      setSeriesNumber((s) => s + 1);
      await fetchExam();
    } catch (e: any) {
      message.error(e.message || "Acquisition failed");
    }
  };

  const decideAcquisition = async (
    acqId: string,
    decision: "accept" | "reject",
    reason = "",
  ) => {
    const ok = await doRequest(
      `exams/${id}/acquisitions/${acqId}/${decision}`,
      { reason },
      decision === "accept" ? "Image accepted" : "Image rejected",
    );
    if (ok) setPendingPreviews((p) => p.filter((a) => a.id !== acqId));
    return ok;
  };

  const recordSafetyChecks = async () => {
    const checks = SAFETY_CHECK_ITEMS.map((item) => ({
      check_item: item.check_item,
      answer: "confirmed",
      notes: "",
    }));
    const ok = await doRequest(
      `exams/${id}/safety-checks`,
      { checks },
      "Safety checks recorded",
    );
    if (ok) message.success("Contrast administration may proceed");
  };

  const completeExam = async () => {
    setCompleting(true);
    try {
      await request(`exams/${id}/complete`, {
        data: { dose_recorded: true, sequences_complete: true },
      });
      message.success("Exam completed — handed off to radiologist");
      await fetchExam();
    } catch (e: any) {
      message.error(e.message || "Completion failed");
    } finally {
      setCompleting(false);
    }
  };

  const submitIncident = async () => {
    let values;
    try {
      values = await incidentForm.validateFields();
    } catch {
      return; // validation errors shown inline
    }
    const ok = await doRequest(
      `exams/${id}/incidents`,
      values,
      "Incident logged",
    );
    if (ok) {
      setIncidentOpen(false);
      incidentForm.resetFields();
    }
  };

  const submitOverride = async () => {
    let values;
    try {
      values = await overrideForm.validateFields();
    } catch {
      return; // validation errors shown inline
    }
    const ok = await doRequest(
      `exams/${id}/overrides`,
      { justification: values.justification, overridden_parameters: {} },
      "Override logged",
    );
    if (ok) {
      setOverrideOpen(false);
      overrideForm.resetFields();
    }
  };

  const submitReject = async () => {
    if (!rejectOpen) return;
    let values;
    try {
      values = await rejectForm.validateFields();
    } catch {
      return;
    }
    await decideAcquisition(rejectOpen, "reject", values.reason);
    setRejectOpen(null);
    rejectForm.resetFields();
  };

  if (loading && !exam) {
    return (
      <Content style={{ padding: 24 }}>
        <div className="exam-loading">
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
        <Button style={{ marginTop: 12 }} onClick={() => navigate("/exams")}>
          Back to worklist
        </Button>
      </Content>
    );
  }

  if (!exam) return null;

  const dose = exam.dose || {};
  const doseLevel = exam.dose_level || "ok";
  const acquisitions = exam.acquisitions || [];
  const rejectedCount = acquisitions.filter(
    (a: any) => a.status === "rejected",
  ).length;
  const isComplete = exam.status === "completed";
  const identityDone =
    !!exam.identity_confirmed_at || exam.status === "in_progress";
  const protocolStarted = !!exam.protocol_name;

  const stepIndex =
    exam.status === "completed"
      ? 4
      : identityDone
        ? protocolStarted
          ? 2
          : 1
        : 0;

  return (
    <Content style={{ padding: 24 }} role="main" id="main-content">
      <div className="exam-header">
        <Button onClick={() => navigate("/exams")} className="exam-back">
          ← Back to worklist
        </Button>
        <div className="exam-header-title">
          <h2>
            Exam {exam.accession_number || exam.id.slice(0, 8)}
            <Tag
              color={PRIORITY_COLORS[exam.priority]}
              className={exam.priority === "stat" ? "stat-tag" : ""}
            >
              {(exam.priority || "routine").toUpperCase()}
            </Tag>
            <Tag color={STATUS_COLORS[exam.status]}>{exam.status}</Tag>
          </h2>
          <span className="exam-subtitle">
            {exam.patient_name || exam.patient_id} · {exam.modality} ·{" "}
            {exam.protocol_name || "No protocol selected"}
          </span>
        </div>
        <Space>
          {canWrite && (
            <Button icon={<BugOutlined />} onClick={() => setIncidentOpen(true)}>
              Log Incident
            </Button>
          )}
          {canWrite && !isComplete && (
            <Button
              icon={<ExclamationCircleOutlined />}
              danger
              onClick={() => setOverrideOpen(true)}
            >
              Emergency Override
            </Button>
          )}
        </Space>
      </div>

      {!canWrite && (
        <Alert
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
          message="Read-only exam console"
          description="You have view access to this exam. Acquisition actions require the EXAM_WRITE permission."
        />
      )}

      <Steps
        size="small"
        current={stepIndex}
        className="exam-steps"
        items={[
          { title: "Verify Patient", icon: <SafetyCertificateOutlined /> },
          { title: "Protocol", icon: <ExperimentOutlined /> },
          { title: "Acquire & QA", icon: <ThunderboltOutlined /> },
          { title: "Dose & Safety", icon: <FlagOutlined /> },
          { title: "Complete", icon: <CheckCircleOutlined /> },
        ]}
      />

      <Divider />

      {/* FR-R06-02: Patient identity verification */}
      <Card
        title="Patient Identity Verification"
        size="small"
        extra={
          identityDone ? (
            <Tag color="green" icon={<CheckCircleOutlined />}>
              Verified
            </Tag>
          ) : canWrite ? (
            <Button type="primary" size="small" onClick={confirmIdentity}>
              Confirm Patient
            </Button>
          ) : (
            <Tag>Awaiting confirmation</Tag>
          )
        }
      >
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
          <Descriptions.Item label="Modality">
            {exam.modality || "—"}
          </Descriptions.Item>
        </Descriptions>
      </Card>

      {/* FR-R06-03: Protocol selection + start */}
      <Card
        title="Protocol"
        size="small"
        style={{ marginTop: 16 }}
        extra={
          !isComplete && protocolStarted ? (
            <Tag color="gold">Started: {exam.protocol_name}</Tag>
          ) : undefined
        }
      >
        {protocolStarted ? (
          <Descriptions size="small" column={1} bordered>
            <Descriptions.Item label="Protocol">
              {exam.protocol_name}
            </Descriptions.Item>
            <Descriptions.Item label="Workflow (FR-R06-10)">
              {workflow
                ? `${workflow.name}: ${workflow.sequences.join(" → ")}`
                : "—"}
            </Descriptions.Item>
          </Descriptions>
        ) : canWrite ? (
          <>
            <Select
              placeholder="Select protocol"
              style={{ width: 320 }}
              value={selectedProtocol}
              onChange={setSelectedProtocol}
              options={protocols.map((p) => ({ value: p.name, label: p.name }))}
              showSearch
              optionFilterProp="label"
            />
            <Button
              type="primary"
              style={{ marginLeft: 12 }}
              onClick={startProtocol}
              disabled={!selectedProtocol && !exam.protocol_name}
            >
              Start Protocol
            </Button>
          </>
        ) : (
          <Alert
            type="info"
            showIcon
            message="No protocol started yet — read-only view."
          />
        )}
      </Card>

      {/* FR-R06-04/05: Acquisition + QA */}
      <Card
        title="Acquisition & QA"
        size="small"
        style={{ marginTop: 16 }}
        extra={
          canWrite && !isComplete && identityDone && protocolStarted ? (
            <Button type="primary" onClick={acquireImage}>
              Acquire Image
            </Button>
          ) : undefined
        }
      >
        {(!identityDone || !protocolStarted) && !isComplete ? (
          <Alert
            type="info"
            showIcon
            message="Confirm the patient and start the protocol before acquiring images."
          />
        ) : (
          <div className="exam-acq">
            <div className="exam-acq-preview">
              <SimulatedPreview
                label={`Series ${Math.max(1, seriesNumber - (pendingPreviews.length ? 1 : 0))} preview`}
              />
            </div>
            <div className="exam-acq-queue">
              <h4>QA Queue ({pendingPreviews.length} pending)</h4>
              {pendingPreviews.length === 0 && (
                <span className="exam-acq-empty">
                  Pending acquisitions will appear here for accept/reject.
                </span>
              )}
              {pendingPreviews.map((acq) => (
                <div key={acq.id} className="exam-acq-item">
                  <div>
                    <b>{acq.description || "Series"}</b>
                    <span className="exam-acq-item-meta">
                      DLP {acq.dlp || 0} · CTDIvol {acq.ctdivol || 0} · kVp{" "}
                      {acq.kvp || 0}
                    </span>
                  </div>
                  <Space>
                    {canWrite && (
                      <>
                        <Button
                          size="small"
                          type="primary"
                          onClick={() => decideAcquisition(acq.id, "accept")}
                        >
                          Accept
                        </Button>
                        <Button
                          size="small"
                          danger
                          onClick={() => setRejectOpen(acq.id)}
                        >
                          Reject
                        </Button>
                      </>
                    )}
                  </Space>
                </div>
              ))}
            </div>
          </div>
        )}
        {isComplete && (
          <Alert type="success" showIcon message="Acquisition complete." />
        )}
      </Card>

      {/* FR-R06-05: Dose documentation */}
      <Card title="Dose Documentation" size="small" style={{ marginTop: 16 }}>
        <div className="exam-dose">
          <Descriptions size="small" column={4} bordered>
            <Descriptions.Item label="Cumulative DLP">
              {Number(dose.total_dlp || 0).toFixed(1)} mGy·cm
            </Descriptions.Item>
            <Descriptions.Item label="Cumulative CTDIvol">
              {Number(dose.total_ctdivol || 0).toFixed(1)} mGy
            </Descriptions.Item>
            <Descriptions.Item label="Total mAs">
              {Number(dose.total_mas || 0).toFixed(0)}
            </Descriptions.Item>
            <Descriptions.Item label="Exposure (ms)">
              {Number(dose.total_exposure || 0).toFixed(0)}
            </Descriptions.Item>
          </Descriptions>
          {exam.benchmark_dlp ? (
            <div className="exam-dose-benchmark">
              <Progress
                percent={Math.min(
                  100,
                  Math.round(
                    (Number(dose.total_dlp || 0) / exam.benchmark_dlp) * 100,
                  ),
                )}
                status={
                  doseLevel === "danger"
                    ? "exception"
                    : doseLevel === "warning"
                      ? "active"
                      : "normal"
                }
                format={(p) =>
                  `${p}% of ACR benchmark (${exam.benchmark_dlp} mGy·cm)`
                }
              />
            </div>
          ) : (
            <span className="exam-dose-note">
              ACR benchmark not defined for {exam.modality || "this modality"}.
            </span>
          )}
        </div>
      </Card>

      {/* FR-R06-06: Safety checks */}
      <Card
        title="Safety Checks (pre-contrast)"
        size="small"
        style={{ marginTop: 16 }}
        extra={
          canWrite && !isComplete && !(exam.safety_checks || []).length ? (
            <Button
              onClick={recordSafetyChecks}
              icon={<SafetyCertificateOutlined />}
            >
              Record Safety Checks
            </Button>
          ) : undefined
        }
      >
        {(exam.safety_checks || []).length ? (
          <Table
            rowKey="id"
            size="small"
            pagination={false}
            dataSource={exam.safety_checks}
            columns={[
              { title: "Check", dataIndex: "check_item" },
              { title: "Answer", dataIndex: "answer", width: 120 },
              { title: "Checked by", dataIndex: "checked_by", width: 140 },
              { title: "At", dataIndex: "checked_at", width: 180 },
            ]}
          />
        ) : (
          <Alert
            type="warning"
            showIcon
            message={
              exam.status === "completed"
                ? "No safety checks recorded for this exam."
                : "Record safety checks before contrast administration."
            }
          />
        )}
      </Card>

      {/* FR-R06-07: Complete + handoff */}
      {!isComplete && canWrite && (
        <Card
          title="Complete Exam"
          size="small"
          style={{ marginTop: 16 }}
          extra={
            <Button
              type="primary"
              danger
              icon={<CheckCircleOutlined />}
              loading={completing}
              onClick={completeExam}
            >
              Complete Exam
            </Button>
          }
        >
          <Alert
            type="info"
            showIcon
            message="Completing the exam hands it off to the radiologist worklist and notifies the reading team."
            description={
              rejectedCount > 0
                ? `${rejectedCount} image(s) rejected this exam — consider logging an incident.`
                : undefined
            }
          />
        </Card>
      )}

      {isComplete && (
        <Alert
          type="success"
          showIcon
          style={{ marginTop: 16 }}
          message="Exam completed and handed off to the radiologist worklist."
        />
      )}

      {/* FR-R06-08: Incident log modal */}
      <Modal
        title="Log Incident"
        open={incidentOpen}
        onCancel={() => setIncidentOpen(false)}
        onOk={submitIncident}
        okText="Log Incident"
        destroyOnHidden
      >
        <Form form={incidentForm} layout="vertical">
          <Form.Item
            name="incident_type"
            label="Incident type"
            rules={[{ required: true, message: "Select incident type" }]}
          >
            <Select
              placeholder="Select type"
              options={INCIDENT_TYPES.map((t) => ({
                value: t,
                label: t.replace(/_/g, " "),
              }))}
            />
          </Form.Item>
          <Form.Item
            name="severity"
            label="Severity"
            rules={[{ required: true }]}
            initialValue="medium"
          >
            <Select
              options={["low", "medium", "high", "critical"].map((s) => ({
                value: s,
                label: s,
              }))}
            />
          </Form.Item>
          <Form.Item
            name="description"
            label="Description"
            rules={[{ required: true, message: "Describe the incident" }]}
          >
            <Input.TextArea
              rows={3}
              placeholder="e.g. patient moved during scan"
            />
          </Form.Item>
        </Form>
      </Modal>

      {/* FR-R06-09: Emergency override modal */}
      <Modal
        title="Emergency Protocol Override"
        open={overrideOpen}
        onCancel={() => setOverrideOpen(false)}
        onOk={submitOverride}
        okText="Confirm Override"
        okButtonProps={{ danger: true }}
        destroyOnHidden
      >
        <Alert
          type="warning"
          showIcon
          style={{ marginBottom: 16 }}
          message="Overrides are audited and logged. A justification is required."
        />
        <Form form={overrideForm} layout="vertical">
          <Form.Item
            name="justification"
            label="Justification (required)"
            rules={[
              {
                required: true,
                message: "Justification is required for protocol override",
              },
              { min: 10, message: "Provide at least 10 characters" },
            ]}
          >
            <Input.TextArea
              rows={3}
              placeholder="e.g. Trauma — reducing sequence count"
            />
          </Form.Item>
        </Form>
      </Modal>

      {/* FR-R06-04 reject reason modal */}
      <Modal
        title="Reject Image"
        open={!!rejectOpen}
        onCancel={() => setRejectOpen(null)}
        onOk={submitReject}
        okText="Reject Image"
        okButtonProps={{ danger: true }}
        destroyOnHidden
      >
        <Form form={rejectForm} layout="vertical">
          <Form.Item
            name="reason"
            label="Reject reason"
            rules={[{ required: true, message: "Select a reject reason" }]}
          >
            <Select
              placeholder="Select reason"
              options={[
                "Patient motion",
                "Positioning error",
                "Artifact",
                "Exposure error",
                "Other",
              ].map((r) => ({ value: r, label: r }))}
            />
          </Form.Item>
        </Form>
      </Modal>
    </Content>
  );
}

export default withSidebar(ExamConsole);
