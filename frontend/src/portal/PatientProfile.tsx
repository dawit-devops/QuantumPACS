import { useDocumentTitle, useTenantRefetch } from "../hooks";
import React, { useCallback, useEffect, useRef, useState } from "react";
import {
  App,
  Layout,
  Card,
  Descriptions,
  Row,
  Col,
  Tag,
  Button,
  Spin,
  Alert,
  Empty,
  Typography,
  Divider,
  Switch,
  Modal,
  Input,
  Space,
} from "antd";
import {
  UserOutlined,
  SafetyCertificateOutlined,
  InfoCircleOutlined,
  EditOutlined,
} from "@ant-design/icons";
import { useNavigate } from "react-router";
import withSidebar from "../common/base";
import { PageState } from "../common/PageState";
import {
  listScope,
  getPortalPatient,
  updateConsent,
  type PortalScope,
  type PortalPatientBundle,
} from "../api/portal";
import "./Portal.css";

const { Text, Paragraph } = Typography;
const Content = Layout.Content;

// Patient profile page — read-only demographics + consent management.
// Demographics are view-only (changes handled by front desk during registration).
// Consent toggle controls patients.meta.consent_results which gates portal
// visibility of reports and orders.
function PatientProfile() {
  const { message } = App.useApp();
  useDocumentTitle("QuantumPACS - My Profile");
  const navigate = useNavigate();

  const [scope, setScope] = useState<PortalScope[]>([]);
  const [loadingScope, setLoadingScope] = useState(true);
  const [activePatientId, setActivePatientId] = useState<string | null>(null);
  const [bundle, setBundle] = useState<PortalPatientBundle | null>(null);
  const [loadingPatient, setLoadingPatient] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Consent state — derived from the bundle's patient data
  const [consentResults, setConsentResults] = useState<boolean>(false);
  const [consentLoading, setConsentLoading] = useState(false);
  const [consentModalOpen, setConsentModalOpen] = useState(false);
  const [consentReason, setConsentReason] = useState("");

  const loadScope = useCallback(() => {
    setLoadingScope(true);
    setError(null);
    listScope()
      .then((rows) => {
        setScope(rows);
        if (rows.length > 0) setActivePatientId(rows[0].patient_id);
        else setActivePatientId(null);
      })
      .catch((e: any) => setError(e.message || "Failed to load profile"))
      .finally(() => setLoadingScope(false));
  }, []);

  useEffect(() => {
    loadScope();
  }, [loadScope]);

  useTenantRefetch(loadScope);

  // Sequence-guard patient loads
  const patientSeq = useRef(0);
  const loadPatient = useCallback((patientId: string) => {
    const seq = ++patientSeq.current;
    setLoadingPatient(true);
    setError(null);
    setBundle(null);
    getPortalPatient(patientId)
      .then((b) => {
        if (seq !== patientSeq.current) return;
        setBundle(b);
        // Consent status now comes from the bundle's demographics
        // (patients.meta.consent_results projected by the backend, S8) —
        // no more guessing from report visibility.
        const consent = b?.patient && (b.patient as any).consent_status;
        if (consent === "true") {
          setConsentResults(true);
        } else if (consent === "false" || consent === "") {
          setConsentResults(false);
        }
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

  // Consent toggle handler — calls the real consent endpoint so withdrawal
  // revokes portal visibility server-side (patients.meta.consent_results).
  const handleConsentToggle = (checked: boolean) => {
    if (!checked) {
      // Withdrawing consent — show confirmation modal
      setConsentModalOpen(true);
    } else {
      // Granting consent — call the API directly
      setConsentLoading(true);
      updateConsent(activePatientId!, true)
        .then(() => {
          setConsentResults(true);
          message.success("Consent granted — your records are now visible in the portal");
        })
        .catch((e: any) => message.error(e.message || "Failed to update consent"))
        .finally(() => setConsentLoading(false));
    }
  };

  const confirmConsentWithdrawal = () => {
    setConsentLoading(true);
    updateConsent(activePatientId!, false)
      .then(() => {
        setConsentResults(false);
        message.info("Consent withdrawn — reports and orders will no longer be visible in the portal");
      })
      .catch((e: any) => message.error(e.message || "Failed to update consent"))
      .finally(() => {
        setConsentLoading(false);
        setConsentModalOpen(false);
        setConsentReason("");
      });
  };

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
          title="Failed to load your profile"
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
            description="No records are shared with you yet."
          />
        </Card>
      </Content>
    );
  }

  return (
    <Content className="portal-home" role="main">
      {/* Header */}
      <div className="portal-home-header">
        <div>
          <h2 style={{ margin: 0 }}>
            <UserOutlined style={{ marginRight: 8 }} />
            My Profile
          </h2>
          <Text type="secondary">
            Your patient information — managed by your healthcare provider
          </Text>
        </div>
        <Button onClick={() => navigate("/portal")}>
          Back to Portal
        </Button>
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
      ) : patient ? (
        <>
          {/* Demographics Card — Read Only */}
          <Card
            className="portal-card"
            style={{ marginBottom: 16 }}
            title={
              <span>
                <UserOutlined style={{ marginRight: 6 }} />
                Patient Demographics
              </span>
            }
            extra={
              <Tag color="default">
                <InfoCircleOutlined style={{ marginRight: 4 }} />
                Read-only — contact front desk for changes
              </Tag>
            }
          >
            <Descriptions column={{ xs: 1, sm: 2, md: 3 }} bordered size="small">
              <Descriptions.Item label="Full Name">
                <Text strong>{patient.name || "—"}</Text>
              </Descriptions.Item>
              <Descriptions.Item label="Medical Record Number (MRN)">
                <Text strong>{patient.patient_id || "—"}</Text>
              </Descriptions.Item>
              <Descriptions.Item label="Date of Birth">
                {patient.birth_date || "—"}
              </Descriptions.Item>
              <Descriptions.Item label="Sex">
                {patient.sex || "—"}
              </Descriptions.Item>
              <Descriptions.Item label="Phone">
                {(patient as any).phone || (
                  <Text type="secondary">On file</Text>
                )}
              </Descriptions.Item>
              <Descriptions.Item label="Email">
                {(patient as any).email || (
                  <Text type="secondary">On file</Text>
                )}
              </Descriptions.Item>
            </Descriptions>

            <Alert
              type="info"
              showIcon
              icon={<InfoCircleOutlined />}
              message="Need to update your information?"
              description="Contact the front desk during your next visit or call the registration desk to update your address, phone, email, or emergency contact."
              style={{ marginTop: 16 }}
            />
          </Card>

          {/* Consent Management Card */}
          <Card
            className="portal-card"
            id="consent"
            title={
              <span>
                <SafetyCertificateOutlined style={{ marginRight: 6 }} />
                Consent Management
              </span>
            }
          >
            <Paragraph type="secondary" style={{ marginBottom: 16 }}>
              Control whether your imaging results and orders are visible in this
              portal. Withdrawing consent will hide your reports and orders from
              view — you can re-grant consent at any time.
            </Paragraph>

            {/* Results consent */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                padding: "12px 16px",
                borderRadius: 8,
                border: "1px solid var(--border-color)",
                marginBottom: 12,
              }}
            >
              <div>
                <Text strong>Share imaging results via portal</Text>
                <br />
                <Text type="secondary" style={{ fontSize: 13 }}>
                  {consentResults
                    ? "Your signed reports are visible in the portal"
                    : "Your reports are hidden from the portal"}
                </Text>
              </div>
              <Switch
                checked={consentResults}
                onChange={handleConsentToggle}
                loading={consentLoading}
                checkedChildren="ON"
                unCheckedChildren="OFF"
              />
            </div>

            {/* Appointments consent — always on for scheduled patients */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                padding: "12px 16px",
                borderRadius: 8,
                border: "1px solid var(--border-color)",
                marginBottom: 12,
              }}
            >
              <div>
                <Text strong>Show appointment details</Text>
                <br />
                <Text type="secondary" style={{ fontSize: 13 }}>
                  View your upcoming and past appointments
                </Text>
              </div>
              <Switch defaultChecked disabled checkedChildren="ON" unCheckedChildren="OFF" />
            </div>

            <Divider style={{ margin: "16px 0" }} />

            <Alert
              type="warning"
              showIcon
              message="What happens when you withdraw consent?"
              description={
                <ul style={{ margin: 0, paddingLeft: 16 }}>
                  <li>Your signed reports will no longer appear in the portal</li>
                  <li>Your orders may become hidden</li>
                  <li>You can re-grant consent at any time from this page</li>
                  <li>Your healthcare team can still access your records</li>
                </ul>
              }
            />
          </Card>

          {/* Consent Withdrawal Confirmation Modal */}
          <Modal
            title="Withdraw Consent for Results Sharing"
            open={consentModalOpen}
            onOk={confirmConsentWithdrawal}
            onCancel={() => {
              setConsentModalOpen(false);
              setConsentReason("");
            }}
            okText="Yes, Withdraw Consent"
            okButtonProps={{ danger: true }}
            cancelText="Cancel"
          >
            <Paragraph>
              Are you sure you want to withdraw consent for sharing your imaging
              results via this portal?
            </Paragraph>
            <Paragraph type="secondary">
              Your signed reports and orders will no longer be visible here. You
              can re-grant consent at any time.
            </Paragraph>
            <Input.TextArea
              placeholder="Reason for withdrawal (optional — for audit trail)"
              value={consentReason}
              onChange={(e) => setConsentReason(e.target.value)}
              rows={3}
            />
          </Modal>
        </>
      ) : (
        <Card>
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description="No patient record found."
          />
        </Card>
      )}
    </Content>
  );
}

export default withSidebar(PatientProfile);
