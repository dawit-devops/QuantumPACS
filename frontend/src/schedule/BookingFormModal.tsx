import { App, Button, Input, Modal, Tag } from "antd";
import React, { useEffect, useState } from "react";
import { toErrorMessage } from "../common/errors";
import {
  bookAppointment,
  searchRisOrders,
  type ResourceAvailabilitySlot,
  type RisOrderRow,
  type RisResource,
} from "../api/scheduling";
import { dayjs, slotToIso } from "./time";
import "./schedule.css";

export interface BookingFormModalProps {
  open: boolean;
  resource: RisResource | null;
  slot: ResourceAvailabilitySlot | null;
  day: string;
  onClose: () => void;
  onDone: () => void;
  /** Conflict (409) from the engine — availability may have changed. */
  onConflict?: (message: string) => void;
}

/**
 * Booking form for the calendar grid (S4-15). A scheduler either picks an
 * existing RIS order (search by name/MRN/accession) or types a patient ID
 * directly for an order-less booking. Slot times from availability are UTC
 * wall-clock, so the ISO instants sent to the engine are built in UTC — never
 * browser-local — or the engine rejects them as outside availability.
 */
export default function BookingFormModal({
  open,
  resource,
  slot,
  day,
  onClose,
  onDone,
  onConflict,
}: BookingFormModalProps) {
  const { message } = App.useApp();
  const [orderSearch, setOrderSearch] = useState("");
  const [orderResults, setOrderResults] = useState<RisOrderRow[]>([]);
  const [orderSearching, setOrderSearching] = useState(false);
  const [pickedOrder, setPickedOrder] = useState<RisOrderRow | null>(null);
  const [patientId, setPatientId] = useState("");
  const [reason, setReason] = useState("");
  const [submitting, setSubmitting] = useState(false);

  // Reset transient form state whenever the modal is (re)opened for a slot.
  useEffect(() => {
    if (open) {
      setPickedOrder(null);
      setOrderResults([]);
      setPatientId("");
      setReason("");
    }
  }, [open, resource?.id, slot?.start]);

  const runOrderSearch = async () => {
    const term = orderSearch.trim();
    if (term.length < 2) return;
    setOrderSearching(true);
    try {
      const page = await searchRisOrders({ search: term, per_page: 20 });
      setOrderResults(page.data);
    } catch (e: unknown) {
      message.error(toErrorMessage(e) || "Order search failed");
    } finally {
      setOrderSearching(false);
    }
  };

  const submitBooking = async () => {
    if (!resource || !slot) return;
    if (!pickedOrder && !patientId.trim()) {
      message.error("Select an order or enter a patient ID");
      return;
    }
    setSubmitting(true);
    try {
      const startISO = slotToIso(day, slot.start);
      const endISO = slotToIso(day, slot.end);
      await bookAppointment({
        order_id: pickedOrder?.id ?? "",
        resource_id: resource.id,
        patient_id: pickedOrder?.patient_id ?? patientId.trim(),
        start_time: startISO,
        end_time: endISO,
        reason,
      });
      message.success("Appointment booked");
      onDone();
    } catch (e: unknown) {
      const err = e as { status?: number; message?: string; code?: string };
      if (err.status === 409 || err.code === "SLOT_CONFLICT") {
        onConflict?.(err.message || "Slot just taken — availability refreshed");
        reset();
        onClose();
      } else {
        message.error(toErrorMessage(e) || "Booking failed");
      }
    } finally {
      setSubmitting(false);
    }
  };

  const reset = () => {
    setPickedOrder(null);
    setOrderResults([]);
    setPatientId("");
    setReason("");
  };

  return (
    <Modal
      title="Book Appointment"
      open={open}
      onCancel={() => {
        reset();
        onClose();
      }}
      width={560}
      footer={
        <div style={{ display: "flex", justifyContent: "space-between" }}>
          <span style={{ color: "var(--text-secondary)" }}>
            {resource?.name} · {slot?.start}–
            {slot?.end}
          </span>
          <Button
            type="primary"
            loading={submitting}
            disabled={!pickedOrder && !patientId.trim()}
            onClick={submitBooking}
          >
            Confirm Booking
          </Button>
        </div>
      }
    >
      <div style={{ marginBottom: 16 }} className="sched-form-section">
        <div className="sched-form-section-title">
          Search order or enter patient
        </div>
        <Input.Search
          aria-label="Search order"
          placeholder="Search order (name, MRN or accession)"
          value={orderSearch}
          onChange={(e) => setOrderSearch(e.target.value)}
          onSearch={runOrderSearch}
          loading={orderSearching}
          enterButton
          style={{ marginBottom: 8 }}
        />
        {orderResults.map((o) => (
          <div
            key={o.id}
            className={`sched-order-result ${pickedOrder?.id === o.id ? "is-selected" : ""}`}
            onClick={() => {
              setPickedOrder(o);
              setPatientId(o.patient_id);
            }}
            role="button"
            tabIndex={0}
            aria-label={`Select order ${o.patient_name || o.patient_id}`}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                setPickedOrder(o);
                setPatientId(o.patient_id);
              }
            }}
          >
            <div>
              <b>{o.patient_name || o.patient_id}</b>
              <div className="sched-order-meta">
                {o.accession_number} · {o.patient_id}
                {o.referring_physician ? ` · ${o.referring_physician}` : ""}
              </div>
            </div>
            <Tag color={o.status === "ORDERED" ? "blue" : "default"}>{o.status}</Tag>
          </div>
        ))}
        <Input
          aria-label="Patient ID"
          placeholder="Or patient ID directly (no order)"
          value={patientId}
          onChange={(e) => {
            setPatientId(e.target.value);
            setPickedOrder(null);
          }}
          style={{ marginTop: 8 }}
        />
        <Input
          aria-label="Reason"
          placeholder="Reason (optional)"
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          style={{ marginTop: 8 }}
        />
      </div>
    </Modal>
  );
}