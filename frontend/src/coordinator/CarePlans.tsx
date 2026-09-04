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
  DatePicker,
  Checkbox,
} from "antd";
import { ReloadOutlined, PlusOutlined } from "@ant-design/icons";
import dayjs from "dayjs";
import withSidebar from "../common/base";
import { PageState } from "../common/PageState";
import { listCarePlans, createCarePlan, updateCarePlan, type CarePlan } from "../api/care-plans";
import "./CarePlans.css";

const Content = Layout.Content;
const REFRESH_MS = 60000;

const STATUS_COLORS: Record<string, string> = {
  active: "green",
  on_hold: "orange",
  completed: "default",
};

const STATUS_OPTIONS = [
  { value: "active", label: "Active" },
  { value: "on_hold", label: "On Hold" },
  { value: "completed", label: "Completed" },
];

// CC-02: care-plan board — per-patient plans with tasks, status
// transitions, provider and follow-up date. Create/edit posts to the
// CARE_PLAN_WRITE-gated API; browse is PATIENT_READ.
function CarePlans() {
  const { message } = App.useApp();
  useDocumentTitle("QuantumPACS - Care Plans");
  const [plans, setPlans] = useState<CarePlan[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string | undefined>();
  const [editOpen, setEditOpen] = useState(false);
  const [editing, setEditing] = useState<CarePlan | null>(null);

  const fetch = useCallback(() => {
    setLoading(true);
    setError(null);
    const query: Record<string, string> = {};
    if (statusFilter) query.status = statusFilter;
    listCarePlans(query)
      .then((res) => {
        setLoading(false);
        setPlans(res.data || []);
      })
      .catch((e: any) => {
        setLoading(false);
        setError(e.message);
        message.error(e.message);
      });
  }, [message, statusFilter]);

  useEffect(() => {
    fetch();
  }, [fetch]);

  useEffect(() => {
    const interval = setInterval(fetch, REFRESH_MS);
    return () => clearInterval(interval);
  }, [fetch]);

  const openCreate = () => {
    setEditing(null);
    setEditOpen(true);
  };

  const openEdit = (plan: CarePlan) => {
    setEditing(plan);
    setEditOpen(true);
  };

  const handleSave = async (values: any) => {
    const payload = {
      patient_id: values.patient_id,
      title: values.title,
      status: values.status || "active",
      tasks: (values.tasks || []).map((t: { label: string; done?: boolean }) => ({
        label: t.label,
        done: !!t.done,
      })),
      responsible_provider: values.responsible_provider || "",
      follow_up_at: values.follow_up_at ? values.follow_up_at.toISOString() : null,
      notes: values.notes || "",
    };
    try {
      if (editing) {
        await updateCarePlan(editing.id, payload);
        message.success("Care plan updated");
      } else {
        await createCarePlan(payload);
        message.success("Care plan created");
      }
      setEditOpen(false);
      fetch();
    } catch (e: any) {
      message.error(e.message || "Save failed");
    }
  };

  const taskProgress = (tasks: CarePlan["tasks"]) => {
    // Defense in depth: the API now parses the jsonb tasks list, but an
    // older payload (or a legacy row) can still hand back a raw string.
    if (!Array.isArray(tasks) || tasks.length === 0) return "-";
    const done = tasks.filter((t) => t.done).length;
    return `${done}/${tasks.length}`;
  };

  const columns: any[] = [
    { title: "Patient", dataIndex: "patient_id", width: "12%" },
    { title: "Title", dataIndex: "title", width: "22%" },
    {
      title: "Status",
      dataIndex: "status",
      width: "12%",
      render: (s: string) => (
        <Tag color={STATUS_COLORS[s] || "default"}>{(s || "").replace("_", " ").toUpperCase()}</Tag>
      ),
    },
    {
      title: "Tasks",
      key: "tasks",
      width: "10%",
      render: (_: unknown, row: CarePlan) => taskProgress(row.tasks),
    },
    {
      title: "Provider",
      dataIndex: "responsible_provider",
      width: "16%",
      render: (v: string) => v || "-",
    },
    {
      title: "Follow-Up",
      dataIndex: "follow_up_at",
      width: "14%",
      render: (v: string) => (v ? dayjs(v).format("YYYY-MM-DD") : "-"),
    },
    {
      title: "",
      key: "action",
      width: "14%",
      render: (_: unknown, row: CarePlan) => (
        <Button size="small" onClick={() => openEdit(row)}>
          Edit
        </Button>
      ),
    },
  ];

  return (
    <Content style={{ padding: 24 }} role="main">
      <div className="care-plans-header">
        <h2>Care Plans</h2>
        <Space>
          <Select
            allowClear
            placeholder="All statuses"
            style={{ width: 160 }}
            options={STATUS_OPTIONS}
            value={statusFilter}
            onChange={(v) => setStatusFilter(v)}
          />
          <Button icon={<PlusOutlined />} onClick={openCreate}>
            New Plan
          </Button>
          <Button icon={<ReloadOutlined />} onClick={fetch}>
            Refresh
          </Button>
        </Space>
      </div>

      <PageState
        error={error}
        onRetry={() => fetch()}
        empty={!loading && !error && plans.length === 0}
        emptyMessage="No care plans yet"
      >
        <Table
          rowKey="id"
          columns={columns}
          dataSource={plans}
          loading={loading}
          pagination={{ pageSize: 20 }}
          size="middle"
        />
      </PageState>

      <Modal
        title={editing ? "Edit Care Plan" : "New Care Plan"}
        open={editOpen}
        onCancel={() => setEditOpen(false)}
        footer={null}
        width={560}
      >
        <Form
          layout="vertical"
          onFinish={handleSave}
          initialValues={
            editing
              ? {
                  patient_id: editing.patient_id,
                  title: editing.title,
                  status: editing.status,
                  tasks: editing.tasks || [],
                  responsible_provider: editing.responsible_provider,
                  follow_up_at: editing.follow_up_at ? dayjs(editing.follow_up_at) : undefined,
                  notes: editing.notes,
                }
              : { status: "active", tasks: [] }
          }
        >
          <Form.Item
            name="patient_id"
            label="Patient ID"
            rules={[{ required: true, message: "Patient ID is required" }]}
          >
            <Input />
          </Form.Item>
          <Form.Item
            name="title"
            label="Title"
            rules={[{ required: true, message: "Title is required" }]}
          >
            <Input />
          </Form.Item>
          <Form.Item name="status" label="Status">
            <Select options={STATUS_OPTIONS} />
          </Form.Item>
          <Form.Item name="responsible_provider" label="Responsible Provider">
            <Input />
          </Form.Item>
          <Form.Item name="follow_up_at" label="Follow-Up Date">
            <DatePicker style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="notes" label="Notes">
            <Input.TextArea rows={3} />
          </Form.Item>
          <Form.List name="tasks">
            {(fields, { add, remove }) => (
              <>
                {fields.map((field) => (
                  <Space key={field.key} align="baseline">
                    <Form.Item
                      name={[field.name, "label"]}
                      rules={[{ required: true, message: "Task label is required" }]}
                    >
                      <Input placeholder="Task" />
                    </Form.Item>
                    <Form.Item name={[field.name, "done"]} valuePropName="checked">
                      <Checkbox>Done</Checkbox>
                    </Form.Item>
                    <Button onClick={() => remove(field.name)}>Remove</Button>
                  </Space>
                ))}
                <Button onClick={() => add({ label: "", done: false })}>Add Task</Button>
              </>
            )}
          </Form.List>
          <Button type="primary" htmlType="submit" block style={{ marginTop: 16 }}>
            {editing ? "Update Plan" : "Create Plan"}
          </Button>
        </Form>
      </Modal>
    </Content>
  );
}

export default withSidebar(CarePlans);
