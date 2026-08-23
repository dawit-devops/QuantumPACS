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
  Descriptions,
  Divider,
  Space,
  Empty,
} from "antd";
import {
  FileTextOutlined,
  ArrowLeftOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
} from "@ant-design/icons";
import { useNavigate, useParams } from "react-router";
import withSidebar from "../common/base";
import { PageState } from "../common/PageState";
import {
  listScope,
  getPortalReport,
  type PortalScope,
} from "../api/portal";
import "./Portal.css";

const { Title, Text, Paragraph } = Typography;
const Content = Layout.Content;

// Extended report type — backend returns fields not in the base PortalReport
// interface (findings, recommendations, signed_by).
interface PortalReportDetail {
  report_id?: string;
  id?: string;
  exam_id?: string;
  accession_number?: string;
  modality?: string;
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
      {/* Header */}
      <div className="portal-home-header">
        <div>
          <h2 style={{ margin: 0 }}>
            <FileTextOutlined style={{ marginRight: 8 }} />
            Imaging Report
          </h2>
          <Text type="secondary">
            {report?.accession_number
              ? `Accession ${report.accession_number}`
              : ""}
            {report?.modality ? ` · ${report.modality}` : ""}
          </Text>
        </div>
        <Button onClick={() => navigate("/portal/results")}>
          <ArrowLeftOutlined /> Back to Results
        </Button>
      </div>

      {/* Report metadata */}
      <Card className="portal-card" style={{ marginBottom: 16 }}>
        <Descriptions column={{ xs: 1, sm: 2, md: 3 }} size="small">
          <Descriptions.Item label="Accession Number">
            <Text strong>{report?.accession_number || "—"}</Text>
          </Descriptions.Item>
          <Descriptions.Item label="Modality">
            {report?.modality ? <Tag>{report.modality}</Tag> : "—"}
          </Descriptions.Item>
          <Descriptions.Item label="Status">
            <Tag color="green" icon={<CheckCircleOutlined />}>
              Signed
            </Tag>
          </Descriptions.Item>
          <Descriptions.Item label="Signed Date">
            {report?.signed_at
              ? new Date(report.signed_at).toLocaleString()
              : "—"}
          </Descriptions.Item>
          <Descriptions.Item label="Signed By">
            {report?.signed_by || "—"}
          </Descriptions.Item>
          <Descriptions.Item label="Report ID">
            <Text type="secondary" style={{ fontSize: 12 }}>
              {reportId || "—"}
            </Text>
          </Descriptions.Item>
        </Descriptions>
      </Card>

      {/* Findings */}
      <Card
        className="portal-card"
        style={{ marginBottom: 16 }}
        title={
          <span>
            <FileTextOutlined style={{ marginRight: 6 }} />
            Findings
          </span>
        }
      >
        {findings ? (
          <Paragraph style={{ whiteSpace: "pre-wrap", margin: 0, lineHeight: 1.8 }}>
            {findings}
          </Paragraph>
        ) : (
          <Text type="secondary">No findings documented.</Text>
        )}
      </Card>

      {/* Impression */}
      <Card
        className="portal-card"
        style={{ marginBottom: 16 }}
        title={
          <span>
            <CheckCircleOutlined style={{ marginRight: 6 }} />
            Impression
          </span>
        }
      >
        {impression ? (
          <Paragraph
            style={{
              whiteSpace: "pre-wrap",
              margin: 0,
              lineHeight: 1.8,
              fontWeight: 500,
            }}
          >
            {impression}
          </Paragraph>
        ) : (
          <Text type="secondary">No impression documented.</Text>
        )}
      </Card>

      {/* Recommendations */}
      {recommendations ? (
        <Card
          className="portal-card"
          style={{ marginBottom: 16 }}
          title={
            <span>
              <ClockCircleOutlined style={{ marginRight: 6 }} />
              Recommendations
            </span>
          }
        >
          <Paragraph style={{ whiteSpace: "pre-wrap", margin: 0, lineHeight: 1.8 }}>
            {recommendations}
          </Paragraph>
        </Card>
      ) : null}

      {/* Footer note */}
      <Divider />
      <Space direction="vertical" size={4}>
        <Text type="secondary" style={{ fontSize: 12 }}>
          This report was signed by the reading radiologist and represents the
          final interpretation of your imaging study.
        </Text>
        <Text type="secondary" style={{ fontSize: 12 }}>
          If you have questions about this report, please contact your ordering
          physician or the radiology department.
        </Text>
      </Space>
    </Content>
  );
}

export default withSidebar(ReportDetail);
