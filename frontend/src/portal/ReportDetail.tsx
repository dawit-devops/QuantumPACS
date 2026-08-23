import { useDocumentTitle, useTenantRefetch } from "../hooks";
import React, { useCallback, useEffect, useRef, useState } from "react";
import {
  App,
  Layout,
  Card,
  Typography,
  Button,
  Spin,
  Alert,
  Tag,
  Divider,
  Empty,
} from "antd";
import {
  FileTextOutlined,
  ArrowLeftOutlined,
  CheckCircleOutlined,
  SafetyCertificateOutlined,
} from "@ant-design/icons";
import { useNavigate, useParams } from "react-router";
import withSidebar from "../common/base";
import { PageState } from "../common/PageState";
import { useAuth } from "../auth/AuthContext";
import {
  listScope,
  getPortalReport,
  type PortalScope,
} from "../api/portal";
import "./Portal.css";

const { Text, Paragraph } = Typography;
const Content = Layout.Content;

// Extended report type — backend returns fields not in the base PortalReport
// interface (findings, recommendations, signed_by).
interface PortalReportDetail {
  report_id?: string;
  id?: string;
  exam_id?: string;
  accession_number?: string;
  modality?: string;
  requested_procedure_desc?: string;
  findings?: string;
  finding?: string;
  impression?: string;
  recommendations?: string;
  signed_by?: string;
  signed_at?: string;
  status?: string;
}

// Report detail page — shows full report content for a signed (final) report.
// Handles: scope loading, report fetching, consent gate, HIM hold, 404.
function ReportDetail() {
  const { message } = App.useApp();
  useDocumentTitle("QuantumPACS - Report Detail");
  const navigate = useNavigate();
  const { reportId } = useParams<{ reportId: string }>();
  const { user } = useAuth();
  const tenantName = user?.tenant_name || "Imaging Services";

  const [scope, setScope] = useState<PortalScope[]>([]);
  const [loadingScope, setLoadingScope] = useState(true);
  const [activePatientId, setActivePatientId] = useState<string | null>(null);
  const [report, setReport] = useState<PortalReportDetail | null>(null);
  const [loadingReport, setLoadingReport] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notFound, setNotFound] = useState(false);

  const loadScope = useCallback(() => {
    setLoadingScope(true);
    setError(null);
    listScope()
      .then((rows) => {
        setScope(rows);
        if (rows.length > 0) setActivePatientId(rows[0].patient_id);
        else setActivePatientId(null);
      })
      .catch((e: any) => setError(e.message || "Failed to load report"))
      .finally(() => setLoadingScope(false));
  }, []);

  useEffect(() => {
    loadScope();
  }, [loadScope]);

  useTenantRefetch(loadScope);

  // Fetch report when we have both patientId and reportId
  const reportSeq = useRef(0);
  const loadReport = useCallback(
    (patientId: string, rptId: string) => {
      const seq = ++reportSeq.current;
      setLoadingReport(true);
      setError(null);
      setReport(null);
      setNotFound(false);
      getPortalReport(patientId, rptId)
        .then((r) => {
          if (seq !== reportSeq.current) return;
          if (!r) {
            setNotFound(true);
          } else {
            setReport(r as PortalReportDetail);
          }
        })
        .catch((e: any) => {
          if (seq === reportSeq.current) {
            if (e?.status === 404) {
              setNotFound(true);
            } else {
              setError(e.message || "Failed to load report");
            }
          }
        })
        .finally(() => {
          if (seq === reportSeq.current) setLoadingReport(false);
        });
    },
    [],
  );

  useEffect(() => {
    if (activePatientId && reportId) {
      loadReport(activePatientId, reportId);
    }
  }, [activePatientId, reportId, loadReport]);

  const isLoading = loadingScope || loadingReport;
  const findings = report?.findings || report?.finding || "";
  const impression = report?.impression || "";
  const recommendations = report?.recommendations || "";

  // --- Loading state ---
  if (isLoading) {
    return (
      <Content className="portal-home">
        <div className="portal-loading">
          <Spin size="large" />
        </div>
      </Content>
    );
  }

  // --- Error state ---
  if (error) {
    return (
      <Content className="portal-home">
        <div className="portal-home-header">
          <h2 style={{ margin: 0 }}>
            <FileTextOutlined style={{ marginRight: 8 }} />
            Report Detail
          </h2>
          <Button onClick={() => navigate("/portal/results")}>
            <ArrowLeftOutlined /> Back to Results
          </Button>
        </div>
        <Alert
          type="error"
          title="Failed to load report"
          description={error}
          showIcon
          action={
            <Button size="small" onClick={() => activePatientId && reportId && loadReport(activePatientId, reportId)}>
              Retry
            </Button>
          }
        />
      </Content>
    );
  }

  // --- No scope / empty ---
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

  // --- Not found (404 or HIM-held) ---
  if (notFound) {
    return (
      <Content className="portal-home">
        <div className="portal-home-header">
          <h2 style={{ margin: 0 }}>
            <FileTextOutlined style={{ marginRight: 8 }} />
            Report Detail
          </h2>
          <Button onClick={() => navigate("/portal/results")}>
            <ArrowLeftOutlined /> Back to Results
          </Button>
        </div>
        <Alert
          type="warning"
          title="Report not found"
          description="This report may have been held by the medical records department, or you may not have access to view it. Contact your healthcare provider for more information."
          showIcon
        />
      </Content>
    );
  }

  // --- Report loaded ---
  return (
    <Content className="portal-home" role="main">
      {/* Toolbar */}
      <div className="portal-home-header portal-report-toolbar">
        <div>
          <h2 style={{ margin: 0 }}>
            <FileTextOutlined style={{ marginRight: 8 }} />
            Imaging Report
          </h2>
        </div>
        <Button onClick={() => navigate("/portal/results")}>
          <ArrowLeftOutlined /> Back to Results
        </Button>
      </div>

      {/* Branded letterhead + report body in one card */}
      <Card className="portal-report-sheet" bodyStyle={{ padding: 0 }}>
        {/* ── Letterhead: tenant + platform branding ── */}
        <div className="portal-report-letterhead">
          <div className="portal-report-brand">
            <svg
              width="34"
              height="34"
              viewBox="0 0 40 40"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
              aria-hidden="true"
            >
              <defs>
                <linearGradient id="portal-qp-grad" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor="var(--color-primary)" />
                  <stop offset="50%" stopColor="var(--color-secondary)" />
                  <stop offset="100%" stopColor="var(--color-accent)" />
                </linearGradient>
              </defs>
              <circle cx="20" cy="20" r="18" fill="url(#portal-qp-grad)" />
              <path
                d="M13 13a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H15a2 2 0 0 1-2-2V13Zm6 3a2 2 0 1 0 0-4 2 2 0 0 0 0 4Zm5 2h-8a1 1 0 0 0 0 2h8a1 1 0 0 0 0-2Zm0 4h-8a1 1 0 0 0 0 2h8a1 1 0 0 0 0-2Z"
                fill="#fff"
                opacity="0.92"
              />
            </svg>
            <div className="portal-report-brand-text">
              <span className="portal-report-brand-name">
                Quantum<strong>PACS</strong>
              </span>
              <span className="portal-report-brand-sub">Radiology Report</span>
            </div>
          </div>

          <div className="portal-report-tenant">
            <span className="portal-report-tenant-label">Issued by</span>
            <span className="portal-report-tenant-name">{tenantName}</span>
            <span className="portal-report-tenant-secure">
              <SafetyCertificateOutlined /> Confidential — patient records
            </span>
          </div>
        </div>

        {/* ── Divider with watermark ── */}
        <div className="portal-report-rule" />

        {/* ── Document title ── */}
        <div className="portal-report-title">
          <h3>Final Imaging Report</h3>
          <div className="portal-report-title-meta">
            <Tag color="green" icon={<CheckCircleOutlined />}>Signed</Tag>
            <span>{report?.requested_procedure_desc || "Imaging study"}</span>
          </div>
        </div>

        {/* ── Metadata grid ── */}
        <div className="portal-report-meta-grid">
          <div className="portal-report-meta-cell">
            <span className="portal-report-meta-label">Accession No.</span>
            <span className="portal-report-meta-value">
              {report?.accession_number || "—"}
            </span>
          </div>
          <div className="portal-report-meta-cell">
            <span className="portal-report-meta-label">Modality</span>
            <span className="portal-report-meta-value">
              {report?.modality || "—"}
            </span>
          </div>
          <div className="portal-report-meta-cell">
            <span className="portal-report-meta-label">Signed Date</span>
            <span className="portal-report-meta-value">
              {report?.signed_at
                ? new Date(report.signed_at).toLocaleDateString(undefined, {
                    year: "numeric",
                    month: "short",
                    day: "numeric",
                  })
                : "—"}
            </span>
          </div>
          <div className="portal-report-meta-cell">
            <span className="portal-report-meta-label">Reading Radiologist</span>
            <span className="portal-report-meta-value">
              {report?.signed_by || "—"}
            </span>
          </div>
        </div>

        <Divider style={{ margin: "18px 0" }} />

        {/* ── Body sections ── */}
        <div className="portal-report-body-wrap">
          <div className="portal-report-section">
            <div className="portal-report-section-head">
              <span className="portal-report-section-mark">FINDINGS</span>
            </div>
            {findings ? (
              <Paragraph className="portal-report-body">{findings}</Paragraph>
            ) : (
              <Text type="secondary">No findings documented.</Text>
            )}
          </div>

          <div className="portal-report-section">
            <div className="portal-report-section-head">
              <span className="portal-report-section-mark portal-report-section-mark-accent">
                IMPRESSION
              </span>
            </div>
            {impression ? (
              <Paragraph className="portal-report-body portal-report-impression">
                {impression}
              </Paragraph>
            ) : (
              <Text type="secondary">No impression documented.</Text>
            )}
          </div>

          {recommendations ? (
            <div className="portal-report-section">
              <div className="portal-report-section-head">
                <span className="portal-report-section-mark">RECOMMENDATIONS</span>
              </div>
              <Paragraph className="portal-report-body">
                {recommendations}
              </Paragraph>
            </div>
          ) : null}
        </div>

        {/* ── Footer ── */}
        <div className="portal-report-footer">
          <Text type="secondary" style={{ fontSize: 12 }}>
            This report was signed by the reading radiologist and represents the
            final interpretation of your imaging study.
          </Text>
          <Text type="secondary" style={{ fontSize: 12 }}>
            If you have questions, contact your ordering physician or the
            radiology department.
          </Text>
        </div>
      </Card>
    </Content>
  );
}

export default withSidebar(ReportDetail);
