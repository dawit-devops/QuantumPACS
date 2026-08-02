import React, { useState, useEffect } from "react";
import {
  Layout,
  Card,
  Table,
  Tag,
  Button,
  Select,
  Input,
  Space,
  Statistic,
  Row,
  Col,
  Tabs,
  Descriptions,
  Modal,
  Spin,
  message,
  Tooltip,
  Alert,
} from "antd";
import {
  ReloadOutlined,
  SearchOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  WarningOutlined,
  InfoCircleOutlined,
} from "@ant-design/icons";
import withRouter from "../withRouter";
import withSidebar from "../common/base";
import {
  listHl7Messages,
  getHl7Message,
  getHl7Metrics,
  getHl7Config,
  updateHl7Config,
  getHl7Status,
} from "../api/hl7";
import { PageState } from "../common/PageState";
import "./Hl7.css";

const { Content } = Layout;
const { TextArea } = Input;

function Hl7Dashboard(props: any) {
  // Messages tab
  let [messages, setMessages] = useState<any[]>([]);
  let [total, setTotal] = useState(0);
  let [msgLoading, setMsgLoading] = useState(true);
  let [msgError, setMsgError] = useState<string | null>(null);
  let [msgFilter, setMsgFilter] = useState("");
  let [statusFilter, setStatusFilter] = useState("");
  let [patientFilter, setPatientFilter] = useState("");
  let [facilityFilter, setFacilityFilter] = useState("");
  let [limit] = useState(50);
  let [offset, setOffset] = useState(0);
  let [detailModal, setDetailModal] = useState<any>(null);

  // Analytics tab
  let [metrics, setMetrics] = useState<any>(null);
  let [metricsLoading, setMetricsLoading] = useState(false);
  let [period, setPeriod] = useState("24h");

  // Config tab
  let [config, setConfig] = useState<any>(null);
  let [configLoading, setConfigLoading] = useState(false);
  let [configError, setConfigError] = useState<string | null>(null);
  let [status, setStatus] = useState<any>(null);
  let [statusLoading, setStatusLoading] = useState(false);
  let [configSaving, setConfigSaving] = useState(false);
  let [allowedIpsText, setAllowedIpsText] = useState("");
  let [mllpPort, setMllpPort] = useState(12579);

  const fetchMessages = async () => {
    setMsgLoading(true);
    setMsgError(null);
    try {
      const res = await listHl7Messages({
        limit,
        offset,
        ...(msgFilter ? { message_type: msgFilter } : {}),
        ...(statusFilter ? { parse_status: statusFilter } : {}),
        ...(patientFilter ? { patient_id: patientFilter } : {}),
        ...(facilityFilter ? { sending_facility: facilityFilter } : {}),
      });
      setMessages(res.messages || []);
      setTotal(res.total || 0);
    } catch (e: any) {
      setMsgError(e.message);
    } finally {
      setMsgLoading(false);
    }
  };

  const fetchMetrics = async () => {
    setMetricsLoading(true);
    try {
      const res = await getHl7Metrics(period);
      setMetrics(res);
    } catch {
    } finally {
      setMetricsLoading(false);
    }
  };

  const fetchConfig = async () => {
    setConfigLoading(true);
    try {
      const res = await getHl7Config();
      setConfig(res);
      setConfigError(null);
      setAllowedIpsText((res.allowed_ips || []).join("\n"));
      setMllpPort(res.mllp_port || 12579);
    } catch (e: any) {
      // Surface load failures: with config left null the Save button stays
      // disabled so a failed load can never overwrite the server's real
      // configuration with local defaults.
      setConfig(null);
      setConfigError(e.message);
    } finally {
      setConfigLoading(false);
    }
  };

  const fetchStatus = async () => {
    setStatusLoading(true);
    try {
      const res = await getHl7Status();
      setStatus(res);
    } catch {
    } finally {
      setStatusLoading(false);
    }
  };

  useEffect(() => {
    fetchMessages();
  }, [offset, msgFilter, statusFilter, patientFilter, facilityFilter]);

  useEffect(() => {
    if (metricsLoading === false && !metrics) fetchMetrics();
  }, []);

  useEffect(() => {
    if (configLoading === false && !config) fetchConfig();
    if (statusLoading === false && !status) fetchStatus();
  }, []);

  const handleViewDetail = async (id: string) => {
    try {
      const res = await getHl7Message(id);
      setDetailModal(res);
    } catch (e: any) {
      message.error(e.message);
    }
  };

  const handleSaveConfig = async () => {
    if (!config) {
      message.error("Configuration failed to load — reload before saving");
      return;
    }
    setConfigSaving(true);
    try {
      const ips = allowedIpsText
        .split("\n")
        .map((s) => s.trim())
        .filter(Boolean);
      await updateHl7Config({ mllp_port: mllpPort, allowed_ips: ips });
      message.success("Configuration saved");
      fetchConfig();
      fetchStatus();
    } catch (e: any) {
      message.error(e.message);
    } finally {
      setConfigSaving(false);
    }
  };

  const statusBadge = (status: string) => {
    const m: Record<string, [string, string]> = {
      ok: ["green", "Parsed"],
      partial: ["orange", "Partial"],
      failed: ["red", "Failed"],
    };
    const [color, label] = m[status] || ["default", status];
    return <Tag color={color}>{label}</Tag>;
  };

  const columns = [
    {
      title: "Time",
      dataIndex: "created_at",
      key: "created_at",
      render: (t: string) => new Date(t).toLocaleString(),
      width: 160,
    },
    {
      title: "Type",
      key: "type",
      width: 140,
      render: (_: any, r: any) => (
        <Tag>
          {r.message_type}
          {r.event_type ? `-${r.event_type}` : ""}
        </Tag>
      ),
    },
    {
      title: "Patient ID",
      dataIndex: "patient_id",
      key: "patient_id",
      width: 120,
    },
    {
      title: "Accession",
      dataIndex: "accession_number",
      key: "accession_number",
      width: 120,
    },
    {
      title: "Facility",
      dataIndex: "sending_facility",
      key: "sending_facility",
      width: 120,
    },
    {
      title: "Status",
      dataIndex: "parse_status",
      key: "parse_status",
      render: statusBadge,
      width: 90,
    },
    {
      title: "Actions",
      key: "actions",
      width: 80,
      render: (_: any, r: any) => (
        <Button size="small" onClick={() => handleViewDetail(r.id)}>
          View
        </Button>
      ),
    },
  ];

  return (
    <Content className="hl7-dashboard" style={{ padding: 24 }}>
      <Tabs
        defaultActiveKey="messages"
        items={[
          {
            key: "messages",
            label: "Messages",
            children: (
              <div>
                <Space style={{ marginBottom: 12 }} wrap>
                  <Select
                    value={msgFilter}
                    onChange={(v) => {
                      setMsgFilter(v);
                      setOffset(0);
                    }}
                    allowClear
                    placeholder="Message Type"
                    style={{ width: 150 }}
                    options={[
                      { value: "", label: "All Types" },
                      { value: "ADT", label: "ADT" },
                      { value: "ORM", label: "ORM" },
                    ]}
                  />
                  <Select
                    value={statusFilter}
                    onChange={(v) => {
                      setStatusFilter(v);
                      setOffset(0);
                    }}
                    allowClear
                    placeholder="Status"
                    style={{ width: 130 }}
                    options={[
                      { value: "", label: "All Status" },
                      { value: "ok", label: "Parsed OK" },
                      { value: "partial", label: "Partial" },
                      { value: "failed", label: "Failed" },
                    ]}
                  />
                  <Input
                    placeholder="Patient ID"
                    value={patientFilter}
                    onChange={(e) => setPatientFilter(e.target.value)}
                    onPressEnter={() => setOffset(0)}
                    style={{ width: 150 }}
                    prefix={<SearchOutlined />}
                    allowClear
                  />
                  <Input
                    placeholder="Facility"
                    value={facilityFilter}
                    onChange={(e) => setFacilityFilter(e.target.value)}
                    onPressEnter={() => setOffset(0)}
                    style={{ width: 150 }}
                    prefix={<SearchOutlined />}
                    allowClear
                  />
                  <Button icon={<ReloadOutlined />} onClick={fetchMessages}>
                    Refresh
                  </Button>
                  <span
                    style={{ color: "var(--text-secondary)", fontSize: 12 }}
                  >
                    {total} messages
                  </span>
                </Space>
                <Table
                  dataSource={messages}
                  columns={columns}
                  rowKey="id"
                  loading={msgLoading && !msgError}
                  size="small"
                  pagination={{
                    current: offset / limit + 1,
                    pageSize: limit,
                    total,
                    onChange: (page) => setOffset((page - 1) * limit),
                    showSizeChanger: false,
                  }}
                  locale={{ emptyText: "No HL7 messages received yet." }}
                />
              </div>
            ),
          },
          {
            key: "analytics",
            label: "Analytics",
            children: (
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
                {metricsLoading && !metrics ? (
                  <Spin style={{ display: "block", margin: "40px auto" }} />
                ) : metrics ? (
                  <Row gutter={16}>
                    <Col span={8}>
                      <Card>
                        <Statistic
                          title="Total Messages"
                          value={metrics.total}
                        />
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
                                render: statusBadge,
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
                          <div
                            style={{
                              textAlign: "center",
                              color: "var(--text-secondary)",
                              padding: 16,
                            }}
                          >
                            No data
                          </div>
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
                            rowKey={(r, i) =>
                              `${r.message_type}-${r.event_type}-${i}`
                            }
                            pagination={false}
                            size="small"
                          />
                        ) : (
                          <div
                            style={{
                              textAlign: "center",
                              color: "var(--text-secondary)",
                              padding: 16,
                            }}
                          >
                            No data
                          </div>
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
                          <div
                            style={{
                              textAlign: "center",
                              color: "var(--text-secondary)",
                              padding: 16,
                            }}
                          >
                            No data
                          </div>
                        )}
                      </Card>
                    </Col>
                  </Row>
                ) : null}
              </div>
            ),
          },
          {
            key: "config",
            label: "Configuration",
            children: (
              <div>
                <Row gutter={16}>
                  <Col span={12}>
                    <Card title="MLLP Server" size="small">
                      {configError ? (
                        <Alert
                          type="error"
                          showIcon
                          message="Failed to load configuration"
                          description={configError}
                          action={
                            <Button size="small" onClick={fetchConfig}>
                              Retry
                            </Button>
                          }
                          style={{ marginBottom: 12 }}
                        />
                      ) : null}
                      {configLoading ? (
                        <Spin />
                      ) : config ? (
                        <Descriptions column={1} size="small">
                          <Descriptions.Item label="Status">
                            {statusLoading ? (
                              <Spin size="small" />
                            ) : status ? (
                              <Tag
                                icon={
                                  status.listening ? (
                                    <CheckCircleOutlined />
                                  ) : (
                                    <CloseCircleOutlined />
                                  )
                                }
                                color={status.listening ? "green" : "red"}
                              >
                                {status.listening
                                  ? "Listening"
                                  : "Not Reachable"}
                              </Tag>
                            ) : (
                              <Tag color="default">Unknown</Tag>
                            )}
                          </Descriptions.Item>
                          <Descriptions.Item label="Host">
                            {status?.host || "0.0.0.0"}
                          </Descriptions.Item>
                          <Descriptions.Item label="Port">
                            <Input
                              type="number"
                              value={mllpPort}
                              onChange={(e) =>
                                setMllpPort(Number(e.target.value))
                              }
                              style={{ width: 120 }}
                            />
                          </Descriptions.Item>
                          <Descriptions.Item label="Response Time">
                            {status?.response_time_ms || "-"}ms
                          </Descriptions.Item>
                        </Descriptions>
                      ) : null}
                      <Space style={{ marginTop: 12 }}>
                        <Button
                          type="primary"
                          onClick={handleSaveConfig}
                          loading={configSaving}
                          disabled={!config}
                        >
                          Save
                        </Button>
                        <Button onClick={fetchStatus} loading={statusLoading}>
                          Check Status
                        </Button>
                      </Space>
                    </Card>
                  </Col>
                  <Col span={12}>
                    <Card
                      title={
                        <Space>
                          <span>Allowed IPs</span>
                          <Tooltip title="One IP or CIDR per line. Leave empty to allow all.">
                            <InfoCircleOutlined
                              style={{ color: "var(--text-secondary)" }}
                            />
                          </Tooltip>
                        </Space>
                      }
                      size="small"
                    >
                      <TextArea
                        value={allowedIpsText}
                        onChange={(e) => setAllowedIpsText(e.target.value)}
                        rows={6}
                        placeholder="10.0.0.0/24&#10;192.168.1.100&#10;10.0.0.0/8"
                      />
                    </Card>
                  </Col>
                </Row>
              </div>
            ),
          },
        ]}
      />

      {/* Detail Modal */}
      <Modal
        title={`HL7 Message Detail`}
        open={!!detailModal}
        onCancel={() => setDetailModal(null)}
        width={720}
        footer={<Button onClick={() => setDetailModal(null)}>Close</Button>}
      >
        {detailModal && (
          <div>
            <Descriptions column={2} size="small" bordered>
              <Descriptions.Item label="Type">
                {detailModal.message_type}-{detailModal.event_type}
              </Descriptions.Item>
              <Descriptions.Item label="Status">
                {statusBadge(detailModal.parse_status)}
              </Descriptions.Item>
              <Descriptions.Item label="Patient ID">
                {detailModal.patient_id || "-"}
              </Descriptions.Item>
              <Descriptions.Item label="Accession">
                {detailModal.accession_number || "-"}
              </Descriptions.Item>
              <Descriptions.Item label="Facility">
                {detailModal.sending_facility || "-"}
              </Descriptions.Item>
              <Descriptions.Item label="Time">
                {new Date(detailModal.created_at).toLocaleString()}
              </Descriptions.Item>
            </Descriptions>
            {detailModal.error_message && (
              <Card size="small" title="Error" style={{ marginTop: 12 }}>
                <pre
                  style={{ color: "red", margin: 0, whiteSpace: "pre-wrap" }}
                >
                  {detailModal.error_message}
                </pre>
              </Card>
            )}
            <Card size="small" title="Parsed Fields" style={{ marginTop: 12 }}>
              <pre
                style={{
                  margin: 0,
                  maxHeight: 200,
                  overflow: "auto",
                  fontSize: 12,
                }}
              >
                {JSON.stringify(detailModal.parsed_fields, null, 2)}
              </pre>
            </Card>
            <Card size="small" title="Raw Content" style={{ marginTop: 12 }}>
              <pre
                style={{
                  margin: 0,
                  maxHeight: 300,
                  overflow: "auto",
                  fontSize: 11,
                  whiteSpace: "pre-wrap",
                }}
              >
                {detailModal.raw_content}
              </pre>
            </Card>
            {detailModal.errors?.length > 0 && (
              <Card size="small" title="Parse Errors" style={{ marginTop: 12 }}>
                <Table
                  dataSource={detailModal.errors}
                  columns={[
                    { title: "Segment", dataIndex: "segment", key: "segment" },
                    {
                      title: "Field",
                      dataIndex: "field_name",
                      key: "field_name",
                    },
                    {
                      title: "Raw Value",
                      dataIndex: "raw_value",
                      key: "raw_value",
                    },
                    {
                      title: "Error",
                      dataIndex: "error_message",
                      key: "error_message",
                    },
                  ]}
                  rowKey="id"
                  pagination={false}
                  size="small"
                />
              </Card>
            )}
          </div>
        )}
      </Modal>
    </Content>
  );
}

export default withRouter(withSidebar(Hl7Dashboard));
