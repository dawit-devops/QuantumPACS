import { useDocumentTitle } from "../hooks";
import React, { useState, useEffect, useCallback } from "react";
import { App, Layout, Table, Tag, Button, Alert, Statistic, Row, Col } from "antd";
import { ReloadOutlined } from "@ant-design/icons";
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

  const fetch = useCallback(() => {
    setLoading(true);
    setError(null);
    getUnbilledAging()
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
  }, [message]);

  useEffect(() => {
    fetch();
  }, [fetch]);

  useEffect(() => {
    const interval = setInterval(fetch, REFRESH_MS);
    return () => clearInterval(interval);
  }, [fetch]);

  const columns: any[] = [
    {
      title: "Sign Date",
      dataIndex: "date",
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
        <Button
          icon={<ReloadOutlined />}
          onClick={fetch}
          style={{ marginBottom: 16 }}
        >
          Refresh
        </Button>
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
                valueStyle={{
                  color:
                    groups[0].oldest_charge_days > AGING_DAYS
                      ? "#ff4d4f"
                      : undefined,
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