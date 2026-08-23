import { useDocumentTitle, useTenantRefetch } from "../hooks";
import React, { useCallback, useEffect, useState } from "react";
import {
  App,
  Layout,
  Card,
  Form,
  Select,
  Input,
  Button,
  Timeline,
  Tag,
  Space,
  Alert,
  Empty,
  Typography,
  Divider,
  Spin,
  Modal,
} from "antd";
import {
  SolutionOutlined,
  ArrowLeftOutlined,
  SendOutlined,
  ClockCircleOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ReloadOutlined,
} from "@ant-design/icons";
import { useNavigate } from "react-router";
import withSidebar from "../common/base";
import { PageState } from "../common/PageState";
import {
  listScope,
  listFollowUps,
  createFollowUp,
  updateFollowUp,
  type PortalScope,
  type PortalFollowUp,
} from "../api/portal";
import "./Portal.css";

const { Text, Paragraph } = Typography;
const Content = Layout.Content;

const FOLLOWUP_STATUS_CONFIG: Record<
  string,
  { color: string; icon: React.ReactNode; label: string }
> = {
  submitted: {
    color: "blue",
    icon: <ClockCircleOutlined />,
    label: "Submitted",
  },
  acknowledged: {
    color: "orange",
    icon: <ClockCircleOutlined />,
    label: "In Progress",
  },
  completed: {
    color: "green",
    icon: <CheckCircleOutlined />,
    label: "Completed",
  },
  cancelled: {
    color: "red",
    icon: <CloseCircleOutlined />,
    label: "Cancelled",
  },
};

const REASON_OPTIONS = [
  { value: "result_question", label: "Question about results" },
  { value: "appointment_request", label: "Request appointment" },
  { value: "referral_status", label: "Referral status" },
  { value: "other", label: "Other" },
];

const CONTACT_OPTIONS = [
  { value: "phone", label: "Phone" },
  { value: "email", label: "Email" },
];

function FollowUpHub() {
  const { message } = App.useApp();
  useDocumentTitle("QuantumPACS - Follow-up Requests");
  const navigate = useNavigate();

  const [scope, setScope] = useState<PortalScope[]>([]);
  const [loadingScope, setLoadingScope] = useState(true);
  const [activePatientId, setActivePatientId] = useState<string | null>(null);
  const [followUps, setFollowUps] = useState<PortalFollowUp[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [form] = Form.useForm();

  const loadScope = useCallback(() => {
    setLoadingScope(true);
    setError(null);
    listScope()
      .then((rows) => {
        setScope(rows);
        if (rows.length > 0) setActivePatientId(rows[0].patient_id);
        else setActivePatientId(null);
      })
      .catch((e: any) => setError(e.message || "Failed to load follow-ups"))
      .finally(() => setLoadingScope(false));
  }, []);

  useEffect(() => {
    loadScope();
  }, [loadScope]);

  useTenantRefetch(loadScope);

  const loadFollowUps = useCallback(() => {
    setLoading(true);
    setError(null);
    listFollowUps()
      .then((rows) => {
        setFollowUps(rows);
      })
      .catch((e: any) => {
        setError(e.message || "Failed to load follow-ups");
      })
      .finally(() => {
        setLoading(false);
      });
  }, []);

  useEffect(() => {
    loadFollowUps();
  }, [loadFollowUps]);

  const handleSubmit = async (values: any) => {
    if (!activePatientId) return;
    setSubmitting(true);
    try {
      await createFollowUp({
        patient_id: activePatientId,
        reason: values.reason,
        contact_method: values.contact_method,
        note: values.note || "",
        priority: values.priority || "routine",
      });
      message.success("Follow-up request submitted");
      form.resetFields();
      loadFollowUps();
    } catch (e: any) {
      message.error(e.message || "Failed to submit request");
    } finally {
      setSubmitting(false);
    }
  };

  const handleCancel = (id: string) => {
    Modal.confirm({
      title: "Cancel this follow-up request?",
      content: "This action cannot be undone.",
      okText: "Yes, cancel",
      okType: "danger",
      onOk: async () => {
        try {
          await updateFollowUp(id, { status: "cancelled" });
          message.success("Follow-up request cancelled");
          loadFollowUps();
        } catch (e: any) {
          message.error(e.message || "Failed to cancel");
        }
      },
    });
  };

  // Group by status
  const activeRequests = followUps.filter(
    (f) => f.status === "submitted" || f.status === "acknowledged",
  );
  const completedRequests = followUps.filter(
    (f) => f.status === "completed" || f.status === "cancelled",
  );

  return (
    <Content className="portal-home" role="main">
      <div className="portal-home-header">
        <div>
          <h2 style={{ margin: 0 }}>
            <SolutionOutlined style={{ marginRight: 8 }} />
            Follow-up Requests
          </h2>
          <Text type="secondary">
            Request follow-ups and track their status
          </Text>
        </div>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={loadFollowUps}>
            Refresh
          </Button>
          <Button onClick={() => navigate("/portal")}>
            <ArrowLeftOutlined /> Back to Portal
          </Button>
        </Space>
      </div>

      {error && (
        <Alert
          type="warning"
          title="Some data could not be loaded"
          description={error}
          showIcon
          closable
          style={{ marginBottom: 16 }}
        />
      )}

      {/* Request Form */}
      <Card
        className="portal-card"
        title={
          <span>
            <SendOutlined style={{ marginRight: 6 }} />
            New Request
          </span>
        }
        style={{ marginBottom: 16 }}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
          initialValues={{ contact_method: "phone", priority: "routine" }}
        >
          <Form.Item
            name="reason"
            label="Reason for follow-up"
            rules={[{ required: true, message: "Please select a reason" }]}
          >
            <Select
              placeholder="Select a reason"
              options={REASON_OPTIONS}
            />
          </Form.Item>

          <Form.Item
            name="contact_method"
            label="Preferred contact method"
            rules={[{ required: true, message: "Please select a method" }]}
          >
            <Select options={CONTACT_OPTIONS} />
          </Form.Item>

          <Form.Item name="note" label="Additional details (optional)">
            <Input.TextArea
              placeholder="Describe your question or request..."
              rows={3}
              maxLength={500}
              showCount
            />
          </Form.Item>

          <Form.Item>
            <Button
              type="primary"
              htmlType="submit"
              loading={submitting}
              icon={<SendOutlined />}
            >
              Submit Request
            </Button>
          </Form.Item>
        </Form>
      </Card>

      {/* Active Requests */}
      <Card
        className="portal-card"
        title={
          <span>
            <ClockCircleOutlined style={{ marginRight: 6 }} />
            Active Requests ({activeRequests.length})
          </span>
        }
        style={{ marginBottom: 16 }}
      >
        <PageState
          loading={loading}
          error={null}
          empty={activeRequests.length === 0}
          emptyMessage="No active follow-up requests"
        >
          <Timeline
            items={activeRequests.map((fu) => {
              const cfg = FOLLOWUP_STATUS_CONFIG[fu.status || "submitted"] || FOLLOWUP_STATUS_CONFIG.submitted;
              return {
                dot: cfg.icon,
                color: cfg.color,
                children: (
                  <div key={fu.id}>
                    <Space>
                      <Tag color={cfg.color}>{cfg.label}</Tag>
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        {fu.created_at
                          ? new Date(fu.created_at).toLocaleString()
                          : ""}
                      </Text>
                    </Space>
                    <Paragraph style={{ margin: "4px 0", fontSize: 13 }}>
                      {fu.reason || "No reason specified"}
                    </Paragraph>
                    {fu.status === "submitted" && (
                      <Button
                        size="small"
                        danger
                        onClick={() => handleCancel(fu.id)}
                      >
                        Cancel
                      </Button>
                    )}
                  </div>
                ),
              };
            })}
          />
        </PageState>
      </Card>

      {/* Completed / Cancelled Requests */}
      {completedRequests.length > 0 && (
        <Card
          className="portal-card"
          title={
            <span>
              <CheckCircleOutlined style={{ marginRight: 6 }} />
              Past Requests ({completedRequests.length})
            </span>
          }
        >
          <Timeline
            items={completedRequests.map((fu) => {
              const cfg = FOLLOWUP_STATUS_CONFIG[fu.status || "completed"] || FOLLOWUP_STATUS_CONFIG.completed;
              return {
                dot: cfg.icon,
                color: cfg.color,
                children: (
                  <div key={fu.id}>
                    <Space>
                      <Tag color={cfg.color}>{cfg.label}</Tag>
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        {fu.created_at
                          ? new Date(fu.created_at).toLocaleString()
                          : ""}
                      </Text>
                    </Space>
                    <Paragraph style={{ margin: "4px 0", fontSize: 13 }}>
                      {fu.reason || "No reason specified"}
                    </Paragraph>
                  </div>
                ),
              };
            })}
          />
        </Card>
      )}
    </Content>
  );
}

export default withSidebar(FollowUpHub);
