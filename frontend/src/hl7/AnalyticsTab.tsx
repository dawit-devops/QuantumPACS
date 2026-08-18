import React from "react";
import {
  Card,
  Table,
  Tag,
  Button,
  Select,
  Space,
  Statistic,
  Row,
  Col,
  Spin,
} from "antd";
import { ReloadOutlined } from "@ant-design/icons";
import { StatusBadge } from "./StatusBadge";

interface AnalyticsTabProps {
  metrics: any;
  loading: boolean;
  period: string;
  setPeriod: (v: string) => void;
  fetchMetrics: () => void;
}

export function AnalyticsTab({
  metrics,
  loading,
  period,
  setPeriod,
  fetchMetrics,
}: AnalyticsTabProps) {
  const empty = (
    <div
      style={{
        textAlign: "center",
        color: "var(--text-secondary)",
        padding: 16,
      }}
    >
      No data
    </div>
  );

  return (
    <div>
      <Space style={{ marginBottom: 12 }}>
        <Select
          value={period}
          onChange={(v) => {
            setPeriod(v);
            fetchMetrics();
          }}
          style={{ width: 120 }}
          options={[
            { value: "1h", label: "Last Hour" },
            { value: "24h", label: "Last 24 Hours" },
            { value: "7d", label: "Last 7 Days" },
            { value: "30d", label: "Last 30 Days" },
          ]}
        />
        <Button icon={<ReloadOutlined />} onClick={fetchMetrics}>
          Refresh
        </Button>
      </Space>
      {loading && !metrics ? (
        <Spin style={{ display: "block", margin: "40px auto" }} />
      ) : metrics ? (
        <Row gutter={16}>
          <Col span={8}>
            <Card>
              <Statistic title="Total Messages" value={metrics.total} />
            </Card>
          </Col>
          <Col span={16}>
            <Card title="By Status" size="small">
              {metrics.by_status?.length > 0 ? (
                <Table
                  dataSource={metrics.by_status}
                  columns={[
                    {
                      title: "Status",
                      dataIndex: "parse_status",
                      key: "parse_status",
                      render: (s: string) => <StatusBadge status={s} />,
                    },
                    {
                      title: "Count",
                      dataIndex: "count",
                      key: "count",
                    },
                  ]}
                  rowKey="parse_status"
                  pagination={false}
                  size="small"
                />
              ) : (
                empty
              )}
            </Card>
          </Col>
          <Col span={24} style={{ marginTop: 16 }}>
            <Card title="By Message Type" size="small">
              {metrics.by_type?.length > 0 ? (
                <Table
                  dataSource={metrics.by_type}
                  columns={[
                    {
                      title: "Type",
                      key: "type",
                      render: (_: any, r: any) => (
                        <Tag>
                          {r.message_type}-{r.event_type}
                        </Tag>
                      ),
                    },
                    {
                      title: "Count",
                      dataIndex: "count",
                      key: "count",
                    },
                  ]}
                  rowKey={(r) => `${r.message_type}-${r.event_type}`}
                  pagination={false}
                  size="small"
                />
              ) : (
                empty
              )}
            </Card>
          </Col>
          <Col span={24} style={{ marginTop: 16 }}>
            <Card title="Top Sending Facilities" size="small">
              {metrics.by_facility?.length > 0 ? (
                <Table
                  dataSource={metrics.by_facility}
                  columns={[
                    {
                      title: "Facility",
                      dataIndex: "sending_facility",
                      key: "sending_facility",
                    },
                    {
                      title: "Count",
                      dataIndex: "count",
                      key: "count",
                    },
                  ]}
                  rowKey="sending_facility"
                  pagination={false}
                  size="small"
                />
              ) : (
                empty
              )}
            </Card>
          </Col>
        </Row>
      ) : null}
    </div>
  );
}
