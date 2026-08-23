import { useDocumentTitle, useTenantRefetch } from "../hooks";
import React, { useCallback, useEffect, useRef, useState } from "react";
import {
  App,
  Layout,
  Card,
  Row,
  Col,
  Tag,
  Button,
  Spin,
  Alert,
  Empty,
  Typography,
  Statistic,
  Space,
  Divider,
} from "antd";
import {
  CalendarOutlined,
  FileTextOutlined,
  UserOutlined,
  MedicineBoxOutlined,
  SolutionOutlined,
  BellOutlined,
  RightOutlined,
  TeamOutlined,
  PhoneOutlined,
  MailOutlined,
} from "@ant-design/icons";
import { useNavigate } from "react-router";
import withSidebar from "../common/base";
import { PageState } from "../common/PageState";
import {
  listScope,
  getPortalPatient,
  getPortalOrders,
  getPortalAppointments,
  type PortalScope,
  type PortalPatientBundle,
  type PortalOrder,
  type PortalReport,
  type PortalAppointment,
} from "../api/portal";
import "./Portal.css";

const { Text, Paragraph } = Typography;
const Content = Layout.Content;

// Portal home dashboard — replaces the old tabbed Portal.tsx with a
// card-based layout. Shows: upcoming appointments, recent results,
// quick actions, patient info, and imaging summary.
function PortalHome() {
  const { message } = App.useApp();
  useDocumentTitle("QuantumPACS - Patient Portal");
  const navigate = useNavigate();

  const [scope, setScope] = useState<PortalScope[]>([]);
  const [loadingScope, setLoadingScope] = useState(true);
  const [activePatientId, setActivePatientId] = useState<string | null>(null);
  const [bundle, setBundle] = useState<PortalPatientBundle | null>(null);
  const [orders, setOrders] = useState<PortalOrder[]>([]);
  const [appointments, setAppointments] = useState<PortalAppointment[]>([]);
  const [loadingPatient, setLoadingPatient] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadScope = useCallback(() => {
    setLoadingScope(true);
    setError(null);
    listScope()
      .then((rows) => {
        setScope(rows);
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

  // Sequence-guard patient loads (same pattern as original Portal.tsx)
  const patientSeq = useRef(0);
  const loadPatient = useCallback((patientId: string) => {
    const seq = ++patientSeq.current;
    setLoadingPatient(true);
    setError(null);
    setBundle(null);
    setOrders([]);
    setAppointments([]);
    Promise.all([
      getPortalPatient(patientId),
      getPortalOrders(patientId),
      getPortalAppointments(patientId),
    ])
      .then(([b, o, a]) => {
        if (seq !== patientSeq.current) return;
        setBundle(b);
        setOrders(o);
        setAppointments(a);
        if (!b || !b.patient) {
          message.warning("No records are currently shared for this patient.");
        }
      })
      .catch((e: any) => {
        if (seq === patientSeq.current) {
          setError(e.message || "Failed to load patient");
        }
      })
      .finally(() => {
        if (seq === patientSeq.current) setLoadingPatient(false);
      });
  }, []);

  useEffect(() => {
    if (activePatientId) loadPatient(activePatientId);
  }, [activePatientId, loadPatient]);

  const patient = bundle?.patient;
  const reports = bundle?.reports ?? [];

  // Upcoming appointments from the real appointments endpoint
  const upcomingAppointments = appointments.filter(
    (a) => a.status === "SCHEDULED" || a.status === "CONFIRMED",
  );

  // Recent results = signed/preliminary reports
  const recentResults = reports.filter(
    (r) => r.status === "signed" || r.status === "final" || r.status === "preliminary",
  );

  // Imaging summary counts
  const modalityCounts: Record<string, number> = {};
  reports.forEach((r) => {
    if (r.modality) {
      modalityCounts[r.modality] = (modalityCounts[r.modality] || 0) + 1;
    }
  });
  const thisYear = new Date().getFullYear();
  const thisYearCount = reports.filter((r) => {
    if (!r.signed_at) return false;
    return new Date(r.signed_at).getFullYear() === thisYear;
  }).length;
  const pendingCount = orders.filter(
    (o) => o.status === "ordered" || o.status === "scheduled",
  ).length;

  // --- Loading / Error states ---
  if (loadingScope) {
    return (
      <Content className="portal-home">
        <div className="portal-loading">
          <Spin size="large" />
        </div>
      </Content>
    );
  }

  if (error && scope.length === 0) {
    return (
      <Content className="portal-home">
        <Alert
          type="error"
          title="Failed to load your records"
          description={error}
          showIcon
          action={
            <Button size="small" onClick={loadScope}>
              Retry
            </Button>
          }
        />
      </Content>
    );
  }

  if (scope.length === 0) {
    return (
      <Content className="portal-home">
        <Card>
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description="No records are shared with you yet. If you believe this is an error, contact your radiology department."
          />
        </Card>
      </Content>
    );
  }

  // --- Main dashboard layout ---
  return (
    <Content className="portal-home" role="main">
      {/* Page header */}
      <div className="portal-home-header">
        <div>
          <h2 style={{ margin: 0 }}>
            <MedicineBoxOutlined style={{ marginRight: 8 }} />
            QuantumPACS Patient Portal
          </h2>
          <Text type="secondary">
            Welcome{patient?.name ? `, ${patient.name}` : ""} — your imaging
            records
          </Text>
        </div>
        <Space>
          {scope.length > 1 && (
            <Tag color="blue">{scope.length} linked patients</Tag>
          )}
        </Space>
      </div>

      {error && (
        <Alert
          type="warning"
          title="Some data could not be loaded"
          description={error}
          showIcon
          closable
          style={{ marginBottom: 16 }}
        />
      )}

      {loadingPatient ? (
        <div className="portal-loading">
          <Spin />
        </div>
      ) : (
        <>
          {/* Row 1: Upcoming Appointments + Recent Results + Quick Actions */}
          <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
            {/* Upcoming Appointments */}
            <Col xs={24} md={8}>
              <Card
                className="portal-card"
                title={
                  <span>
                    <CalendarOutlined style={{ marginRight: 6 }} />
                    Upcoming Appointments
                  </span>
                }
                extra={
                  <Button
                    type="link"
                    size="small"
                    onClick={() => navigate("/portal/appointments")}
                  >
                    View all <RightOutlined />
                  </Button>
                }
              >
                {loadingPatient ? (
                  <Spin size="small" />
                ) : upcomingAppointments.length === 0 ? (
                  <Empty
                    image={Empty.PRESENTED_IMAGE_SIMPLE}
                    description="No upcoming appointments"
                    imageStyle={{ height: 40 }}
                  />
                ) : (
                  <div className="portal-card-list">
                    {upcomingAppointments.slice(0, 3).map((apt) => (
                      <div key={apt.id} className="portal-card-item portal-appt-item">
                        <div className="portal-card-item-main">
                          <Text strong>{apt.procedure || "Imaging"}</Text>
                          <Text type="secondary" style={{ fontSize: 12 }}>
                            {apt.start_time
                              ? `${new Date(apt.start_time).toLocaleDateString(undefined, {
                                  month: "short",
                                  day: "numeric",
                                })}, ${new Date(apt.start_time).toLocaleTimeString(undefined, {
                                  hour: "numeric",
                                  minute: "2-digit",
                                })}`
                              : "—"}
                          </Text>
                          {apt.room && (
                            <Text type="secondary" style={{ fontSize: 12 }}>
                              Room: {apt.room}
                            </Text>
                          )}
                        </div>
                        <div className="portal-card-item-side">
                          <Tag
                            color={
                              apt.priority === "STAT"
                                ? "red"
                                : apt.priority === "URGENT"
                                  ? "orange"
                                  : "default"
                            }
                          >
                            {apt.priority?.toLowerCase() || "routine"}
                          </Tag>
                          <Button
                            type="link"
                            size="small"
                            onClick={() => navigate("/portal/appointments")}
                          >
                            View Details
                          </Button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </Card>
            </Col>

            {/* Recent Results */}
            <Col xs={24} md={8}>
              <Card
                className="portal-card"
                title={
                  <span>
                    <FileTextOutlined style={{ marginRight: 6 }} />
                    Recent Results
                  </span>
                }
                extra={
                  <Button
                    type="link"
                    size="small"
                    onClick={() => navigate("/portal/results")}
                  >
                    View all <RightOutlined />
                  </Button>
                }
              >
                {loadingPatient ? (
                  <Spin size="small" />
                ) : recentResults.length === 0 ? (
                  <Empty
                    image={Empty.PRESENTED_IMAGE_SIMPLE}
                    description="No results available yet"
                    imageStyle={{ height: 40 }}
                  />
                ) : (
                  <div className="portal-card-list">
                    {recentResults.slice(0, 3).map((rpt) => (
                      <div key={rpt.id} className="portal-card-item portal-result-new">
                        <div className="portal-card-item-main">
                          <Text strong>
                            {(rpt as any).requested_procedure_desc ||
                              rpt.modality ||
                              rpt.accession_number ||
                              "Imaging report"}
                          </Text>
                          <Text type="secondary" style={{ fontSize: 12 }}>
                            {rpt.signed_at
                              ? `Signed ${new Date(rpt.signed_at).toLocaleDateString()}`
                              : "Pending"}
                            {(rpt as any).signed_by_name
                              ? ` · ${(rpt as any).signed_by_name}`
                              : ""}
                          </Text>
                        </div>
                        <div className="portal-card-item-side">
                          <Tag
                            color={
                              rpt.status === "signed" || rpt.status === "final"
                                ? "green"
                                : "orange"
                            }
                          >
                            {rpt.status || "draft"}
                          </Tag>
                          <Button
                            type="link"
                            size="small"
                            onClick={() => navigate(`/portal/results/${rpt.id}`)}
                          >
                            Read Report
                          </Button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </Card>
            </Col>

            {/* Quick Actions */}
            <Col xs={24} md={8}>
              <Card
                className="portal-card"
                title={
                  <span>
                    <SolutionOutlined style={{ marginRight: 6 }} />
                    Quick Actions
                  </span>
                }
              >
                <div className="portal-quick-actions">
                  <Button
                    block
                    icon={<SolutionOutlined />}
                    onClick={() => navigate("/portal/follow-ups")}
                    style={{ marginBottom: 8 }}
                  >
                    Request Follow-up
                  </Button>
                  <Button
                    block
                    icon={<FileTextOutlined />}
                    onClick={() => navigate("/portal/results")}
                    style={{ marginBottom: 8 }}
                  >
                    View Records
                  </Button>
                  <Button
                    block
                    icon={<CalendarOutlined />}
                    onClick={() => navigate("/portal/appointments")}
                  >
                    View Appointments
                  </Button>
                  <Divider style={{ margin: "8px 0" }} />
                  <Button
                    block
                    icon={<PhoneOutlined />}
                    onClick={() => navigate("/portal")}
                    type="default"
                  >
                    Contact Us
                  </Button>
                </div>
              </Card>
            </Col>
          </Row>

          {/* Row 2: Patient Info */}
          {patient && (
            <Card
              className="portal-card"
              style={{ marginBottom: 16 }}
              title={
                <span>
                  <UserOutlined style={{ marginRight: 6 }} />
                  Patient Info
                </span>
              }
              extra={
                <Space>
                  <Button
                    type="link"
                    size="small"
                    onClick={() => navigate("/portal/profile")}
                  >
                    View Profile
                  </Button>
                  <Button
                    type="link"
                    size="small"
                    onClick={() => navigate("/portal/profile#consent")}
                  >
                    Manage Consent
                  </Button>
                </Space>
              }
            >
              <Row gutter={[24, 8]}>
                <Col xs={12} sm={6}>
                  <Text type="secondary" style={{ fontSize: 12 }}>Name</Text>
                  <br />
                  <Text strong>{patient.name || "—"}</Text>
                </Col>
                <Col xs={12} sm={6}>
                  <Text type="secondary" style={{ fontSize: 12 }}>MRN</Text>
                  <br />
                  <Text strong>{patient.patient_id || "—"}</Text>
                </Col>
                <Col xs={12} sm={6}>
                  <Text type="secondary" style={{ fontSize: 12 }}>DOB</Text>
                  <br />
                  <Text strong>{patient.birth_date || "—"}</Text>
                </Col>
                <Col xs={12} sm={6}>
                  <Text type="secondary" style={{ fontSize: 12 }}>Sex</Text>
                  <br />
                  <Text strong>{patient.sex || "—"}</Text>
                </Col>
                <Col xs={12} sm={6}>
                  <Text type="secondary" style={{ fontSize: 12 }}>Phone</Text>
                  <br />
                  <Text strong>
                    {(patient as any).phone || (
                      <Text type="secondary">On file</Text>
                    )}
                  </Text>
                </Col>
                <Col xs={12} sm={6}>
                  <Text type="secondary" style={{ fontSize: 12 }}>Email</Text>
                  <br />
                  <Text strong>
                    {(patient as any).email || (
                      <Text type="secondary">On file</Text>
                    )}
                  </Text>
                </Col>
              </Row>
            </Card>
          )}

          {/* Row 3: Imaging Summary */}
          <Card
            className="portal-card"
            title={
              <span>
                <TeamOutlined style={{ marginRight: 6 }} />
                My Imaging Summary
              </span>
            }
          >
            <Row gutter={[24, 16]}>
              <Col xs={8}>
                <Statistic
                  title="Total Reports"
                  value={reports.length}
                />
              </Col>
              <Col xs={8}>
                <Statistic
                  title={`This Year (${thisYear})`}
                  value={thisYearCount}
                />
              </Col>
              <Col xs={8}>
                <Statistic
                  title="Pending"
                  value={pendingCount}
                  valueStyle={
                    pendingCount > 0
                      ? { color: "#fa8c16" }
                      : undefined
                  }
                />
              </Col>
            </Row>
            {Object.keys(modalityCounts).length > 0 && (
              <>
                <Divider style={{ margin: "12px 0" }} />
                <Space wrap>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    Modalities:
                  </Text>
                  {Object.entries(modalityCounts).map(([mod, count]) => (
                    <Tag key={mod}>
                      {mod}({count})
                    </Tag>
                  ))}
                </Space>
              </>
            )}
          </Card>
        </>
      )}
    </Content>
  );
}

export default withSidebar(PortalHome);
