import { useDocumentTitle } from "../hooks";
import React, { useState, useCallback, useEffect } from "react";
import { App,
  Form,
  Input,
  InputNumber,
  Button,
  Layout,
  Modal,
  Row,
  Col,
  Typography,
  Space,
  Tooltip,
  Table,
  Tag,
  Popconfirm,
} from "antd";
import {
  CopyOutlined,
  ShareAltOutlined,
  CheckOutlined,
  DeleteOutlined,
  LinkOutlined,
} from "@ant-design/icons";
import { listFileShares, createFileShare, revokeFileShare } from "../api/files";

const { Content } = Layout;
const { Text } = Typography;

function Share(props: any) {
  const { message } = App.useApp();
  useDocumentTitle("QuantumPACS - Share");
  let [loading, setLoading] = useState(false);
  let [key, setKey] = useState<string | null>(null);
  let [copied, setCopied] = useState(false);
  let [links, setLinks] = useState<any[]>([]);
  let [linksLoading, setLinksLoading] = useState(false);
  let [revoking, setRevoking] = useState<string | null>(null);
  const [form] = Form.useForm();

  const fetchLinks = useCallback(() => {
    setLinksLoading(true);
    listFileShares(props.file.id)
      .then((res) => setLinks(res))
      .catch(() => {})
      .finally(() => setLinksLoading(false));
  }, [props.file.id]);

  useEffect(() => {
    fetchLinks();
  }, [fetchLinks]);

  const handleSubmit = () => {
    setLoading(true);
    form
      .validateFields()
      .then((values: any) => {
        createFileShare(props.file.id, values)
          .then((data: any) => {
            setLoading(false);
            setKey(data.key);
            fetchLinks();
            form.resetFields();
          })
          .catch(() => {
            setLoading(false);
            message.error("Share failed");
          });
      })
      .catch(() => setLoading(false));
  };

  const shareUrl = key ? `${window.location.origin}/view/${key}` : "";

  const copyToClipboard = useCallback(() => {
    navigator.clipboard
      .writeText(shareUrl)
      .then(() => {
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
        message.success("Link copied!");
      })
      .catch(() => {
        const textArea = document.createElement("textarea");
        textArea.value = shareUrl;
        document.body.appendChild(textArea);
        textArea.select();
        document.execCommand("copy");
        document.body.removeChild(textArea);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
        message.success("Link copied!");
      });
  }, [shareUrl]);

  const nativeShare = useCallback(() => {
    if (navigator.share) {
      navigator
        .share({
          title: "QuantumPACS Shared Study",
          text: "View this medical study securely",
          url: shareUrl,
        })
        .catch(() => {});
    } else {
      copyToClipboard();
    }
  }, [shareUrl, copyToClipboard]);

  const handleRevoke = async (shareId: string) => {
    setRevoking(shareId);
    try {
      await revokeFileShare(props.file.id, shareId);
      message.success("Share link revoked");
      fetchLinks();
    } catch {
      message.error("Failed to revoke share link");
    } finally {
      setRevoking(null);
    }
  };

  const copyLink = (url: string) => {
    navigator.clipboard.writeText(url).then(() => {
      message.success("Link copied!");
    });
  };

  const columns = [
    {
      title: "Created",
      dataIndex: "created",
      key: "created",
      render: (v: string) => new Date(v).toLocaleString(),
      width: 160,
    },
    {
      title: "Expires",
      dataIndex: "expires",
      key: "expires",
      render: (v: string) => new Date(v).toLocaleString(),
      width: 160,
    },
    {
      title: "Key",
      dataIndex: "hash",
      key: "hash",
      width: 120,
    },
    {
      title: "Status",
      dataIndex: "active",
      key: "active",
      render: (v: boolean) =>
        v ? (
          <Tag color="green">Active</Tag>
        ) : (
          <Tag color="default">Expired</Tag>
        ),
      width: 100,
    },
    {
      title: "Actions",
      key: "actions",
      render: (_: any, record: any) => (
        <Space>
          <Tooltip title="Copy link">
            <Button
              size="small"
              icon={<CopyOutlined />}
              onClick={() =>
                copyLink(
                  `${window.location.origin}/view/${record.hash.replace("…", "")}`,
                )
              }
            />
          </Tooltip>
          {record.active && (
            <Popconfirm
              title="Revoke this share link?"
              description="The link will stop working immediately."
              onConfirm={() => handleRevoke(record.id)}
              okText="Revoke"
              cancelText="Cancel"
            >
              <Button
                size="small"
                danger
                icon={<DeleteOutlined />}
                loading={revoking === record.id}
              />
            </Popconfirm>
          )}
        </Space>
      ),
      width: 120,
    },
  ];

  return (
    <Content
      style={{
        padding: 24,
        background: "var(--bg-surface, #fff)",
        minHeight: 360,
        maxWidth: 600,
        borderRadius: 8,
      }}
    >
      <Form form={form} onFinish={handleSubmit} layout="vertical">
        <Form.Item
          name="duration"
          label="Share duration (hours)"
          rules={[{ required: true, message: "Please enter duration!" }]}
        >
          <InputNumber
            min={1}
            max={8760}
            style={{ width: "100%" }}
            placeholder="e.g., 24"
          />
        </Form.Item>
        <Form.Item>
          <Button
            type="primary"
            htmlType="submit"
            loading={loading}
            icon={<ShareAltOutlined />}
            size="large"
          >
            Generate Share Link
          </Button>
        </Form.Item>
      </Form>
      {key !== null && (
        <Modal
          open={key !== null}
          title="Share Link"
          footer={null}
          onCancel={() => setKey(null)}
        >
          <Space direction="vertical" style={{ width: "100%" }}>
            <Row gutter={8} align="middle">
              <Col flex="auto">
                <Input
                  value={shareUrl}
                  readOnly
                  style={{ fontFamily: "monospace", fontSize: 13 }}
                />
              </Col>
              <Col>
                <Tooltip title={copied ? "Copied!" : "Copy link"}>
                  <Button
                    icon={copied ? <CheckOutlined /> : <CopyOutlined />}
                    onClick={copyToClipboard}
                    type={copied ? "primary" : "default"}
                  />
                </Tooltip>
              </Col>
              <Col>
                <Button icon={<ShareAltOutlined />} onClick={nativeShare}>
                  Share
                </Button>
              </Col>
            </Row>
            <Text type="secondary" style={{ fontSize: 12 }}>
              This link expires after the specified duration. Anyone with the
              link can view the study.
            </Text>
          </Space>
        </Modal>
      )}
      <div style={{ marginTop: 24 }}>
        <Text
          strong
          style={{ fontSize: 14, display: "block", marginBottom: 12 }}
        >
          <LinkOutlined /> Existing Share Links
        </Text>
        <Table
          dataSource={links}
          columns={columns}
          rowKey="id"
          loading={linksLoading}
          pagination={false}
          size="small"
          locale={{ emptyText: "No share links created yet" }}
        />
      </div>
    </Content>
  );
}

export default Share;
