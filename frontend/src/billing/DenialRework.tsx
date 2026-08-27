import { useDocumentTitle } from "../hooks";
import React, { useState, useCallback, useEffect, useMemo } from "react";
import {
  App,
  Layout,
  Table,
  Tag,
  Button,
  Space,
  Input,
  Select,
  Modal,
  Drawer,
  Timeline,
  Alert,
} from "antd";
import { ReloadOutlined, UploadOutlined } from "@ant-design/icons";
import withSidebar from "../common/base";
import { PageState } from "../common/PageState";
import {
  listDenialRework,
  resubmitClaim,
  getClaimHistory,
  batchResubmitClaims,
  importDenial,
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
  // D3: the rework queue is grouped by denial-code; status/payer filters
  // refine the groups so coders work one root cause at a time.
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [payerFilter, setPayerFilter] = useState("");
  // R2-02-01: 835-style denial intake — record a payer denial on a claim.
  const [importOpen, setImportOpen] = useState(false);
  const [importClaimId, setImportClaimId] = useState("");
  const [importReason, setImportReason] = useState("");
  const [importing, setImporting] = useState(false);

  const filteredRows = useMemo(() => {
    const q = payerFilter.trim().toLowerCase();
    return rows.filter(
      (r) =>
        (statusFilter === "all" || r.status === statusFilter) &&
        (!q || (r.payer_name || "").toLowerCase().includes(q))
    );
  }, [rows, statusFilter, payerFilter]);

  const groups = useMemo(() => {
    const m = new Map<string, DenialReworkRow[]>();
    for (const r of filteredRows) {
      const code = r.rejection_code || "NO CODE";
      m.set(code, [...(m.get(code) || []), r]);
    }
    return [...m.entries()];
  }, [filteredRows]);

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

  // R2-02-01: record a 835-style payer denial on a claim so it enters the
  // rework queue with a reason code (the trail starts at intake).
  const submitImport = async () => {
    if (!importClaimId.trim()) return;
    setImporting(true);
    try {
      const res = await importDenial({
        claim_id: importClaimId.trim(),
        reason: importReason.trim() || undefined,
      });
      message.success(`Denial recorded on claim ${res.id} (${res.code})`);
      setImportOpen(false);
      setImportClaimId("");
      setImportReason("");
      fetchRows();
    } catch (e) {
      message.error(e instanceof Error ? e.message : "Import failed");
    } finally {
      setImporting(false);
    }
  };

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

  // B-10: rework a whole reason-code group with one shared correction note.
  const [batchGroup, setBatchGroup] = useState<{
    code: string;
    ids: string[];
  } | null>(null);
  const [batchSubmitting, setBatchSubmitting] = useState(false);

  const submitBatchRework = async () => {
    if (!batchGroup) return;
    setBatchSubmitting(true);
    try {
      const res = await batchResubmitClaims(batchGroup.ids, note);
      message.success(`Resubmitted ${res.resubmitted.length} claim(s) for ${batchGroup.code}`);
      setBatchGroup(null);
      setNote("");
      fetchRows();
    } catch (e) {
      message.error(e instanceof Error ? e.message : "Batch resubmit failed");
    } finally {
      setBatchSubmitting(false);
    }
  };

  const columns = [
    {
      title: "Patient",
      dataIndex: "patient_name",
      render: (v: string, row: DenialReworkRow) => (
        <Space vertical size={0}>
          <span>{v || "—"}</span>
          <span style={{ fontSize: 12, color: "#888" }}>{row.accession_number}</span>
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
          <Button
            type="primary"
            ghost
            icon={<UploadOutlined />}
            onClick={() => {
              setImportClaimId("");
              setImportReason("");
              setImportOpen(true);
            }}
          >
            Import Denial
          </Button>
        </Space>
      </div>
      {error && <Alert type="error" title={error} style={{ marginBottom: 16 }} />}
      <Space style={{ marginBottom: 16 }} wrap>
        <Select
          aria-label="Filter by status"
          value={statusFilter}
          onChange={setStatusFilter}
          style={{ width: 160 }}
          options={[
            { value: "all", label: "All statuses" },
            { value: "DENIED", label: "Denied" },
            { value: "RESUBMITTED", label: "Resubmitted" },
          ]}
        />
        <Input
          aria-label="Filter by payer"
          placeholder="Filter by payer"
          allowClear
          value={payerFilter}
          onChange={(e) => setPayerFilter(e.target.value)}
          style={{ width: 200 }}
        />
      </Space>
      {groups.length === 0 ? (
        <Table
          rowKey="id"
          size="small"
          loading={loading}
          dataSource={[]}
          columns={columns}
          pagination={false}
          locale={{ emptyText: "No denied claims match the filters" }}
        />
      ) : (
        groups.map(([code, groupRows]) => (
          <div key={code} style={{ marginBottom: 24 }}>
            <Space size="small" style={{ marginBottom: 8 }}>
              <h3 style={{ margin: 0 }}>{code}</h3>
              <Button
                size="small"
                aria-label={`Rework all for ${code}`}
                onClick={() =>
                  setBatchGroup({
                    code,
                    ids: groupRows.map((r) => r.id),
                  })
                }
              >
                Rework all ({groupRows.length})
              </Button>
            </Space>
            <Table
              rowKey="id"
              size="small"
              loading={loading}
              dataSource={groupRows}
              columns={columns}
              pagination={{ pageSize: 20, showSizeChanger: false }}
            />
          </div>
        ))
      )}

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
              <strong>{reworkTarget.rejection_code}</strong> {reworkTarget.rejection_reason}
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

      {/* R2-02-01: 835-style denial intake */}
      <Modal
        title="Import Denial"
        open={importOpen}
        onOk={submitImport}
        onCancel={() => setImportOpen(false)}
        okText="Record denial"
        confirmLoading={importing}
        okButtonProps={{ disabled: !importClaimId.trim() }}
      >
        <p>
          Records a payer denial on an existing claim (835-style intake). The claim enters the
          rework queue with a reason code.
        </p>
        <Space direction="vertical" style={{ width: "100%" }}>
          <Input
            aria-label="Claim ID"
            placeholder="Claim ID (required)"
            value={importClaimId}
            onChange={(e) => setImportClaimId(e.target.value)}
          />
          <Input.TextArea
            role="textbox"
            rows={2}
            value={importReason}
            onChange={(e) => setImportReason(e.target.value)}
            placeholder="Payer reason / note (optional)"
          />
        </Space>
      </Modal>

      {/* B-10: shared correction note for the whole reason-code group. */}
      <Modal
        title={`Batch rework — ${batchGroup?.code || ""}`}
        open={batchGroup !== null}
        onOk={submitBatchRework}
        onCancel={() => setBatchGroup(null)}
        okText={`Resubmit ${batchGroup?.ids.length ?? 0} claim(s)`}
        confirmLoading={batchSubmitting}
        okButtonProps={{ disabled: !note.trim() }}
      >
        <p>
          Applies one correction note to {batchGroup?.ids.length ?? 0} denied claims and resubmits
          them all.
        </p>
        <Input.TextArea
          role="textbox"
          rows={3}
          value={note}
          onChange={(e) => setNote(e.target.value)}
          placeholder="Shared correction note (required for the audit trail)"
        />
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
