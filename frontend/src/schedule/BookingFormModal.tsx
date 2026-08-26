import { Alert, App, Button, Input, Modal, Select, Tag } from "antd";
import React, { useEffect, useState } from "react";
import { toErrorMessage } from "../common/errors";
import {
  bookAppointment,
  getResourceAvailability,
  getRisOrder,
  searchRisOrders,
  type ResourceAvailabilitySlot,
  type RisOrderProcedure,
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

const PRIORITY_COLOR: Record<string, string> = {
  STAT: "red",
  URGENT: "orange",
  ROUTINE: "blue",
};

/**
 * Booking form for the calendar grid (S4-15). A scheduler either picks an
 * existing RIS order (search by name/MRN/accession) or types a patient ID
 * directly for an order-less booking. Slot times from availability are UTC
 * wall-clock, so the ISO instants sent to the engine are built in UTC — never
 * browser-local — or the engine rejects them as outside availability.
 *
 * C4: multi-procedure orders expose a procedure picker (the choice is
 * recorded as the booking reason so technologists know what to perform);
 * the order's priority shows beside the slot; and a prior-authorization
 * conflict surfaces an audited override path (R2-01-05/R2-01-06) instead of
 * a dead-end toast.
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
  const [procedures, setProcedures] = useState<RisOrderProcedure[]>([]);
  const [procedureId, setProcedureId] = useState<string>("");
  const [patientId, setPatientId] = useState("");
  const [reason, setReason] = useState("");
  const [conflictMessage, setConflictMessage] = useState("");
  const [overrideReason, setOverrideReason] = useState("");
  const [submitting, setSubmitting] = useState(false);
  // S-10: the order detail already carries the auth state — surface it
  // BEFORE confirm instead of letting the engine's 409 be the first notice.
  const [priorAuthStatus, setPriorAuthStatus] = useState<string>("");
  // S-02: a slot conflict keeps this modal open and offers the next free
  // slot — losing the whole order/patient context over a race is worse
  // than a one-click move to the alternative.
  const [slotConflictMsg, setSlotConflictMsg] = useState("");
  const [slotAlt, setSlotAlt] = useState<ResourceAvailabilitySlot | null>(null);

  // Reset transient form state whenever the modal is (re)opened for a slot.
  useEffect(() => {
    if (open) {
      setPickedOrder(null);
      setOrderResults([]);
      setPatientId("");
      setReason("");
      setProcedures([]);
      setProcedureId("");
      setConflictMessage("");
      setOverrideReason("");
      setSlotConflictMsg("");
      setSlotAlt(null);
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

  const pickOrder = async (o: RisOrderRow) => {
    setPickedOrder(o);
    setPatientId(o.patient_id);
    setProcedures([]);
    setProcedureId("");
    try {
      const detail = await getRisOrder(o.id);
      const procs = detail.procedures ?? [];
      setPriorAuthStatus(detail.order?.prior_auth_status || "");
      setProcedures(procs);
      if (procs.length > 0) {
        const first = procs[0];
        setProcedureId(first.id ?? "");
        // The chosen procedure becomes the visible booking reason — the
        // engine has no procedure input, so this is how the selection is
        // recorded for the technologist.
        setReason(`Procedure: ${first.procedure_name || first.procedure_code || ""}`);
      }
    } catch (e: unknown) {
      // Detail fetch is enhancement-only — booking proceeds without it.
      message.warning(toErrorMessage(e) || "Could not load order procedures");
    }
  };

  const submitBooking = async (override = false, target?: ResourceAvailabilitySlot) => {
    const s = target ?? slot;
    if (!resource || !s) return;
    if (!pickedOrder && !patientId.trim()) {
      message.error("Select an order or enter a patient ID");
      return;
    }
    if (override && !overrideReason.trim()) {
      message.error("An override reason is required");
      return;
    }
    setSubmitting(true);
    try {
      const startISO = slotToIso(day, s.start);
      const endISO = slotToIso(day, s.end);
      await bookAppointment({
        order_id: pickedOrder?.id ?? "",
        resource_id: resource.id,
        patient_id: pickedOrder?.patient_id ?? patientId.trim(),
        start_time: startISO,
        end_time: endISO,
        reason,
        ...(override ? { override_reason: overrideReason.trim() } : {}),
      });
      message.success("Appointment booked");
      setSlotConflictMsg("");
      setSlotAlt(null);
      onDone();
    } catch (e: unknown) {
      const err = e as { status?: number; message?: string; code?: string };
      if (err.status === 409 && /requires prior authorization/i.test(err.message || "")) {
        // R2-01-06: keep the form open and offer the audited override —
        // a plain toast loses the whole booking context.
        setConflictMessage(err.message || "Prior authorization required");
      } else if (err.status === 409 || err.code === "SLOT_CONFLICT") {
        // S-02: stay in context — find the next free slot after the failed
        // attempt and offer it inline; the parent refreshes the grid behind.
        const msg = err.message || "Slot just taken";
        setSlotConflictMsg(msg);
        setSlotAlt(null);
        try {
          const slots = await getResourceAvailability(resource.id, day);
          setSlotAlt(slots.find((cand) => cand.start > s.start) ?? null);
        } catch {
          /* suggestion is best-effort — the message alone still explains */
        }
        onConflict?.(msg);
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
    setProcedures([]);
    setProcedureId("");
    setConflictMessage("");
    setOverrideReason("");
    setPriorAuthStatus("");
  };

  // S-10: auth states that will block (or should stop) a booking. The
  // engine's reactive 409 stays as the backstop; this is the heads-up.
  const AUTH_BLOCKING = new Set(["REQUIRED", "PENDING", "DENIED", "EXPIRED"]);
  const authWarning =
    pickedOrder && AUTH_BLOCKING.has(priorAuthStatus)
      ? {
          tone: (priorAuthStatus === "DENIED" || priorAuthStatus === "EXPIRED"
            ? "error"
            : "warning") as "error" | "warning",
          text:
            priorAuthStatus === "DENIED"
              ? "Prior authorization was DENIED — booking requires an audited override."
              : priorAuthStatus === "EXPIRED"
                ? "Prior authorization has EXPIRED — booking requires an audited override."
                : `Prior authorization is ${priorAuthStatus} — the engine will block this booking until it is approved, or you provide an override.`,
        }
      : null;

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
            {resource?.name} · {slot?.start}–{slot?.end}
          </span>
          <Button
            type="primary"
            loading={submitting}
            disabled={!pickedOrder && !patientId.trim()}
            onClick={() => submitBooking(false)}
          >
            Confirm Booking
          </Button>
        </div>
      }
    >
      {pickedOrder && (
        <div style={{ marginBottom: 8 }} data-testid="booking-order-summary">
          <Tag>{pickedOrder.accession_number}</Tag>
          <Tag color={PRIORITY_COLOR[pickedOrder.priority] ?? "default"}>
            {pickedOrder.priority}
          </Tag>
        </div>
      )}
      {authWarning && (
        <Alert
          type={authWarning.tone}
          showIcon
          data-testid="prior-auth-warning"
          message="Prior authorization check"
          description={authWarning.text}
          style={{ marginBottom: 12 }}
        />
      )}
      <div style={{ marginBottom: 16 }} className="sched-form-section">
        <div className="sched-form-section-title">Search order or enter patient</div>
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
        {procedures.length > 1 && (
          <Select
            aria-label="Procedure"
            placeholder="Choose procedure"
            value={procedureId || undefined}
            onChange={(id) => {
              setProcedureId(id);
              const proc = procedures.find((p) => p.id === id);
              if (proc) {
                setReason(`Procedure: ${proc.procedure_name || proc.procedure_code || ""}`);
              }
            }}
            style={{ marginTop: 8, width: "100%" }}
            options={procedures.map((p) => ({
              value: p.id ?? "",
              label: p.procedure_name || p.procedure_code || `Procedure ${p.id ?? ""}`,
            }))}
          />
        )}
        <Input
          aria-label="Reason"
          placeholder="Reason (optional)"
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          style={{ marginTop: 8 }}
        />
        {conflictMessage && (
          <Alert
            type="warning"
            showIcon
            style={{ marginTop: 12 }}
            message="Booking blocked by prior authorization"
            description={
              <>
                <div style={{ marginBottom: 8 }}>{conflictMessage}</div>
                <Input
                  aria-label="Override reason"
                  placeholder="Override reason (required, audited)"
                  value={overrideReason}
                  onChange={(e) => setOverrideReason(e.target.value)}
                />
                <Button
                  danger
                  style={{ marginTop: 8 }}
                  loading={submitting}
                  onClick={() => submitBooking(true)}
                >
                  Book with override
                </Button>
              </>
            }
          />
        )}
        {/* S-02: slot-conflict resolution — the failed attempt stays visible
            with a one-click alternative instead of a dead-end toast. */}
        {slotConflictMsg && (
          <Alert
            type="warning"
            showIcon
            data-testid="slot-conflict-alert"
            style={{ marginTop: 12 }}
            message="Booking blocked by a scheduling conflict"
            description={
              <>
                <div style={{ marginBottom: 8 }}>
                  {slotConflictMsg}
                  {!slotAlt && " — no later free slot this day on this resource."}
                </div>
                {slotAlt && (
                  <>
                    <div style={{ marginBottom: 8 }}>
                      Next free on {resource?.name}: {slotAlt.start}–{slotAlt.end}
                    </div>
                    <Button
                      type="primary"
                      danger
                      loading={submitting}
                      onClick={() => void submitBooking(false, slotAlt)}
                    >
                      Book {slotAlt.start} instead
                    </Button>
                  </>
                )}
              </>
            }
          />
        )}
      </div>
    </Modal>
  );
}
