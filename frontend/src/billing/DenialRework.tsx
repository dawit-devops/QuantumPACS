import { useDocumentTitle } from "../hooks";
import React, { useState, useCallback, useEffect } from "react";
import {
  App,
  Layout,
  Table,
  Tag,
  Button,
  Space,
  Input,
  Modal,
  Drawer,
  Timeline,
  Alert,
} from "antd";
import { ReloadOutlined } from "@ant-design/icons";
import withSidebar from "../common/base";
import { PageState } from "../common/PageState";
import {
  listDenialRework,
  resubmitClaim,
  getClaimHistory,
  type DenialReworkRow,
  type ClaimEvent,
} from "../api/billing-ris";
import "./BillingQueue.css";

const Content = Layout.Content;

// R2-02-02: denial rework queue — denied/resubmitted claims grouped by
// payer reason code; the coder corrects and pushes the claim back into
// the submission cycle. Every action is attributable via claim history.
function DenialRework() {
  const { message } = App.useApp();
  useDocumentTitle("QuantumPACS - Denial Rework");
  const [rows, setRows] = useState<DenialReworkRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [reworkTarget, setReworkTarget] = useState<DenialReworkRow | null>(null);
  const [note, setNote] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [historyFor, setHistoryFor] = useState<DenialReworkRow | null>(null);
  const [history, setHistory] = useState<ClaimEvent[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);

  const fetchRows = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setRows(await listDenialRework());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load denials");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchRows();
  }, [fetchRows]);

  const openRework = (row: DenialReworkRow) => {
    setNote("");
    setReworkTarget(row);
  };

  const submitRework = async () => {
    if (!reworkTarget) return;
    setSubmitting(true);
    try {
      await resubmitClaim(reworkTarget.id, { note });
      message.success("Claim corrected and resubmitted");
      setReworkTarget(null);
      fetchRows();
    } catch (e) {
      message.error(e instanceof Error ? e.message : "Resubmit failed");
    } finally {
      setSubmitting(false);
    }
  };

  const openHistory = async (row: DenialReworkRow) => {
    setHistoryFor(row);
    setHistoryLoading(true);
    try {
      setHistory(await getClaimHistory(row.id));
    } catch {
      setHistory([]);
    } finally {
      setHistoryLoading(false);
    }
  };

  const columns = [
    {
      title: "Patient",
      dataIndex: "patient_name",
      render: (v: string, row: DenialReworkRow) => (
        <Space vertical size={0}>
          <span>{v || "—"}</span>
          <span style={{ fontSize: 12, color: "#888" }}>
            {row.accession_number}
          </span>
        </Space>
      ),
    },
    { title: "CPT", dataIndex: "cpt_code", width: 90 },
    {
      title: "Payer",
      dataIndex: "payer_name",
      render: (v: string) => v || "—",
    },
    {
      title: "Reason",
      dataIndex: "rejection_code",
      render: (code: string, row: DenialReworkRow) => (
        <Space vertical size={0}>
          <Tag color="red">{code || "—"}</Tag>
          <span style={{ fontSize: 12 }}>{row.rejection_reason}</span>
        </Space>
      ),
    },
    {
      title: "Auth #",
      dataIndex: "prior_auth_number",
      width: 120,
      render: (v?: string) =>
        v ? <Tag color="blue">{v}</Tag> : <span style={{ color: "#bbb" }}>—</span>,
    },
    {
      title: "Corrections",
      dataIndex: "correction_count",
      width: 110,
      align: "right" as const,
    },
    {
      title: "Actions",
      key: "actions",
      width: 180,
      render: (_: unknown, row: DenialReworkRow) => (
        <Space>
          <Button size="small" onClick={() => openRework(row)}>
            Rework
          </Button>
          <Button size="small" onClick={() => openHistory(row)}>
            History
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <Content style={{ padding: 24 }}>
      <div style={{ marginBottom: 16 }}>
        <h2>Denial Rework</h2>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={fetchRows}>
            Refresh
          </Button>
        </Space>
      </div>
      {error && (
        <Alert type="error" title={error} style={{ marginBottom: 16 }} />
      )}
      <Table
        rowKey="id"
        size="small"
        loading={loading}
        dataSource={rows}
        columns={columns}
        pagination={{ pageSize: 20, showSizeChanger: false }}
        locale={{ emptyText: "No denied claims in the rework queue" }}
      />

      <Modal
        title={`Rework — ${reworkTarget?.claim_number || ""}`}
        open={reworkTarget !== null}
        onOk={submitRework}
        onCancel={() => setReworkTarget(null)}
        okText="Submit"
        confirmLoading={submitting}
      >
        {reworkTarget && (
          <>
            <p>
              <strong>{reworkTarget.rejection_code}</strong>{" "}
              {reworkTarget.rejection_reason}
            </p>
            <Input.TextArea
              role="textbox"
              rows={3}
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="Correction note (required for the audit trail)"
            />
          </>
        )}
      </Modal>

      <Drawer
        title={`History — ${historyFor?.claim_number || ""}`}
        open={historyFor !== null}
        onClose={() => setHistoryFor(null)}
        size={420}
      >
        <PageState loading={historyLoading}>
          <Timeline
            items={history.map((ev) => ({
              children: (
                <>
                  <strong>{ev.event_type}</strong>
                  {ev.note ? ` — ${ev.note}` : ""}
                  {ev.created_at ? (
                    <div style={{ fontSize: 12, color: "#888" }}>
                      {new Date(ev.created_at).toLocaleString()}
                    </div>
                  ) : null}
                </>
              ),
            }))}
          />
        </PageState>
      </Drawer>
    </Content>
  );
}

const DenialReworkPage = withSidebar(DenialRework);
export default DenialReworkPage;
export { DenialRework };
