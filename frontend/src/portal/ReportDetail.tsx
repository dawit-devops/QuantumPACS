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
  Empty,
} from "antd";
import {
  FileTextOutlined,
  ArrowLeftOutlined,
} from "@ant-design/icons";
import { useNavigate, useParams } from "react-router";
import withSidebar from "../common/base";
import { PageState } from "../common/PageState";
import ReportDocument from "../common/ReportDocument";
import {
  listScope,
  getPortalReport,
  type PortalScope,
} from "../api/portal";
import "./Portal.css";

const { Text, Paragraph } = Typography;
const Content = Layout.Content;

// Extended report type — the backend report detail carries the exam's
// patient/demographics/referral fields for the ACR-style letterhead.
interface PortalReportDetail {
  report_id?: string;
  id?: string;
  exam_id?: string;
  accession_number?: string;
  modality?: string;
  requested_procedure_desc?: string;
  patient_name?: string;
  patient_birth_date?: string;
  patient_sex?: string;
  referring_physician?: string;
  priority?: string;
  protocol_name?: string;
  findings?: string;
  finding?: string;
  impression?: string;
  recommendations?: string;
  signed_by?: string;
  signed_by_name?: string;
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

      {/* Branded report document — design-system REPORT-TEMPLATE.html */}
      <ReportDocument
        meta={{
          patient_name: report?.patient_name,
          patient_id: report?.exam_id,
          patient_birth_date: report?.patient_birth_date,
          patient_sex: report?.patient_sex,
          accession_number: report?.accession_number,
          modality: report?.modality,
          requested_procedure_desc: report?.requested_procedure_desc,
          referring_physician: report?.referring_physician,
          priority: report?.priority,
          protocol_name: report?.protocol_name,
        }}
        findings={findings}
        impression={impression}
        recommendations={recommendations}
        signedBy={report?.signed_by_name || report?.signed_by}
        signedAt={report?.signed_at}
      />
    </Content>
  );
}

export default withSidebar(ReportDetail);
