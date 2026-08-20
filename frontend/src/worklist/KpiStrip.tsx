import React from "react";
import { Row, Col, Statistic, Button, Alert } from "antd";
import { ReloadOutlined } from "@ant-design/icons";
import type { TrackingKpi } from "../api/tracking";

interface KpiStripProps {
  kpi: TrackingKpi | null;
  kpiError: string | null;
  lastUpdated: Date | null;
  onRefresh: () => void;
}

// S6-18: the live KPI strip for the tracking board. Kept separate from the
// board table so the board stays a focused component; the strip renders its
// own stale/error states instead of the board swallowing them.
export default function KpiStrip({
  kpi,
  kpiError,
  lastUpdated,
  onRefresh,
}: KpiStripProps) {
  return (
    <>
      {kpi && (
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col span={4}>
            <Statistic title="Today's Volume" value={kpi.volume} />
          </Col>
          <Col span={4}>
            <Statistic
              title="In Progress"
              value={kpi.in_progress}
              valueStyle={{ color: "#fa8c16" }}
            />
          </Col>
          <Col span={4}>
            <Statistic
              title="Awaiting Read"
              value={kpi.awaiting_read}
              valueStyle={{ color: "#1890ff" }}
            />
          </Col>
          <Col span={4}>
            <Statistic
              title="Overdue"
              value={kpi.overdue}
              valueStyle={{ color: kpi.overdue > 0 ? "#ff4d4f" : undefined }}
            />
          </Col>
          <Col span={4}>
            <Statistic
              title="STAT Queue"
              value={kpi.stat_count}
              valueStyle={{ color: kpi.stat_count > 0 ? "#ff4d4f" : undefined }}
            />
          </Col>
          <Col span={4}>
            <Button
              icon={<ReloadOutlined />}
              onClick={onRefresh}
              style={{ marginTop: 24 }}
            >
              Refresh
            </Button>
          </Col>
        </Row>
      )}
      {kpiError && (
        <Alert
          type="warning"
          showIcon
          message={kpiError}
          style={{ marginBottom: 16 }}
        />
      )}
      {lastUpdated && (
        <div style={{ marginBottom: 16, color: "var(--text-secondary)" }}>
          Updated {lastUpdated.toLocaleTimeString()}
        </div>
      )}
    </>
  );
}