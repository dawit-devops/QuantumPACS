import { useDocumentTitle } from "../hooks";
import React, { useState, useEffect, useCallback } from "react";
import { App, Layout, Table, Tag, Button, Space, Input, Alert } from "antd";
import { ReloadOutlined, DollarOutlined } from "@ant-design/icons";
import withSidebar from "../common/base";
import { PageState } from "../common/PageState";
import {
  listBillingQueue,
  dropCharge,
  getCptSuggestions,
  batchDropCharges,
  type BillingQueueEntry,
  type CptSuggestion,
} from "../api/billing-ris";
import "./BillingQueue.css";

const Content = Layout.Content;

// S11-11: billing queue — signed-but-unbilled charges the coder reviews,
// confirms the suggested CPT/ICD-10 coding, and drops to billing. Refresh
// cadence mirrors the tracking board (30s) so new sign-offs appear promptly.
const REFRESH_MS = 30000;

function BillingQueue() {
  const { message } = App.useApp();
  useDocumentTitle("QuantumPACS - Billing Queue");
  const [data, setData] = useState<BillingQueueEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pagination, setPagination] = useState({
    current: 1,
    pageSize: 20,
    total: 0,
  });
  const [suggestions, setSuggestions] = useState<Record<string, CptSuggestion>>({});
  const [editing, setEditing] = useState<Record<string, string>>({});
  // B-05: batch confirm-and-drop selection.
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);
  const [batchDropping, setBatchDropping] = useState(false);

  const fetch = useCallback(() => {
    setLoading(true);
    setError(null);
    listBillingQueue({ page: String(pagination.current), per_page: String(pagination.pageSize) })
      .then((res) => {
        setLoading(false);
        setData(res.data);
        setPagination((prev) => ({ ...prev, total: res.total }));
      })
      .catch((e: any) => {
        setLoading(false);
        setError(e.message);
        message.error(e.message);
      });
  }, [pagination.current, pagination.pageSize, message]);

  useEffect(() => {
    fetch();
  }, [fetch]);

  // Refresh so new sign-offs show up without a manual reload.
  useEffect(() => {
    const interval = setInterval(fetch, REFRESH_MS);
    return () => clearInterval(interval);
  }, [fetch]);

  const loadSuggestions = async (entry: BillingQueueEntry) => {
    // B-12 fix: the coding map keys on procedure descriptions — pass the
    // charge's resolved CPT description (falls back to accession only when
    // the drop left the description empty).
    const procedureKey = entry.cpt_description || entry.accession_number;
    if (!procedureKey) return;
    const res = await getCptSuggestions(procedureKey).catch(() => ({
      data: [] as CptSuggestion[],
    }));
    if (res.data && res.data.length > 0) {
      setSuggestions((prev) => ({ ...prev, [entry.id]: res.data[0] }));
    }
  };

  const handleDrop = async (entry: BillingQueueEntry) => {
    try {
      await dropCharge(entry.id);
      message.success(`Charge ${entry.cpt_code || "dropped"} confirmed`);
      fetch();
    } catch (e: any) {
      message.error(e.message || "Failed to drop charge");
    }
  };

  // B-05: drop every selected charge in one server round-trip.
  const handleBatchDrop = async () => {
    if (selectedRowKeys.length === 0) return;
    setBatchDropping(true);
    try {
      const res = await batchDropCharges(selectedRowKeys.map(String));
      message.success(
        `Dropped ${res.dropped.length} charge(s)` +
          (res.missing.length ? ` — ${res.missing.length} not found` : "") +
          (res.skipped.length
            ? ` — ${res.skipped.length} skipped (not PENDING)`
            : ""),
      );
      setSelectedRowKeys([]);
      fetch();
    } catch (e: any) {
      message.error(e.message || "Batch drop failed");
    } finally {
      setBatchDropping(false);
    }
  };

  const columns: any[] = [
    {
      title: "Patient",
      dataIndex: "patient_name",
      width: "16%",
      render: (v: string) => v || "-",
    },
    { title: "Patient ID", dataIndex: "patient_id", width: "10%" },
    { title: "Accession #", dataIndex: "accession_number", width: "12%" },
    {
      title: "CPT",
      dataIndex: "cpt_code",
      width: "10%",
      render: (v: string, r: BillingQueueEntry) => (
        <Tag color={v ? "blue" : "default"}>{v || "—"}</Tag>
      ),
    },
    {
      title: "ICD-10",
      dataIndex: "icd10_code",
      width: "10%",
      render: (v: string) => v || "—",
    },
    {
      title: "Amount",
      dataIndex: "charge_amount",
      width: "10%",
      render: (v: number) => (v != null ? `$${Number(v).toFixed(2)}` : "-"),
    },
    {
      title: "Actions",
      key: "actions",
      width: "14%",
      render: (_: any, record: BillingQueueEntry) => (
        <Space size="small">
          <Button
            size="small"
            icon={<DollarOutlined />}
            aria-label="Drop charge"
            onClick={() => handleDrop(record)}
          >
            Confirm & Drop
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <Content style={{ padding: 24 }} role="main">
      <div className="billing-queue-header">
        <h2>Billing Queue</h2>
        {selectedRowKeys.length > 0 && (
          <Button
            type="primary"
            icon={<DollarOutlined />}
            loading={batchDropping}
            onClick={handleBatchDrop}
            aria-label="Drop selected charges"
          >
            Confirm & Drop ({selectedRowKeys.length})
          </Button>
        )}
        <Button
          icon={<ReloadOutlined />}
          onClick={fetch}
          style={{ marginBottom: 16 }}
        >
          Refresh
        </Button>
      </div>
      {suggestions && Object.keys(suggestions).length > 0 && (
        <Alert
          type="info"
          showIcon
          title={
            <>
              CPT/ICD-10 suggestions loaded from the coding map — confirm each
              charge to drop it to billing.{" "}
              {Object.values(suggestions).some((s) => s.confidence != null) &&
                "Confidence reflects match quality (95% exact, 75% partial)."}
            </>
          }
          style={{ marginBottom: 16 }}
        />
      )}
      <PageState
        error={error}
        onRetry={() => fetch()}
        empty={!loading && !error && data.length === 0}
        emptyMessage="No unbilled charges — everything is captured"
      >
        <Table
          rowKey="id"
          columns={columns}
          dataSource={data}
          loading={loading}
          rowSelection={{
            selectedRowKeys,
            onChange: (keys: React.Key[]) => setSelectedRowKeys(keys),
          }}
          pagination={{
            ...pagination,
            showSizeChanger: true,
            showTotal: (t: number) => `${t} charges`,
          }}
          onChange={(pag: any) => setPagination(pag)}
          onRow={(record) => ({
            onMouseEnter: () => loadSuggestions(record),
          })}
          size="middle"
        />
      </PageState>
    </Content>
  );
}

export default withSidebar(BillingQueue);