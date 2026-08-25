import { useDocumentTitle } from "../hooks";
import React, { useState, useEffect } from "react";
import { Layout, Table, Tag, Button } from "antd";
import { useNavigate } from "react-router";
import { ArrowRightOutlined } from "@ant-design/icons";
import withSidebar from "../common/base";
import PageHeader from "../common/PageHeader";
import { PageState } from "../common/PageState";
import { getPrepList, type PrepListRow } from "../api/nursing";
import { EXAM_PRIORITY_COLORS, EXAM_STATUS_COLORS } from "../common/statusColors";

const Content = Layout.Content;

// §2.11: nursing's entry queue — exams currently awaiting prep. The spec
// keeps nursing minimal ("linked from exam console"): rows deep-link into
// the exam console where the NursingPanel does the actual charting.
function NursingPrepList() {
  useDocumentTitle("QuantumPACS - Nursing Prep");
  const navigate = useNavigate();
  const [rows, setRows] = useState<PrepListRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    getPrepList()
      .then((data) => {
        if (!alive) return;
        setRows(data);
        setLoading(false);
      })
      .catch((e: any) => {
        if (!alive) return;
        setError(e.message);
        setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, []);

  const columns = [
    {
      title: "Patient",
      dataIndex: "patient_name",
      render: (name: string | undefined, r: PrepListRow) => name || r.patient_id || "—",
    },
    { title: "Modality", dataIndex: "modality", width: 100 },
    {
      title: "Priority",
      dataIndex: "priority",
      width: 100,
      render: (p?: string) =>
        p ? (
          <Tag color={EXAM_PRIORITY_COLORS[p] || "default"}>{String(p).toUpperCase()}</Tag>
        ) : null,
    },
    {
      title: "Exam status",
      dataIndex: "status",
      width: 120,
      render: (s?: string) =>
        s ? <Tag color={EXAM_STATUS_COLORS[s] || "default"}>{s.toUpperCase()}</Tag> : null,
    },
    {
      title: "Pre-procedure checklist",
      key: "checklist",
      render: (_: unknown, r: PrepListRow) => {
        if (!r.checklist_id) return <Tag>Not started</Tag>;
        if (r.checklist_status === "complete") return <Tag color="success">CONFIRMED</Tag>;
        const checked = r.checked_count ?? 0;
        const required = r.required_count ?? 0;
        return (
          <Tag color={required > 0 && checked >= required ? "processing" : "warning"}>
            {checked}/{required || "?"} REQUIRED CHECKED
          </Tag>
        );
      },
    },
    {
      title: "",
      key: "open",
      width: 140,
      render: (_: unknown, r: PrepListRow) => (
        <Button
          size="small"
          icon={<ArrowRightOutlined />}
          onClick={() => navigate(`/exams/${r.exam_id}`)}
          aria-label={`Open exam console for ${r.patient_name || r.patient_id}`}
        >
          Open console
        </Button>
      ),
    },
  ];

  return (
    <Content style={{ padding: 24 }}>
      <PageHeader
        title="Nursing Prep"
        description="Exams awaiting pre-procedure preparation — vitals, checklist and contrast consent live in each exam console."
      />
      <PageState
        error={error}
        onRetry={() => window.location.reload()}
        empty={!loading && !error && rows.length === 0}
        emptyMessage="No exams awaiting preparation"
      >
        <Table
          rowKey="exam_id"
          loading={loading}
          dataSource={rows}
          columns={columns}
          pagination={false}
        />
      </PageState>
    </Content>
  );
}

export default withSidebar(NursingPrepList);
