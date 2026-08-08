import React, { useCallback, useEffect, useMemo, useState } from "react";
import { App, Modal, DatePicker, Select, Button, Spin, Tag, Alert, Input } from "antd";
import { CalendarOutlined, CheckCircleOutlined } from "@ant-design/icons";
import dayjs from "dayjs";
import {
  getAvailability,
  createAppointment,
  searchPatients,
  type AvailabilitySlot,
  type FrontDeskPatient,
} from "../api/frontdesk";
import "./FrontDesk.css";

const MODALITIES = [
  "CT",
  "MR",
  "PET",
  "DX",
  "US",
  "MG",
  "FL",
  "XA",
  "NM",
];

interface AppointmentBookingProps {
  open: boolean;
  onClose: () => void;
  onBooked?: () => void;
  // Preselected patient (registration flow). When empty, the modal shows a
  // patient search step first (scheduler flow on the schedule board).
  patientId?: string;
  patientName?: string;
}

/**
 * Capacity-aware appointment booking (US-R08-04). Loads the backend slot
 * availability for the chosen modality/date (each slot carries capacity and
 * booked counts), renders a keyboard-navigable slot grid with full slots
 * disabled, and confirms the booking in a single POST that the backend
 * re-checks inside a transaction — a 409 SLOT_CONFLICT surfaces the
 * refreshed availability instead of double-booking.
 */
function AppointmentBooking({
  open,
  onClose,
  onBooked,
  patientId,
  patientName,
}: AppointmentBookingProps) {
  const { message } = App.useApp();
  const [modality, setModality] = useState<string>("CT");
  const [date, setDate] = useState<dayjs.Dayjs>(() => dayjs());
  const [slots, setSlots] = useState<AvailabilitySlot[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [conflict, setConflict] = useState<string | null>(null);

  // Patient search step — used when no patient is preselected (board flow).
  const [patientQuery, setPatientQuery] = useState("");
  const [patientResults, setPatientResults] = useState<FrontDeskPatient[]>([]);
  const [patientSearching, setPatientSearching] = useState(false);
  const [pickedPatient, setPickedPatient] = useState<FrontDeskPatient | null>(
    null,
  );

  const effectivePatientId = patientId || pickedPatient?.patient_id || "";
  const effectivePatientName =
    patientName || pickedPatient?.name || "New patient";

  const runPatientSearch = async () => {
    const term = patientQuery.trim();
    if (term.length < 2) return;
    setPatientSearching(true);
    try {
      setPatientResults(await searchPatients(term));
    } catch (e: any) {
      message.error(e.message || "Patient search failed");
    } finally {
      setPatientSearching(false);
    }
  };

  const fetchAvailability = useCallback(
    (mod: string, d: dayjs.Dayjs) => {
      setLoading(true);
      setError(null);
      setSelected(null);
      // Conflict state is NOT reset here: the conflict handler re-fetches
      // availability to show the refreshed grid and the conflict banner side
      // by side. Only a fresh open/modality/date change clears it.
      getAvailability({
        modality: mod,
        date: d.format("YYYY-MM-DD"),
      })
        .then((rows) => {
          setLoading(false);
          setSlots(rows);
        })
        .catch((e: any) => {
          setLoading(false);
          setError(e.message || "Failed to load availability");
        });
    },
    [],
  );

  useEffect(() => {
    if (open) {
      setConflict(null);
      fetchAvailability(modality, date);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, modality, date]);

  const freeSlots = useMemo(() => slots.filter((s) => s.state !== "full"), [
    slots,
  ]);

  const confirm = async () => {
    if (!selected || !effectivePatientId) return;
    setSubmitting(true);
    setConflict(null);
    try {
      await createAppointment({
        patient_id: effectivePatientId,
        modality,
        scheduled_date: date.format("YYYY-MM-DD"),
        scheduled_time: `${selected}:00`,
      });
      message.success("Appointment booked — added to the modality worklist");
      setSelected(null);
      onBooked?.();
      onClose();
    } catch (e: any) {
      if (e.code === "SLOT_CONFLICT" || e.status === 409) {
        setConflict(e.message || "Slot was just taken — availability refreshed");
        // The slot may have filled under us: reload availability so the grid
        // reflects the conflict (US-R08-04 conflict path).
        fetchAvailability(modality, date);
      } else {
        message.error(e.message || "Booking failed");
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Modal
      title={
        <span>
          <CalendarOutlined style={{ marginRight: 8 }} />
          Book Appointment
        </span>
      }
      open={open}
      onCancel={onClose}
      width={640}
      footer={
        <div style={{ display: "flex", justifyContent: "space-between" }}>
          <span style={{ color: "var(--text-secondary)" }}>
            {freeSlots.length} free / {slots.length} slots
          </span>            <Button
              type="primary"
              icon={<CheckCircleOutlined />}
              onClick={confirm}
              loading={submitting}
              disabled={!selected || !effectivePatientId}
            >
            Confirm Booking
          </Button>
        </div>
      }
    >
      {!patientId && (
        <div style={{ marginBottom: 16 }}>
          {pickedPatient ? (
            <div className="fd-booking-patient">
              Patient: {pickedPatient.name} ({pickedPatient.patient_id})
              <Button
                size="small"
                type="link"
                onClick={() => {
                  setPickedPatient(null);
                  setPatientResults([]);
                }}
              >
                Change
              </Button>
            </div>
          ) : (
            <>
              <Input.Search
                placeholder="Search patient (name or MRN)"
                value={patientQuery}
                onChange={(e) => setPatientQuery(e.target.value)}
                onSearch={runPatientSearch}
                loading={patientSearching}
                enterButton
                style={{ marginBottom: 8 }}
              />
              {patientResults.map((p) => (
                <div key={p.id} className="fd-patient-result">
                  <div>
                    <b>{p.name}</b>
                    <div className="fd-patient-meta">
                      {p.patient_id} · DOB {p.birth_date || "—"}
                    </div>
                  </div>
                  <Button size="small" onClick={() => setPickedPatient(p)}>
                    Select
                  </Button>
                </div>
              ))}
            </>
          )}
        </div>
      )}

      {effectivePatientId && (
        <div className="fd-booking-patient">
          {effectivePatientName}
        </div>
      )}

      <div style={{ display: "flex", gap: 12, marginBottom: 16 }}>
        <Select
          value={modality}
          onChange={setModality}
          style={{ width: 120 }}
          aria-label="Modality"
          options={MODALITIES.map((m) => ({ value: m, label: m }))}
        />
        <DatePicker
          value={date}
          onChange={(d) => d && setDate(d)}
          style={{ width: 160 }}
          allowClear={false}
          disabledDate={(d) => d.isBefore(dayjs().startOf("day"))}
        />
      </div>

      {conflict && (
        <Alert
          type="warning"
          showIcon
          style={{ marginBottom: 12 }}
          message={conflict}
        />
      )}
      {error && (
        <Alert
          type="error"
          showIcon
          style={{ marginBottom: 12 }}
          message={error}
        />
      )}

      {loading ? (
        <div className="fd-loading">
          <Spin />
        </div>
      ) : slots.length === 0 ? (
        <Alert
          type="info"
          showIcon
          message="No availability returned for this modality/date."
        />
      ) : (
        <div
          className="fd-slot-grid"
          role="grid"
          aria-label={`Available slots for ${modality} on ${date.format("YYYY-MM-DD")}`}
        >
          {slots.map((slot) => {
            const full = slot.state === "full";
            const active = selected === slot.time;
            return (
              <button
                key={slot.time}
                type="button"
                role="gridcell"
                className={`fd-slot ${full ? "is-full" : ""} ${active ? "is-active" : ""}`}
                disabled={full}
                onClick={() => setSelected(slot.time)}
                aria-pressed={active}
                aria-label={`${slot.time}${full ? " (full)" : ""}`}
              >
                <span className="fd-slot-time">{slot.time}</span>
                <span className="fd-slot-meta">
                  {full ? (
                    <Tag color="red" style={{ margin: 0, fontSize: 10 }}>
                      Full
                    </Tag>
                  ) : (
                    <Tag color="green" style={{ margin: 0, fontSize: 10 }}>
                      {slot.booked}/{slot.capacity}
                    </Tag>
                  )}
                </span>
              </button>
            );
          })}
        </div>
      )}
    </Modal>
  );
}

export default AppointmentBooking;
