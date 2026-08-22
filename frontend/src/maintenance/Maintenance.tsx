import { useDocumentTitle } from "../hooks";
import React, { useCallback, useEffect, useState } from "react";
import {
  App,
  Layout,
  Card,
  Button,
  Space,
  Typography,
  Tag,
  Modal,
  Form,
  Input,
  InputNumber,
  Popconfirm,
  Table,
  Alert,
} from "antd";
import { PlayCircleOutlined, PauseCircleOutlined } from "@ant-design/icons";
import withSidebar from "../common/base";
import PageHeader from "../common/PageHeader";
import { PageState } from "../common/PageState";
import {
  getAdminStatus,
  setMaintenance,
  type MaintenanceState,
} from "../api/admin";
import { listLogs } from "../api/logs";
import { useAuth } from "../auth/AuthContext";
import { useTenantRefetch } from "../hooks";

const { Content } = Layout;
const { Text } = Typography;

interface MaintenanceEvent {
  id: number;
  created_at?: string | null;
  actor: string;
  description: string;
}

function Maintenance() {
  const { message } = App.useApp();
  useDocumentTitle("QuantumPACS - Maintenance Mode");
  const { hasPermission } = useAuth();
  const [state, setState] = useState<MaintenanceState | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [enterOpen, setEnterOpen] = useState(false);
  const [form] = Form.useForm();
  const [events, setEvents] = useState<MaintenanceEvent[]>([]);

  const canToggle = hasPermission("SYSTEM_ADMIN");

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    getAdminStatus()
      .then((res) => setState(res.maintenance))
      .catch((e: any) => setError(e.message))
      .finally(() => setLoading(false));
    listLogs({ limit: 8, event_type: "system.maintenance_mode" })
      .then((res) =>
        setEvents(
          (res.data ?? []).slice(0, 5).map((l) => ({
            id: l.id,
            created_at: l.created_at,
            actor: l.actor ?? "system",
            description: l.description ?? "",
          })),
        ),
      )
      .catch(() => {});
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  useTenantRefetch(load);

  const enterMaintenance = async () => {
    const values = await form.validateFields();
    setSubmitting(true);
    try {
      await setMaintenance(true, values.reason);
      message.success("Maintenance mode enabled");
      setEnterOpen(false);
      form.resetFields();
      load();
    } catch (e: any) {
      message.error(e.message);
    } finally {
      setSubmitting(false);
    }
  };

  const exitMaintenance = async () => {
    setSubmitting(true);
    try {
      await setMaintenance(false, "");
      message.success("Maintenance mode disabled — writes resumed");
      load();
    } catch (e: any) {
      message.error(e.message);
    } finally {
      setSubmitting(false);
    }
  };

  const active = state?.active ?? false;

  return (
    <Content style={{ padding: 24 }}>
      <PageHeader
        title="Maintenance Mode"
        description="Pause platform writes before an upgrade or migration. Reads stay available; users see a banner explaining the pause."
      />

      <PageState loading={loading} error={error} onRetry={load}>
        <Space direction="vertical" style={{ width: "100%" }} size={16}>
          <Card size="small">
            <Space align="center" size={16} wrap>
              <span
                className={`dashboard-health-dot dashboard-health-dot-${active ? "error" : "ok"}`}
                style={{
                  width: 12,
                  height: 12,
                  borderRadius: "50%",
                  display: "inline-block",
                }}
                aria-hidden="true"
              />
              {active ? (
                <>
                  <Tag color="orange">MAINTENANCE ACTIVE</Tag>
                  <Text>
                    since{" "}
                    {state?.since
                      ? new Date(state.since).toLocaleString()
                      : "—"}
                  </Text>
                  {state?.reason && (
                    <Text type="secondary">Reason: {state.reason}</Text>
                  )}
                </>
              ) : (
                <>
                  <Tag color="green">PLATFORM ONLINE</Tag>
                  <Text type="secondary">All writes allowed</Text>
                </>
              )}
            </Space>
            <div style={{ marginTop: 16 }}>
              {active ? (
                <Popconfirm
                  title="Exit maintenance mode?"
                  description="Resumes all clinical and platform writes."
                  onConfirm={exitMaintenance}
                  okText="Resume writes"
                >
                  <Button
                    type="primary"
                    icon={<PlayCircleOutlined />}
                    loading={submitting}
                    disabled={!canToggle}
                  >
                    Exit maintenance
                  </Button>
                </Popconfirm>
              ) : (
                <Button
                  danger
                  icon={<PauseCircleOutlined />}
                  disabled={!canToggle}
                  onClick={() => setEnterOpen(true)}
                >
                  Enter maintenance
                </Button>
              )}
              {!canToggle && (
                <Text type="secondary" style={{ marginLeft: 12, fontSize: 12 }}>
                  Only the platform admin can toggle maintenance.
                </Text>
              )}
            </div>
          </Card>

          <Card size="small" title="Recent maintenance events">
            {events.length === 0 ? (
              <Text type="secondary">No maintenance events recorded.</Text>
            ) : (
              <Table
                size="small"
                rowKey="id"
                pagination={false}
                dataSource={events}
                columns={[
                  {
                    title: "Time",
                    dataIndex: "created_at",
                    width: 200,
                    render: (t: string) =>
                      t ? new Date(t).toLocaleString() : "—",
                  },
                  { title: "Actor", dataIndex: "actor", width: 160 },
                  { title: "Event", dataIndex: "description" },
                ]}
              />
            )}
          </Card>
        </Space>
      </PageState>

      <Modal
        title="Enter maintenance mode"
        open={enterOpen}
        onCancel={() => setEnterOpen(false)}
        onOk={enterMaintenance}
        okText="Enter maintenance"
        confirmLoading={submitting}
        okButtonProps={{ danger: true }}
      >
        <Alert
          type="warning"
          showIcon
          style={{ marginBottom: 16 }}
          title="This blocks all clinical and platform writes until you exit maintenance."
        />
        <Form form={form} layout="vertical">
          <Form.Item
            name="reason"
            label="Reason"
            rules={[{ required: true, message: "A reason is required" }]}
          >
            <Input.TextArea
              placeholder="e.g. v3 release migration window"
              maxLength={500}
              rows={3}
            />
          </Form.Item>
          <Form.Item
            name="duration_hours"
            label="Expected duration (hours, optional)"
          >
            <InputNumber
              min={1}
              max={720}
              style={{ width: "100%" }}
              placeholder="Optional"
            />
          </Form.Item>
        </Form>
      </Modal>
    </Content>
  );
}

export default withSidebar(Maintenance);
