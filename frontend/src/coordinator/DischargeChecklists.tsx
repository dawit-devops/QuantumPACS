import { useDocumentTitle } from "../hooks";
import React, { useState, useEffect, useCallback } from "react";
import { App, Layout, Table, Tag, Button, Space, Input, Modal, Form, Select, Checkbox } from "antd";
import { ReloadOutlined, PlusOutlined } from "@ant-design/icons";
import withSidebar from "../common/base";
import { PageState } from "../common/PageState";
import {
  listDischargeChecklists,
  createDischargeChecklist,
  updateDischargeChecklist,
  DEFAULT_DISCHARGE_ITEMS,
  type DischargeChecklist,
  type DischargeItem,
} from "../api/ris";
import "./DischargeChecklists.css";

const Content = Layout.Content;

const STATUS_COLORS: Record<string, string> = {
  open: "blue",
  completed: "green",
};

function DischargeChecklists() {
  const { message } = App.useApp();
  useDocumentTitle("QuantumPACS - Discharge Checklists");
  const [checklists, setChecklists] = useState<DischargeChecklist[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string | undefined>();
  const [patientFilter, setPatientFilter] = useState("");
  const [createOpen, setCreateOpen] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [editing, setEditing] = useState<DischargeChecklist | null>(null);
  const [createForm] = Form.useForm();
  const [editForm] = Form.useForm();

  const fetch = useCallback(() => {
    setLoading(true);
    setError(null);
    listDischargeChecklists({
      status: statusFilter,
      patient_id: patientFilter || undefined,
    })
      .then((data) => {
        setLoading(false);
        setChecklists(data || []);
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
      const items = (values.items || []).map((t: { label: string; done?: boolean }) => ({
        label: t.label,
        done: !!t.done,
      }));
      await createDischargeChecklist({
        patient_id: values.patient_id,
        items: items.length > 0 ? items : undefined,
        notes: values.notes || "",
      });
      message.success("Discharge checklist created");
      setCreateOpen(false);
      createForm.resetFields();
      fetch();
    } catch (e: any) {
      message.error(e.message || "Create failed");
    }
  };

  const openEdit = (cl: DischargeChecklist) => {
    setEditing(cl);
    editForm.setFieldsValue({
      status: cl.status,
      items: cl.items || [],
      notes: cl.notes,
    });
    setEditOpen(true);
  };

  const handleUpdate = async (values: any) => {
    if (!editing) return;
    try {
      const items = (values.items || []).map((t: { label: string; done?: boolean }) => ({
        label: t.label,
        done: !!t.done,
      }));
      await updateDischargeChecklist(editing.id, {
        status: values.status,
        items,
        notes: values.notes || "",
      });
      message.success("Checklist updated");
      setEditOpen(false);
      setEditing(null);
      fetch();
    } catch (e: any) {
      message.error(e.message || "Update failed");
    }
  };

  const itemProgress = (items: DischargeItem[]) => {
    if (!items || items.length === 0) return "-";
    const done = items.filter((t) => t.done).length;
    return `${done}/${items.length}`;
  };

  const columns: any[] = [
    { title: "Patient", dataIndex: "patient_id", width: "12%" },
    { title: "Title", dataIndex: "title", width: "20%" },
    {
      title: "Status",
      dataIndex: "status",
      width: "12%",
      render: (s: string) => (
        <Tag color={STATUS_COLORS[s] || "default"}>{s ? s.toUpperCase() : "OPEN"}</Tag>
      ),
    },
    {
      title: "Items",
      key: "items",
      width: "10%",
      render: (_: unknown, row: DischargeChecklist) => itemProgress(row.items),
    },
    {
      title: "Notes",
      dataIndex: "notes",
      width: "30%",
      render: (v: string) => v || "-",
    },
    {
      title: "Created",
      dataIndex: "created_at",
      width: "16%",
      render: (v: string) => (v ? new Date(v).toLocaleString() : "-"),
    },
    {
      title: "",
      key: "action",
      width: "10%",
      render: (_: unknown, row: DischargeChecklist) => (
        <Button size="small" onClick={() => openEdit(row)}>
          Edit
        </Button>
      ),
    },
  ];

  return (
    <Content style={{ padding: 24 }} role="main">
      <div className="discharge-header">
        <div>
          <h2 style={{ margin: 0 }}>Discharge Planning Checklists</h2>
          <span className="discharge-subtitle">
            Pre-discharge checklist: follow-up appointments, medication reconciliation, patient
            education
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
            options={[
              { value: "open", label: "Open" },
              { value: "completed", label: "Completed" },
            ]}
            value={statusFilter}
            onChange={(v) => setStatusFilter(v)}
          />
          <Button icon={<PlusOutlined />} type="primary" onClick={() => setCreateOpen(true)}>
            New Checklist
          </Button>
          <Button icon={<ReloadOutlined />} onClick={fetch}>
            Refresh
          </Button>
        </Space>
      </div>

      <PageState
        error={error}
        onRetry={() => fetch()}
        empty={!loading && !error && checklists.length === 0}
        emptyMessage="No discharge checklists yet"
      >
        <Table
          rowKey="id"
          columns={columns}
          dataSource={checklists}
          loading={loading}
          pagination={{ pageSize: 20 }}
          size="middle"
        />
      </PageState>

      {/* Create Modal */}
      <Modal
        title="New Discharge Checklist"
        open={createOpen}
        onCancel={() => setCreateOpen(false)}
        footer={null}
        width={520}
      >
        <Form
          form={createForm}
          layout="vertical"
          onFinish={handleCreate}
          initialValues={{ items: DEFAULT_DISCHARGE_ITEMS }}
        >
          <Form.Item
            name="patient_id"
            label="Patient ID"
            rules={[{ required: true, message: "Patient ID is required" }]}
          >
            <Input placeholder="e.g. P001" />
          </Form.Item>
          <Form.Item name="notes" label="Notes">
            <Input.TextArea rows={3} placeholder="Additional discharge notes…" />
          </Form.Item>
          <Form.List name="items">
            {(fields, { add, remove }) => (
              <>
                {fields.map((field) => (
                  <Space key={field.key} align="baseline">
                    <Form.Item
                      name={[field.name, "label"]}
                      rules={[{ required: true, message: "Item label is required" }]}
                    >
                      <Input placeholder="Checklist item" style={{ width: 240 }} />
                    </Form.Item>
                    <Form.Item name={[field.name, "done"]} valuePropName="checked">
                      <Checkbox>Done</Checkbox>
                    </Form.Item>
                    <Button onClick={() => remove(field.name)}>Remove</Button>
                  </Space>
                ))}
                <Button
                  onClick={() => add({ label: "", done: false })}
                  style={{ display: "block", marginTop: 8 }}
                >
                  Add Item
                </Button>
              </>
            )}
          </Form.List>
          <Button type="primary" htmlType="submit" block style={{ marginTop: 16 }}>
            Create Checklist
          </Button>
        </Form>
      </Modal>

      {/* Edit Modal */}
      <Modal
        title={editing ? `Edit: ${editing.title}` : "Edit Checklist"}
        open={editOpen}
        onCancel={() => {
          setEditOpen(false);
          setEditing(null);
        }}
        footer={null}
        width={520}
      >
        <Form form={editForm} layout="vertical" onFinish={handleUpdate}>
          <Form.Item
            name="status"
            label="Status"
            rules={[{ required: true, message: "Status is required" }]}
          >
            <Select
              options={[
                { value: "open", label: "Open" },
                { value: "completed", label: "Completed" },
              ]}
            />
          </Form.Item>
          <Form.Item name="notes" label="Notes">
            <Input.TextArea rows={3} />
          </Form.Item>
          <Form.List name="items">
            {(fields, { add, remove }) => (
              <>
                {fields.map((field) => (
                  <Space key={field.key} align="baseline">
                    <Form.Item
                      name={[field.name, "label"]}
                      rules={[{ required: true, message: "Item label is required" }]}
                    >
                      <Input placeholder="Checklist item" style={{ width: 240 }} />
                    </Form.Item>
                    <Form.Item name={[field.name, "done"]} valuePropName="checked">
                      <Checkbox>Done</Checkbox>
                    </Form.Item>
                    <Button onClick={() => remove(field.name)}>Remove</Button>
                  </Space>
                ))}
                <Button
                  onClick={() => add({ label: "", done: false })}
                  style={{ display: "block", marginTop: 8 }}
                >
                  Add Item
                </Button>
              </>
            )}
          </Form.List>
          <Button type="primary" htmlType="submit" block style={{ marginTop: 16 }}>
            Update Checklist
          </Button>
        </Form>
      </Modal>
    </Content>
  );
}

export default withSidebar(DischargeChecklists);
