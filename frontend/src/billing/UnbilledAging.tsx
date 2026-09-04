import { useDocumentTitle } from "../hooks";
import React, { useState, useEffect, useCallback } from "react";
import { App, Layout, Table, Tag, Button, Alert, Statistic, Row, Col, Select } from "antd";
import { ReloadOutlined, DownloadOutlined } from "@ant-design/icons";
import withSidebar from "../common/base";
import { PageState } from "../common/PageState";
import {
  getUnbilledAging,
  type UnbilledAgingGroup,
} from "../api/billing-ris";
import "./UnbilledAging.css";

const Content = Layout.Content;
const REFRESH_MS = 30000;

// S11-08: unbilled aging dashboard — groups PENDING charges over the aging
// threshold (5 days) by sign date, surfacing delays so the billing team can
// prioritise. Aged rows (> 5d) render with a red indicator.
const AGING_DAYS = 5;

function UnbilledAging() {
  const { message } = App.useApp();
  useDocumentTitle("QuantumPACS - Unbilled Aging");
  const [groups, setGroups] = useState<UnbilledAgingGroup[]>([]);
  const [totalUnbilled, setTotalUnbilled] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // D2: dimension switch — date (default), site or payer.
  const [groupBy, setGroupBy] = useState<"date" | "site" | "payer">("date");

  // B-11: export the current groups for offline reconciliation.
  const exportCsv = () => {
    if (groups.length === 0) return;
    const keys = Object.keys(groups[0]);
    const esc = (v: unknown) =>
      typeof v === "string" && v.includes(",") ? `"${v}"` : String(v ?? "");
    const csv = [
      keys.join(","),
      ...groups.map((g) => keys.map((k) => esc((g as any)[k])).join(",")),
    ].join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `unbilled-aging-${groupBy}-${new Date()
      .toISOString()
      .slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
    message.success("Unbilled aging exported");
  };

  const fetch = useCallback(() => {
    setLoading(true);
    setError(null);
    getUnbilledAging({ group_by: groupBy })
      .then((res) => {
        setLoading(false);
        setGroups(res.groups);
        setTotalUnbilled(res.total_unbilled);
      })
      .catch((e: any) => {
        setLoading(false);
        setError(e.message);
        message.error(e.message);
      });
  }, [message, groupBy]);

  useEffect(() => {
    fetch();
  }, [fetch]);

  useEffect(() => {
    const interval = setInterval(fetch, REFRESH_MS);
    return () => clearInterval(interval);
  }, [fetch]);

  const columns: any[] = [
    {
      title:
        groupBy === "site" ? "Site / Room"
        : groupBy === "payer" ? "Payer"
        : "Sign Date",
      dataIndex: groupBy === "date" ? "date" : "bucket",
      width: "20%",
      render: (v: string) => v || "-",
    },
    {
      title: "Count",
      dataIndex: "count",
      width: "15%",
    },
    {
      title: "Total Amount",
      dataIndex: "total_amount",
      width: "20%",
      render: (v: number) => (v != null ? `$${Number(v).toFixed(2)}` : "-"),
    },
    {
      title: "Oldest (days)",
      dataIndex: "oldest_charge_days",
      width: "15%",
      render: (v: number) =>
        v != null ? (
          <Tag color={v > AGING_DAYS ? "red" : "default"}>{v}d</Tag>
        ) : (
          "-"
        ),
    },
  ];

  return (
    <Content style={{ padding: 24 }} role="main">
      <div className="unbilled-header">
        <h2>Unbilled Aging</h2>
        <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
          <Select
            aria-label="Group aging by"
            value={groupBy}
            onChange={(v) => setGroupBy(v)}
            style={{ width: 140 }}
            options={[
              { value: "date", label: "By sign date" },
              { value: "site", label: "By site" },
              { value: "payer", label: "By payer" },
            ]}
          />
          <Button
            icon={<DownloadOutlined />}
            onClick={exportCsv}
            disabled={groups.length === 0}
            aria-label="Export unbilled aging CSV"
          >
            Export CSV
          </Button>
          <Button icon={<ReloadOutlined />} onClick={fetch}>
            Refresh
          </Button>
        </div>
      </div>

      {totalUnbilled > 0 && (
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col span={6}>
            <Statistic title="Total Unbilled" value={totalUnbilled} />
          </Col>
          {groups.length > 0 && (
            <Col span={6}>
              <Statistic
                title="Oldest (days)"
                value={groups[0].oldest_charge_days}
                suffix="d"
                styles={{
                  content: {
                    color:
                      groups[0].oldest_charge_days > AGING_DAYS
                        ? "#ff4d4f"
                        : undefined,
                  },
                }}
              />
            </Col>
          )}
        </Row>
      )}

      <PageState
        error={error}
        onRetry={() => fetch()}
        empty={!loading && !error && groups.length === 0}
        emptyMessage="No unbilled charges — all caught up"
      >
        <Table
          rowKey="date"
          columns={columns}
          dataSource={groups}
          loading={loading}
          pagination={false}
          size="middle"
        />
      </PageState>
    </Content>
  );
}

export default withSidebar(UnbilledAging);