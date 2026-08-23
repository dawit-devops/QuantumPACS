import { useDocumentTitle, useTenantRefetch } from "../hooks";
import React, { useCallback, useEffect, useState } from "react";
import {
  App,
  Layout,
  Card,
  Form,
  Input,
  Select,
  Button,
  Alert,
  Tag,
  Divider,
  Spin,
  Space,
  Checkbox,
} from "antd";
import {
  SearchOutlined,
  UserAddOutlined,
  CalendarOutlined,
  IdcardOutlined,
} from "@ant-design/icons";
import withSidebar from "../common/base";
import { useAuth } from "../auth/AuthContext";
import {
  searchPatients,
  createPatient,
  createVisit,
  type FrontDeskPatient,
} from "../api/frontdesk";
import AppointmentBooking from "./AppointmentBooking";
import "./FrontDesk.css";

const Content = Layout.Content;

// US-R08-01/02: search-first registration with a dedup banner before any
// new-patient record can be created, and inline-validated demographics.
function Registration() {
  const { message } = App.useApp();
  useDocumentTitle("QuantumPACS - Patient Registration");
  const { hasPermission } = useAuth();
  const canWrite = hasPermission("REGISTRATION_WRITE");
  const canSchedule = hasPermission("SCHEDULE_WRITE");

  const [query, setQuery] = useState("");
  const [results, setResults] = useState<FrontDeskPatient[]>([]);
  const [searching, setSearching] = useState(false);
  const [searched, setSearched] = useState(false);
  const [dedupSelected, setDedupSelected] = useState<FrontDeskPatient | null>(
    null,
  );
  const [saving, setSaving] = useState(false);
  const [bookFor, setBookFor] = useState<FrontDeskPatient | null>(null);
  const [form] = Form.useForm();

  const runSearch = useCallback((q: string) => {
    const term = q.trim();
    if (term.length < 2) {
      setResults([]);
      setSearched(false);
      return;
    }
    setSearching(true);
    searchPatients(term)
      .then((rows) => {
        setResults(rows);
        setSearched(true);
      })
      .catch((e: any) => {
        message.error(e.message || "Search failed");
      })
      .finally(() => setSearching(false));
  }, []);

  useTenantRefetch(() => {
    setQuery("");
    setResults([]);
    setSearched(false);
    setDedupSelected(null);
  });

  // R1-16: patient creation and visit opening are independent operations —
  // a failed visit must not leave the user retrying a registration that
  // already succeeded (that retry would duplicate the patient).
  const register = async () => {
    let values;
    try {
      values = await form.validateFields();
    } catch {
      return; // inline validation errors shown
    }
    setSaving(true);
    let patient: FrontDeskPatient;
    try {
      patient = await createPatient({
        patient_id: values.patient_id || undefined,
        name: values.name,
        birth_date: values.birth_date || undefined,
        sex: values.sex || undefined,
        phone: values.phone || undefined,
        email: values.email || undefined,
        // E1: consent captured at registration (R2-05-07) — the portal gate
        // keeps reports/orders hidden until this is granted.
        meta: { consent_results: Boolean(values.consent) },
      });
    } catch (e: any) {
      message.error(e.message || "Registration failed");
      setSaving(false);
      return;
    }
    try {
      // A registration always opens a visit: the visit seeds the three
      // baseline consents and feeds the waiting queue + technologist list.
      await createVisit({
        patient_id: patient.patient_id,
        destination_room: values.destination_room || "",
      });
      message.success(
        `Registered ${patient.name} and opened a visit (${patient.patient_id})`,
      );
      form.resetFields();
      setDedupSelected(null);
      setQuery("");
      setResults([]);
      setSearched(false);
    } catch (e: any) {
      // The patient exists server-side; keep the form values and surface the
      // existing record through the dedup path so the next action is "open a
      // visit" — not a duplicate registration.
      message.error(
        `${e.message || "Visit could not be opened"} — the patient was created; open a visit from the patient list instead.`,
      );
      setDedupSelected(patient);
    } finally {
      setSaving(false);
    }
  };

  const useExisting = (p: FrontDeskPatient) => {
    setDedupSelected(p);
    message.info(`Using existing patient ${p.name} (${p.patient_id}).`);
  };

  // A returning patient needs a visit too: dedup-selected records get a
  // direct "Open Visit" action here instead of forcing a trip to the Visits
  // screen (US-R08-05 check-in requires a registered visit).
  const [openingVisit, setOpeningVisit] = useState(false);
  const openVisitFor = async (p: FrontDeskPatient) => {
    setOpeningVisit(true);
    try {
      await createVisit({
        patient_id: p.patient_id,
        destination_room: "",
      });
      message.success(`Opened a new visit for ${p.name}`);
    } catch (e: any) {
      message.error(e.message || "Failed to open visit");
    } finally {
      setOpeningVisit(false);
    }
  };

  return (
    <Content style={{ padding: 24 }} role="main">
      <div className="fd-header">
        <div className="fd-header-title">
          <IdcardOutlined
            style={{ fontSize: 22, color: "var(--color-primary)" }}
          />
          <div>
            <h2>Patient Registration</h2>
            <span className="fd-subtitle">
              Search first to avoid duplicates — then register or book
            </span>
          </div>
        </div>
      </div>

      <Card size="small" style={{ marginBottom: 16 }}>
        <div className="fd-toolbar">
          <Input.Search
            className="fd-search"
            placeholder="Search name or MRN (min 2 chars)"
            allowClear
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onSearch={runSearch}
            loading={searching}
            enterButton={<SearchOutlined />}
            aria-label="Search existing patients"
          />
          {canWrite && (
            <Button
              type="primary"
              icon={<UserAddOutlined />}
              // Scrolls to the registration form below the search — the
              // form is the target of the primary registration action.
              // R1-12: no smooth scroll for reduced-motion users.
              onClick={() => {
                const el = document.getElementById("fd-registration-form");
                if (!el) return;
                el.scrollIntoView(
                  window.matchMedia("(prefers-reduced-motion: reduce)").matches
                    ? { block: "start" }
                    : { behavior: "smooth", block: "start" },
                );
              }}
            >
              Register New Patient
            </Button>
          )}
        </div>

        {!canWrite && (
          <Alert
            type="info"
            showIcon
            title="Read-only registration — you can search patients but not create records."
          />
        )}

        {searched && results.length === 0 && (
          <Alert
            type="warning"
            showIcon
            className="fd-dedup-banner"
            title="No existing patient matched — registering a new record is allowed."
          />
        )}

        {results.map((p) => (
          <div key={p.id} className="fd-patient-result">
            <div>
              <b>{p.name}</b>
              <div className="fd-patient-meta">
                MRN {p.patient_id} · DOB {p.birth_date || "—"} · {p.sex || "—"}
              </div>
            </div>
            {dedupSelected?.id === p.id ? (
              <Tag color="green">Selected</Tag>
            ) : (
              <Button size="small" onClick={() => useExisting(p)}>
                Use this patient
              </Button>
            )}
          </div>
        ))}
      </Card>

      {dedupSelected && (
        <Alert
          type="info"
          showIcon
          className="fd-dedup-banner"
          title={`Selected ${dedupSelected.name} (${dedupSelected.patient_id})`}
          action={
            <Space>
              {canWrite && (
                <Button
                  size="small"
                  onClick={() => openVisitFor(dedupSelected)}
                  loading={openingVisit}
                >
                  Open Visit
                </Button>
              )}
              {canSchedule && (
                <Button
                  size="small"
                  icon={<CalendarOutlined />}
                  onClick={() => setBookFor(dedupSelected)}
                >
                  Book Appointment
                </Button>
              )}
            </Space>
          }
        />
      )}

      <Divider />

      <Card
        title="New Patient Registration"
        size="small"
        id="fd-registration-form"
        extra={
          dedupSelected ? (
            <Tag color="orange">
              Duplicate check: use the existing record above
            </Tag>
          ) : undefined
        }
      >
        <Form form={form} layout="vertical" style={{ maxWidth: 640 }}>
          <div style={{ display: "flex", gap: 12 }}>
            <Form.Item
              name="name"
              label="Full name"
              style={{ flex: 2 }}
              rules={[{ required: true, message: "Name is required" }]}
            >
              <Input placeholder="e.g. Jane Doe" />
            </Form.Item>
            <Form.Item
              name="patient_id"
              label="MRN / Patient ID (optional)"
              style={{ flex: 1 }}
              rules={[
                {
                  pattern: /^[A-Za-z0-9-]+$/,
                  message: "Letters, digits and dashes only",
                },
              ]}
            >
              <Input placeholder="Auto-generated if empty" />
            </Form.Item>
          </div>
          <div style={{ display: "flex", gap: 12 }}>
            <Form.Item
              name="birth_date"
              label="Date of birth"
              style={{ flex: 1 }}
              rules={[
                {
                  pattern: /^\d{4}-\d{2}-\d{2}$/,
                  message: "YYYY-MM-DD",
                },
              ]}
            >
              <Input placeholder="YYYY-MM-DD" />
            </Form.Item>
            <Form.Item name="sex" label="Sex" style={{ flex: 1 }}>
              <Select
                allowClear
                placeholder="Select"
                options={[
                  { value: "M", label: "Male" },
                  { value: "F", label: "Female" },
                  { value: "O", label: "Other" },
                ]}
              />
            </Form.Item>
            <Form.Item
              name="phone"
              label="Phone"
              style={{ flex: 1 }}
            >
              <Input placeholder="(555) 123-4567" />
            </Form.Item>
            <Form.Item
              name="email"
              label="Email"
              style={{ flex: 1 }}
            >
              <Input placeholder="patient@example.com" />
            </Form.Item>
            <Form.Item
              name="destination_room"
              label="Destination room (optional)"
              style={{ flex: 1 }}
            >
              <Input placeholder="e.g. CT Room 1" />
            </Form.Item>
          </div>
          <Form.Item
            name="consent"
            valuePropName="checked"
            style={{ marginBottom: 8 }}
          >
            <Checkbox disabled={!canWrite}>
              Patient consents to results being shared via the portal
            </Checkbox>
          </Form.Item>
          <Form.Item style={{ marginBottom: 0 }}>
            <Button
              type="primary"
              icon={<UserAddOutlined />}
              onClick={register}
              loading={saving}
              disabled={!canWrite}
            >
              Register & Open Visit
            </Button>
            {saving && (
              <span style={{ marginLeft: 12 }}>
                <Spin size="small" /> Saving…
              </span>
            )}
          </Form.Item>
        </Form>
      </Card>

      <AppointmentBooking
        open={!!bookFor}
        onClose={() => setBookFor(null)}
        patientId={bookFor?.patient_id || ""}
        patientName={bookFor?.name}
      />
    </Content>
  );
}

export default withSidebar(Registration);
