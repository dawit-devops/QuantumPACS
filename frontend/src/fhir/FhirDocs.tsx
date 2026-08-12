import React, { useState, useEffect } from "react";
import {
  App,
  Layout,
  Card,
  Collapse,
  Select,
  Input,
  Button,
  Tag,
  Spin,
  Descriptions,
  Space,
  Alert,
  Tabs,
  Tooltip,
  Row,
  Col,
  Typography,
} from "antd";
import {
  PlayCircleOutlined,
  CopyOutlined,
  DownloadOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  LinkOutlined,
} from "@ant-design/icons";
import withSidebar from "../common/base";
import { getFhirMetadata, fhirResourceRequest } from "../api/fhir";
import { PageState } from "../common/PageState";
import "./Fhir.css";

const { Content } = Layout;
const { TextArea } = Input;
const { Paragraph, Text } = Typography;

function FhirDocs(props: any) {
  const { message } = App.useApp();
  const [capability, setCapability] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Try-it panel
  const [resourceType, setResourceType] = useState("Patient");
  const [interaction, setInteraction] = useState("read");
  const [resourceId, setResourceId] = useState("");
  const [searchParams, setSearchParams] = useState<Record<string, string>>({});
  const [response, setResponse] = useState<any>(null);
  const [executing, setExecuting] = useState(false);
  const [responseTime, setResponseTime] = useState(0);

  const resourceOptions = ["Patient", "ImagingStudy", "DocumentReference"];

  useEffect(() => {
    fetchCapability();
  }, []);

  const fetchCapability = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getFhirMetadata();
      setCapability(res);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const getSearchParamsForResource = (rt: string) => {
    if (!capability?.rest?.[0]?.resource) return [];
    const r = capability.rest[0].resource.find((r: any) => r.type === rt);
    return r?.searchParam || [];
  };

  const handleExecute = async () => {
    setExecuting(true);
    setResponse(null);
    try {
      let url = `fhir/${resourceType}`;
      if (interaction === "read") {
        if (!resourceId.trim()) {
          message.warning("Resource ID is required");
          setExecuting(false);
          return;
        }
        url += `/${resourceId}`;
      } else {
        const params = new URLSearchParams();
        for (const [k, v] of Object.entries(searchParams)) {
          if (v) params.set(k, v);
        }
        const qs = params.toString();
        if (qs) url += `?${qs}`;
      }

      const start = performance.now();
      const res = await fhirResourceRequest(url);
      const elapsed = Math.round(performance.now() - start);
      setResponseTime(elapsed);
      setResponse(res);
    } catch (e: any) {
      setResponse({ error: e.message || "Request failed" });
      try {
        setResponse(JSON.parse(e.message));
      } catch {}
    } finally {
      setExecuting(false);
    }
  };

  const handleCopyResponse = () => {
    navigator.clipboard.writeText(JSON.stringify(response, null, 2));
    message.success("Response copied");
  };

  const handleDownloadResponse = () => {
    const blob = new Blob([JSON.stringify(response, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${resourceType}-response.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (loading) {
    return (
      <Content className="fhir-docs" style={{ padding: 24 }}>
        <Spin size="large" style={{ display: "block", margin: "80px auto" }} />
      </Content>
    );
  }

  if (error) {
    return (
      <Content className="fhir-docs" style={{ padding: 24 }}>
        <PageState
          error={error}
          onRetry={fetchCapability}
          emptyMessage="FHIR server unavailable — check the FHIR Config page to enable it."
        />
      </Content>
    );
  }

  const rest = capability?.rest?.[0];
  const resources = rest?.resource || [];

  return (
    <Content className="fhir-docs" style={{ padding: 24 }}>
      <Row gutter={16}>
        {/* Capability Statement */}
        <Col span={12}>
          <Card
            title="Capability Statement"
            extra={
              <Button
                size="small"
                icon={<CopyOutlined />}
                onClick={() => {
                  navigator.clipboard.writeText(
                    JSON.stringify(capability, null, 2),
                  );
                  message.success("Copied");
                }}
              >
                Copy
              </Button>
            }
          >
            <Descriptions column={1} size="small">
              <Descriptions.Item label="Publisher">
                {capability?.publisher || "N/A"}
              </Descriptions.Item>
              <Descriptions.Item label="FHIR Version">
                {capability?.fhirVersion || "N/A"}
              </Descriptions.Item>
              <Descriptions.Item label="Status">
                <Tag
                  color={capability?.status === "active" ? "green" : "default"}
                >
                  {capability?.status}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="Formats">
                {capability?.format?.map((f: string) => (
                  <Tag key={f}>{f}</Tag>
                ))}
              </Descriptions.Item>
              <Descriptions.Item label="Software">
                {capability?.software?.name} {capability?.software?.version}
              </Descriptions.Item>
            </Descriptions>

            <div style={{ fontWeight: 600, marginTop: 16, marginBottom: 8 }}>
              Supported Resources
            </div>
            <Collapse
              ghost
              size="small"
              items={resources.map((r: any) => ({
                key: r.type,
                label: (
                  <span>
                    <Tag>{r.type}</Tag>{" "}
                    {r.interaction?.map((i: any) => i.code).join(", ")}
                  </span>
                ),
                children: (
                  <div>
                    {r.searchParam?.length > 0 && (
                      <>
                        <div
                          style={{
                            fontWeight: 600,
                            fontSize: 12,
                            marginBottom: 4,
                          }}
                        >
                          Search Parameters
                        </div>
                        {r.searchParam.map((p: any) => (
                          <div
                            key={p.name}
                            style={{ fontSize: 12, marginBottom: 2 }}
                          >
                            <code>{p.name}</code>{" "}
                            <Tag style={{ fontSize: 10 }}>{p.type}</Tag>
                          </div>
                        ))}
                      </>
                    )}
                    {(!r.searchParam || r.searchParam.length === 0) && (
                      <div
                        style={{ fontSize: 12, color: "var(--text-secondary)" }}
                      >
                        No search parameters
                      </div>
                    )}
                  </div>
                ),
              }))}
            />
          </Card>
        </Col>

        {/* Try-it Panel */}
        <Col span={12}>
          <Card
            title="Try It"
            extra={
              rest?.security && (
                <Tag>{rest.security?.description || "SMART-on-FHIR"}</Tag>
              )
            }
          >
            <Space orientation="vertical" style={{ width: "100%" }}>
              <Space>
                <Select
                  value={resourceType}
                  onChange={(v) => {
                    setResourceType(v);
                    setResponse(null);
                    setSearchParams({});
                  }}
                  style={{ width: 180 }}
                  options={resourceOptions.map((r) => ({ value: r, label: r }))}
                />
                <Select
                  value={interaction}
                  onChange={(v) => setInteraction(v)}
                  style={{ width: 120 }}
                  options={[
                    { value: "read", label: "Read by ID" },
                    { value: "search", label: "Search" },
                  ]}
                />
              </Space>

              {interaction === "read" ? (
                <Input
                  placeholder={`${resourceType} ID`}
                  value={resourceId}
                  onChange={(e) => setResourceId(e.target.value)}
                />
              ) : (
                <div>
                  {getSearchParamsForResource(resourceType).map((p: any) => (
                    <Input
                      key={p.name}
                      placeholder={`${p.name} (${p.type})`}
                      value={searchParams[p.name] || ""}
                      onChange={(e) =>
                        setSearchParams({
                          ...searchParams,
                          [p.name]: e.target.value,
                        })
                      }
                      style={{ marginBottom: 4 }}
                    />
                  ))}
                  {getSearchParamsForResource(resourceType).length === 0 && (
                    <Text type="secondary">No search parameters available</Text>
                  )}
                </div>
              )}

              <Button
                type="primary"
                icon={<PlayCircleOutlined />}
                onClick={handleExecute}
                loading={executing}
                block
              >
                Execute
              </Button>

              {response && (
                <Card
                  size="small"
                  title={
                    <Space>
                      {response.resourceType ? (
                        <CheckCircleOutlined style={{ color: "green" }} />
                      ) : (
                        <CloseCircleOutlined style={{ color: "red" }} />
                      )}
                      <span>
                        {response.resourceType || "Error"} — {responseTime}ms
                      </span>
                    </Space>
                  }
                  extra={
                    <Space>
                      <Tooltip title="Copy">
                        <Button
                          size="small"
                          icon={<CopyOutlined />}
                          onClick={handleCopyResponse}
                        />
                      </Tooltip>
                      <Tooltip title="Download">
                        <Button
                          size="small"
                          icon={<DownloadOutlined />}
                          onClick={handleDownloadResponse}
                        />
                      </Tooltip>
                    </Space>
                  }
                >
                  <pre
                    style={{
                      maxHeight: 400,
                      overflow: "auto",
                      fontSize: 12,
                      margin: 0,
                      whiteSpace: "pre-wrap",
                    }}
                  >
                    {JSON.stringify(response, null, 2)}
                  </pre>
                </Card>
              )}
            </Space>
          </Card>
        </Col>
      </Row>
    </Content>
  );
}

export default withSidebar(FhirDocs);
