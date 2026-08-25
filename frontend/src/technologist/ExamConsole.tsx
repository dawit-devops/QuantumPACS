import { useDocumentTitle } from "../hooks";
import React, { useState, useEffect, useCallback, useMemo } from "react";
import {
  App,
  Layout,
  Card,
  Descriptions,
  Button,
  Checkbox,
  Tag,
  Modal,
  Form,
  Select,
  Input,
  Steps,
  Alert,
  Spin,
  Table,
  Progress,
  Divider,
  Space,
} from "antd";
import { StarFilled, StarOutlined } from "@ant-design/icons";
import {
  CheckCircleOutlined,
  SafetyCertificateOutlined,
  ThunderboltOutlined,
  ExperimentOutlined,
  BugOutlined,
  ExclamationCircleOutlined,
  FlagOutlined,
  AlertOutlined,
} from "@ant-design/icons";
import { useParams, useNavigate, Link } from "react-router";
import withSidebar from "../common/base";
import NursingPanel from "./NursingPanel";
import { request } from "../helpers";
import { useAuth } from "../auth/AuthContext";
import SimulatedPreview from "./SimulatedPreview";
import ExamViewport from "./ExamViewport";
import { EXAM_STATUS_COLORS, EXAM_PRIORITY_COLORS } from "../common/statusColors";
import "./ExamConsole.css";

const Content = Layout.Content;

const STATUS_COLORS = EXAM_STATUS_COLORS;

const PRIORITY_COLORS = EXAM_PRIORITY_COLORS;

// Modality-specific acquisition workflows (FR-R06-10). These drive the
// sequence list shown in the acquisition panel.
const MODALITY_WORKFLOWS: Record<string, { name: string; sequences: string[] }> = {
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

// Reject reasons map onto incident types (FR-R06-08): a rejected image IS an
// incident candidate, so Log Incident pre-fills the type from the reason the
// technologist picked in the QA queue.
const REJECT_TO_INCIDENT: Record<string, string> = {
  "Patient motion": "patient_motion",
  "Positioning error": "positioning_error",
  Artifact: "other",
  "Exposure error": "other",
  Other: "other",
};

const SAFETY_CHECK_ITEMS = [
  { check_item: "No known contrast allergies", key: "allergies" },
  {
    check_item: "Not pregnant (or documented radiation risk accepted)",
    key: "pregnancy",
  },
  { check_item: "Creatinine/recent lab values reviewed", key: "renal" },
];

// The QA queue merges this session's optimistic previews with the server's
// pending acquisitions (which survive a reload, FR-R06-04), deduped by id —
// the same acquisition appears in both until the refetch lands.
function mergePending(previews: any[], server: any[]): any[] {
  const byId = new Map<string, any>();
  for (const a of previews) byId.set(a.id, a);
  for (const a of server) {
    if (a.status === "pending") byId.set(a.id, a);
  }
  return [...byId.values()];
}

// Highest recorded series number across the ledger; the next series is
// derived from this instead of a client counter so a reload can never reuse
// a number already in the dose ledger (FR-R06-05).
function maxSeriesOf(previews: any[], server: any[]): number {
  let m = 0;
  for (const a of [...previews, ...server]) {
    const n = Number(a.series_number);
    if (Number.isFinite(n) && n > m) m = n;
  }
  return m;
}

function ExamConsole() {
  const { message } = App.useApp();
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

  // T-06: protocol favorites + body-part narrowing on the registry picker.
  const [favOnly, setFavOnly] = useState(false);
  const [bodyPartFilter, setBodyPartFilter] = useState<string>("");

  // Acquisition state.
  const [pendingPreviews, setPendingPreviews] = useState<any[]>([]);

  // Modals.
  const [incidentOpen, setIncidentOpen] = useState(false);
  const [overrideOpen, setOverrideOpen] = useState(false);
  const [rejectOpen, setRejectOpen] = useState<string | null>(null); // acquisition id
  const [flagOpen, setFlagOpen] = useState(false);
  const [flagging, setFlagging] = useState(false);
  const [completing, setCompleting] = useState(false);
  // Per-item safety confirmations (FR-R06-06): each item must be explicitly
  // checked before it is sent — no all-or-nothing hardcoded "confirmed".
  const [safetyChecked, setSafetyChecked] = useState<string[]>([]);

  const [incidentForm] = Form.useForm();
  const [overrideForm] = Form.useForm();
  const [rejectForm] = Form.useForm();
  const [flagForm] = Form.useForm();

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

  // technologist review P2-1: "who is next" on the modality, so the tech
  // keeps the room moving without tabbing back to the worklist mid-scan.
  // Refetched whenever the exam payload lands (identity/protocol/acquire all
  // refetch it), so the pointer stays fresh while the room progresses.
  const [nextExam, setNextExam] = useState<any | null>(null);
  useEffect(() => {
    if (!exam) return;
    request("exams", {
      query: {
        status: "ready",
        modality: exam.modality || "",
        assigned: "pool",
        per_page: "1",
      },
    })
      .then((res: any) => {
        const rows = Array.isArray(res.data) ? res.data : [];
        const n = rows.find((r: any) => r.id !== exam.id) || null;
        setNextExam(n);
      })
      .catch(() => {});
  }, [exam?.id, exam?.modality, exam?.status, exam?.accession_number]);

  // C8 (NFR-R06-06): Ctrl+Shift+W jumps back to the worklist from anywhere
  // in the exam console; preventDefault stops the browser from closing the
  // tab (Ctrl+W is the tab-close chord, Ctrl+Shift+W has no default here).
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key.toLowerCase() === "w") {
        e.preventDefault();
        navigate("/exams");
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [navigate]);

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

  // T-06: flip the favorite flag on one protocol; response carries the new
  // state so no refetch is needed.
  const toggleFavorite = useCallback(
    async (name: string) => {
      const proto = protocols.find((p: any) => p.name === name);
      if (!proto?.id) return;
      try {
        const res = await request(`protocols/${proto.id}/favorite`, {
          method: "POST",
          data: undefined,
        });
        const fav = !!res?.data?.is_favorite;
        setProtocols((prev: any[]) =>
          prev.map((p: any) => (p.id === proto.id ? { ...p, is_favorite: fav } : p))
        );
      } catch {
        /* favorite toggle is best-effort — keep current state on failure */
      }
    },
    [protocols]
  );

  // T-06: registry options narrowed by body part / favorites-only.
  const protocolOptions = useMemo(() => {
    return protocols
      .filter((p: any) => (favOnly ? p.is_favorite : true))
      .filter((p: any) => (bodyPartFilter ? p.body_part === bodyPartFilter : true))
      .map((p: any) => ({
        value: p.name,
        label: p.is_favorite ? `★ ${p.name}` : p.name,
      }));
  }, [protocols, favOnly, bodyPartFilter]);

  const bodyParts = useMemo(
    () => Array.from(new Set(protocols.map((p: any) => p.body_part).filter(Boolean))).sort(),
    [protocols]
  );

  const workflow = useMemo(
    () => MODALITY_WORKFLOWS[exam?.modality || ""] || null,
    [exam?.modality]
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
    [fetchExam]
  );

  const confirmIdentity = async () => {
    const ok = await doRequest(
      `exams/${id}/identity-confirm`,
      { confirmed: true },
      "Patient identity confirmed"
    );
    if (ok) message.success("Exam is now in progress");
  };

  const startProtocol = async () => {
    const ok = await doRequest(
      `exams/${id}/protocol`,
      { protocol_name: selectedProtocol || exam?.protocol_name || "" },
      "Protocol started"
    );
    if (ok) message.info("Acquisition ready — acquire images below");
  };

  const acquireImage = async (retakeOf?: any) => {
    // Record a simulated acquisition with plausible dose parameters for the
    // modality, then show it in the pending QA queue (FR-R06-04/05). When
    // retakeOf is set this is a re-acquisition of a rejected series: the new
    // series number is the rejected one + 1 and the description marks the
    // retake so the linkage is visible in the QA queue.
    //
    // The next series number is derived from the recorded ledger
    // (exam.acquisitions + this session's pending items) rather than a
    // client counter, so a reload can never reuse a series number already in
    // the dose ledger (FR-R06-05) — the collision the retake flow makes
    // likely: rejects happen after several acquisitions.
    const dose =
      exam?.modality === "CT"
        ? { kvp: 120, mas: 210, dlp: 520, ctdivol: 12.5 }
        : exam?.modality === "MR"
          ? { kvp: 0, mas: 0, dlp: 0, ctdivol: 0, exposure_time: 3200 }
          : exam?.modality === "PET"
            ? { kvp: 140, mas: 120, dlp: 0, ctdivol: 0, exposure_time: 1800 }
            : { kvp: 75, mas: 8, dlp: 0, ctdivol: 0, exposure_time: 40 };
    const maxSeries = maxSeriesOf(pendingPreviews, exam?.acquisitions || []);
    const nextSeries = retakeOf
      ? Math.max(maxSeries, Number(retakeOf.series_number) || 0) + 1
      : maxSeries + 1;
    const description = retakeOf
      ? `Retake — ${retakeOf.description || `Series ${retakeOf.series_number}`}`
      : workflow?.sequences[Math.min(nextSeries - 1, (workflow?.sequences.length || 1) - 1)] ||
        `Series ${nextSeries}`;
    try {
      const res = await request(`exams/${id}/acquisitions`, {
        data: {
          series_number: nextSeries,
          description,
          ...dose,
        },
      });
      message.success(retakeOf ? "Retake acquired — pending QA" : "Image acquired");
      setPendingPreviews((p) => [...p, res.data]);
      await fetchExam();
    } catch (e: any) {
      message.error(e.message || "Acquisition failed");
    }
  };

  const decideAcquisition = async (acqId: string, decision: "accept" | "reject", reason = "") => {
    const ok = await doRequest(
      `exams/${id}/acquisitions/${acqId}/${decision}`,
      { reason },
      decision === "accept" ? "Image accepted" : "Image rejected"
    );
    if (ok) setPendingPreviews((p) => p.filter((a) => a.id !== acqId));
    return ok;
  };

  // FR-R06-08: a rejected image is an incident candidate — open the incident
  // modal pre-filled from the reject reason the technologist just picked.
  const openIncidentForRejected = (acq: any) => {
    incidentForm.setFieldsValue({
      incident_type: REJECT_TO_INCIDENT[acq.reject_reason] || "other",
      severity: "medium",
      description:
        `Rejected series ${acq.series_number}` +
        (acq.reject_reason ? ` (${acq.reject_reason})` : "") +
        (acq.description ? `: ${acq.description}` : ""),
    });
    setIncidentOpen(true);
  };

  const recordSafetyChecks = async () => {
    // Only the items the technologist individually confirmed are recorded
    // (FR-R06-06); unverified items stay absent rather than "confirmed".
    const checks = SAFETY_CHECK_ITEMS.filter((item) => safetyChecked.includes(item.key)).map(
      (item) => ({
        check_item: item.check_item,
        answer: "confirmed",
        notes: "",
      })
    );
    if (!checks.length) {
      message.warning("Confirm at least one safety check before recording");
      return;
    }
    const ok = await doRequest(`exams/${id}/safety-checks`, { checks }, "Safety checks recorded");
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
    const ok = await doRequest(`exams/${id}/incidents`, values, "Incident logged");
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
      "Override logged"
    );
    if (ok) {
      setOverrideOpen(false);
      overrideForm.resetFields();
    }
  };

  // technologist review P1-1: flag an alarming finding for immediate read.
  const submitFlag = async () => {
    let values;
    try {
      values = await flagForm.validateFields();
    } catch {
      return; // validation errors shown inline
    }
    setFlagging(true);
    try {
      await request(`exams/${id}/critical-flag`, {
        data: {
          severity: values.severity,
          note: values.note,
          series_id: values.series_id ?? null,
        },
      });
      message.success("Flagged for immediate read");
      setFlagOpen(false);
      flagForm.resetFields();
      await fetchExam();
    } catch (e: any) {
      message.error(e.message || "Flag failed");
    } finally {
      setFlagging(false);
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
        <Alert type="error" title="Failed to load exam" description={error} showIcon />
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
  // Server-side pending acquisitions survive a reload (FR-R06-04): they come
  // back in exam.acquisitions with status 'pending', so the QA queue is the
  // merge of those with this session's optimistic previews.
  const pendingAcqs = mergePending(pendingPreviews, acquisitions);
  const nextSeries = maxSeriesOf(pendingPreviews, acquisitions) + 1;
  const rejectedCount = acquisitions.filter((a: any) => a.status === "rejected").length;
  // Rejected acquisitions stay visible with Retake / Log Incident actions
  // (FR-R06-04: rejects require re-acquisition). Derived from the server
  // list so rejects survive reloads, matching how rejectedCount is computed.
  const rejectedAcqs: any[] = acquisitions.filter((a: any) => a.status === "rejected");
  const isComplete = exam.status === "completed";
  const identityDone = !!exam.identity_confirmed_at || exam.status === "in_progress";
  const protocolStarted = !!exam.protocol_name;
  // FR-R06-02: prior studies for the comparison link in the identity card.
  const priorStudies = exam.prior_studies || [];

  const stepIndex = exam.status === "completed" ? 4 : identityDone ? (protocolStarted ? 2 : 1) : 0;

  return (
    <Content style={{ padding: 24 }} role="main">
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
          {exam.critical_flag && (
            <Tag color="red" icon={<AlertOutlined />} data-testid="critical-flag-badge">
              CRITICAL FLAG ({String(exam.critical_flag).toUpperCase()})
            </Tag>
          )}
          {hasPermission("CRITICAL_RESULTS_WRITE") && !isComplete && (
            <Button icon={<AlertOutlined />} danger onClick={() => setFlagOpen(true)}>
              Flag Critical
            </Button>
          )}
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
          title="Read-only exam console"
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

      {/* technologist review P2-1: who is next on this modality, so the
          tech keeps the room moving without tabbing back mid-scan. */}
      {nextExam && (
        <Alert
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
          title={
            <span>
              <b>Next:</b> {nextExam.accession_number || "—"} ·{" "}
              {nextExam.patient_name || nextExam.patient_id || "—"} · {nextExam.modality || ""}{" "}
              {nextExam.priority && nextExam.priority !== "routine" && (
                <Tag color={PRIORITY_COLORS[nextExam.priority]}>
                  {String(nextExam.priority).toUpperCase()}
                </Tag>
              )}
            </span>
          }
          action={
            <Button size="small" type="link" onClick={() => navigate(`/exams/${nextExam.id}`)}>
              Open
            </Button>
          }
        />
      )}

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
          <Descriptions.Item label="Patient Name">{exam.patient_name || "—"}</Descriptions.Item>
          <Descriptions.Item label="Patient ID">{exam.patient_id || "—"}</Descriptions.Item>
          <Descriptions.Item label="DOB">{exam.patient_birth_date || "—"}</Descriptions.Item>
          <Descriptions.Item label="Sex">{exam.patient_sex || "—"}</Descriptions.Item>
          <Descriptions.Item label="Accession">{exam.accession_number || "—"}</Descriptions.Item>
          <Descriptions.Item label="Modality">{exam.modality || "—"}</Descriptions.Item>
          <Descriptions.Item label="Prior Studies" span={3}>
            {priorStudies.length === 0 ? (
              "—"
            ) : (
              <div className="exam-prior-studies">
                {priorStudies.map((s: any) => (
                  <div key={s.id} className="exam-prior-study">
                    <span>
                      {s.description || s.accession_number || `Study ${s.id}`}
                      {s.modality ? ` · ${s.modality}` : ""}
                    </span>
                    {s.first_file_id ? (
                      <Link to={`/files/${s.first_file_id}`} className="exam-prior-link">
                        Open in viewer
                      </Link>
                    ) : (
                      <span className="exam-prior-nofiles">no images</span>
                    )}
                  </div>
                ))}
              </div>
            )}
          </Descriptions.Item>
        </Descriptions>
      </Card>

      {/* FR-R06-03..07: acquisition console layout (S-R06-03/04) — protocol
          + viewport/QA stay in the main column while dose, safety, and
          completion ride the right rail, so the technologist can glance
          between patient, image, and dose without scrolling (NFR-R06-10). */}
      <div className="exam-console-grid">
        <div className="exam-console-main">
          {/* FR-R06-03: Protocol selection + start */}
          <Card
            title="Protocol"
            size="small"
            extra={
              !isComplete && protocolStarted ? (
                <Tag color="gold">Started: {exam.protocol_name}</Tag>
              ) : undefined
            }
          >
            {protocolStarted ? (
              <Descriptions size="small" column={1} bordered>
                <Descriptions.Item label="Protocol">{exam.protocol_name}</Descriptions.Item>
                <Descriptions.Item label="Workflow (FR-R06-10)">
                  {workflow ? `${workflow.name}: ${workflow.sequences.join(" → ")}` : "—"}
                </Descriptions.Item>
              </Descriptions>
            ) : canWrite ? (
              <>
                <Space size="middle" wrap>
                  <Select
                    placeholder="Select protocol"
                    style={{ width: 320 }}
                    value={selectedProtocol || undefined}
                    onChange={setSelectedProtocol}
                    options={protocolOptions}
                    showSearch={{ optionFilterProp: "label" }}
                  />
                  {/* T-06: favorite star for the highlighted protocol. */}
                  <Button
                    aria-label={
                      protocols.find((p: any) => p.name === selectedProtocol)?.is_favorite
                        ? "Unfavorite protocol"
                        : "Favorite protocol"
                    }
                    icon={
                      protocols.find((p: any) => p.name === selectedProtocol)?.is_favorite ? (
                        <StarFilled />
                      ) : (
                        <StarOutlined />
                      )
                    }
                    onClick={() => selectedProtocol && toggleFavorite(selectedProtocol)}
                  />
                  <Select
                    allowClear
                    placeholder="Body part"
                    style={{ width: 140 }}
                    value={bodyPartFilter || undefined}
                    onChange={(v: string) => setBodyPartFilter(v || "")}
                    options={bodyParts.map((bp: string) => ({
                      value: bp,
                      label: bp,
                    }))}
                  />
                  <Checkbox checked={favOnly} onChange={(e) => setFavOnly(e.target.checked)}>
                    Favorites only
                  </Checkbox>
                </Space>
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
              <Alert type="info" showIcon title="No protocol started yet — read-only view." />
            )}
          </Card>

          {/* FR-R06-04/05: Acquisition + QA */}
          <Card
            title="Acquisition & QA"
            size="small"
            style={{ marginTop: 16 }}
            extra={
              canWrite && !isComplete && identityDone && protocolStarted ? (
                <Button type="primary" onClick={() => acquireImage()}>
                  Acquire Image
                </Button>
              ) : undefined
            }
          >
            {(!identityDone || !protocolStarted) && !isComplete ? (
              <Alert
                type="info"
                showIcon
                title="Confirm the patient and start the protocol before acquiring images."
              />
            ) : (
              <div className="exam-acq">
                <div className="exam-acq-preview">
                  {/* C11 (Sprint D): mount the real viewer when the exam's study
                  has been stored; SimulatedPreview stays the no-DICOM
                  fallback so the console never shows an empty box. */}
                  {exam.imaging && exam.imaging_patient ? (
                    <ExamViewport
                      patient={exam.imaging_patient}
                      patientName={exam.patient_name}
                      patientId={exam.patient_id}
                      examModality={exam.modality}
                    />
                  ) : (
                    <SimulatedPreview label={`Series ${Math.max(1, nextSeries)} preview`} />
                  )}
                </div>
                <div className="exam-acq-queue">
                  <h4>QA Queue ({pendingAcqs.length} pending)</h4>
                  {pendingAcqs.length === 0 && (
                    <span className="exam-acq-empty">
                      Pending acquisitions will appear here for accept/reject.
                    </span>
                  )}
                  {pendingAcqs.map((acq) => (
                    <div key={acq.id} className="exam-acq-item">
                      {/* §3-10: each pending acquisition is represented by a
                          thumbnail, not text only — the real viewport mounts
                          for exams with DICOM (C11); the simulated mini
                          canvas covers the fallback path. */}
                      <SimulatedPreview
                        mini
                        width={88}
                        height={88}
                        label={acq.description || "Series"}
                      />
                      <div className="exam-acq-item-info">
                        <b>{acq.description || "Series"}</b>
                        <span className="exam-acq-item-meta">
                          DLP {acq.dlp || 0} · CTDIvol {acq.ctdivol || 0} · kVp {acq.kvp || 0}
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
                            <Button size="small" danger onClick={() => setRejectOpen(acq.id)}>
                              Reject
                            </Button>
                          </>
                        )}
                      </Space>
                    </div>
                  ))}
                  {rejectedAcqs.length > 0 && (
                    <div className="exam-acq-rejected">
                      <h4>Rejected ({rejectedAcqs.length})</h4>
                      {rejectedAcqs.map((acq: any) => (
                        <div key={acq.id} className="exam-acq-item exam-acq-item-rejected">
                          <div>
                            <b>{acq.description || "Series"}</b>
                            <span className="exam-acq-item-meta">
                              Series {acq.series_number} · Rejected:{" "}
                              {acq.reject_reason || "no reason"}
                            </span>
                          </div>
                          <Space>
                            {canWrite && (
                              <>
                                <Button
                                  size="small"
                                  type="primary"
                                  ghost
                                  onClick={() => acquireImage(acq)}
                                >
                                  Retake
                                </Button>
                                <Button size="small" onClick={() => openIncidentForRejected(acq)}>
                                  Log Incident
                                </Button>
                              </>
                            )}
                          </Space>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}
            {isComplete && <Alert type="success" showIcon title="Acquisition complete." />}
          </Card>
        </div>

        <div className="exam-console-rail">
          {/* FR-R06-05: Dose documentation */}
          <Card title="Dose Documentation" size="small">
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
              {acquisitions.length > 0 && (
                <div className="exam-dose-series">
                  {/* C6 (FR-R06-05): per-series ledger alongside the cumulative
                  totals. The label prefixes the series number so the QA
                  queue's bare description stays a distinct text node. */}
                  <h4>Per-series dose</h4>
                  <Table
                    rowKey="id"
                    size="small"
                    pagination={false}
                    dataSource={acquisitions}
                    columns={[
                      {
                        title: "Series",
                        render: (_: any, a: any) => `S${a.series_number} · ${a.description || "—"}`,
                      },
                      {
                        title: "DLP (mGy·cm)",
                        align: "right" as const,
                        render: (_: any, a: any) => Number(a.dlp || 0).toFixed(1),
                      },
                      {
                        title: "CTDIvol (mGy)",
                        align: "right" as const,
                        render: (_: any, a: any) => Number(a.ctdivol || 0).toFixed(1),
                      },
                      {
                        title: "kVp",
                        align: "right" as const,
                        render: (_: any, a: any) => Number(a.kvp || 0).toFixed(0),
                      },
                      {
                        title: "Status",
                        render: (_: any, a: any) => (
                          <Tag color={STATUS_COLORS[a.status] || "default"}>{a.status}</Tag>
                        ),
                      },
                    ]}
                  />
                </div>
              )}
              {exam.benchmark_dlp ? (
                <div className="exam-dose-benchmark">
                  <Progress
                    percent={Math.min(
                      100,
                      Math.round((Number(dose.total_dlp || 0) / exam.benchmark_dlp) * 100)
                    )}
                    status={
                      doseLevel === "danger"
                        ? "exception"
                        : doseLevel === "warning"
                          ? "active"
                          : "normal"
                    }
                    format={(p) => `${p}% of ACR benchmark (${exam.benchmark_dlp} mGy·cm)`}
                  />
                </div>
              ) : (
                <span className="exam-dose-note">
                  ACR benchmark not defined for {exam.modality || "this modality"}.
                </span>
              )}
              {/* C6 (FR-R06-05): flag the panel itself when the ACR benchmark is
              approached or exceeded — the bar's color is not enough. */}
              {doseLevel === "warning" && (
                <Alert
                  type="warning"
                  showIcon
                  style={{ marginTop: 12 }}
                  title="Approaching the ACR benchmark — review remaining exposures."
                />
              )}
              {doseLevel === "danger" && (
                <Alert
                  type="error"
                  showIcon
                  style={{ marginTop: 12 }}
                  title="ACR dose benchmark exceeded — document and notify QA."
                />
              )}
            </div>
          </Card>

          {/* FR-R06-06: Safety checks */}
          <Card
            title="Safety Checks (pre-contrast)"
            size="small"
            extra={
              canWrite && !isComplete && !(exam.safety_checks || []).length ? (
                <Button
                  onClick={recordSafetyChecks}
                  icon={<SafetyCertificateOutlined />}
                  disabled={!safetyChecked.length}
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
            ) : canWrite && !isComplete ? (
              /* Each item is individually confirmed (FR-R06-06); the pregnancy
             item carries a radiation warning since confirming it is a
             prerequisite for ionizing-radiation studies. */
              <div className="exam-safety-list">
                {SAFETY_CHECK_ITEMS.map((item) => (
                  <div key={item.key} className="exam-safety-item">
                    <Checkbox
                      checked={safetyChecked.includes(item.key)}
                      onChange={(e) =>
                        setSafetyChecked((prev) =>
                          e.target.checked
                            ? [...prev, item.key]
                            : prev.filter((k) => k !== item.key)
                        )
                      }
                    >
                      {item.check_item}
                    </Checkbox>
                    {item.key === "pregnancy" && (
                      <Alert
                        type="warning"
                        showIcon
                        className="exam-safety-warning"
                        title="Ionizing radiation risk: confirm pregnancy status before scanning. Flag for review if unknown."
                      />
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <Alert
                type="warning"
                showIcon
                title={
                  exam.status === "completed"
                    ? "No safety checks recorded for this exam."
                    : "Record safety checks before contrast administration."
                }
              />
            )}
            {/* technologist review P2-3: prior contrast/safety screening for
                the same patient — the tech sees documented reactions before
                scanning instead of discovering them after the fact. */}
            {(exam.prior_safety_checks || []).length > 0 && (
              <div style={{ marginTop: 12 }}>
                <Divider style={{ margin: "8px 0" }} />
                <h4>Prior screenings</h4>
                {exam.prior_safety_checks.map((s: any, i: number) => (
                  <div key={i} className="exam-prior-study">
                    <span>
                      {s.check_item} · {s.answer} ·{" "}
                      {s.accession_number ? `Exam ${s.accession_number}` : ""}{" "}
                      {s.checked_at ? `· ${String(s.checked_at).slice(0, 10)}` : ""}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </Card>

          {/* §2.11 nursing (N-01..N-04): exam-linked vitals / pre-procedure
              checklist / contrast consent / nurse notes. Renders only for
              NURSING_READ holders; EXAM_READ-only viewers (tech, radiologist)
              see the records read-only per spec N-04 visibility. */}
          <NursingPanel exam={exam} />

          {/* FR-R06-07: Complete + handoff */}
          {!isComplete && canWrite && (
            <Card
              title="Complete Exam"
              size="small"
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
                title="Completing the exam hands it off to the radiologist worklist and notifies the reading team."
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
              title="Exam completed and handed off to the radiologist worklist."
            />
          )}
        </div>
      </div>

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
            <Input.TextArea rows={3} placeholder="e.g. patient moved during scan" />
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
          title="Overrides are audited and logged. A justification is required."
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
            <Input.TextArea rows={3} placeholder="e.g. Trauma — reducing sequence count" />
          </Form.Item>
        </Form>
      </Modal>

      {/* technologist review P1-1: flag an alarming finding for immediate
          radiology read. Severity mirrors the incident scale; series_id
          optionally points at the acquisition that triggered the flag. */}
      <Modal
        title="Flag Critical Finding"
        open={flagOpen}
        onCancel={() => setFlagOpen(false)}
        onOk={submitFlag}
        okText="Flag for Immediate Read"
        okButtonProps={{ danger: true, loading: flagging }}
        destroyOnHidden
      >
        <Alert
          type="warning"
          showIcon
          style={{ marginBottom: 16 }}
          title="This flag is visible to the reading team immediately."
        />
        <Form form={flagForm} layout="vertical">
          <Form.Item
            name="severity"
            label="Severity"
            rules={[{ required: true }]}
            initialValue="critical"
          >
            <Select
              options={["low", "medium", "high", "critical"].map((s) => ({
                value: s,
                label: s,
              }))}
            />
          </Form.Item>
          <Form.Item name="series_id" label="Series (optional)">
            <Select
              allowClear
              placeholder="Series that triggered the flag"
              options={acquisitions.map((a: any) => ({
                value: a.id,
                label: `S${a.series_number} · ${a.description || "—"}`,
              }))}
            />
          </Form.Item>
          <Form.Item
            name="note"
            label="Why is this critical?"
            rules={[
              { required: true, message: "Describe the finding" },
              { min: 10, message: "Provide at least 10 characters" },
            ]}
          >
            <Input.TextArea
              rows={3}
              placeholder="e.g. massive subdural hematoma visible on localizer"
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
