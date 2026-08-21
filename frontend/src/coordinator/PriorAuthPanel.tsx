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
  InputNumber,
  DatePicker,
  Radio,
} from "antd";
import { ReloadOutlined, PlusOutlined } from "@ant-design/icons";
import dayjs from "dayjs";
import withSidebar from "../common/base";
import { PageState } from "../common/PageState";
import {
  listPriorAuth,
  submitPriorAuth,
  decidePriorAuth,
  type PriorAuthRequest,
} from "../api/prior-auth";
import "./PriorAuthPanel.css";

const Content = Layout.Content;
const REFRESH_MS = 60000;

const STATUS_COLORS: Record<string, string> = {
  NOT_REQUIRED: "default",
  REQUIRED: "blue",
  PENDING: "orange",
  APPROVED: "green",
  DENIED: "red",
  EXPIRED: "red",
};

// R2-01: prior-authorization management — submit a request for an order,
// review payer decisions, and approve/deny (syncing the order's status).
function PriorAuthPanel() {
  const { message } = App.useApp();
  useDocumentTitle("QuantumPACS - Prior Authorization");
  const [data, setData] = useState<PriorAuthRequest[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitOpen, setSubmitOpen] = useState(false);
  const [decideFor, setDecideFor] = useState<PriorAuthRequest | null>(null);

  const fetch = useCallback(() => {
    setLoading(true);
    setError(null);
    listPriorAuth()
      .then((res) => {
        setLoading(false);
        setData(res.data);
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

  const handleSubmit = async (values: any) => {
    try {
      await submitPriorAuth({
        order_id: values.order_id,
        procedure_code: values.procedure_code,
        payer_id: values.payer_id,
        payer_name: values.payer_name,
      });
      message.success("Prior-auth request submitted");
      setSubmitOpen(false);
      fetch();
    } catch (e: any) {
      message.error(e.message || "Submit failed");
    }
  };

  const handleDecide = async (values: any) => {
    if (!decideFor) return;
    try {
      await decidePriorAuth(decideFor.id, {
        action: values.action,
        auth_number: values.auth_number,
        approved_units: values.approved_units,
        expiry_date: values.expiry_date
          ? dayjs(values.expiry_date).format("YYYY-MM-DD")
          : undefined,
        denial_reason: values.denial_reason,
      });
      message.success(
        values.action === "approve"
          ? "Prior auth approved"
          : "Prior auth denied",
      );
      setDecideFor(null);
      fetch();
    } catch (e: any) {
      message.error(e.message || "Decision failed");
    }
  };

  const columns: any[] = [
    { title: "Order", dataIndex: "order_id", width: "14%" },
    {
      title: "Procedure",
      dataIndex: "procedure_code",
      width: "16%",
      render: (v: string) => v || "-",
    },
    { title: "Payer", dataIndex: "payer_name", width: "16%",
      render: (v: string) => v || "-" },
    {
      title: "Status",
      dataIndex: "status",
      width: "12%",
      render: (s: string) => (
        <Tag color={STATUS_COLORS[s] || "default"}>{s}</Tag>
      ),
    },
    {
      title: "Auth #",
      dataIndex: "auth_number",
      width: "12%",
      render: (v: string) => v || "-",
    },
    {
      title: "Expiry",
      dataIndex: "expiry_date",
      width: "12%",
      render: (v: string) => v || "-",
    },
    {
      title: "Actions",
      key: "actions",
      width: "16%",
      render: (_: any, record: PriorAuthRequest) => (
        <Space size="small">
          {record.status === "PENDING" && (
            <Button
              size="small"
              type="primary"
              aria-label="Approve prior auth"
              onClick={() => {
                setDecideFor(record);
              }}
            >
              Decide
            </Button>
          )}
        </Space>
      ),
    },
  ];

  return (
    <Content style={{ padding: 24 }} role="main">
      <div className="pa-header">
        <h2>Prior Authorization</h2>
        <Space>
          <Button
            icon={<PlusOutlined />}
            onClick={() => setSubmitOpen(true)}
          >
            New Request
          </Button>
          <Button icon={<ReloadOutlined />} onClick={fetch}>
            Refresh
          </Button>
        </Space>
      </div>

      <PageState
        error={error}
        onRetry={() => fetch()}
        empty={!loading && !error && data.length === 0}
        emptyMessage="No prior-auth requests"
      >
        <Table
          rowKey="id"
          columns={columns}
          dataSource={data}
          loading={loading}
          pagination={{ pageSize: 20, showSizeChanger: true }}
          size="middle"
        />
      </PageState>

      <Modal
        title="New Prior-Auth Request"
        open={submitOpen}
        onCancel={() => setSubmitOpen(false)}
        footer={null}
      >
        <Form layout="vertical" onFinish={handleSubmit}>
          <Form.Item
            name="order_id"
            label="Order ID"
            rules={[{ required: true, message: "Order ID is required" }]}
          >
            <Input placeholder="Order UUID or accession" />
          </Form.Item>
          <Form.Item name="procedure_code" label="Procedure Code">
            <Input placeholder="e.g. CT CHEST" />
          </Form.Item>
          <Form.Item name="payer_id" label="Payer ID">
            <Input />
          </Form.Item>
          <Form.Item name="payer_name" label="Payer Name">
            <Input placeholder="e.g. Medicare" />
          </Form.Item>
          <Button type="primary" htmlType="submit" block>
            Submit Request
          </Button>
        </Form>
      </Modal>

      <Modal
        title={`Decision — Order ${decideFor?.order_id ?? ""}`}
        open={!!decideFor}
        onCancel={() => setDecideFor(null)}
        footer={null}
      >
        <Form
          layout="vertical"
          onFinish={handleDecide}
          initialValues={{ action: "approve" }}
        >
          <Form.Item name="action" label="Action" rules={[{ required: true }]}>
            <Radio.Group>
              <Radio.Button value="approve">Approve</Radio.Button>
              <Radio.Button value="deny">Deny</Radio.Button>
            </Radio.Group>
          </Form.Item>
          <Form.Item
            noStyle
            shouldUpdate={(prev, cur) => prev.action !== cur.action}
          >
            {({ getFieldValue }) =>
              getFieldValue("action") === "approve" ? (
                <>
                  <Form.Item name="auth_number" label="Auth Number">
                    <Input placeholder="Payer authorization number" />
                  </Form.Item>
                  <Form.Item name="approved_units" label="Approved Units">
                    <InputNumber min={1} style={{ width: "100%" }} />
                  </Form.Item>
                  <Form.Item name="expiry_date" label="Expiry Date">
                    <DatePicker style={{ width: "100%" }} />
                  </Form.Item>
                </>
              ) : (
                <Form.Item name="denial_reason" label="Denial Reason">
                  <Input.TextArea rows={2} />
                </Form.Item>
              )
            }
          </Form.Item>
          <Button type="primary" htmlType="submit" block>
            Confirm Decision
          </Button>
        </Form>
      </Modal>
    </Content>
  );
}

export default withSidebar(PriorAuthPanel);