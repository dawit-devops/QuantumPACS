import React, { useEffect, useMemo, useState } from "react";
import {
  App,
  Layout,
  Table,
  Button,
  Statistic,
  Row,
  Col,
  Card,
  Alert,
} from "antd";
import { ReloadOutlined } from "@ant-design/icons";
import { useDocumentTitle } from "../hooks";
import withSidebar from "../common/base";
import { request } from "../helpers";
import "./BillingQueue.css";

const Content = Layout.Content;

interface RevenueData {
  days: number;
  daily: { day: string; collected: number }[];
  by_payer: { payer_name: string; paid: number }[];
  by_modality: { modality: string; billed: number }[];
  ar_aging: { current: number; over5: number; over10: number };
}

const money = (v: unknown) =>
  typeof v === "number" ? `$${v.toFixed(2)}` : "$0.00";

// B-07: revenue dashboard — collections trend, payer/modality breakdowns
// and unbilled AR aging in dollars (billing/revenue?days=).
function RevenueDashboard() {
  const { message } = App.useApp();
  useDocumentTitle("QuantumPACS - Revenue");
  const [data, setData] = useState<RevenueData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchRev = () => {
    setLoading(true);
    setError(null);
    request("ris/billing/revenue?days=30")
      .then((res: any) => setData(res?.data ?? null))
      .catch((e: any) => {
        setError(e.message || "Failed to load revenue");
        message.error(e.message || "Failed to load revenue");
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchRev();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const totalCollected = useMemo(
    () =>
      (data?.daily ?? []).reduce((acc, d) => acc + Number(d.collected || 0), 0),
    [data],
  );

  return (
    <Content style={{ padding: 24 }} role="main">
      <div className="billing-queue-header">
        <h2>Revenue</h2>
        <Button icon={<ReloadOutlined />} onClick={fetchRev} loading={loading}>
          Refresh
        </Button>
      </div>

      {error && (
        <Alert type="error" title="Failed to load revenue" description={error} showIcon />
      )}

      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title={`Collected (${data?.days ?? 30}d)`}
              value={money(totalCollected)}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic title="AR current" value={money(data?.ar_aging.current)} />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title="AR > 5 days"
              value={money(data?.ar_aging.over5)}
              valueStyle={
                Number(data?.ar_aging.over5) > 0
                  ? { color: "#faad14" }
                  : undefined
              }
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title="AR > 10 days"
              value={money(data?.ar_aging.over10)}
              valueStyle={
                Number(data?.ar_aging.over10) > 0
                  ? { color: "#cf1322" }
                  : undefined
              }
            />
          </Card>
        </Col>
      </Row>

      <Card title="Daily collections" size="small" style={{ marginBottom: 16 }}>
        <Table
          rowKey="day"
          size="small"
          pagination={false}
          loading={loading}
          dataSource={data?.daily ?? []}
          columns={[
            {
              title: "Date",
              dataIndex: "day",
              key: "day",
              render: (d: string) => String(d).slice(0, 10),
            },
            {
              title: "Collected",
              dataIndex: "collected",
              key: "collected",
              render: money,
            },
          ]}
        />
      </Card>

      <Row gutter={16}>
        <Col span={12}>
          <Card title="Paid by payer" size="small" style={{ marginBottom: 16 }}>
            <Table
              rowKey="payer_name"
              size="small"
              pagination={false}
              loading={loading}
              dataSource={data?.by_payer ?? []}
              columns={[
                { title: "Payer", dataIndex: "payer_name", key: "payer" },
                {
                  title: "Paid",
                  dataIndex: "paid",
                  key: "paid",
                  render: money,
                },
              ]}
            />
          </Card>
        </Col>
        <Col span={12}>
          <Card title="Billed by modality" size="small">
            <Table
              rowKey="modality"
              size="small"
              pagination={false}
              loading={loading}
              dataSource={data?.by_modality ?? []}
              columns={[
                { title: "Modality", dataIndex: "modality", key: "mod" },
                {
                  title: "Billed",
                  dataIndex: "billed",
                  key: "billed",
                  render: money,
                },
              ]}
            />
          </Card>
        </Col>
      </Row>
    </Content>
  );
}

export default withSidebar(RevenueDashboard);
