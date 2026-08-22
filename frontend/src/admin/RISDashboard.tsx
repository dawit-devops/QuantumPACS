import { useDocumentTitle } from "../hooks";
import React, { useState, useEffect, useCallback } from "react";
import {
  App,
  Layout,
  Table,
  Tag,
  Button,
  Statistic,
  Row,
  Col,
  Alert,
} from "antd";
import { ReloadOutlined } from "@ant-design/icons";
import withSidebar from "../common/base";
import { PageState } from "../common/PageState";
import {
  getRisDashboardKpi,
  type RisDashboardKpi,
} from "../api/dashboard-ris";
import "./RISDashboard.css";

const Content = Layout.Content;
const REFRESH_MS = 60000;

function fmtDuration(seconds: number | undefined): string {
  if (seconds == null) return "-";
  if (seconds < 60) return `${Math.round(seconds)}s`;
  if (seconds < 3600) return `${(seconds / 60).toFixed(1)}m`;
  return `${(seconds / 3600).toFixed(1)}h`;
}

// S12-35: department-manager dashboard — TAT by priority (p95), resource
// utilization, unbilled aging, and exam volume, with per-report drill-down.
function RISDashboard() {
  const { message } = App.useApp();
  useDocumentTitle("QuantumPACS - RIS Dashboard");
  const [kpi, setKpi] = useState<RisDashboardKpi | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [drillDown, setDrillDown] = useState(false);

  const fetch = useCallback(
    (drill: boolean) => {
      setLoading(true);
      setError(null);
      getRisDashboardKpi(drill)
        .then((res) => {
          setLoading(false);
          setKpi(res);
        })
        .catch((e: any) => {
          setLoading(false);
          setError(e.message);
          message.error(e.message);
        });
    },
    [message],
  );

  useEffect(() => {
    fetch(drillDown);
  }, [fetch, drillDown]);

  useEffect(() => {
    const interval = setInterval(() => fetch(drillDown), REFRESH_MS);
    return () => clearInterval(interval);
  }, [fetch, drillDown]);

  const tatColumns: any[] = [
    {
      title: "Priority",
      dataIndex: "priority",
      width: "30%",
      render: (v: string) => (
        <Tag color={v === "stat" ? "red" : v === "urgent" ? "orange" : "blue"}>
          {v}
        </Tag>
      ),
    },
    {
      title: "p95 TAT",
      dataIndex: "p95_seconds",
      width: "30%",
      render: (v: number) => fmtDuration(v),
    },
  ];

  return (
    <Content style={{ padding: 24 }} role="main">
      <div className="ris-dash-header">
        <h2>RIS Dashboard</h2>
        <Button
          icon={<ReloadOutlined />}
          onClick={() => fetch(drillDown)}
          style={{ marginBottom: 16 }}
        >
          Refresh
        </Button>
      </div>

      {kpi && (
        <>
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col span={6}>
            <Statistic title="Today's Volume" value={kpi.volume} />
          </Col>
          <Col span={6}>
            <Statistic
              title="Utilization (7d)"
              value={kpi.utilization}
              precision={2}
              suffix=""
            />
          </Col>
          <Col span={6}>
            <Statistic
              title="Unbilled"
              value={kpi.unbilled_aging?.total_unbilled ?? 0}
              styles={{
                content: {
                  color:
                    (kpi.unbilled_aging?.total_unbilled ?? 0) > 0
                      ? "#fa8c16"
                      : undefined,
                },
              }}
            />
          </Col>
          <Col span={6}>
            <Statistic
              title="Prior-Auth Approval"
              value={((kpi.prior_auth?.approval_rate ?? 0) * 100).toFixed(1)}
              suffix="%"
              styles={{
                content: {
                  color:
                    (kpi.prior_auth?.approval_rate ?? 0) < 0.95
                      ? "#fa8c16"
                      : undefined,
                },
              }}
            />
          </Col>
        </Row>
        {kpi.prior_auth && (
          <Row gutter={16} style={{ marginBottom: 16 }}>
            {["APPROVED", "PENDING", "DENIED", "EXPIRED"].map((st) => (
              <Col span={6} key={st}>
                <Statistic
                  title={`Prior-Auth ${st}`}
                  value={
                    kpi.prior_auth?.mix?.find((m) => m.status === st)?.n ?? 0
                  }
                />
              </Col>
            ))}
          </Row>
        )}
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col span={6}>
            <Statistic
              title="Cross-site bookings (mo)"
              value={
                kpi.chargeback?.rows?.reduce(
                  (sum, r) => sum + Number(r.bookings ?? 0),
                  0,
                ) ?? 0
              }
            />
          </Col>
          <Col span={6}>
            <Statistic
              title="Claim denial rate"
              value={((kpi.denial_rate ?? 0) * 100).toFixed(1)}
              suffix="%"
              styles={{
                content: {
                  color:
                    (kpi.denial_rate ?? 0) > 0.1 ? "#fa8c16" : undefined,
                },
              }}
            />
          </Col>
        </Row>
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col span={6}>
            <Statistic
              title="STAT p95 TAT"
              value={fmtDuration(
                kpi.tat_by_priority?.find((t) => t.priority === "stat")
                  ?.p95_seconds,
              )}
            />
          </Col>
        </Row>
        </>
      )}

      <PageState
        error={error}
        onRetry={() => fetch(drillDown)}
        empty={!loading && !error && (!kpi || kpi.tat_by_priority?.length === 0)}
        emptyMessage="No report TAT data yet — sign some reports to populate the dashboard"
      >
        {kpi && (
          <>
            <Table
              rowKey="priority"
              title={() => "Report TAT by Priority (p95)"}
              columns={tatColumns}
              dataSource={kpi.tat_by_priority ?? []}
              loading={loading}
              pagination={false}
              size="middle"
              style={{ marginBottom: 16 }}
            />
            {drillDown && (kpi.drill_down?.length ?? 0) > 0 && (
              <Alert
                type="info"
                showIcon
                title={`Drill-down: ${kpi.drill_down?.length} most recent signed reports`}
                style={{ marginBottom: 16 }}
              />
            )}
          </>
        )}
      </PageState>
    </Content>
  );
}

export default withSidebar(RISDashboard);