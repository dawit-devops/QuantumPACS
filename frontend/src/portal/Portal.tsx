import { useDocumentTitle, useTenantRefetch } from "../hooks";
import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  App,
  Layout,
  Card,
  Descriptions,
  Tag,
  Table,
  Tabs,
  Spin,
  Alert,
  Empty,
  Button,
} from "antd";
import {
  UserOutlined,
  FileTextOutlined,
  MedicineBoxOutlined,
  SolutionOutlined,
  LockOutlined,
} from "@ant-design/icons";
import withSidebar from "../common/base";
import {
  listScope,
  getPortalPatient,
  getPortalOrders,
  type PortalScope,
  type PortalPatientBundle,
  type PortalOrder,
  type PortalReport,
} from "../api/portal";
import "./Portal.css";

const Content = Layout.Content;

// R19 / patient portal: every patient record shown is scope-gated server-side
// (patient_staff_scope for the requesting user). Out-of-scope patients never
// render — the backend returns data: null, indistinguishable from missing.
function Portal() {
  const { message } = App.useApp();
  useDocumentTitle("QuantumPACS - My Records");

  const [scope, setScope] = useState<PortalScope[]>([]);
  const [loadingScope, setLoadingScope] = useState(true);
  const [activePatientId, setActivePatientId] = useState<string | null>(null);
  const [bundle, setBundle] = useState<PortalPatientBundle | null>(null);
  const [orders, setOrders] = useState<PortalOrder[]>([]);
  const [loadingPatient, setLoadingPatient] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadScope = useCallback(() => {
    setLoadingScope(true);
    setError(null);
    listScope()
      .then((rows) => {
        setScope(rows);
        // Default to the first scoped patient (usually the only one).
        if (rows.length > 0) setActivePatientId(rows[0].patient_id);
        else setActivePatientId(null);
      })
      .catch((e: any) => setError(e.message || "Failed to load records"))
      .finally(() => setLoadingScope(false));
  }, []);

  useEffect(() => {
    loadScope();
  }, [loadScope]);

  useTenantRefetch(loadScope);

  const loadPatient = useCallback(
    (patientId: string) => {
      setLoadingPatient(true);
      setError(null);
      setBundle(null);
      setOrders([]);
      Promise.all([
        getPortalPatient(patientId),
        getPortalOrders(patientId),
      ])
        .then(([b, o]) => {
          setBundle(b);
          setOrders(o);
          if (!b || !b.patient) {
            message.warning("No records are currently shared for this patient.");
          }
        })
        .catch((e: any) => setError(e.message || "Failed to load patient"))
        .finally(() => setLoadingPatient(false));
    },
    [],
  );

  useEffect(() => {
    if (activePatientId) loadPatient(activePatientId);
  }, [activePatientId, loadPatient]);

  const reports = useMemo(
    () => bundle?.reports ?? [],
    [bundle],
  );

  const reportColumns = [
    {
      title: "Exam",
      dataIndex: "accession_number",
      key: "accession_number",
      render: (v: string) => v || "—",
    },
    {
      title: "Modality",
      dataIndex: "modality",
      key: "modality",
      width: 90,
    },
    {
      title: "Status",
      dataIndex: "status",
      key: "status",
      width: 110,
      render: (s: string) => (
        <Tag color={s === "signed" || s === "final" ? "green" : "orange"}>
          {s || "preliminary"}
        </Tag>
      ),
    },
    {
      title: "Impression",
      key: "impression",
      ellipsis: true,
      render: (_: unknown, r: PortalReport) => r.impression || r.finding || "—",
    },
    {
      title: "Signed",
      dataIndex: "signed_at",
      key: "signed_at",
      width: 160,
      render: (v: string) => (v ? new Date(v).toLocaleDateString() : "—"),
    },
  ];

  const orderColumns = [
    {
      title: "Procedure",
      dataIndex: "requested_procedure",
      key: "requested_procedure",
      render: (v: string) => v || "—",
    },
    {
      title: "Urgency",
      dataIndex: "urgency",
      key: "urgency",
      width: 100,
      render: (v: string) => (
        <Tag color={v === "stat" ? "red" : v === "urgent" ? "orange" : "default"}>
          {v || "routine"}
        </Tag>
      ),
    },
    {
      title: "Status",
      dataIndex: "status",
      key: "status",
      width: 100,
      render: (v: string) => <Tag>{v || "open"}</Tag>,
    },
    {
      title: "Ordered",
      dataIndex: "created_at",
      key: "created_at",
      width: 140,
      render: (v: string) => (v ? new Date(v).toLocaleDateString() : "—"),
    },
  ];

  const patient = bundle?.patient;

  return (
    <Content style={{ padding: 24 }} role="main" id="main-content">
      <div className="portal-header">
        <div className="portal-header-title">
          <LockOutlined style={{ fontSize: 22, color: "var(--color-primary)" }} />
          <div>
            <h2>My Records</h2>
            <span className="portal-subtitle">
              Your imaging history — shared with you securely
            </span>
          </div>
        </div>
      </div>

      {loadingScope ? (
        <div className="portal-loading">
          <Spin />
        </div>
      ) : scope.length === 0 ? (
        <Card>
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description="No records are shared with you yet. If you believe this is an error, contact your radiology department."
          />
        </Card>
      ) : (
        <>
          <div className="portal-tabs">
            <Tabs
              activeKey={activePatientId || undefined}
              onChange={setActivePatientId}
              items={scope.map((s) => ({
                key: s.patient_id,
                label: (
                  <span>
                    <UserOutlined style={{ marginRight: 6 }} />
                    {s.patient_id}
                  </span>
                ),
              }))}
            />
          </div>

          {error && (
            <Alert
              type="error"
              message="Failed to load records"
              description={error}
              showIcon
              style={{ marginBottom: 16 }}
              action={
                <Button size="small" onClick={() => activePatientId && loadPatient(activePatientId)}>
                  Retry
                </Button>
              }
            />
          )}

          {loadingPatient ? (
            <div className="portal-loading">
              <Spin />
            </div>
          ) : patient ? (
            <>
              <Card size="small" style={{ marginBottom: 16 }}>
                <Descriptions size="small" column={4}>
                  <Descriptions.Item label="Name">
                    {patient.name || "—"}
                  </Descriptions.Item>
                  <Descriptions.Item label="MRN">
                    {patient.patient_id || "—"}
                  </Descriptions.Item>
                  <Descriptions.Item label="DOB">
                    {patient.birth_date || "—"}
                  </Descriptions.Item>
                  <Descriptions.Item label="Sex">
                    {patient.sex || "—"}
                  </Descriptions.Item>
                </Descriptions>
              </Card>

              <Tabs
                items={[
                  {
                    key: "orders",
                    label: (
                      <span>
                        <MedicineBoxOutlined style={{ marginRight: 6 }} />
                        Orders ({orders.length})
                      </span>
                    ),
                    children: (
                      <Card size="small">
                        <Table
                          rowKey={(r: any) => r.id}
                          columns={orderColumns}
                          dataSource={orders}
                          pagination={false}
                          size="small"
                          locale={{ emptyText: "No orders on file" }}
                        />
                      </Card>
                    ),
                  },
                  {
                    key: "reports",
                    label: (
                      <span>
                        <FileTextOutlined style={{ marginRight: 6 }} />
                        Reports ({reports.length})
                      </span>
                    ),
                    children: (
                      <Card size="small">
                        <Table
                          rowKey={(r: any) => r.id}
                          columns={reportColumns}
                          dataSource={reports}
                          pagination={false}
                          size="small"
                          locale={{ emptyText: "No final reports yet" }}
                        />
                      </Card>
                    ),
                  },
                ]}
              />
            </>
          ) : (
            <Card>
              <Empty
                image={Empty.PRESENTED_IMAGE_SIMPLE}
                description="No records are currently shared for this patient."
              />
            </Card>
          )}
        </>
      )}
    </Content>
  );
}

export default withSidebar(Portal);
