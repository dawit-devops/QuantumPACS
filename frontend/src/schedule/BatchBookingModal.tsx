import { Alert, App, Button, Checkbox, Empty, Input, Modal, Select, Spin, Tag } from "antd";
import React, { useEffect, useState } from "react";
import { toErrorMessage } from "../common/errors";
import {
  batchBookAppointments,
  getResourceAvailability,
  getRisOrder,
  searchRisOrders,
  type ResourceAvailabilitySlot,
  type RisOrderRow,
  type RisResource,
} from "../api/scheduling";
import { slotToIso } from "./time";
import "./schedule.css";

export interface BatchBookingModalProps {
  open: boolean;
  day: string;
  resources: RisResource[];
  onClose: () => void;
  onDone: () => void;
}

/**
 * S-06: batch booking — pick a resource, a patient (order search or raw
 * patient ID), then select several of the resource's free slots and book
 * them in one call. The backend books each item independently and reports
 * per-item success so the summary can say "3 of 5 booked".
 */
export default function BatchBookingModal({
  open,
  day,
  resources,
  onClose,
  onDone,
}: BatchBookingModalProps) {
  const { message } = App.useApp();
  const [resourceId, setResourceId] = useState<string>("");
  const [orderSearch, setOrderSearch] = useState("");
  const [orderResults, setOrderResults] = useState<RisOrderRow[]>([]);
  const [pickedOrder, setPickedOrder] = useState<RisOrderRow | null>(null);
  const [patientId, setPatientId] = useState("");
  const [reason, setReason] = useState("");
  const [slots, setSlots] = useState<ResourceAvailabilitySlot[]>([]);
  const [slotsLoading, setSlotsLoading] = useState(false);
  const [selected, setSelected] = useState<string[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<string | null>(null);

  const resource = resources.find((r) => r.id === resourceId) ?? null;

  useEffect(() => {
    if (!open) return;
    setResourceId("");
    setOrderResults([]);
    setPickedOrder(null);
    setPatientId("");
    setReason("");
    setSlots([]);
    setSelected([]);
    setResult(null);
  }, [open]);

  // Load the resource's free slots whenever the resource changes.
  useEffect(() => {
    if (!open || !resourceId) {
      setSlots([]);
      return;
    }
    let cancelled = false;
    setSlotsLoading(true);
    getResourceAvailability(resourceId, day)
      .then((rows) => {
        if (!cancelled) setSlots(rows);
      })
      .catch((e: unknown) => {
        if (!cancelled) message.warning(toErrorMessage(e) || "Could not load availability");
      })
      .finally(() => {
        if (!cancelled) setSlotsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [open, resourceId, day, message]);

  const runOrderSearch = async () => {
    const term = orderSearch.trim();
    if (term.length < 2) return;
    try {
      const page = await searchRisOrders({ search: term, per_page: 20 });
      setOrderResults(page.data);
    } catch (e: unknown) {
      message.error(toErrorMessage(e) || "Order search failed");
    }
  };

  const pickOrder = async (o: RisOrderRow) => {
    setPickedOrder(o);
    setPatientId(o.patient_id);
    try {
      const detail = await getRisOrder(o.id);
      const procs = detail.procedures ?? [];
      if (procs.length > 0) {
        const first = procs[0];
        setReason(`Procedure: ${first.procedure_name || first.procedure_code || ""}`);
      }
    } catch {
      /* enhancement-only — booking proceeds without procedures */
    }
  };

  const confirm = async () => {
    if (!resource) return;
    if (!pickedOrder && !patientId.trim()) {
      message.error("Select an order or enter a patient ID");
      return;
    }
    const chosen = slots.filter((s) => selected.includes(s.start));
    if (chosen.length === 0) {
      message.error("Select at least one slot");
      return;
    }
    setSubmitting(true);
    setResult(null);
    try {
      const res = await batchBookAppointments(
        chosen.map((s) => ({
          order_id: pickedOrder?.id ?? "",
          resource_id: resource.id,
          patient_id: pickedOrder?.patient_id ?? patientId.trim(),
          start_time: slotToIso(day, s.start),
          end_time: slotToIso(day, s.end),
          reason,
        }))
      );
      const booked = res.results.filter((r) => r.success).length;
      const failed = res.results.length - booked;
      setResult(
        failed === 0
          ? `Booked ${booked} appointment${booked === 1 ? "" : "s"}.`
          : `Booked ${booked} of ${res.results.length}; ${failed} failed.`
      );
      if (failed === 0) onDone();
    } catch (e: unknown) {
      message.error(toErrorMessage(e) || "Batch booking failed");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Modal
      title="Batch Book"
      open={open}
      onCancel={onClose}
      width={640}
      footer={
        <div style={{ display: "flex", justifyContent: "space-between" }}>
          <span style={{ color: "var(--text-secondary)" }}>
            {selected.length > 0
              ? `${selected.length} slot${selected.length === 1 ? "" : "s"} selected`
              : "Select slots to book"}
          </span>
          <Button
            type="primary"
            loading={submitting}
            disabled={!resource || (!pickedOrder && !patientId.trim()) || selected.length === 0}
            onClick={() => void confirm()}
          >
            Book {selected.length || ""} Appointment{selected.length === 1 ? "" : "s"}
          </Button>
        </div>
      }
    >
      <div className="sched-form-section">
        <div className="sched-form-section-title">1. Resource</div>
        <Select
          aria-label="Resource"
          placeholder="Choose a resource"
          style={{ width: "100%" }}
          value={resourceId || undefined}
          onChange={setResourceId}
          options={resources.map((r) => ({
            value: r.id,
            label: `${r.name} (${r.resource_type}${r.modality ? ` · ${r.modality}` : ""})`,
          }))}
        />
      </div>

      <div className="sched-form-section">
        <div className="sched-form-section-title">2. Patient</div>
        <Input.Search
          aria-label="Search order"
          placeholder="Search order (name, MRN or accession)"
          value={orderSearch}
          onChange={(e) => setOrderSearch(e.target.value)}
          onSearch={() => void runOrderSearch()}
          enterButton
          style={{ marginBottom: 8 }}
        />
        {orderResults.map((o) => (
          <div
            key={o.id}
            className={`sched-order-result ${pickedOrder?.id === o.id ? "is-selected" : ""}`}
            onClick={() => void pickOrder(o)}
            role="button"
            tabIndex={0}
            aria-label={`Select order ${o.patient_name || o.patient_id}`}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                void pickOrder(o);
              }
            }}
          >
            <div>
              <b>{o.patient_name || o.patient_id}</b>
              <div className="sched-order-meta">
                {o.accession_number} · {o.patient_id}
              </div>
            </div>
            <Tag>{o.status}</Tag>
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
          placeholder="Reason (optional, applied to all)"
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          style={{ marginTop: 8 }}
        />
      </div>

      <div className="sched-form-section">
        <div className="sched-form-section-title">
          3. Slots on {day} — {resource?.name ?? "choose a resource"}
        </div>
        {slotsLoading ? (
          <div style={{ padding: 20, textAlign: "center" }}>
            <Spin />
          </div>
        ) : slots.length === 0 ? (
          <Empty description="No free slots for this resource today" imageStyle={{ height: 40 }} />
        ) : (
          <div className="sched-batch-slots">
            {slots.map((s) => (
              <Checkbox
                key={s.start}
                aria-label={`Slot ${s.start}`}
                checked={selected.includes(s.start)}
                onChange={(e) =>
                  setSelected((prev) =>
                    e.target.checked ? [...prev, s.start] : prev.filter((x) => x !== s.start)
                  )
                }
              >
                {s.start}–{s.end}
              </Checkbox>
            ))}
          </div>
        )}
      </div>

      {result && (
        <Alert
          type={result.includes("failed") ? "warning" : "success"}
          showIcon
          style={{ marginTop: 12 }}
          message={result}
          data-testid="batch-result"
        />
      )}
    </Modal>
  );
}
