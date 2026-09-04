import React from "react";
import {
  Card,
  Descriptions,
  Tag,
  Button,
  Input,
  Space,
  Spin,
  Alert,
  Tooltip,
  Row,
  Col,
} from "antd";
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  InfoCircleOutlined,
} from "@ant-design/icons";

const { TextArea } = Input;

interface ConfigTabProps {
  config: any;
  configLoading: boolean;
  configError: string | null;
  status: any;
  statusLoading: boolean;
  configSaving: boolean;
  mllpPort: number;
  setMllpPort: (v: number) => void;
  allowedIpsText: string;
  setAllowedIpsText: (v: string) => void;
  fetchConfig: () => void;
  fetchStatus: () => void;
  handleSaveConfig: () => void;
  canWrite: boolean;
}

export function ConfigTab({
  config,
  configLoading,
  configError,
  status,
  statusLoading,
  configSaving,
  mllpPort,
  setMllpPort,
  allowedIpsText,
  setAllowedIpsText,
  fetchConfig,
  fetchStatus,
  handleSaveConfig,
  canWrite,
}: ConfigTabProps) {
  return (
    <div>
      <Row gutter={16}>
        <Col span={12}>
          <Card title="MLLP Server" size="small">
            {configError ? (
              <Alert
                type="error"
                showIcon
                title="Failed to load configuration"
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
                      {status.listening ? "Listening" : "Not Reachable"}
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
                    onChange={(e) => setMllpPort(Number(e.target.value))}
                    disabled={!canWrite}
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
                disabled={!config || !canWrite}
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
              disabled={!canWrite}
              rows={6}
              placeholder="10.0.0.0/24&#10;192.168.1.100&#10;10.0.0.0/8"
            />
            {!canWrite && (
              <div style={{ marginTop: 8 }}>
                <Tag color="default">
                  Read-only — you need HL7_WRITE to change configuration.
                </Tag>
              </div>
            )}
          </Card>
        </Col>
      </Row>
    </div>
  );
}
