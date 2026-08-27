import { useDocumentTitle } from "../hooks";
import React, { useState, useEffect, useCallback } from "react";
import { App, Layout, Table, Tag, Button, Space, Input, Modal, Form, Select } from "antd";
import { ReloadOutlined, PlusOutlined } from "@ant-design/icons";
import withSidebar from "../common/base";
import { PageState } from "../common/PageState";
import { listReferrals, createReferral, updateReferral, type Referral } from "../api/ris";
import "./Referrals.css";

const Content = Layout.Content;

const STATUS_COLORS: Record<string, string> = {
  pending: "blue",
  accepted: "gold",
  completed: "green",
  cancelled: "red",
};

const STATUS_OPTIONS = [
  { value: "pending", label: "Pending" },
  { value: "accepted", label: "Accepted" },
  { value: "completed", label: "Completed" },
  { value: "cancelled", label: "Cancelled" },
];

function ReferralTracking() {
  const { message } = App.useApp();
  useDocumentTitle("QuantumPACS - Referral Tracking");
  const [referrals, setReferrals] = useState<Referral[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string | undefined>();
  const [patientFilter, setPatientFilter] = useState("");
  const [createOpen, setCreateOpen] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [editing, setEditing] = useState<Referral | null>(null);
  const [createForm] = Form.useForm();
  const [editForm] = Form.useForm();

  const fetch = useCallback(() => {
    setLoading(true);
    setError(null);
    listReferrals({
      status: statusFilter,
      patient_id: patientFilter || undefined,
    })
      .then((data) => {
        setLoading(false);
        setReferrals(data || []);
      })
      .catch((e: any) => {
        setLoading(false);
        setError(e.message);
        message.error(e.message);
      });
  }, [message, statusFilter, patientFilter]);

  useEffect(() => {
    fetch();
  }, [fetch]);

  const handleCreate = async (values: any) => {
    try {
      await createReferral({
        patient_id: values.patient_id,
        from_provider: values.from_provider || "",
        to_specialist: values.to_specialist,
        specialty: values.specialty || "",
        notes: values.notes || "",
      });
      message.success("Referral created");
      setCreateOpen(false);
      createForm.resetFields();
      fetch();
    } catch (e: any) {
      message.error(e.message || "Create failed");
    }
  };

  const openEdit = (ref: Referral) => {
    setEditing(ref);
    editForm.setFieldsValue({
      status: ref.status,
      notes: ref.notes,
    });
    setEditOpen(true);
  };

  const handleUpdate = async (values: any) => {
    if (!editing) return;
    try {
      await updateReferral(editing.id, {
        status: values.status,
        notes: values.notes || "",
      });
      message.success("Referral updated");
      setEditOpen(false);
      setEditing(null);
      fetch();
    } catch (e: any) {
      message.error(e.message || "Update failed");
    }
  };

  const columns: any[] = [
    { title: "Patient", dataIndex: "patient_id", width: "10%" },
    { title: "From", dataIndex: "from_provider", width: "14%" },
    { title: "To Specialist", dataIndex: "to_specialist", width: "14%" },
    {
      title: "Specialty",
      dataIndex: "specialty",
      width: "12%",
      render: (v: string) => v || "-",
    },
    {
      title: "Status",
      dataIndex: "status",
      width: "12%",
      render: (s: string) => (
        <Tag color={STATUS_COLORS[s] || "default"}>{s ? s.toUpperCase() : "PENDING"}</Tag>
      ),
    },
    {
      title: "Notes",
      dataIndex: "notes",
      width: "20%",
      render: (v: string) => <span className="referral-note-text">{v || "-"}</span>,
    },
    {
      title: "",
      key: "action",
      width: "10%",
      render: (_: unknown, row: Referral) => (
        <Button size="small" onClick={() => openEdit(row)}>
          Update
        </Button>
      ),
    },
  ];

  return (
    <Content style={{ padding: 24 }} role="main">
      <div className="referral-header">
        <div>
          <h2 style={{ margin: 0 }}>Referral Tracking</h2>
          <span className="referral-subtitle">
            Track referrals from ordering provider to specialist
          </span>
        </div>
        <Space>
          <Input
            placeholder="Filter by patient ID"
            allowClear
            style={{ width: 180 }}
            value={patientFilter}
            onChange={(e) => setPatientFilter(e.target.value)}
          />
          <Select
            allowClear
            placeholder="All statuses"
            style={{ width: 150 }}
            options={STATUS_OPTIONS}
            value={statusFilter}
            onChange={(v) => setStatusFilter(v)}
          />
          <Button icon={<PlusOutlined />} type="primary" onClick={() => setCreateOpen(true)}>
            New Referral
          </Button>
          <Button icon={<ReloadOutlined />} onClick={fetch}>
            Refresh
          </Button>
        </Space>
      </div>

      <PageState
        error={error}
        onRetry={() => fetch()}
        empty={!loading && !error && referrals.length === 0}
        emptyMessage="No referrals yet"
      >
        <Table
          rowKey="id"
          columns={columns}
          dataSource={referrals}
          loading={loading}
          pagination={{ pageSize: 20 }}
          size="middle"
        />
      </PageState>

      {/* Create Modal */}
      <Modal
        title="New Referral"
        open={createOpen}
        onCancel={() => setCreateOpen(false)}
        footer={null}
        width={520}
      >
        <Form
          form={createForm}
          layout="vertical"
          onFinish={handleCreate}
          initialValues={{ status: "pending" }}
        >
          <Form.Item
            name="patient_id"
            label="Patient ID"
            rules={[{ required: true, message: "Patient ID is required" }]}
          >
            <Input placeholder="e.g. P001" />
          </Form.Item>
          <Form.Item
            name="to_specialist"
            label="To Specialist"
            rules={[{ required: true, message: "Specialist name is required" }]}
          >
            <Input placeholder="e.g. Dr. Smith" />
          </Form.Item>
          <Form.Item name="specialty" label="Specialty">
            <Input placeholder="e.g. Cardiology" />
          </Form.Item>
          <Form.Item name="from_provider" label="From Provider">
            <Input placeholder="e.g. Dr. Jones" />
          </Form.Item>
          <Form.Item name="notes" label="Notes">
            <Input.TextArea rows={3} placeholder="Reason for referral…" />
          </Form.Item>
          <Button type="primary" htmlType="submit" block>
            Create Referral
          </Button>
        </Form>
      </Modal>

      {/* Update Modal */}
      <Modal
        title={editing ? `Referral to ${editing.to_specialist}` : "Update Referral"}
        open={editOpen}
        onCancel={() => {
          setEditOpen(false);
          setEditing(null);
        }}
        footer={null}
        width={480}
      >
        <Form form={editForm} layout="vertical" onFinish={handleUpdate}>
          <Form.Item
            name="status"
            label="Status"
            rules={[{ required: true, message: "Status is required" }]}
          >
            <Select options={STATUS_OPTIONS} />
          </Form.Item>
          <Form.Item name="notes" label="Notes">
            <Input.TextArea rows={3} placeholder="Status update notes…" />
          </Form.Item>
          <Button type="primary" htmlType="submit" block>
            Update Referral
          </Button>
        </Form>
      </Modal>
    </Content>
  );
}

export default withSidebar(ReferralTracking);
