import { useDocumentTitle } from "../hooks";
import React, { useState, useEffect, useCallback } from "react";
import {
  App,
  Layout,
  Table,
  Tag,
  Button,
  Space,
  Input,
  Modal,
  Form,
  Select,
  InputNumber,
  Switch,
  Tabs,
  Alert,
} from "antd";
import { ReloadOutlined, SendOutlined } from "@ant-design/icons";
import withSidebar from "../common/base";
import { PageState } from "../common/PageState";
import {
  listReminderLog,
  listReminderConfig,
  saveReminderConfig,
  sendReminder,
  listPatientOptOuts,
  setPatientOptOut,
  type MessageLogEntry,
  type ReminderConfig,
  type PatientOptOutEntry,
} from "../api/reminders";
import "./Reminders.css";

const Content = Layout.Content;
const REFRESH_MS = 60000;

const CHANNEL_LABELS: Record<string, string> = {
  sms: "SMS",
  email: "Email",
  phone: "Phone",
};

const EVENT_OPTIONS = [
  { value: "reminder.appointment", label: "Appointment Reminder" },
  { value: "reminder.prior_auth", label: "Prior-Auth Reminder" },
  { value: "reminder.delivery", label: "Result Delivery" },
];

const STATUS_COLORS: Record<string, string> = {
  SENT: "green",
  FAILED: "red",
};

// R2-02: reminders management — per-event config (channel, template, lead
// time, opt-out), a delivery audit log (send/receipt), and manual send.
function Reminders() {
  const { message } = App.useApp();
  useDocumentTitle("QuantumPACS - Reminders");
  const [config, setConfig] = useState<ReminderConfig[]>([]);
  const [log, setLog] = useState<MessageLogEntry[]>([]);
  const [optOuts, setOptOuts] = useState<PatientOptOutEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [configOpen, setConfigOpen] = useState(false);
  const [sendOpen, setSendOpen] = useState(false);
  const [optOutOpen, setOptOutOpen] = useState(false);

  const fetch = useCallback(() => {
    setLoading(true);
    setError(null);
    Promise.all([listReminderConfig(), listReminderLog(), listPatientOptOuts()])
      .then(([cfg, lg, outs]) => {
        setLoading(false);
        setConfig(cfg.data);
        setLog(lg.data);
        setOptOuts(outs.data || []);
      })
      .catch((e: any) => {
        setLoading(false);
        setError(e.message);
        message.error(e.message);
      });
  }, [message]);

  useEffect(() => {
    fetch();
  }, [fetch]);

  useEffect(() => {
    const interval = setInterval(fetch, REFRESH_MS);
    return () => clearInterval(interval);
  }, [fetch]);

  const handleSaveConfig = async (values: any) => {
    try {
      await saveReminderConfig({
        event_type: values.event_type,
        channel: values.channel,
        template: values.template || "",
        lead_time_hours: values.lead_time_hours,
        active: values.active !== false,
      });
      message.success("Reminder config updated");
      setConfigOpen(false);
      fetch();
    } catch (e: any) {
      message.error(e.message || "Save failed");
    }
  };

  const handleSend = async (values: any) => {
    try {
      await sendReminder({
        event_type: values.event_type,
        recipient: values.recipient,
        channel: values.channel,
        subject: values.subject,
        body: values.body,
      });
      message.success("Reminder sent");
      setSendOpen(false);
      fetch();
    } catch (e: any) {
      message.error(e.message || "Send failed");
    }
  };

  const handleOptOut = async (values: any) => {
    try {
      await setPatientOptOut({
        patient_id: values.patient_id,
        event_type: values.event_type || null,
        opted_out: true,
      });
      message.success("Opt-out recorded");
      setOptOutOpen(false);
      fetch();
    } catch (e: any) {
      message.error(e.message || "Save failed");
    }
  };

  const handleOptIn = async (row: PatientOptOutEntry) => {
    try {
      await setPatientOptOut({
        patient_id: row.patient_id,
        event_type: row.event_type || null,
        opted_out: false,
      });
      message.success("Opt-out removed");
      fetch();
    } catch (e: any) {
      message.error(e.message || "Update failed");
    }
  };

  const logColumns: any[] = [
    {
      title: "Sent At",
      dataIndex: "sent_at",
      width: "18%",
      render: (v: string) => (v ? new Date(v).toLocaleString() : "-"),
    },
    {
      title: "Channel",
      dataIndex: "channel",
      width: "10%",
      render: (v: string) => <Tag>{CHANNEL_LABELS[v] || v}</Tag>,
    },
    { title: "Recipient", dataIndex: "recipient", width: "20%" },
    {
      title: "Event",
      dataIndex: "event_type",
      width: "22%",
      render: (v: string) => v || "-",
    },
    {
      title: "Status",
      dataIndex: "status",
      width: "10%",
      render: (s: string) => (
        <Tag color={STATUS_COLORS[s] || "default"}>{s}</Tag>
      ),
    },
    {
      title: "Attempts",
      dataIndex: "attempts",
      width: "8%",
      render: (v: number) => v ?? 1,
    },
    {
      title: "Receipt",
      dataIndex: "provider_receipt",
      width: "14%",
      render: (v: string) => v || "-",
    },
  ];

  const configColumns: any[] = [
    {
      title: "Event",
      dataIndex: "event_type",
      render: (v: string) => v || "-",
    },
    {
      title: "Channel",
      dataIndex: "channel",
      render: (v: string) => CHANNEL_LABELS[v] || v,
    },
    {
      title: "Lead Time (h)",
      dataIndex: "lead_time_hours",
      width: 130,
    },
    {
      title: "Active",
      dataIndex: "active",
      width: 90,
      render: (v: boolean) => (v ? <Tag color="green">On</Tag> : <Tag>Off</Tag>),
    },
  ];

  const optOutColumns: any[] = [
    { title: "Patient", dataIndex: "patient_id", width: "25%" },
    {
      title: "Event",
      dataIndex: "event_type",
      width: "30%",
      render: (v: string | null) => (v ? v : <Tag color="orange">All events</Tag>),
    },
    {
      title: "Since",
      dataIndex: "created_at",
      width: "20%",
      render: (v: string) => (v ? new Date(v).toLocaleDateString() : "-"),
    },
    {
      title: "",
      key: "action",
      width: "25%",
      render: (_: unknown, row: PatientOptOutEntry) => (
        <Button size="small" onClick={() => handleOptIn(row)}>
          Remove
        </Button>
      ),
    },
  ];

  const optOutTab = (
    <PageState
      error={error}
      onRetry={() => fetch()}
      empty={!loading && !error && optOuts.length === 0}
      emptyMessage="No patients have opted out"
    >
      <Button
        onClick={() => setOptOutOpen(true)}
        style={{ marginBottom: 16 }}
      >
        Add Opt-Out
      </Button>
      <Table
        rowKey={(r: PatientOptOutEntry) =>
          `${r.patient_id}|${r.event_type || "*"}`
        }
        columns={optOutColumns}
        dataSource={optOuts}
        loading={loading}
        pagination={false}
        size="middle"
      />
    </PageState>
  );

  const configTab = (
    <div>
      <Button
        icon={<SendOutlined />}
        onClick={() => setConfigOpen(true)}
        style={{ marginBottom: 16 }}
      >
        Edit Config
      </Button>
      <Table
        rowKey="event_type"
        columns={configColumns}
        dataSource={config}
        loading={loading}
        pagination={false}
        size="middle"
        style={{ marginBottom: 16 }}
      />
    </div>
  );

  const logTab = (
    <PageState
      error={error}
      onRetry={() => fetch()}
      empty={!loading && !error && log.length === 0}
      emptyMessage="No reminder deliveries yet"
    >
      <Table
        rowKey="id"
        columns={logColumns}
        dataSource={log}
        loading={loading}
        pagination={{ pageSize: 20 }}
        size="middle"
      />
    </PageState>
  );

  return (
    <Content style={{ padding: 24 }} role="main">
      <div className="reminders-header">
        <h2>Reminders</h2>
        <Space>
          <Button icon={<SendOutlined />} onClick={() => setSendOpen(true)}>
            Send Reminder
          </Button>
          <Button icon={<ReloadOutlined />} onClick={fetch}>
            Refresh
          </Button>
        </Space>
      </div>

      <Tabs
        items={[
          { key: "config", label: "Config", children: configTab },
          { key: "log", label: "Delivery Log", children: logTab },
          { key: "optouts", label: "Patient Opt-Outs", children: optOutTab },
        ]}
      />

      <Modal
        title="Reminder Config"
        open={configOpen}
        onCancel={() => setConfigOpen(false)}
        footer={null}
      >
        <Form
          layout="vertical"
          onFinish={handleSaveConfig}
          initialValues={{ channel: "email", lead_time_hours: 24, active: true }}
        >
          <Form.Item
            name="event_type"
            label="Event Type"
            rules={[{ required: true }]}
          >
            <Select options={EVENT_OPTIONS} />
          </Form.Item>
          <Form.Item name="channel" label="Channel" rules={[{ required: true }]}>
            <Select
              options={[
                { value: "sms", label: "SMS" },
                { value: "email", label: "Email" },
                { value: "phone", label: "Phone" },
              ]}
            />
          </Form.Item>
          <Form.Item name="template" label="Template">
            <Input.TextArea rows={3} placeholder="e.g. Your exam is at {time}" />
          </Form.Item>
          <Form.Item name="lead_time_hours" label="Lead Time (hours)">
            <InputNumber min={1} max={720} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="active" label="Active (opt-out gate)" valuePropName="checked">
            <Switch />
          </Form.Item>
          <Button type="primary" htmlType="submit" block>
            Save Config
          </Button>
        </Form>
      </Modal>

      <Modal
        title="Send Reminder"
        open={sendOpen}
        onCancel={() => setSendOpen(false)}
        footer={null}
      >
        <Form
          layout="vertical"
          onFinish={handleSend}
          initialValues={{ channel: "email" }}
        >
          <Form.Item
            name="event_type"
            label="Event Type"
            rules={[{ required: true }]}
          >
            <Select options={EVENT_OPTIONS} />
          </Form.Item>
          <Form.Item
            name="recipient"
            label="Recipient"
            rules={[{ required: true, message: "Recipient is required" }]}
          >
            <Input placeholder="Email address or phone number" />
          </Form.Item>
          <Form.Item name="channel" label="Channel" rules={[{ required: true }]}>
            <Select
              options={[
                { value: "sms", label: "SMS" },
                { value: "email", label: "Email" },
                { value: "phone", label: "Phone" },
              ]}
            />
          </Form.Item>
          <Form.Item name="subject" label="Subject">
            <Input />
          </Form.Item>
          <Form.Item name="body" label="Body">
            <Input.TextArea rows={3} />
          </Form.Item>
          <Button type="primary" htmlType="submit" block>
            Send
          </Button>
        </Form>
      </Modal>
      <Modal
        title="Add Patient Opt-Out"
        open={optOutOpen}
        onCancel={() => setOptOutOpen(false)}
        footer={null}
      >
        <Form layout="vertical" onFinish={handleOptOut}>
          <Form.Item
            name="patient_id"
            label="Patient ID"
            rules={[{ required: true, message: "Patient ID is required" }]}
          >
            <Input placeholder="e.g. 8675309" />
          </Form.Item>
          <Form.Item
            name="event_type"
            label="Event Type (leave empty for all events)"
          >
            <Select
              allowClear
              placeholder="All events"
              options={EVENT_OPTIONS}
            />
          </Form.Item>
          <Button type="primary" htmlType="submit" block>
            Record Opt-Out
          </Button>
        </Form>
      </Modal>
    </Content>
  );
}

export default withSidebar(Reminders);