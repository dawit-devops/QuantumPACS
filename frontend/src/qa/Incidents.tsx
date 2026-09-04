import { useDocumentTitle } from "../hooks";
import React, { useState, useEffect, useCallback } from "react";
import {
  App,
  Layout,
  Table,
  Button,
  Input,
  Select,
  Modal,
  Form,
  InputNumber,
  Alert,
  Space,
  Tag,
} from "antd";
import { PlusOutlined, ReloadOutlined } from "@ant-design/icons";
import withSidebar from "../common/base";
import { useAuth } from "../auth/AuthContext";
import { request } from "../helpers";
import "./Incidents.css";

const Content = Layout.Content;
const { TextArea } = Input;

const INCIDENT_TYPES = [
  "positioning",
  "artifact",
  "protocol_deviation",
  "patient_motion",
  "equipment_malfunction",
  "contrast_extravasation",
];

const SEVERITY_COLORS: Record<string, string> = {
  low: "default",
  medium: "orange",
  high: "red",
  critical: "magenta",
};

function Incidents() {
  const { message } = App.useApp();
  useDocumentTitle("QuantumPACS - Incidents");
  const { hasPermission } = useAuth();
  const canWrite = hasPermission("QA_WRITE");
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [form] = Form.useForm();
  const [typeFilter, setTypeFilter] = useState<string | undefined>();
  const [statusFilter, setStatusFilter] = useState<string | undefined>();
  const [search, setSearch] = useState("");

  const fetchIncidents = useCallback(() => {
    setLoading(true);
    const query: Record<string, string> = {};
    if (typeFilter) query.incident_type = typeFilter;
    if (statusFilter) query.status = statusFilter;
    if (search) query.search = search;
    request("qa/incidents", { query })
      .then((res: any) => {
        setLoading(false);
        setData(Array.isArray(res.data) ? res.data : []);
      })
      .catch((e: any) => {
        setLoading(false);
        setError(e.message);
      });
  }, [typeFilter, statusFilter, search]);

  useEffect(() => {
    fetchIncidents();
  }, [fetchIncidents]);

  const submit = async () => {
    const values = await form.validateFields();
    try {
      await request("qa/incidents", { method: "POST", data: values });
      message.success("Incident logged");
      setModalOpen(false);
      form.resetFields();
      fetchIncidents();
    } catch (e: any) {
      message.error(e.message || "Failed to log incident");
    }
  };

  const resolve = async (id: string, notes: string) => {
    try {
      await request(`qa/incidents/${id}/resolve`, {
        method: "POST",
        data: { notes },
      });
      message.success("Incident resolved");
      fetchIncidents();
    } catch (e: any) {
      message.error(e.message || "Failed to resolve incident");
    }
  };

  const columns = [
    {
      title: "Type",
      dataIndex: "incident_type",
      key: "type",
      render: (v: string) => <Tag>{v}</Tag>,
    },
    {
      title: "Severity",
      dataIndex: "severity",
      key: "severity",
      render: (v: string) => (
        <Tag color={SEVERITY_COLORS[v] || "default"}>{v}</Tag>
      ),
    },
    {
      title: "Patient / Accession",
      key: "context",
      render: (_: any, row: any) => (
        <span>
          {row.patient_name || "-"}{" "}
          {row.accession_number ? `(${row.accession_number})` : ""}
        </span>
      ),
    },
    {
      title: "Description",
      dataIndex: "description",
      key: "desc",
      ellipsis: true,
    },
    {
      title: "Status",
      dataIndex: "status",
      key: "status",
      render: (v: string) => (
        <Tag
          color={
            v === "resolved" ? "green" : v === "in_progress" ? "blue" : "gold"
          }
        >
          {v || "open"}
        </Tag>
      ),
    },
    {
      title: "",
      key: "actions",
      render: (_: any, row: any) =>
        canWrite && row.status !== "resolved" ? (
          <ResolveButton incidentId={row.id} onResolve={resolve} />
        ) : null,
    },
  ];

  return (
    <Content style={{ padding: "16px" }}>
      <div className="qa-header">
        <h2>Incidents &amp; Retakes</h2>
        <Space>
          <Select
            allowClear
            placeholder="Type"
            style={{ width: 180 }}
            value={typeFilter}
            onChange={setTypeFilter}
            options={INCIDENT_TYPES.map((t) => ({ value: t, label: t }))}
          />
          <Select
            allowClear
            placeholder="Status"
            style={{ width: 120 }}
            value={statusFilter}
            onChange={setStatusFilter}
            options={["open", "in_progress", "resolved"].map((s) => ({
              value: s,
              label: s,
            }))}
          />
          <Input
            allowClear
            placeholder="Search patient / accession"
            style={{ width: 200 }}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <Button
            icon={<ReloadOutlined />}
            onClick={fetchIncidents}
            aria-label="Refresh incidents"
          />
          {canWrite && (
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => setModalOpen(true)}
            >
              Log Incident
            </Button>
          )}
        </Space>
      </div>
      {error && (
        <Alert
          type="error"
          showIcon
          title={error}
          style={{ margin: "8px 0" }}
        />
      )}
      <Table
        rowKey="id"
        loading={loading}
        columns={columns}
        dataSource={data}
        pagination={false}
      />

      <Modal
        title="Log Incident"
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={submit}
        okText="Log incident"
        width={560}
      >
        <Form
          form={form}
          layout="vertical"
          initialValues={{ severity: "medium" }}
        >
          <Form.Item
            name="exam_id"
            label="Exam ID"
            rules={[{ required: true, message: "Exam ID required" }]}
          >
            <Input
              placeholder="Exam UUID (from queue/review)"
              aria-label="Exam ID"
            />
          </Form.Item>
          <div className="proto-form-grid">
            <Form.Item
              name="incident_type"
              label="Incident Type"
              rules={[{ required: true }]}
            >
              <Select
                options={INCIDENT_TYPES.map((t) => ({ value: t, label: t }))}
              />
            </Form.Item>
            <Form.Item name="severity" label="Severity">
              <Select
                options={["low", "medium", "high", "critical"].map((s) => ({
                  value: s,
                  label: s,
                }))}
              />
            </Form.Item>
          </div>
          <div className="proto-form-grid">
            <Form.Item name="study_uid" label="Study UID (optional)">
              <Input aria-label="Study UID" />
            </Form.Item>
            <Form.Item
              name="repeat_study_uid"
              label="Repeat Study UID (optional)"
            >
              <Input aria-label="Repeat study UID" />
            </Form.Item>
          </div>
          <Form.Item
            name="description"
            label="Description"
            rules={[{ required: true, message: "Description required" }]}
          >
            <TextArea
              rows={3}
              maxLength={500}
              showCount
              aria-label="Description"
            />
          </Form.Item>
        </Form>
      </Modal>
    </Content>
  );
}

function ResolveButton({
  incidentId,
  onResolve,
}: {
  incidentId: string;
  onResolve: (id: string, notes: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const [notes, setNotes] = useState("");
  return (
    <>
      <Button size="small" onClick={() => setOpen(true)}>
        Resolve
      </Button>
      <Modal
        title="Resolve Incident"
        open={open}
        onCancel={() => setOpen(false)}
        onOk={() => {
          onResolve(incidentId, notes);
          setOpen(false);
          setNotes("");
        }}
        okText="Resolve"
      >
        <Input.TextArea
          rows={3}
          placeholder="Resolution notes"
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          aria-label="Resolution notes"
        />
      </Modal>
    </>
  );
}

export default withSidebar(Incidents);
