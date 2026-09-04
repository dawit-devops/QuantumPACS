import { useDocumentTitle } from "../hooks";
import React, { useState, useEffect, useCallback } from "react";
import { App, Layout, Table, Tag, Button, Space, Input, Modal, Form, Select } from "antd";
import { ReloadOutlined, PlusOutlined, CheckCircleOutlined } from "@ant-design/icons";
import withSidebar from "../common/base";
import { PageState } from "../common/PageState";
import {
  listHandoffNotes,
  createHandoffNote,
  markHandoffNoteRead,
  type HandoffNote,
} from "../api/ris";
import "./HandoffNotes.css";

const Content = Layout.Content;

const PRIORITY_COLORS: Record<string, string> = {
  low: "default",
  normal: "blue",
  high: "orange",
  urgent: "red",
};

const PRIORITY_OPTIONS = [
  { value: "low", label: "Low" },
  { value: "normal", label: "Normal" },
  { value: "high", label: "High" },
  { value: "urgent", label: "Urgent" },
];

function HandoffNotes() {
  const { message } = App.useApp();
  useDocumentTitle("QuantumPACS - Handoff Notes");
  const [notes, setNotes] = useState<HandoffNote[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [patientFilter, setPatientFilter] = useState("");
  const [unreadOnly, setUnreadOnly] = useState(false);
  const [createOpen, setCreateOpen] = useState(false);
  const [createForm] = Form.useForm();

  const fetch = useCallback(() => {
    setLoading(true);
    setError(null);
    listHandoffNotes({
      patient_id: patientFilter || undefined,
      unread_only: unreadOnly || undefined,
    })
      .then((data) => {
        setLoading(false);
        setNotes(data || []);
      })
      .catch((e: any) => {
        setLoading(false);
        setError(e.message);
        message.error(e.message);
      });
  }, [message, patientFilter, unreadOnly]);

  useEffect(() => {
    fetch();
  }, [fetch]);

  const handleCreate = async (values: any) => {
    try {
      await createHandoffNote({
        patient_id: values.patient_id,
        note: values.note,
        priority: values.priority || "normal",
      });
      message.success("Handoff note created");
      setCreateOpen(false);
      createForm.resetFields();
      fetch();
    } catch (e: any) {
      message.error(e.message || "Create failed");
    }
  };

  const handleMarkRead = async (id: string) => {
    try {
      await markHandoffNoteRead(id);
      message.success("Marked as read");
      fetch();
    } catch (e: any) {
      message.error(e.message || "Failed to mark as read");
    }
  };

  const columns: any[] = [
    {
      title: "Patient",
      dataIndex: "patient_id",
      width: "12%",
    },
    {
      title: "Priority",
      dataIndex: "priority",
      width: "10%",
      render: (p: string) => (
        <Tag color={PRIORITY_COLORS[p] || "default"}>{(p || "normal").toUpperCase()}</Tag>
      ),
    },
    {
      title: "Note",
      dataIndex: "note",
      width: "40%",
      render: (v: string) => <span className="handoff-note-text">{v || "-"}</span>,
    },
    {
      title: "Created",
      dataIndex: "created_at",
      width: "16%",
      render: (v: string) => (v ? new Date(v).toLocaleString() : "-"),
    },
    {
      title: "Status",
      key: "status",
      width: "10%",
      render: (_: unknown, row: HandoffNote) =>
        row.is_read ? (
          <Tag icon={<CheckCircleOutlined />} color="default">
            Read
          </Tag>
        ) : (
          <Tag color="blue">Unread</Tag>
        ),
    },
    {
      title: "",
      key: "action",
      width: "12%",
      render: (_: unknown, row: HandoffNote) =>
        !row.is_read ? (
          <Button size="small" onClick={() => handleMarkRead(row.id)}>
            Mark Read
          </Button>
        ) : null,
    },
  ];

  return (
    <Content style={{ padding: 24 }} role="main">
      <div className="handoff-header">
        <div>
          <h2 style={{ margin: 0 }}>Handoff Notes</h2>
          <span className="handoff-subtitle">
            Coordinator handoff notes — visible to the next coordinator handling the patient
          </span>
        </div>
        <Space>
          <Input
            placeholder="Filter by patient ID"
            allowClear
            style={{ width: 200 }}
            value={patientFilter}
            onChange={(e) => setPatientFilter(e.target.value)}
          />
          <Select
            allowClear
            placeholder="Filter: all"
            style={{ width: 130 }}
            options={[{ value: "unread", label: "Unread only" }]}
            value={unreadOnly ? "unread" : undefined}
            onChange={(v) => setUnreadOnly(v === "unread")}
          />
          <Button icon={<PlusOutlined />} type="primary" onClick={() => setCreateOpen(true)}>
            New Note
          </Button>
          <Button icon={<ReloadOutlined />} onClick={fetch}>
            Refresh
          </Button>
        </Space>
      </div>

      <PageState
        error={error}
        onRetry={() => fetch()}
        empty={!loading && !error && notes.length === 0}
        emptyMessage="No handoff notes yet"
      >
        <Table
          rowKey="id"
          columns={columns}
          dataSource={notes}
          loading={loading}
          pagination={{ pageSize: 20 }}
          size="middle"
        />
      </PageState>

      <Modal
        title="New Handoff Note"
        open={createOpen}
        onCancel={() => setCreateOpen(false)}
        footer={null}
        width={520}
      >
        <Form
          form={createForm}
          layout="vertical"
          onFinish={handleCreate}
          initialValues={{ priority: "normal" }}
        >
          <Form.Item
            name="patient_id"
            label="Patient ID"
            rules={[{ required: true, message: "Patient ID is required" }]}
          >
            <Input placeholder="e.g. P001" />
          </Form.Item>
          <Form.Item
            name="note"
            label="Note"
            rules={[{ required: true, message: "Note text is required" }]}
          >
            <Input.TextArea rows={4} placeholder="Details for the next coordinator…" />
          </Form.Item>
          <Form.Item name="priority" label="Priority">
            <Select options={PRIORITY_OPTIONS} />
          </Form.Item>
          <Button type="primary" htmlType="submit" block>
            Create Note
          </Button>
        </Form>
      </Modal>
    </Content>
  );
}

export default withSidebar(HandoffNotes);
