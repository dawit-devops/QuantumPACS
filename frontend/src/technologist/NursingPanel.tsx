import React, { useEffect, useRef, useState } from "react";
import {
  Alert,
  App,
  Button,
  Card,
  Checkbox,
  Descriptions,
  Form,
  Input,
  InputNumber,
  Table,
  Tabs,
  Tag,
  Timeline,
  Typography,
} from "antd";
import { CheckCircleOutlined } from "@ant-design/icons";
import { useAuth } from "../auth/AuthContext";
import RequirePermission from "../auth/RequirePermission";
import SignaturePad, { type SignaturePadHandle } from "../common/SignaturePad";
import {
  addNurseNote,
  getChecklist,
  getConsent,
  getExamVitals,
  getNurseNotes,
  recordConsent,
  recordExamVitals,
  updateChecklist,
  type ChecklistItem,
  type ConsentRow,
  type NurseNoteRow,
  type VitalsRow,
} from "../api/nursing";

const { Text } = Typography;

// Spec N-03: contrast administration carries documented risks — the fixed
// acknowledgment text is versioned so a stored consent names what was read.
const CONSENT_TEXT_VERSION = "contrast-v1";

const num = (v: number | null | undefined): string =>
  v === null || v === undefined ? "—" : String(v);

/**
 * §2.11 Nursing panel inside the exam console. Visible with NURSING_READ;
 * every write control additionally requires NURSING_WRITE — technologists
 * and radiologists (EXAM_READ holders) see the records read-only (spec N-04).
 */
function NursingPanel({ exam }: { exam: any }) {
  const { hasPermission } = useAuth();
  const { message } = App.useApp();
  const canWrite = hasPermission("NURSING_WRITE");

  // Vitals (N-01)
  const [vitals, setVitals] = useState<VitalsRow[]>([]);
  const [vitalsForm] = Form.useForm();
  const [recordingVitals, setRecordingVitals] = useState(false);
  // Checklist (N-02)
  const [items, setItems] = useState<ChecklistItem[]>([]);
  const [checklistStatus, setChecklistStatus] = useState<"in_progress" | "complete">("in_progress");
  const [savingChecklist, setSavingChecklist] = useState<"progress" | "confirm" | null>(null);
  // Consent (N-03)
  const padRef = useRef<SignaturePadHandle>(null);
  const [hasSignature, setHasSignature] = useState(false);
  const [acknowledged, setAcknowledged] = useState(false);
  const [declineReason, setDeclineReason] = useState("");
  const [consent, setConsent] = useState<ConsentRow | null>(null);
  const [submittingConsent, setSubmittingConsent] = useState(false);
  // Notes (N-04)
  const [notes, setNotes] = useState<NurseNoteRow[]>([]);
  const [newNote, setNewNote] = useState("");
  // Per-surface load failures: a swallowed error once rendered an
  // apparently-empty record clinicians could chart against.
  const [loadErrors, setLoadErrors] = useState<Record<string, boolean>>({});

  const markLoadError = (key: string, failed: boolean) =>
    setLoadErrors((prev) => ({ ...prev, [key]: failed }));

  useEffect(() => {
    if (!exam?.id) return;
    if (!hasPermission("NURSING_READ") && !hasPermission("EXAM_READ")) return;
    setLoadErrors({});
    getExamVitals(exam.id)
      .then((rows) => {
        setVitals(rows);
        markLoadError("vitals", false);
      })
      .catch(() => markLoadError("vitals", true));
    getChecklist(exam.id)
      .then((row) => {
        setItems(row.items || []);
        setChecklistStatus(row.status || "in_progress");
        markLoadError("checklist", false);
      })
      .catch(() => markLoadError("checklist", true));
    getConsent(exam.id)
      .then((row) => {
        setConsent(row);
        markLoadError("consent", false);
      })
      .catch(() => markLoadError("consent", true));
    getNurseNotes(exam.id)
      .then((rows) => {
        setNotes(rows);
        markLoadError("notes", false);
      })
      .catch(() => markLoadError("notes", true));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [exam?.id]);

  const reload = (key: "vitals" | "checklist" | "consent" | "notes") => {
    if (!exam?.id) return;
    markLoadError(key, false);
    const fail = () => markLoadError(key, true);
    if (key === "vitals") getExamVitals(exam.id).then(setVitals).catch(fail);
    else if (key === "checklist")
      getChecklist(exam.id)
        .then((row) => {
          setItems(row.items || []);
          setChecklistStatus(row.status || "in_progress");
        })
        .catch(fail);
    else if (key === "consent") getConsent(exam.id).then(setConsent).catch(fail);
    else getNurseNotes(exam.id).then(setNotes).catch(fail);
  };

  /** Inline retryable banner shown at the top of a tab whose load failed. */
  const loadErrorBanner = (key: "vitals" | "checklist" | "consent" | "notes", label: string) =>
    loadErrors[key] ? (
      <div data-testid={`nursing-${key}-load-error`}>
        <Alert
          type="error"
          showIcon
          message={`Failed to load ${label}`}
          action={
            <Button size="small" danger onClick={() => reload(key)}>
              Retry
            </Button>
          }
          style={{ marginBottom: 12 }}
        />
      </div>
    ) : null;

  // Mount rule mirrors the API's record-read gate: NURSING_READ holders work
  // here; EXAM_READ-only viewers (tech, radiologist) see the same records
  // read-only — spec N-04 makes nurse documentation visible to them.
  if (!exam || (!hasPermission("NURSING_READ") && !hasPermission("EXAM_READ"))) {
    return null;
  }

  const recordVitals = async () => {
    const values = await vitalsForm.validateFields().catch(() => null);
    if (!values) return;
    setRecordingVitals(true);
    try {
      await recordExamVitals(exam.id, values);
      message.success("Vitals recorded");
      vitalsForm.resetFields();
      setVitals(await getExamVitals(exam.id));
    } catch (e: any) {
      message.error(e.message || "Failed to record vitals");
    } finally {
      setRecordingVitals(false);
    }
  };

  const unmetRequired = () => items.filter((i) => i.required && !i.checked).map((i) => i.label);

  const saveChecklist = async (confirmed: boolean) => {
    setSavingChecklist(confirmed ? "confirm" : "progress");
    try {
      const row = await updateChecklist(exam.id, { items, confirmed });
      setItems(row.items || items);
      setChecklistStatus(row.status || checklistStatus);
      message.success(confirmed ? "Checklist confirmed" : "Checklist progress saved");
    } catch (e: any) {
      // The server re-validates the required-items rule before confirming.
      message.error(e.message || "Failed to save checklist");
    } finally {
      setSavingChecklist(null);
    }
  };

  const submitConsent = async (accepted: boolean) => {
    setSubmittingConsent(true);
    try {
      const row = await recordConsent(
        exam.id,
        accepted
          ? {
              accepted: true,
              signature_png: padRef.current?.capture() || "",
              consent_text_version: CONSENT_TEXT_VERSION,
            }
          : { accepted: false, declined_reason: declineReason.trim() }
      );
      setConsent(row);
      message.success(accepted ? "Consent stored" : "Decline recorded");
    } catch (e: any) {
      message.error(e.message || "Failed to store consent");
    } finally {
      setSubmittingConsent(false);
    }
  };

  const addNote = async () => {
    const note = newNote.trim();
    if (!note) return;
    try {
      const row = await addNurseNote(exam.id, note);
      setNotes([row, ...notes]);
      setNewNote("");
      message.success("Note added");
    } catch (e: any) {
      message.error(e.message || "Failed to add note");
    }
  };

  const vitalColumns = [
    { title: "Recorded", dataIndex: "recorded_at", width: 170 },
    {
      title: "BP",
      key: "bp",
      render: (_: unknown, r: VitalsRow) => `${num(r.bp_systolic)}/${num(r.bp_diastolic)}`,
      width: 80,
    },
    { title: "HR", dataIndex: "hr", width: 60 },
    { title: "SpO₂", dataIndex: "spo2", width: 60 },
    { title: "Temp °C", dataIndex: "temperature", width: 80 },
    { title: "Resp", dataIndex: "respiration", width: 60 },
  ];

  const vitalsTab = (
    <div>
      {loadErrorBanner("vitals", "vitals")}
      <Table
        rowKey="id"
        size="small"
        pagination={false}
        dataSource={vitals}
        columns={vitalColumns}
        locale={{
          // A failed load must not read as "no vitals exist".
          emptyText: loadErrors.vitals
            ? "Could not load vitals."
            : "No vitals recorded for this exam yet",
        }}
        style={{ marginBottom: 16 }}
      />
      <RequirePermission permission="NURSING_WRITE">
        <Form form={vitalsForm} layout="inline" size="small">
          <Form.Item name="bp_systolic" rules={[{ type: "number", min: 30, max: 250 }]}>
            <InputNumber placeholder="BP sys" min={30} max={250} style={{ width: 90 }} />
          </Form.Item>
          <Form.Item name="bp_diastolic" rules={[{ type: "number", min: 20, max: 150 }]}>
            <InputNumber placeholder="BP dia" min={20} max={150} style={{ width: 90 }} />
          </Form.Item>
          <Form.Item name="heart_rate" rules={[{ type: "number", min: 20, max: 260 }]}>
            <InputNumber placeholder="HR" min={20} max={260} style={{ width: 70 }} />
          </Form.Item>
          <Form.Item name="spo2" rules={[{ type: "number", min: 50, max: 100 }]}>
            <InputNumber placeholder="SpO₂" min={50} max={100} style={{ width: 70 }} />
          </Form.Item>
          <Form.Item name="temperature_c" rules={[{ type: "number", min: 30, max: 43 }]}>
            <InputNumber placeholder="Temp °C" min={30} max={43} step={0.1} style={{ width: 90 }} />
          </Form.Item>
          <Form.Item name="respiration" rules={[{ type: "number", min: 4, max: 60 }]}>
            <InputNumber placeholder="Resp" min={4} max={60} style={{ width: 70 }} />
          </Form.Item>
          <Form.Item name="weight_kg" rules={[{ type: "number", min: 0, max: 500 }]}>
            <InputNumber placeholder="Weight kg" min={0} max={500} style={{ width: 100 }} />
          </Form.Item>
          <Form.Item name="height_cm" rules={[{ type: "number", min: 0, max: 300 }]}>
            <InputNumber placeholder="Height cm" min={0} max={300} style={{ width: 100 }} />
          </Form.Item>
          <Form.Item>
            <Button type="primary" loading={recordingVitals} onClick={recordVitals}>
              Record vitals
            </Button>
          </Form.Item>
        </Form>
      </RequirePermission>
    </div>
  );

  const allRequiredChecked = unmetRequired().length === 0;

  const checklistTab = (
    <div>
      {loadErrorBanner("checklist", "the pre-procedure checklist")}
      {checklistStatus === "complete" && (
        <Alert
          type="success"
          showIcon
          icon={<CheckCircleOutlined />}
          title="Checklist confirmed"
          style={{ marginBottom: 12 }}
        />
      )}
      <div className="exam-safety-list">
        {items.map((item) => (
          <div key={item.key} className="exam-safety-item">
            <Checkbox
              checked={item.checked}
              disabled={!canWrite || checklistStatus === "complete"}
              onChange={(e) =>
                setItems((prev) =>
                  prev.map((i) => (i.key === item.key ? { ...i, checked: e.target.checked } : i))
                )
              }
            >
              {item.label}
              {item.required && <Tag style={{ marginLeft: 6, fontSize: 10 }}>required</Tag>}
            </Checkbox>
          </div>
        ))}
      </div>
      {!allRequiredChecked && canWrite && (
        <Alert
          type="info"
          showIcon
          title="Every required item must be checked before the checklist can be confirmed."
          style={{ margin: "8px 0" }}
        />
      )}
      {canWrite && checklistStatus !== "complete" && (
        <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
          <Button size="small" onClick={() => saveChecklist(false)}>
            Save progress
          </Button>
          <Button
            size="small"
            type="primary"
            disabled={!allRequiredChecked}
            loading={savingChecklist === "confirm"}
            onClick={() => saveChecklist(true)}
          >
            Confirm checklist
          </Button>
        </div>
      )}
    </div>
  );

  const consentTab = (
    <div>
      {loadErrorBanner("consent", "the consent record")}
      {consent ? (
        <Descriptions size="small" column={2} bordered style={{ marginBottom: 12 }}>
          <Descriptions.Item label="Decision">
            {consent.accepted ? <Tag color="green">ACCEPTED</Tag> : <Tag color="red">DECLINED</Tag>}
          </Descriptions.Item>
          <Descriptions.Item label="Signed at">{consent.signed_at || "—"}</Descriptions.Item>
          {!consent.accepted && (
            <Descriptions.Item label="Reason" span={2}>
              {consent.declined_reason || "—"}
            </Descriptions.Item>
          )}
        </Descriptions>
      ) : (
        <>
          <Alert
            type="warning"
            showIcon
            title="Contrast administration risks"
            description="Documented reaction history must be reviewed before administration. Risks include allergic reaction and, with iodinated contrast, renal effects. The patient or guardian acknowledges these risks below."
            style={{ marginBottom: 12 }}
          />
          <Checkbox
            checked={acknowledged}
            disabled={!canWrite}
            onChange={(e) => setAcknowledged(e.target.checked)}
            style={{ marginBottom: 8 }}
          >
            Risks acknowledged by patient / guardian
          </Checkbox>
          {canWrite && (
            <>
              <SignaturePad ref={padRef} onSignatureChange={setHasSignature} />
              <div style={{ marginTop: 8, display: "flex", gap: 8 }}>
                <Button
                  type="primary"
                  size="small"
                  loading={submittingConsent}
                  disabled={!acknowledged || !hasSignature}
                  onClick={() => submitConsent(true)}
                >
                  Store consent
                </Button>
                <Input
                  size="small"
                  placeholder="Decline reason (required to decline)"
                  value={declineReason}
                  onChange={(e) => setDeclineReason(e.target.value)}
                  style={{ maxWidth: 320 }}
                />
                <Button
                  size="small"
                  danger
                  loading={submittingConsent}
                  disabled={!declineReason.trim()}
                  onClick={() => submitConsent(false)}
                >
                  Record decline
                </Button>
              </div>
            </>
          )}
        </>
      )}
    </div>
  );

  const notesTab = (
    <div>
      {loadErrorBanner("notes", "nurse notes")}
      <Timeline
        style={{ marginBottom: 12 }}
        items={notes.map((n) => ({
          children: (
            <>
              <Text>{n.note}</Text>
              <br />
              <Text type="secondary" style={{ fontSize: 11 }}>
                {n.author_id ? `user ${n.author_id}` : ""}{" "}
                {n.created_at ? `· ${String(n.created_at).slice(0, 16).replace("T", " ")}` : ""}
              </Text>
            </>
          ),
        }))}
      />
      {notes.length === 0 && !loadErrors.notes && (
        <Text type="secondary">No nurse notes on this exam yet.</Text>
      )}
      {canWrite && (
        <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
          <Input.TextArea
            rows={2}
            maxLength={4000}
            value={newNote}
            onChange={(e) => setNewNote(e.target.value)}
            placeholder="Nursing note visible to technologist and radiologist…"
          />
          <Button size="small" type="primary" onClick={addNote} disabled={!newNote.trim()}>
            Add note
          </Button>
        </div>
      )}
    </div>
  );

  return (
    <Card
      title="Nursing"
      size="small"
      data-testid="nursing-panel"
      extra={!canWrite ? <Tag>read-only</Tag> : undefined}
    >
      <Tabs
        size="small"
        items={[
          { key: "vitals", label: "Vitals", children: vitalsTab },
          { key: "checklist", label: "Pre-procedure", children: checklistTab },
          { key: "consent", label: "Contrast consent", children: consentTab },
          { key: "notes", label: "Notes", children: notesTab },
        ]}
      />
    </Card>
  );
}

export default NursingPanel;
