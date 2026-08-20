import React, { useState, useEffect, useCallback } from "react";
import {
  Modal,
  Form,
  Input,
  Select,
  Button,
  Table,
  Tag,
  Badge,
  Space,
  Card,
  Popconfirm,
  App,
} from "antd";
import {
  AlertOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  ClockCircleOutlined,
} from "@ant-design/icons";
import { request } from "../helpers";
import { useAuth } from "../auth/AuthContext";

export interface CriticalResultItem {
  id: string;
  report_id?: string;
  exam_id?: string;
  accession_number: string;
  patient_id: string;
  patient_name?: string;
  finding_description: string;
  recipient_id?: string;
  recipient_name?: string;
  recipient_role?: string;
  status: "flagged" | "acknowledged" | "escalated" | "cleared";
  flagged_by?: string;
  flagged_at?: string;
  acknowledged_by?: string;
  acknowledged_at?: string;
  escalated_at?: string;
}

interface FlagCriticalModalProps {
  visible: boolean;
  exam?: any;
  report?: any;
  onClose: () => void;
  onSuccess: () => void;
}

export function FlagCriticalModal({
  visible,
  exam,
  report,
  onClose,
  onSuccess,
}: FlagCriticalModalProps) {
  const { message } = App.useApp();
  const [form] = Form.useForm();
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (values: any) => {
    setSubmitting(true);
    try {
      await request("notifications/critical", {
        method: "POST",
        body: {
          report_id: report?.id,
          exam_id: exam?.id,
          accession_number: exam?.accession_number || "",
          patient_id: exam?.patient_id || "",
          patient_name: exam?.patient_name || "",
          finding_description: values.finding_description,
          recipient_role: values.recipient_role || "ed_physician",
          recipient_name: values.recipient_name || "ED Attending Physician",
        },
      });
      message.success("Critical finding flagged & notification dispatched!");
      form.resetFields();
      onSuccess();
      onClose();
    } catch (e: any) {
      message.error(e.message || "Failed to flag critical finding");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Modal
      title={
        <Space>
          <AlertOutlined style={{ color: "#ff4d4f" }} />
          <span>Flag Critical Result</span>
        </Space>
      }
      open={visible}
      onCancel={onClose}
      onOk={() => form.submit()}
      confirmLoading={submitting}
      okText="Flag & Notify Immediately"
      okButtonProps={{ danger: true }}
    >
      <Form
        form={form}
        layout="vertical"
        onFinish={handleSubmit}
        initialValues={{ recipient_role: "ed_physician" }}
      >
        <Form.Item
          name="finding_description"
          label="Critical Finding Description"
          rules={[{ required: true, message: "Please describe the critical finding" }]}
        >
          <Input.TextArea
            rows={4}
            placeholder="e.g. Acute intracranial hemorrhage / tension pneumothorax / pulmonary embolism..."
          />
        </Form.Item>

        <Form.Item name="recipient_role" label="Target Recipient Role">
          <Select
            options={[
              { value: "ed_physician", label: "ED Attending Physician (Immediate)" },
              { value: "ordering_physician", label: "Ordering Physician" },
              { value: "radiologist", label: "On-Call Radiologist / Escalation" },
            ]}
          />
        </Form.Item>

        <Form.Item name="recipient_name" label="Recipient Name / Note (Optional)">
          <Input placeholder="e.g. Dr. Smith (Emergency Dept)" />
        </Form.Item>
      </Form>
    </Modal>
  );
}

export function CriticalResultsList() {
  const { message } = App.useApp();
  const [data, setData] = useState<CriticalResultItem[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchCriticalResults = useCallback(() => {
    setLoading(true);
    request("notifications/critical")
      .then((res: any) => {
        setData(Array.isArray(res.data) ? res.data : []);
      })
      .catch((e: any) => message.error(e.message))
      .finally(() => setLoading(false));
  }, [message]);

  useEffect(() => {
    fetchCriticalResults();
    const interval = setInterval(fetchCriticalResults, 15000);
    return () => clearInterval(interval);
  }, [fetchCriticalResults]);

  const handleAck = async (id: string) => {
    try {
      await request(`notifications/critical/${id}/ack`, { method: "POST" });
      message.success("Critical result acknowledged!");
      fetchCriticalResults();
    } catch (e: any) {
      message.error(e.message);
    }
  };

  const columns = [
    {
      title: "Status",
      dataIndex: "status",
      key: "status",
      width: 130,
      render: (s: string) => {
        if (s === "flagged") {
          return <Tag color="red" icon={<AlertOutlined />}>FLAGGED</Tag>;
        }
        if (s === "escalated") {
          return <Tag color="volcano" icon={<ExclamationCircleOutlined />}>ESCALATED</Tag>;
        }
        if (s === "acknowledged") {
          return <Tag color="green" icon={<CheckCircleOutlined />}>ACKNOWLEDGED</Tag>;
        }
        return <Tag>{s.toUpperCase()}</Tag>;
      },
    },
    {
      title: "Accession",
      dataIndex: "accession_number",
      key: "accession_number",
      width: 130,
    },
    {
      title: "Patient",
      key: "patient",
      render: (_: any, r: CriticalResultItem) => (
        <span>{r.patient_name || r.patient_id}</span>
      ),
    },
    {
      title: "Critical Finding",
      dataIndex: "finding_description",
      key: "finding_description",
    },
    {
      title: "Recipient",
      key: "recipient",
      width: 180,
      render: (_: any, r: CriticalResultItem) => (
        <span>{r.recipient_name || r.recipient_role || "ED Physician"}</span>
      ),
    },
    {
      title: "Flagged At",
      dataIndex: "flagged_at",
      key: "flagged_at",
      width: 170,
      render: (v: string) => (v ? new Date(v).toLocaleString() : "—"),
    },
    {
      title: "Action",
      key: "action",
      width: 140,
      render: (_: any, r: CriticalResultItem) => (
        r.status !== "acknowledged" ? (
          <Popconfirm
            title="Acknowledge critical result?"
            description="Stamps your identity & time of acknowledgment."
            onConfirm={() => handleAck(r.id)}
          >
            <Button size="small" type="primary" danger icon={<CheckCircleOutlined />}>
              Acknowledge
            </Button>
          </Popconfirm>
        ) : (
          <span style={{ color: "#52c41a" }}>
            Ack: {r.acknowledged_at ? new Date(r.acknowledged_at).toLocaleTimeString() : "Yes"}
          </span>
        )
      ),
    },
  ];

  return (
    <Card title="Critical Findings & Alerts" size="small" style={{ marginTop: 16 }}>
      <Table
        rowKey="id"
        columns={columns}
        dataSource={data}
        loading={loading}
        pagination={{ pageSize: 10 }}
        size="small"
      />
    </Card>
  );
}
