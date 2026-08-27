import { useDocumentTitle } from "../hooks";
import React, { useState, useEffect, useCallback } from "react";
import { Layout, Card, Statistic, Row, Col, Button, Alert, Space } from "antd";
import {
  ReloadOutlined,
  CheckCircleOutlined,
  DollarOutlined,
  PercentageOutlined,
} from "@ant-design/icons";
import withSidebar from "../common/base";
import { getReconciliation, type ReconciliationSnapshot } from "../api/billing-ris";
import "./BillingQueue.css";

const Content = Layout.Content;

function Reconciliation() {
  useDocumentTitle("QuantumPACS - Billing Reconciliation");
  const [data, setData] = useState<ReconciliationSnapshot | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setData(await getReconciliation());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load reconciliation");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return (
    <Content style={{ padding: 24 }}>
      <div style={{ marginBottom: 16 }}>
        <h2>Billing Reconciliation</h2>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={fetchData} loading={loading}>
            Refresh
          </Button>
        </Space>
      </div>
      {error && <Alert type="error" title={error} style={{ marginBottom: 16 }} />}
      <Row gutter={[24, 24]}>
        <Col xs={24} sm={8}>
          <Card loading={loading}>
            <Statistic
              title="Signed Reports"
              value={data?.signed_reports ?? 0}
              prefix={<CheckCircleOutlined />}
              styles={{ content: { color: "#1677ff" } }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card loading={loading}>
            <Statistic
              title="Charged Reports"
              value={data?.charged_reports ?? 0}
              prefix={<DollarOutlined />}
              styles={{ content: { color: "#52c41a" } }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card loading={loading}>
            <Statistic
              title="Capture Rate"
              value={data?.capture_rate_pct ?? 0}
              precision={1}
              suffix="%"
              prefix={<PercentageOutlined />}
              styles={{
                content: {
                  color: (data?.capture_rate_pct ?? 100) >= 90 ? "#52c41a" : "#faad14",
                },
              }}
            />
          </Card>
        </Col>
      </Row>
    </Content>
  );
}

const ReconciliationPage = withSidebar(Reconciliation);
export default ReconciliationPage;
export { Reconciliation };
