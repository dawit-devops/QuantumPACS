import { useDocumentTitle } from "../hooks";
import React, { useState, useEffect, useCallback } from "react";
import {
  App,
  Layout,
  Table,
  Tag,
  Button,
  DatePicker,
  Select,
  Modal,
  Form,
  Input,
  Alert,
  Space,
  Empty,
  Tabs,
} from "antd";
import { PlusOutlined, ReloadOutlined, CheckOutlined, StopOutlined } from "@ant-design/icons";
import withSidebar from "../common/base";
import { PageState } from "../common/PageState";
import { request } from "../helpers";
import "./RISDashboard.css";

const Content = Layout.Content;
const { RangePicker } = DatePicker;

export interface StaffScheduleRow {
  id: string;
  patient_name: string;
  accession_number: string;
  modality: string;
  scheduled_date: string;
  scheduled_time: string;
  station_ae_title: string;
  status: string;
  assigned_technologist: string;
}

export interface StaffTimeOffRow {
  id: string;
  staff_id: string;
  staff_name: string;
  modality: string;
  status: string;
  start_date: string;
  end_date: string;
  reason: string;
}

export interface CoverageGap {
  date: string;
  staff_id: string;
  staff_name: string;
  modality: string;
  scheduled_exams: number;
}

const STATUS_COLORS: Record<string, string> = {
  scheduled: "blue",
  completed: "green",
  cancelled: "red",
  REQUESTED: "orange",
  APPROVED: "green",
  REJECTED: "red",
  CANCELLED: "default",
};

const MODALITIES = ["CT", "MR", "US", "DX", "MG", "FL", "PET", "NM", "XR"];

function StaffSchedule() {
  const { message } = App.useApp();
  useDocumentTitle("QuantumPACS - Staff Schedule");
  const [data, setData] = useState<StaffScheduleRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dateRange, setDateRange] = useState<[string, string] | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [form] = Form.useForm();

  // DM-07 time-off state
  const [timeOff, setTimeOff] = useState<StaffTimeOffRow[]>([]);
  const [timeOffLoading, setTimeOffLoading] = useState(false);
  const [timeOffError, setTimeOffError] = useState<string | null>(null);
  const [gaps, setGaps] = useState<CoverageGap[]>([]);
  const [gapsLoading, setGapsLoading] = useState(false);
  const [timeOffModalOpen, setTimeOffModalOpen] = useState(false);
  const [timeOffForm] = Form.useForm();

  const fetchData = useCallback(() => {
    setLoading(true);
    setError(null);
    const query: Record<string, string> = {};
    if (dateRange) {
      query.start_date = dateRange[0];
      query.end_date = dateRange[1];
    }
    request("ris/staff-schedule", { query })
      .then((res: any) => {
        setLoading(false);
        setData(Array.isArray(res.data) ? res.data : []);
      })
      .catch((e: any) => {
        setLoading(false);
        setError(e.message);
      });
  }, [dateRange]);

  const fetchTimeOff = useCallback(() => {
    setTimeOffLoading(true);
    setTimeOffError(null);
    request("ris/staff-time-off")
      .then((res: any) => {
        setTimeOffLoading(false);
        setTimeOff(Array.isArray(res.data) ? res.data : []);
      })
      .catch((e: any) => {
        setTimeOffLoading(false);
        setTimeOffError(e.message);
      });
  }, []);

  const fetchGaps = useCallback(() => {
    setGapsLoading(true);
    request("ris/staff-time-off/coverage-gaps")
      .then((res: any) => {
        setGapsLoading(false);
        setGaps(Array.isArray(res.data) ? res.data : []);
      })
      .catch(() => {
        setGapsLoading(false);
        setGaps([]);
      });
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  useEffect(() => {
    fetchTimeOff();
    fetchGaps();
  }, [fetchTimeOff, fetchGaps]);

  const handleCreate = async () => {
    try {
      const values = await form.validateFields();
      await request("ris/staff-schedule", {
        method: "POST",
        data: values,
      });
      message.success("Schedule entry created");
      setModalOpen(false);
      form.resetFields();
      fetchData();
    } catch (e: any) {
      if (e.message) {
        message.error(e.message || "Failed to create schedule entry");
      }
    }
  };

  const handleCreateTimeOff = async () => {
    try {
      const values = await timeOffForm.validateFields();
      await request("ris/staff-time-off", {
        method: "POST",
        data: values,
      });
      message.success("Time-off request submitted");
      setTimeOffModalOpen(false);
      timeOffForm.resetFields();
      fetchTimeOff();
    } catch (e: any) {
      if (e.message) {
        message.error(e.message || "Failed to submit time-off request");
      }
    }
  };

  const updateTimeOffStatus = async (id: string, status: string) => {
    try {
      await request(`ris/staff-time-off/${id}/status`, {
        method: "PATCH",
        data: { status },
      });
      message.success(`Request ${status.toLowerCase()}`);
      fetchTimeOff();
      fetchGaps();
    } catch (e: any) {
      if (e.message) {
        message.error(e.message || "Failed to update status");
      }
    }
  };

  const onDateChange = (dates: any, dateStrings: [string, string]) => {
    if (dates && dates[0] && dates[1]) {
      setDateRange([dateStrings[0], dateStrings[1]]);
    } else {
      setDateRange(null);
    }
  };

  const columns = [
    {
      title: "Date",
      dataIndex: "scheduled_date",
      key: "date",
      width: 120,
      render: (v: string) => (v ? new Date(v).toLocaleDateString() : "—"),
    },
    {
      title: "Time",
      dataIndex: "scheduled_time",
      key: "time",
      width: 80,
      render: (v: string) => v || "—",
    },
    {
      title: "Modality",
      dataIndex: "modality",
      key: "modality",
      width: 90,
      render: (v: string) => (v ? <Tag>{v}</Tag> : "—"),
    },
    {
      title: "Station",
      dataIndex: "station_ae_title",
      key: "station",
      render: (v: string) => v || "—",
    },
    {
      title: "Technologist",
      dataIndex: "assigned_technologist",
      key: "tech",
      render: (v: string) => v || "Unassigned",
    },
    {
      title: "Patient",
      dataIndex: "patient_name",
      key: "patient",
      render: (v: string, row: StaffScheduleRow) => v || row.accession_number || "—",
    },
    {
      title: "Status",
      dataIndex: "status",
      key: "status",
      width: 110,
      render: (v: string) => <Tag color={STATUS_COLORS[v] || "default"}>{v || "scheduled"}</Tag>,
    },
  ];

  const timeOffColumns = [
    {
      title: "Staff",
      dataIndex: "staff_name",
      key: "staff_name",
      render: (v: string) => v || "—",
    },
    {
      title: "Modality",
      dataIndex: "modality",
      key: "modality",
      width: 90,
      render: (v: string) => (v ? <Tag>{v}</Tag> : "—"),
    },
    {
      title: "Start",
      dataIndex: "start_date",
      key: "start",
      width: 120,
      render: (v: string) => (v ? new Date(v).toLocaleDateString() : "—"),
    },
    {
      title: "End",
      dataIndex: "end_date",
      key: "end",
      width: 120,
      render: (v: string) => (v ? new Date(v).toLocaleDateString() : "—"),
    },
    {
      title: "Reason",
      dataIndex: "reason",
      key: "reason",
      render: (v: string) => v || "—",
    },
    {
      title: "Status",
      dataIndex: "status",
      key: "status",
      width: 110,
      render: (v: string) => <Tag color={STATUS_COLORS[v] || "default"}>{v}</Tag>,
    },
    {
      title: "Actions",
      key: "actions",
      width: 180,
      render: (_: any, row: StaffTimeOffRow) => (
        <Space>
          {row.status === "REQUESTED" && (
            <>
              <Button
                size="small"
                type="primary"
                icon={<CheckOutlined />}
                onClick={() => updateTimeOffStatus(row.id, "APPROVED")}
              >
                Approve
              </Button>
              <Button
                size="small"
                danger
                icon={<StopOutlined />}
                onClick={() => updateTimeOffStatus(row.id, "REJECTED")}
              >
                Reject
              </Button>
            </>
          )}
          {row.status === "APPROVED" && (
            <Button size="small" onClick={() => updateTimeOffStatus(row.id, "CANCELLED")}>
              Cancel
            </Button>
          )}
        </Space>
      ),
    },
  ];

  const scheduleTab = (
    <>
      <div className="ris-dash-header">
        <h2 style={{ margin: 0 }}>Scheduled Exams</h2>
        <Space>
          <RangePicker onChange={onDateChange} />
          <Button icon={<ReloadOutlined />} onClick={fetchData}>
            Refresh
          </Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>
            Add Entry
          </Button>
        </Space>
      </div>

      <PageState
        error={error}
        onRetry={fetchData}
        loading={loading}
        empty={!loading && !error && data.length === 0}
        emptyMessage="No schedule entries for this date range"
      >
        <Table<StaffScheduleRow>
          rowKey="id"
          columns={columns}
          dataSource={data}
          pagination={{ pageSize: 20 }}
          size="middle"
        />
      </PageState>

      <Modal
        title="Add Schedule Entry"
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={handleCreate}
        okText="Create"
        width={520}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="modality"
            label="Modality"
            rules={[{ required: true, message: "Modality required" }]}
          >
            <Select
              placeholder="Select modality"
              options={MODALITIES.map((m) => ({ value: m, label: m }))}
            />
          </Form.Item>
          <Form.Item
            name="scheduled_date"
            label="Date"
            rules={[{ required: true, message: "Date required" }]}
          >
            <Input type="date" />
          </Form.Item>
          <Form.Item name="scheduled_time" label="Time">
            <Input type="time" />
          </Form.Item>
          <Form.Item name="station_ae" label="Station AE Title">
            <Input placeholder="e.g. CT_SCANNER_01" />
          </Form.Item>
          <Form.Item name="technologist" label="Technologist">
            <Input placeholder="Assigned technologist" />
          </Form.Item>
          <Form.Item name="patient_name" label="Patient Name">
            <Input placeholder="Patient name (optional)" />
          </Form.Item>
          <Form.Item name="accession_number" label="Accession Number">
            <Input placeholder="Accession number (optional)" />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );

  const timeOffTab = (
    <>
      <div className="ris-dash-header">
        <h2 style={{ margin: 0 }}>Time Off & Coverage</h2>
        <Space>
          <Button
            icon={<ReloadOutlined />}
            onClick={() => {
              fetchTimeOff();
              fetchGaps();
            }}
          >
            Refresh
          </Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setTimeOffModalOpen(true)}>
            Request Time Off
          </Button>
        </Space>
      </div>

      {gapsLoading && (
        <Alert type="info" message="Checking coverage..." showIcon style={{ marginBottom: 16 }} />
      )}
      {!gapsLoading && gaps.length > 0 && (
        <Alert
          type="warning"
          showIcon
          style={{ marginBottom: 16 }}
          message="Coverage gaps detected"
          description={gaps.map((g) => (
            <div key={`${g.date}-${g.staff_id}`}>
              {g.date} — {g.staff_name} ({g.modality}) is on approved time-off but has{" "}
              {g.scheduled_exams} scheduled exam(s).
            </div>
          ))}
        />
      )}
      {!gapsLoading && gaps.length === 0 && (
        <Alert type="success" showIcon style={{ marginBottom: 16 }} message="No coverage gaps" />
      )}

      <PageState
        error={timeOffError}
        onRetry={fetchTimeOff}
        loading={timeOffLoading}
        empty={!timeOffLoading && !timeOffError && timeOff.length === 0}
        emptyMessage="No time-off requests"
      >
        <Table<StaffTimeOffRow>
          rowKey="id"
          columns={timeOffColumns}
          dataSource={timeOff}
          pagination={{ pageSize: 10 }}
          size="middle"
        />
      </PageState>

      <Modal
        title="Request Time Off"
        open={timeOffModalOpen}
        onCancel={() => setTimeOffModalOpen(false)}
        onOk={handleCreateTimeOff}
        okText="Submit"
        width={520}
      >
        <Form form={timeOffForm} layout="vertical">
          <Form.Item
            name="staff_id"
            label="Staff ID"
            rules={[{ required: true, message: "Staff ID required" }]}
          >
            <Input placeholder="Staff ID" />
          </Form.Item>
          <Form.Item
            name="staff_name"
            label="Staff Name"
            rules={[{ required: true, message: "Staff name required" }]}
          >
            <Input placeholder="Staff name" />
          </Form.Item>
          <Form.Item name="modality" label="Modality">
            <Select
              allowClear
              placeholder="Select modality"
              options={MODALITIES.map((m) => ({ value: m, label: m }))}
            />
          </Form.Item>
          <Form.Item
            name="start_date"
            label="Start Date"
            rules={[{ required: true, message: "Start date required" }]}
          >
            <Input type="date" />
          </Form.Item>
          <Form.Item
            name="end_date"
            label="End Date"
            rules={[{ required: true, message: "End date required" }]}
          >
            <Input type="date" />
          </Form.Item>
          <Form.Item name="reason" label="Reason">
            <Input.TextArea rows={3} placeholder="Reason (optional)" />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );

  return (
    <Content style={{ padding: 24 }} role="main">
      <Tabs
        defaultActiveKey="schedule"
        items={[
          { key: "schedule", label: "Scheduled Exams", children: scheduleTab },
          { key: "timeoff", label: "Time Off & Coverage", children: timeOffTab },
        ]}
      />
    </Content>
  );
}

export default withSidebar(StaffSchedule);
