import React, { useState, useEffect } from "react";
import {
  Layout,
  Card,
  Row,
  Col,
  Tag,
  Table,
  Descriptions,
  Spin,
  Tabs,
  Empty,
  Badge,
  Statistic,
} from "antd";
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  ApiOutlined,
  SearchOutlined,
  DownloadOutlined,
  UploadOutlined,
  DatabaseOutlined,
} from "@ant-design/icons";
import withSidebar from "../common/base";
import { Typography } from "antd";
import {
  getDicomwebAdmin,
  getDicomwebMetrics,
  DicomwebMetrics,
} from "../api/dicomweb-admin";
import { PageState } from "../common/PageState";
import "./DicomWebAdmin.css";

const { Content } = Layout;
const { Text } = Typography;

const serviceIcons: Record<string, React.ReactNode> = {
  qido: <SearchOutlined />,
  wado: <DownloadOutlined />,
  stow: <UploadOutlined />,
};

function DicomWebAdmin(props: any) {
  const [info, setInfo] = useState<any>(null);
  const [metrics, setMetrics] = useState<DicomwebMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchInfo();
  }, []);

  const fetchInfo = async () => {
    setLoading(true);
    setError(null);
    try {
      const [res, m] = await Promise.all([
        getDicomwebAdmin(),
        getDicomwebMetrics(),
      ]);
      setInfo(res);
      setMetrics(m);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <Content className="dicomweb-admin" style={{ padding: 24 }}>
        <Spin size="large" style={{ display: "block", margin: "80px auto" }} />
      </Content>
    );
  }

  if (error) {
    return (
      <Content className="dicomweb-admin" style={{ padding: 24 }}>
        <PageState error={error} onRetry={fetchInfo} />
      </Content>
    );
  }

  const endpointColumns = [
    {
      title: "Method",
      dataIndex: "method",
      key: "method",
      render: (t: string) => <Tag>{t}</Tag>,
      width: 80,
    },
    { title: "Path", dataIndex: "path", key: "path" },
    { title: "Description", dataIndex: "description", key: "description" },
  ];

  return (
    <Content className="dicomweb-admin" style={{ padding: 24 }}>
      <div style={{ fontWeight: 600, fontSize: 16, marginBottom: 16 }}>
        <ApiOutlined style={{ marginRight: 8 }} />
        DICOMweb Server
      </div>

      {/* Service Cards */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        {["qido", "wado", "stow"].map((service) => {
          const s = info?.[service];
          if (!s) return null;
          return (
            <Col span={8} key={service}>
              <Card
                title={
                  <span>
                    {serviceIcons[service]}{" "}
                    <span style={{ marginLeft: 4 }}>
                      {service.toUpperCase()}-RS
                    </span>
                  </span>
                }
                extra={
                  s.enabled ? (
                    <Tag icon={<CheckCircleOutlined />} color="green">
                      Enabled
                    </Tag>
                  ) : (
                    <Tag icon={<CloseCircleOutlined />} color="red">
                      Disabled
                    </Tag>
                  )
                }
              >
                <Descriptions column={1} size="small">
                  <Descriptions.Item label="Format">
                    <Tag>
                      {s.response_format ||
                        s.content_type ||
                        "application/dicom"}
                    </Tag>
                  </Descriptions.Item>
                  {s.pagination && (
                    <Descriptions.Item label="Pagination">
                      {s.pagination}
                    </Descriptions.Item>
                  )}
                  {s.features?.transfer_syntax && (
                    <Descriptions.Item label="Transfer Syntax">
                      {s.features.transfer_syntax}
                    </Descriptions.Item>
                  )}
                  {s.modality_validation !== undefined && (
                    <Descriptions.Item label="Valid Modalities">
                      {s.valid_modalities_count}
                    </Descriptions.Item>
                  )}
                </Descriptions>
              </Card>
            </Col>
          );
        })}
      </Row>

      <Tabs
        defaultActiveKey="endpoints"
        items={[
          {
            key: "endpoints",
            label: "Endpoints",
            children: (
              <Row gutter={16}>
                {["qido", "wado", "stow"].map((service) => {
                  const s = info?.[service];
                  if (!s?.endpoints?.length) return null;
                  return (
                    <Col span={8} key={service}>
                      <Card
                        title={`${service.toUpperCase()}-RS`}
                        size="small"
                        style={{ marginBottom: 16 }}
                      >
                        <Table
                          dataSource={s.endpoints}
                          columns={endpointColumns}
                          rowKey="path"
                          pagination={false}
                          size="small"
                        />
                      </Card>
                    </Col>
                  );
                })}
              </Row>
            ),
          },
          {
            key: "search",
            label: "Search Parameters",
            children: (
              <Card size="small">
                {info?.qido?.search_params?.length > 0 ? (
                  <Table
                    dataSource={info.qido.search_params}
                    columns={[
                      {
                        title: "Parameter",
                        dataIndex: "name",
                        key: "name",
                        render: (t: string) => <code>{t}</code>,
                      },
                      {
                        title: "Type",
                        dataIndex: "type",
                        key: "type",
                        render: (t: string) => <Tag>{t}</Tag>,
                      },
                      {
                        title: "Description",
                        dataIndex: "description",
                        key: "description",
                      },
                    ]}
                    rowKey="name"
                    pagination={false}
                    size="small"
                  />
                ) : (
                  <Empty description="No search parameters" />
                )}
              </Card>
            ),
          },
          {
            key: "modalities",
            label: "Modalities",
            children: (
              <Card size="small">
                <div
                  style={{ marginBottom: 8, color: "var(--text-secondary)" }}
                >
                  {info?.modalities?.length || 0} valid modality codes
                </div>
                {info?.modalities?.map((m: string) => (
                  <Tag key={m} style={{ marginBottom: 4 }}>
                    {m}
                  </Tag>
                ))}
              </Card>
            ),
          },
          {
            key: "metrics",
            label: "Metrics",
            children: (
              <Card size="small">
                {metrics ? (
                  <>
                    <Row gutter={16}>
                      <Col span={8}>
                        <Statistic
                          title={`Studies stored (${metrics.period})`}
                          value={metrics.studies_stored || 0}
                          prefix={<DatabaseOutlined />}
                        />
                      </Col>
                      <Col span={8}>
                        <Statistic
                          title={`Instances stored (${metrics.period})`}
                          value={metrics.files_stored || 0}
                        />
                      </Col>
                    </Row>
                    <Row gutter={16} style={{ marginTop: 16 }}>
                      <Col span={8}>
                        <Statistic
                          title="Total studies"
                          value={metrics.totals?.studies || 0}
                        />
                      </Col>
                      <Col span={8}>
                        <Statistic
                          title="Total series"
                          value={metrics.totals?.series || 0}
                        />
                      </Col>
                      <Col span={8}>
                        <Statistic
                          title="Total instances"
                          value={metrics.totals?.files || 0}
                        />
                      </Col>
                    </Row>
                    {metrics.metrics_note && (
                      <Text
                        type="secondary"
                        style={{ display: "block", marginTop: 16 }}
                      >
                        {metrics.metrics_note}
                      </Text>
                    )}
                  </>
                ) : (
                  <Empty description="No metrics available" />
                )}
              </Card>
            ),
          },
          {
            key: "roadmap",
            label: "Missing Features",
            children: (
              <Card size="small">
                {info?.missing_features?.length > 0 ? (
                  <Table
                    dataSource={info.missing_features.map((f: string) => ({
                      feature: f,
                    }))}
                    columns={[
                      {
                        title: "Feature",
                        dataIndex: "feature",
                        key: "feature",
                      },
                    ]}
                    rowKey="feature"
                    pagination={false}
                    size="small"
                  />
                ) : (
                  <Empty description="No missing features" />
                )}
              </Card>
            ),
          },
        ]}
      />
    </Content>
  );
}

export default withSidebar(DicomWebAdmin);
