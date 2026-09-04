import React, { useEffect, useState } from "react";
import { Card, Col, Row, Statistic, Table, Alert } from "antd";
import { useDocumentTitle } from "../hooks";
import { request } from "../helpers";
import withSidebar from "../common/base";
import "./ResidentHome.css";

// RES-04: My Progress — personal metrics from /reports/reading-stats
// (signed-today, turnaround, STAT compliance, trailing trend, and the
// attending feedback count). REPORT_READ-gated like the rest of the
// reading surfaces; residents reach it from the sidebar.
function ResidentProgress() {
  useDocumentTitle("QuantumPACS - My Progress");
  const [stats, setStats] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    request("reports/reading-stats?days=14")
      .then((res: any) => setStats(res?.data ?? null))
      .catch((e: any) => setError(e.message));
  }, []);

  const avgStatMin =
    typeof stats?.avg_tat_seconds?.stat === "number"
      ? Math.round(stats.avg_tat_seconds.stat / 60)
      : null;

  return (
    <div style={{ padding: 24 }} role="main">
      {error && (
        <Alert type="error" title="Failed to load progress" description={error} showIcon />
      )}
      {!stats && !error ? (
        <Card loading title="My Progress" />
      ) : (
        <>
          <Row gutter={16}>
            <Col span={6}>
              <Card size="small">
                <Statistic title="Signed today" value={stats?.signed_today ?? 0} />
              </Card>
            </Col>
            <Col span={6}>
              <Card size="small">
                <Statistic
                  title="Avg STAT turnaround (min)"
                  value={avgStatMin ?? "—"}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card size="small">
                <Statistic
                  title="STAT compliance"
                  value={stats?.stat_compliance_pct ?? "—"}
                  suffix={typeof stats?.stat_compliance_pct === "number" ? "%" : ""}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card size="small">
                <Statistic
                  title="Feedback received"
                  value={stats?.feedback_received ?? 0}
                />
              </Card>
            </Col>
          </Row>
          <Card title="Last 14 days" size="small" style={{ marginTop: 16 }}>
            <Table
              rowKey="date"
              size="small"
              pagination={false}
              dataSource={stats?.trend ?? []}
              columns={[
                { title: "Date", dataIndex: "date", key: "date" },
                { title: "Reports signed", dataIndex: "count", key: "count" },
                {
                  title: "Avg turnaround (min)",
                  key: "tat",
                  render: (_: any, r: any) =>
                    typeof r.avg_tat_seconds === "number"
                      ? Math.round(r.avg_tat_seconds / 60)
                      : "—",
                },
              ]}
            />
          </Card>
        </>
      )}
    </div>
  );
}

export default withSidebar(ResidentProgress);
