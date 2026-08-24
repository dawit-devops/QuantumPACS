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
} from "antd";
import { PlusOutlined, ReloadOutlined } from "@ant-design/icons";
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
  assigned_station_ae: string;
  status: string;
  assigned_technologist: string;
}

const STATUS_COLORS: Record<string, string> = {
  scheduled: "blue",
  completed: "green",
  cancelled: "red",
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

  useEffect(() => {
    fetchData();
  }, [fetchData]);

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

  const onDateChange = (
    dates: any,
    dateStrings: [string, string],
  ) => {
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
      render: (v: string) =>
        v ? new Date(v).toLocaleDateString() : "—",
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
      dataIndex: "assigned_station_ae",
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
      render: (v: string, row: StaffScheduleRow) =>
        v || row.accession_number || "—",
    },
    {
      title: "Status",
      dataIndex: "status",
      key: "status",
      width: 110,
      render: (v: string) => (
        <Tag color={STATUS_COLORS[v] || "default"}>{v || "scheduled"}</Tag>
      ),
    },
  ];

  return (
    <Content style={{ padding: 24 }} role="main">
      <div className="ris-dash-header">
        <h2 style={{ margin: 0 }}>Staff Schedule</h2>
        <Space>
          <RangePicker onChange={onDateChange} />
          <Button icon={<ReloadOutlined />} onClick={fetchData}>
            Refresh
          </Button>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => setModalOpen(true)}
          >
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
    </Content>
  );
}

export default withSidebar(StaffSchedule);
