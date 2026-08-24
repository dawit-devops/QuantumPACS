import { useDocumentTitle, useTenantRefetch } from "../hooks";
import React, {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import {
  App,
  Layout,
  Table,
  Button,
  Tag,
  Drawer,
  Descriptions,
  Form,
  Input,
  Select,
  Popconfirm,
  Spin,
  Alert,
  Timeline,
  Divider,
} from "antd";
import {
  CheckCircleOutlined,
  FileDoneOutlined,
  MedicineBoxOutlined,
  SafetyCertificateOutlined,
  InsuranceOutlined,
  ClockCircleOutlined,
} from "@ant-design/icons";
import withSidebar from "../common/base";
import { useAuth } from "../auth/AuthContext";
import {
  listVisits,
  getVisit,
  checkInVisit,
  updateVisit,
  listOrders,
  createOrder,
  listConsents,
  attachConsent,
  listInsurance,
  createInsurance,
  getInsuranceEligibility,
  type Visit,
  type VisitOrder,
  type ConsentDocument,
  type InsuranceRecord,
  type InsuranceEligibility,
} from "../api/frontdesk";
import "./FrontDesk.css";

const Content = Layout.Content;

const VISIT_STATUS_COLORS: Record<string, string> = {
  registered: "blue",
  checked_in: "gold",
  in_progress: "cyan",
  complete: "green",
};

const CONSENT_TYPES = [
  { value: "general_consent", label: "General Consent" },
  { value: "privacy_notice", label: "Privacy Notice" },
  { value: "procedure_consent", label: "Procedure Consent" },
];

const STATUS_CHIPS = ["registered", "checked_in", "in_progress", "complete"];

function Visits() {
  const { message } = App.useApp();
  useDocumentTitle("QuantumPACS - Visits & Check-In");
  const { hasPermission } = useAuth();
  const canWrite = hasPermission("REGISTRATION_WRITE");

  const [data, setData] = useState<Visit[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [pagination, setPagination] = useState({
    current: 1,
    pageSize: 20,
    total: 0,
  });

  const [selectedVisit, setSelectedVisit] = useState<Visit | null>(null);
  const [visitDetail, setVisitDetail] = useState<Visit | null>(null);
  const [orders, setOrders] = useState<VisitOrder[]>([]);
  const [consents, setConsents] = useState<ConsentDocument[]>([]);
  const [insurance, setInsurance] = useState<InsuranceRecord[]>([]);
  const [eligibility, setEligibility] = useState<InsuranceEligibility | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const [orderForm] = Form.useForm();
  const [consentForm] = Form.useForm();
  const [insuranceForm] = Form.useForm();
  const [saving, setSaving] = useState(false);

  // R4: seq guard for the list fetch — rapid filter/pagination changes must
  // not let an earlier slow response overwrite a newer one.
  const listSeq = useRef(0);
  const fetch = useCallback(
    (page = 1, pageSize?: number) => {
      const seq = ++listSeq.current;
      setLoading(true);
      setError(null);
      const query: Record<string, string> = {
        page: String(page),
        // S14: accept pageSize as a parameter to avoid stale closure —
        // setPagination hasn't applied yet when onChange calls fetch.
        per_page: String(pageSize ?? pagination.pageSize),
      };
      if (statusFilter) query.status = statusFilter;
      listVisits(query)
        .then((res) => {
          if (seq !== listSeq.current) return;
          setLoading(false);
          setData(res.data);
          setPagination({
            current: res.page || page,
            pageSize: res.per_page || 20,
            total: res.total || res.data.length,
          });
        })
        .catch((e: any) => {
          if (seq !== listSeq.current) return;
          setLoading(false);
          setError(e.message);
        });
    },
    [statusFilter, pagination.pageSize],
  );

  useEffect(() => {
    fetch(1);
  }, [fetch]);

  useTenantRefetch(() => {
    setStatusFilter("");
    fetch(1);
  });

  // R1-05: guard out-of-order resolution — a slow response from an earlier
  // click must never paint another patient's detail under the latest
  // selection. Only the newest loadDetail call may write state.
  const detailSeq = useRef(0);
  const loadDetail = useCallback((visit: Visit) => {
    const seq = ++detailSeq.current;
    setSelectedVisit(visit);
    setDetailLoading(true);
    setVisitDetail(null);
    setOrders([]);
    setConsents([]);
    setInsurance([]);
    setEligibility(null);
    Promise.all([
      getVisit(visit.id),
      listOrders(visit.id),
      listConsents(visit.id),
      listInsurance(visit.patient_id),
      getInsuranceEligibility(visit.patient_id),
    ])
      .then(([v, o, c, i, e]) => {
        if (seq !== detailSeq.current) return;
        setVisitDetail(v);
        setOrders(o);
        setConsents(c);
        setInsurance(i);
        setEligibility(e);
      })
      .catch((e: any) => {
        if (seq === detailSeq.current) {
          message.error(e.message || "Failed to load visit");
        }
      })
      .finally(() => {
        if (seq === detailSeq.current) setDetailLoading(false);
      });
  }, []);

  const doCheckIn = async (visit: Visit) => {
    try {
      await checkInVisit(visit.id);
      message.success(`${visit.patient_id} checked in`);
      fetch(pagination.current);
      if (selectedVisit?.id === visit.id) {
        loadDetail(visit);
      }
    } catch (e: any) {
      message.error(e.message || "Check-in failed");
    }
  };

  const submitOrder = async () => {
    let values;
    try {
      values = await orderForm.validateFields();
    } catch {
      return;
    }
    if (!selectedVisit) return;
    setSaving(true);
    try {
      await createOrder(selectedVisit.id, values);
      message.success("Order captured");
      orderForm.resetFields();
      setOrders(await listOrders(selectedVisit.id));
    } catch (e: any) {
      message.error(e.message || "Order failed");
    } finally {
      setSaving(false);
    }
  };

  const submitConsent = async () => {
    let values;
    try {
      values = await consentForm.validateFields();
    } catch {
      return;
    }
    if (!selectedVisit) return;
    setSaving(true);
    try {
      await attachConsent(selectedVisit.id, values);
      message.success("Consent attached");
      consentForm.resetFields();
      setConsents(await listConsents(selectedVisit.id));
    } catch (e: any) {
      message.error(e.message || "Consent attach failed");
    } finally {
      setSaving(false);
    }
  };

  const submitInsurance = async () => {
    let values;
    try {
      values = await insuranceForm.validateFields();
    } catch {
      return;
    }
    if (!selectedVisit) return;
    setSaving(true);
    try {
      await createInsurance(selectedVisit.patient_id, values);
      message.success("Insurance/guarantor recorded");
      insuranceForm.resetFields();
      setInsurance(await listInsurance(selectedVisit.patient_id));
    } catch (e: any) {
      message.error(e.message || "Insurance save failed");
    } finally {
      setSaving(false);
    }
  };

  const columns = useMemo(
    () => [
      {
        title: "Patient",
        dataIndex: "patient_id",
        key: "patient_id",
        render: (v: string) => v || "—",
      },
      {
        title: "Date",
        dataIndex: "visit_date",
        key: "visit_date",
        width: 120,
        render: (v: string) => v || "—",
      },
      {
        title: "Status",
        dataIndex: "status",
        key: "status",
        width: 130,
        render: (s: string) => (
          <Tag color={VISIT_STATUS_COLORS[s] || "default"}>{s}</Tag>
        ),
      },
      {
        title: "Destination",
        dataIndex: "destination_room",
        key: "destination_room",
        render: (v: string) => v || "—",
      },
      {
        title: "HL7 Sync",
        dataIndex: "hl7_sync_status",
        key: "hl7_sync_status",
        width: 110,
        render: (s: string) => (
          <Tag
            color={
              s === "synced" ? "green" : s === "failed" ? "red" : "default"
            }
          >
            {s || "pending"}
          </Tag>
        ),
      },
      {
        title: "",
        key: "action",
        width: 220,
        render: (_: unknown, record: Visit) => (
          <span style={{ display: "flex", gap: 8 }}>
            <Button size="small" onClick={() => loadDetail(record)}>
              Details
            </Button>
            {canWrite && record.status === "registered" && (
              <Popconfirm
                title="Confirm patient arrival?"
                onConfirm={() => doCheckIn(record)}
              >
                <Button
                  size="small"
                  type="primary"
                  ghost
                  icon={<CheckCircleOutlined />}
                >
                  Check In
                </Button>
              </Popconfirm>
            )}
          </span>
        ),
      },
    ],
    [canWrite, loadDetail, pagination.current],
  );

  // Per-status totals across the whole visit set, not just the current page:
  // the chips count from a server-side per-status call (same convention as the
  // Worklist tab totals) so a filtered view never under-reports other buckets.
  // R1-07: totals are global — they must not re-run on every chip click.
  // They load on mount and on tenant switch (via useTenantRefetch below).
  const [statusTotals, setStatusTotals] = useState<Record<string, number>>({});
  const refreshTotals = useCallback(() => {
    Promise.all(
      STATUS_CHIPS.map((s) =>
        listVisits({ status: s, page: "1", per_page: "1" }),
      ),
    )
      .then((pages) => {
        const totals: Record<string, number> = {};
        STATUS_CHIPS.forEach((s, i) => {
          totals[s] = pages[i]?.total || 0;
        });
        setStatusTotals(totals);
      })
      .catch(() => {});
  }, []);
  useEffect(() => {
    refreshTotals();
  }, [refreshTotals]);
  useTenantRefetch(refreshTotals);
  const allTotal = Object.values(statusTotals).reduce((a, b) => a + b, 0);
  const counts: Record<string, number> = useMemo(
    () => ({ ...statusTotals, all: allTotal }),
    [statusTotals, allTotal],
  );

  return (
    <Content style={{ padding: 24 }} role="main">
      <div className="fd-header">
        <div className="fd-header-title">
          <MedicineBoxOutlined
            style={{ fontSize: 22, color: "var(--color-primary)" }}
          />
          <div>
            <h2>Visits & Check-In</h2>
            <span className="fd-subtitle">
              Today's visits — check patients in when they arrive
            </span>
          </div>
        </div>
      </div>

      <div className="fd-chips">
        <button
          type="button"
          className={`fd-chip ${statusFilter === "" ? "is-active" : ""}`}
          onClick={() => setStatusFilter("")}
        >
          All ({counts.all || 0})
        </button>
        {STATUS_CHIPS.map((s) => (
          <button
            key={s}
            type="button"
            className={`fd-chip ${statusFilter === s ? "is-active" : ""}`}
            onClick={() => setStatusFilter(s)}
          >
            {s} ({counts[s] || 0})
          </button>
        ))}
      </div>

      {error && (
        <Alert
          type="error"
          title="Failed to load visits"
          description={error}
          showIcon
          style={{ marginBottom: 16 }}
          action={
            <Button size="small" onClick={() => fetch()}>
              Retry
            </Button>
          }
        />
      )}

      <Table
        rowKey="id"
        columns={columns}
        dataSource={data}
        loading={loading}
        pagination={pagination}
        onChange={(pag) => {
          const newPageSize = pag.pageSize ?? 20;
          setPagination({
            current: pag.current ?? 1,
            pageSize: newPageSize,
            total: pag.total ?? data.length,
          });
          // S14: pass pageSize explicitly — fetch's closure still has the
          // old value since setPagination hasn't applied yet.
          fetch(pag.current ?? 1, newPageSize);
        }}
        scroll={{ x: 800 }}
        locale={{ emptyText: "No visits for this filter" }}
      />

      <Drawer
        title={
          <span>
            <FileDoneOutlined style={{ marginRight: 8 }} />
            Visit {selectedVisit?.id?.slice(0, 8)}
          </span>
        }
        open={!!selectedVisit}
        onClose={() => setSelectedVisit(null)}
        size={560}
      >
        {detailLoading ? (
          <div className="fd-loading">
            <Spin />
          </div>
        ) : visitDetail ? (
          <>
            <Descriptions size="small" column={2} bordered>
              <Descriptions.Item label="Patient">
                {visitDetail.patient_id}
              </Descriptions.Item>
              <Descriptions.Item label="Status">
                <Tag color={VISIT_STATUS_COLORS[visitDetail.status]}>
                  {visitDetail.status}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="Date">
                {visitDetail.visit_date || "—"}
              </Descriptions.Item>
              <Descriptions.Item label="Destination">
                {visitDetail.destination_room || "—"}
              </Descriptions.Item>
              <Descriptions.Item label="HL7 sync">
                {visitDetail.hl7_sync_status || "—"}
              </Descriptions.Item>
              <Descriptions.Item label="Created">
                {visitDetail.created_at
                  ? new Date(visitDetail.created_at).toLocaleString()
                  : "—"}
              </Descriptions.Item>
            </Descriptions>

            {canWrite && visitDetail.status === "registered" && (
              <Button
                type="primary"
                icon={<CheckCircleOutlined />}
                style={{ marginTop: 12 }}
                onClick={() => doCheckIn(visitDetail)}
              >
                Check In Patient
              </Button>
            )}

            <Divider />

            {/* Orders — US-R08-03 */}
            <div className="fd-visit-section">
              <div className="fd-visit-section-title">
                <span>Orders</span>
              </div>
              {orders.length === 0 ? (
                <Alert
                  type="info"
                  showIcon
                  title="No orders yet — add the referring order below."
                />
              ) : (
                <Timeline
                  items={orders.map((o) => ({
                    dot: <ClockCircleOutlined />,
                    color:
                      o.urgency === "stat"
                        ? "red"
                        : o.urgency === "urgent"
                          ? "orange"
                          : "blue",
                    children: (
                      <>
                        <b>{o.requested_procedure}</b>
                        {o.urgency && (
                          <Tag
                            color={
                              o.urgency === "stat"
                                ? "red"
                                : o.urgency === "urgent"
                                  ? "orange"
                                  : "default"
                            }
                            style={{ marginLeft: 8 }}
                          >
                            {o.urgency.toUpperCase()}
                          </Tag>
                        )}
                        <div
                          style={{
                            color: "var(--text-secondary)",
                            fontSize: 12,
                          }}
                        >
                          {o.indication || "No indication"} · Dr.{" "}
                          {o.referring_physician || "—"}
                        </div>
                      </>
                    ),
                  }))}
                />
              )}
              {canWrite && (
                <Form
                  form={orderForm}
                  layout="vertical"
                  style={{ marginTop: 12 }}
                >
                  <Form.Item
                    name="requested_procedure"
                    label="Requested procedure"
                    rules={[{ required: true, message: "Procedure required" }]}
                  >
                    <Input placeholder="e.g. CT CHEST W CONTRAST" />
                  </Form.Item>
                  <div style={{ display: "flex", gap: 12 }}>
                    <Form.Item
                      name="urgency"
                      label="Urgency"
                      style={{ flex: 1 }}
                      initialValue="routine"
                    >
                      <Select
                        options={["routine", "urgent", "stat"].map((u) => ({
                          value: u,
                          label: u,
                        }))}
                      />
                    </Form.Item>
                    <Form.Item
                      name="referring_physician"
                      label="Referring physician"
                      style={{ flex: 1 }}
                    >
                      <Input placeholder="Last^First" />
                    </Form.Item>
                  </div>
                  <Form.Item name="indication" label="Indication">
                    <Input.TextArea
                      rows={2}
                      placeholder="Clinical indication"
                    />
                  </Form.Item>
                  <Button
                    type="primary"
                    onClick={submitOrder}
                    loading={saving}
                    icon={<MedicineBoxOutlined />}
                  >
                    Add Order
                  </Button>
                </Form>
              )}
            </div>

            <Divider />

            {/* Consents — US-R08-06 */}
            <div className="fd-visit-section">
              <div className="fd-visit-section-title">
                <span>Consents</span>
              </div>
              {consents.length === 0 ? (
                <Alert
                  type="warning"
                  showIcon
                  title="No required consents seeded for this visit."
                />
              ) : (
                consents.map((c) => (
                  <div
                    key={c.id}
                    className="fd-patient-result"
                    style={{ marginBottom: 8 }}
                  >
                    <div>
                      <b>{c.consent_type.replace(/_/g, " ")}</b>
                      <div className="fd-patient-meta">
                        {c.file_name || "No file"} ·{" "}
                        {c.attached_at
                          ? new Date(c.attached_at).toLocaleString()
                          : "not yet attached"}
                      </div>
                    </div>
                    <Tag
                      color={
                        c.status === "attached"
                          ? "green"
                          : c.status === "missing"
                            ? "red"
                            : "orange"
                      }
                    >
                      {c.status}
                    </Tag>
                  </div>
                ))
              )}
              {canWrite && (
                <Form
                  form={consentForm}
                  layout="vertical"
                  style={{ marginTop: 12 }}
                >
                  <div style={{ display: "flex", gap: 12 }}>
                    <Form.Item
                      name="consent_type"
                      label="Consent type"
                      style={{ flex: 1 }}
                      initialValue="general_consent"
                    >
                      <Select options={CONSENT_TYPES} />
                    </Form.Item>
                    <Form.Item
                      name="file_name"
                      label="File name"
                      style={{ flex: 1 }}
                      rules={[
                        { required: true, message: "File name required" },
                      ]}
                    >
                      <Input placeholder="e.g. consent-signed.pdf" />
                    </Form.Item>
                  </div>
                  <Button
                    type="primary"
                    onClick={submitConsent}
                    loading={saving}
                    icon={<SafetyCertificateOutlined />}
                  >
                    Attach Consent
                  </Button>
                </Form>
              )}
            </div>

            <Divider />

            {/* Insurance / guarantor — US-R08-02 companion */}
            <div className="fd-visit-section">
              <div className="fd-visit-section-title">
                <span>Insurance / Guarantor</span>
              </div>
              {eligibility && eligibility.status === "active" && (
                <div className="fd-eligibility" style={{ marginBottom: 8 }}>
                  <div>
                    <Tag color="green">{eligibility.provider || "Active"}</Tag>
                    <span className="fd-patient-meta">
                      Member: {eligibility.member_id || "—"}
                    </span>
                  </div>
                  <div className="fd-patient-meta">
                    Copay:{" "}
                    {eligibility.copay_amount != null
                      ? `$${eligibility.copay_amount}`
                      : "—"}{" "}
                    · Deductible:{" "}
                    {eligibility.deductible_total != null
                      ? `$${eligibility.deductible_total}`
                      : "—"}{" "}
                    · Remaining:{" "}
                    {eligibility.deductible_remaining != null
                      ? `$${eligibility.deductible_remaining}`
                      : "—"}
                  </div>
                </div>
              )}
              {eligibility && eligibility.status === "none" && (
                <Alert
                  type="warning"
                  showIcon
                  style={{ marginBottom: 8 }}
                  title="No coverage on file"
                  description="Add an insurance policy to run an eligibility check."
                />
              )}
              {insurance.length === 0 ? (
                <Alert
                  type="info"
                  showIcon
                  title="No insurance record yet."
                />
              ) : (
                insurance.map((i) => (
                  <div
                    key={i.id}
                    className="fd-patient-result"
                    style={{ marginBottom: 8 }}
                  >
                    <div>
                      <b>{i.policy_number || "No policy #"}</b>
                      <div className="fd-patient-meta">
                        Guarantor: {i.guarantor_name || "—"} ·{" "}
                        {i.authorization_status || "none"}
                      </div>
                    </div>
                    {i.authorization_number && (
                      <Tag color="blue">{i.authorization_number}</Tag>
                    )}
                  </div>
                ))
              )}
              {canWrite && (
                <Form
                  form={insuranceForm}
                  layout="vertical"
                  style={{ marginTop: 12 }}
                >
                  <div style={{ display: "flex", gap: 12 }}>
                    <Form.Item
                      name="policy_number"
                      label="Policy #"
                      style={{ flex: 1 }}
                    >
                      <Input placeholder="Policy number" />
                    </Form.Item>
                    <Form.Item
                      name="guarantor_name"
                      label="Guarantor"
                      style={{ flex: 1 }}
                    >
                      <Input placeholder="Guarantor name" />
                    </Form.Item>
                  </div>
                  <div style={{ display: "flex", gap: 12 }}>
                    <Form.Item name="provider" label="Provider" style={{ flex: 1 }}>
                      <Input placeholder="Payer/provider" />
                    </Form.Item>
                    <Form.Item name="member_id" label="Member ID" style={{ flex: 1 }}>
                      <Input placeholder="Member ID" />
                    </Form.Item>
                  </div>
                  <div style={{ display: "flex", gap: 12 }}>
                    <Form.Item name="copay_amount" label="Copay ($)" style={{ flex: 1 }}>
                      <Input type="number" placeholder="0.00" />
                    </Form.Item>
                    <Form.Item
                      name="deductible_total"
                      label="Deductible ($)"
                      style={{ flex: 1 }}
                    >
                      <Input type="number" placeholder="0.00" />
                    </Form.Item>
                    <Form.Item
                      name="deductible_remaining"
                      label="Deductible remaining ($)"
                      style={{ flex: 1 }}
                    >
                      <Input type="number" placeholder="0.00" />
                    </Form.Item>
                  </div>
                  <Form.Item name="notes" label="Notes">
                    <Input.TextArea rows={2} />
                  </Form.Item>
                  <Button
                    type="primary"
                    onClick={submitInsurance}
                    loading={saving}
                    icon={<InsuranceOutlined />}
                  >
                    Save Insurance
                  </Button>
                </Form>
              )}
            </div>
          </>
        ) : (
          <Alert type="error" showIcon title="Visit could not be loaded." />
        )}
      </Drawer>
    </Content>
  );
}

export default withSidebar(Visits);
