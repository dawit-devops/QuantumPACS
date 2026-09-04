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
} from "antd";
import { ReloadOutlined, PlusOutlined, SearchOutlined } from "@ant-design/icons";
import dayjs from "dayjs";
import { useSearchParams } from "react-router";
import withSidebar from "../common/base";
import { PageState } from "../common/PageState";
import {
  listCommunications,
  createCommunication,
  type Communication,
} from "../api/communications";
import "./Communications.css";

const Content = Layout.Content;

const DIRECTION_COLORS: Record<string, string> = {
  inbound: "blue",
  outbound: "green",
};

const CHANNEL_OPTIONS = [
  { value: "phone", label: "Phone" },
  { value: "email", label: "Email" },
  { value: "sms", label: "SMS" },
  { value: "fax", label: "Fax" },
  { value: "letter", label: "Letter" },
  { value: "portal", label: "Portal" },
];

// CC-04: communication log — inbound/outbound correspondence per patient.
// Search is patient-scoped; the log is append-only.
function Communications() {
  const { message } = App.useApp();
  useDocumentTitle("QuantumPACS - Communications");
  const [searchParams] = useSearchParams();
  const [patientId, setPatientId] = useState(
    searchParams.get("patient") || "",
  );
  const [searchValue, setSearchValue] = useState(
    searchParams.get("patient") || "",
  );
  const [rows, setRows] = useState<Communication[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [logOpen, setLogOpen] = useState(false);
  const [logForm] = Form.useForm();

  const fetch = useCallback(() => {
    if (!patientId) {
      setRows([]);
      return;
    }
    setLoading(true);
    setError(null);
    listCommunications({ patient_id: patientId })
      .then((res) => {
        setLoading(false);
        setRows(res.data || []);
      })
      .catch((e: any) => {
        setLoading(false);
        setError(e.message);
        message.error(e.message);
      });
  }, [message, patientId]);

  useEffect(() => {
    fetch();
  }, [fetch]);

  const handleSearch = () => {
    setPatientId(searchValue.trim());
  };

  const handleLog = async (values: any) => {
    try {
      await createCommunication({
        patient_id: values.patient_id,
        direction: values.direction,
        channel: values.channel || "phone",
        category: values.category || "",
        summary: values.summary,
        related_order_id: values.related_order_id || "",
      });
      message.success("Communication logged");
      setLogOpen(false);
      logForm.resetFields();
      if (!patientId || values.patient_id === patientId) fetch();
      else setPatientId(values.patient_id);
    } catch (e: any) {
      message.error(e.message || "Save failed");
    }
  };

  const columns: any[] = [
    {
      title: "When",
      dataIndex: "created_at",
      width: "16%",
      render: (v: string) =>
        v ? dayjs(v).format("YYYY-MM-DD HH:mm") : "-",
    },
    {
      title: "Direction",
      dataIndex: "direction",
      width: "12%",
      render: (d: string) => (
        <Tag color={DIRECTION_COLORS[d] || "default"}>
          {(d || "").toUpperCase()}
        </Tag>
      ),
    },
    {
      title: "Channel",
      dataIndex: "channel",
      width: "10%",
      render: (v: string) => (v || "").toUpperCase(),
    },
    {
      title: "Category",
      dataIndex: "category",
      width: "12%",
      render: (v: string) => v || "-",
    },
    { title: "Summary", dataIndex: "summary" },
    {
      title: "Order",
      dataIndex: "related_order_id",
      width: "12%",
      render: (v: string) => v || "-",
    },
  ];

  return (
    <Content style={{ padding: 24 }} role="main">
      <div className="communications-header">
        <h2>Communication Log</h2>
        <Space>
          <Input
            placeholder="Patient ID"
            value={searchValue}
            onChange={(e) => setSearchValue(e.target.value)}
            onPressEnter={handleSearch}
            style={{ width: 200 }}
            allowClear
          />
          <Button icon={<SearchOutlined />} onClick={handleSearch}>
            Search
          </Button>
          <Button
            icon={<PlusOutlined />}
            onClick={() => {
              logForm.setFieldsValue({ patient_id: patientId || "" });
              setLogOpen(true);
            }}
          >
            Log Communication
          </Button>
          <Button icon={<ReloadOutlined />} onClick={fetch}>
            Refresh
          </Button>
        </Space>
      </div>

      {!patientId ? (
        <PageState empty emptyMessage="Enter a patient ID to view their communication history">
          <span />
        </PageState>
      ) : (
        <PageState
          error={error}
          onRetry={() => fetch()}
          empty={!loading && !error && rows.length === 0}
          emptyMessage="No communications logged for this patient"
        >
          <Table
            rowKey="id"
            columns={columns}
            dataSource={rows}
            loading={loading}
            pagination={{ pageSize: 20 }}
            size="middle"
          />
        </PageState>
      )}

      <Modal
        title="Log Communication"
        open={logOpen}
        onCancel={() => setLogOpen(false)}
        footer={null}
      >
        <Form form={logForm} layout="vertical" onFinish={handleLog}>
          <Form.Item
            name="patient_id"
            label="Patient ID"
            rules={[{ required: true, message: "Patient ID is required" }]}
          >
            <Input />
          </Form.Item>
          <Form.Item
            name="direction"
            label="Direction"
            rules={[{ required: true }]}
          >
            <Select
              options={[
                { value: "outbound", label: "Outbound" },
                { value: "inbound", label: "Inbound" },
              ]}
            />
          </Form.Item>
          <Form.Item name="channel" label="Channel">
            <Select options={CHANNEL_OPTIONS} />
          </Form.Item>
          <Form.Item name="category" label="Category">
            <Input placeholder="e.g. prep instructions, results call" />
          </Form.Item>
          <Form.Item
            name="summary"
            label="Summary"
            rules={[{ required: true, message: "Summary is required" }]}
          >
            <Input.TextArea rows={3} />
          </Form.Item>
          <Form.Item name="related_order_id" label="Related Order ID">
            <Input />
          </Form.Item>
          <Button type="primary" htmlType="submit" block>
            Log Communication
          </Button>
        </Form>
      </Modal>
    </Content>
  );
}

export default withSidebar(Communications);
