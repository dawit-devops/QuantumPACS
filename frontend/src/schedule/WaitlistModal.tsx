import { Alert, App, Button, Empty, Form, Input, Modal, Select, Table, Tag } from "antd";
import React, { useEffect, useState } from "react";
import { toErrorMessage } from "../common/errors";
import {
  addWaitlistEntry,
  deleteWaitlistEntry,
  listWaitlist,
  updateWaitlistStatus,
  type RisResource,
  type WaitlistEntry,
} from "../api/scheduling";
import "./schedule.css";

export interface WaitlistModalProps {
  open: boolean;
  resources: RisResource[];
  onClose: () => void;
  onDone: () => void;
}

const PRIORITY_COLORS: Record<string, string> = {
  STAT: "red",
  URGENT: "orange",
  ROUTINE: "default",
};

/**
 * S-08: waitlist management — patients waiting for a cancelled slot, sorted
 * by priority (STAT > urgent > routine). Schedulers can add entries, update
 * status (notified/booked/expired/cancelled), and remove.
 */
export default function WaitlistModal({ open, resources, onClose, onDone }: WaitlistModalProps) {
  const { message } = App.useApp();
  const [entries, setEntries] = useState<WaitlistEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [showAdd, setShowAdd] = useState(false);
  const [addResourceId, setAddResourceId] = useState("");
  const [addPatientId, setAddPatientId] = useState("");
  const [addPatientName, setAddPatientName] = useState("");
  const [addPriority, setAddPriority] = useState("ROUTINE");
  const [addModality, setAddModality] = useState("");
  const [addNotes, setAddNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const load = () => {
    setLoading(true);
    listWaitlist()
      .then(setEntries)
      .catch((e: unknown) => message.error(toErrorMessage(e) || "Failed to load waitlist"))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    if (open) {
      setShowAdd(false);
      load();
    }
  }, [open]);

  const addEntry = async () => {
    if (!addResourceId || !addPatientId.trim()) {
      message.error("Resource and patient ID are required");
      return;
    }
    setSubmitting(true);
    try {
      await addWaitlistEntry({
        resource_id: addResourceId,
        patient_id: addPatientId.trim(),
        patient_name: addPatientName.trim(),
        priority: addPriority,
        modality: addModality,
        notes: addNotes.trim(),
      });
      message.success("Added to waitlist");
      setShowAdd(false);
      setAddPatientId("");
      setAddPatientName("");
      setAddNotes("");
      load();
    } catch (e: unknown) {
      message.error(toErrorMessage(e) || "Failed to add to waitlist");
    } finally {
      setSubmitting(false);
    }
  };

  const columns = [
    {
      title: "Patient",
      key: "patient",
      width: 160,
      render: (_: unknown, r: WaitlistEntry) => (
        <span>
          <strong>{r.patient_name || r.patient_id}</strong>
          {r.patient_name && <div className="sched-order-meta">{r.patient_id}</div>}
        </span>
      ),
    },
    {
      title: "Priority",
      dataIndex: "priority",
      key: "priority",
      width: 90,
      render: (v: string) => (
        <Tag color={PRIORITY_COLORS[v] || "default"}>{v?.toLowerCase() || "routine"}</Tag>
      ),
    },
    {
      title: "Modality",
      dataIndex: "modality",
      key: "modality",
      width: 80,
      render: (v: string) => v || "—",
    },
    {
      title: "Status",
      dataIndex: "status",
      key: "status",
      width: 110,
      render: (v: string) => (
        <Tag
          color={
            v === "WAITING"
              ? "blue"
              : v === "NOTIFIED"
                ? "orange"
                : v === "BOOKED"
                  ? "green"
                  : "default"
          }
        >
          {v?.toLowerCase() || "waiting"}
        </Tag>
      ),
    },
    {
      title: "Notes",
      dataIndex: "notes",
      key: "notes",
      ellipsis: true,
      render: (v: string) => v || "—",
    },
    {
      title: "Action",
      key: "action",
      width: 160,
      render: (_: unknown, r: WaitlistEntry) =>
        r.status === "WAITING" ? (
          <>
            <Button
              type="link"
              size="small"
              onClick={() => {
                updateWaitlistStatus(r.id, "NOTIFIED")
                  .then(() => {
                    message.success("Marked as notified");
                    load();
                  })
                  .catch((e: unknown) => message.error(toErrorMessage(e) || "Update failed"));
              }}
            >
              Notify
            </Button>
            <Button
              type="link"
              size="small"
              onClick={() => {
                deleteWaitlistEntry(r.id)
                  .then(() => {
                    message.success("Removed from waitlist");
                    load();
                  })
                  .catch((e: unknown) => message.error(toErrorMessage(e) || "Remove failed"));
              }}
              danger
            >
              Remove
            </Button>
          </>
        ) : null,
    },
  ];

  return (
    <Modal title="Waitlist" open={open} onCancel={onClose} width={700} footer={null}>
      <div style={{ marginBottom: 12, display: "flex", gap: 8 }}>
        <Button type={showAdd ? "default" : "primary"} onClick={() => setShowAdd(!showAdd)}>
          {showAdd ? "Cancel" : "Add to Waitlist"}
        </Button>
        <Button onClick={load} loading={loading}>
          Refresh
        </Button>
      </div>

      {showAdd && (
        <div
          className="sched-form-section"
          style={{
            marginBottom: 16,
            padding: 12,
            border: "1px solid var(--border-color)",
            borderRadius: "var(--radius-md)",
          }}
        >
          <div className="sched-form-section-title">New Waitlist Entry</div>
          <Select
            aria-label="Resource"
            placeholder="Resource"
            style={{ width: "100%", marginBottom: 8 }}
            value={addResourceId || undefined}
            onChange={setAddResourceId}
            options={resources.map((r) => ({
              value: r.id,
              label: `${r.name} (${r.resource_type}${r.modality ? ` · ${r.modality}` : ""})`,
            }))}
          />
          <Input
            aria-label="Patient ID"
            placeholder="Patient ID"
            value={addPatientId}
            onChange={(e) => setAddPatientId(e.target.value)}
            style={{ marginBottom: 8 }}
          />
          <Input
            aria-label="Patient Name"
            placeholder="Patient name (optional)"
            value={addPatientName}
            onChange={(e) => setAddPatientName(e.target.value)}
            style={{ marginBottom: 8 }}
          />
          <Select
            aria-label="Priority"
            placeholder="Priority"
            style={{ width: "100%", marginBottom: 8 }}
            value={addPriority}
            onChange={setAddPriority}
            options={[
              { value: "STAT", label: "STAT" },
              { value: "URGENT", label: "Urgent" },
              { value: "ROUTINE", label: "Routine" },
            ]}
          />
          <Input
            aria-label="Modality"
            placeholder="Modality (optional)"
            value={addModality}
            onChange={(e) => setAddModality(e.target.value)}
            style={{ marginBottom: 8 }}
          />
          <Input.TextArea
            aria-label="Notes"
            placeholder="Notes (optional)"
            value={addNotes}
            onChange={(e) => setAddNotes(e.target.value)}
            rows={2}
            style={{ marginBottom: 8 }}
          />
          <Button type="primary" loading={submitting} onClick={() => void addEntry()}>
            Add
          </Button>
        </div>
      )}

      <Table
        rowKey="id"
        columns={columns}
        dataSource={entries}
        loading={loading}
        pagination={{ pageSize: 10, showSizeChanger: false }}
        size="small"
        locale={{
          emptyText: <Empty description="No waitlisted patients" imageStyle={{ height: 40 }} />,
        }}
      />
    </Modal>
  );
}
