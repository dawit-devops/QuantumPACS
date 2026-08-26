import { useDocumentTitle, useTenantRefetch } from "../hooks";
import React, { useCallback, useEffect, useRef, useState } from "react";
import { App, Layout, Card, Table, Tag, Button, Alert, Empty, Typography, Space } from "antd";
import { FileTextOutlined, CheckCircleOutlined, ArrowLeftOutlined } from "@ant-design/icons";
import { useNavigate } from "react-router";
import withSidebar from "../common/base";
import { PageState } from "../common/PageState";
import { listScope, getPortalPatient, type PortalScope, type PortalReport } from "../api/portal";
import "./Portal.css";

const { Text } = Typography;
const Content = Layout.Content;

const REPORT_STATUS_COLORS: Record<string, string> = {
  signed: "green",
  final: "green",
  preliminary: "orange",
  draft: "default",
};

function ReportList() {
  const { message } = App.useApp();
  useDocumentTitle("QuantumPACS - Results");
  const navigate = useNavigate();

  const [scope, setScope] = useState<PortalScope[]>([]);
  const [loadingScope, setLoadingScope] = useState(true);
  const [activePatientId, setActivePatientId] = useState<string | null>(null);
  const [reports, setReports] = useState<PortalReport[]>([]);
  const [loading, setLoading] = useState(false);
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
      .catch((e: any) => setError(e.message || "Failed to load results"))
      .finally(() => setLoadingScope(false));
  }, []);

  useEffect(() => {
    loadScope();
  }, [loadScope]);

  useTenantRefetch(loadScope);

  const patientSeq = useRef(0);
  const loadReports = useCallback((patientId: string) => {
    const seq = ++patientSeq.current;
    setLoading(true);
    setError(null);
    setReports([]);
    getPortalPatient(patientId)
      .then((b) => {
        if (seq !== patientSeq.current) return;
        // Only show final/signed reports (consent-gated by backend)
        const signed = (b?.reports || []).filter(
          (r) => r.status === "signed" || r.status === "final"
        );
        setReports(signed);
      })
      .catch((e: any) => {
        if (seq === patientSeq.current) {
          setError(e.message || "Failed to load results");
        }
      })
      .finally(() => {
        if (seq === patientSeq.current) setLoading(false);
      });
  }, []);

  useEffect(() => {
    if (activePatientId) loadReports(activePatientId);
  }, [activePatientId, loadReports]);

  const columns = [
    {
      title: "Accession #",
      dataIndex: "accession_number",
      key: "accession",
      width: 140,
      render: (v: string) => <Text strong>{v || "—"}</Text>,
    },
    {
      title: "Modality",
      dataIndex: "modality",
      key: "modality",
      width: 90,
      render: (v: string) => (v ? <Tag>{v}</Tag> : "—"),
    },
    {
      title: "Body Part",
      dataIndex: "body_part",
      key: "body_part",
      width: 120,
      render: (v: string) => v || <Text type="secondary">—</Text>,
    },
    {
      title: "Status",
      dataIndex: "status",
      key: "status",
      width: 110,
      render: (v: string) => (
        <Tag
          color={REPORT_STATUS_COLORS[v] || "default"}
          icon={v === "signed" || v === "final" ? <CheckCircleOutlined /> : undefined}
        >
          {v || "draft"}
        </Tag>
      ),
    },
    {
      title: "Impression",
      dataIndex: "impression",
      key: "impression",
      ellipsis: true,
      render: (v: string) => v || <Text type="secondary">—</Text>,
    },
    {
      title: "Signed By",
      dataIndex: "signed_by_name",
      key: "signed_by_name",
      width: 140,
      render: (v: string) => v || <Text type="secondary">—</Text>,
    },
    {
      title: "Signed Date",
      dataIndex: "signed_at",
      key: "signed_at",
      width: 140,
      render: (v: string) => (v ? new Date(v).toLocaleDateString() : "—"),
    },
    {
      title: "",
      key: "action",
      width: 80,
      render: (_: any, r: PortalReport) => (
        <Button
          type="link"
          size="small"
          onClick={() => navigate(`/portal/results/${r.id || r.exam_id}`)}
        >
          View
        </Button>
      ),
    },
  ];

  return (
    <Content className="portal-home" role="main">
      <div className="portal-home-header">
        <div>
          <h2 style={{ margin: 0 }}>
            <FileTextOutlined style={{ marginRight: 8 }} />
            Results
          </h2>
          <Text type="secondary">Your signed imaging reports</Text>
        </div>
        <Button onClick={() => navigate("/portal")}>
          <ArrowLeftOutlined /> Back to Portal
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

      <Card className="portal-card">
        <PageState
          loading={loading}
          error={null}
          empty={!loading && reports.length === 0}
          emptyMessage="No signed reports available yet"
        >
          <Table
            rowKey="id"
            columns={columns}
            dataSource={reports}
            pagination={{
              pageSize: 10,
              showSizeChanger: false,
              showTotal: (t) => `${t} report${t !== 1 ? "s" : ""}`,
            }}
            size="small"
          />
        </PageState>
      </Card>
    </Content>
  );
}

export default withSidebar(ReportList);
