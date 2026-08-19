import { App, Input, Modal } from "antd";
import React, { useEffect, useState } from "react";
import { toErrorMessage } from "../common/errors";
import {
  cancelRisAppointment,
  type RisAppointment,
} from "../api/scheduling";
import { dayjs } from "./time";
import "./schedule.css";

export interface CancelModalProps {
  open: boolean;
  appointment: RisAppointment | null;
  onClose: () => void;
  onDone: () => void;
}

/**
 * Cancel modal — requires a reason for the audit trail. The confirm button
 * stays disabled until one is typed; the backend enforces the same via
 * CancelRequest.reason min_length.
 */
export default function CancelModal({
  open,
  appointment,
  onClose,
  onDone,
}: CancelModalProps) {
  const { message } = App.useApp();
  const [reason, setReason] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (open) setReason("");
  }, [open, appointment?.id]);

  const doCancel = async () => {
    if (!appointment) return;
    const trimmed = reason.trim();
    if (!trimmed) {
      message.error("A reason is required to cancel");
      return;
    }
    setSubmitting(true);
    try {
      await cancelRisAppointment(appointment.id, trimmed);
      message.success("Appointment cancelled");
      onDone();
    } catch (e: unknown) {
      message.error(toErrorMessage(e) || "Cancel failed");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Modal
      title="Cancel Appointment"
      open={open}
      onCancel={() => {
        setReason("");
        onClose();
      }}
      onOk={doCancel}
      confirmLoading={submitting}
      okButtonProps={{ danger: true, disabled: !reason.trim() }}
      okText="Cancel Appointment"
    >
      {appointment && (
        <div>
          <div className="sched-order-meta" style={{ marginBottom: 12 }}>
            {appointment.patient_id} · {dayjs.utc(appointment.start_time).format("HH:mm")}–
            {dayjs.utc(appointment.end_time).format("HH:mm")}
          </div>
          <Input
            placeholder="Reason (required for audit)"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
          />
        </div>
      )}
    </Modal>
  );
}