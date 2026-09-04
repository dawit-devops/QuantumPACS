import { App, Button, Input, Modal } from "antd";
import React, { useEffect, useState } from "react";
import { toErrorMessage } from "../common/errors";
import {
  rescheduleAppointment,
  type ResourceAvailabilitySlot,
  type RisAppointment,
} from "../api/scheduling";
import { dayjs, slotToIso } from "./time";
import "./schedule.css";

export interface RescheduleModalProps {
  open: boolean;
  appointment: RisAppointment | null;
  slots: ResourceAvailabilitySlot[];
  day: string;
  onClose: () => void;
  onDone: () => void;
  /** Conflict (409) from the engine — availability may have changed. */
  onConflict?: (message: string) => void;
}

/**
 * Reschedule modal (S4-17) — pick a new free slot for an existing
 * appointment. Slot labels are UTC wall-clock; the new start/end instants are
 * built in UTC to match the engine's window checks.
 */
export default function RescheduleModal({
  open,
  appointment,
  slots,
  day,
  onClose,
  onDone,
  onConflict,
}: RescheduleModalProps) {
  const { message } = App.useApp();
  const [newSlot, setNewSlot] = useState<ResourceAvailabilitySlot | null>(null);
  const [reason, setReason] = useState("");
  const [submitting, setSubmitting] = useState(false);

  // S11: Only reset on open / appointment change — NOT on `slots` identity.
  // The parent builds `slots` inline in JSX (new array every render), so
  // including it in deps would wipe the user's typed reason and slot
  // selection on every parent re-render (tenant refetch, fetch completion).
  useEffect(() => {
    if (open) {
      setNewSlot(slots[0] ?? null);
      setReason("");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, appointment?.id]);

  const doReschedule = async () => {
    if (!appointment || !newSlot) return;
    setSubmitting(true);
    try {
      const startISO = slotToIso(day, newSlot.start);
      const endISO = slotToIso(day, newSlot.end);
      await rescheduleAppointment(appointment.id, {
        new_start_time: startISO,
        new_end_time: endISO,
        reason,
      });
      message.success("Appointment rescheduled");
      onDone();
    } catch (e: unknown) {
      const conflict = e as { status?: number; message?: string };
      if (conflict.status === 409 || (conflict as { code?: string }).code === "SLOT_CONFLICT") {
        onConflict?.(conflict.message || "Slot just taken — availability refreshed");
        setNewSlot(null);
        onClose();
      } else {
        message.error(toErrorMessage(e) || "Reschedule failed");
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Modal
      title="Reschedule Appointment"
      open={open}
      onCancel={() => {
        setNewSlot(null);
        onClose();
      }}
      onOk={doReschedule}
      confirmLoading={submitting}
      okText="Reschedule"
    >
      {appointment && (
        <>
          <div className="sched-order-meta" style={{ marginBottom: 12 }}>
            {appointment.patient_id} · {dayjs.utc(appointment.start_time).format("HH:mm")}–
            {dayjs.utc(appointment.end_time).format("HH:mm")}
          </div>
          <div className="sched-form-section-title">New slot</div>
          <div className="sched-slot-options">
            {slots.map((s) => (
              <Button
                key={s.start}
                className="sched-slot-option"
                type={newSlot?.start === s.start ? "primary" : "default"}
                onClick={() => setNewSlot(s)}
              >
                {s.start}
              </Button>
            ))}
          </div>
          <Input
            placeholder="Reason (optional)"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            style={{ marginTop: 12 }}
          />
        </>
      )}
    </Modal>
  );
}