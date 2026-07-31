import React, { useState, useEffect } from "react";
import {
  Layout,
  Table,
  message,
  Button,
  Tag,
  Modal,
  Form,
  Input,
  InputNumber,
  Switch,
  Popconfirm,
} from "antd";
import { EditOutlined, DeleteOutlined } from "@ant-design/icons";
import withSidebar from "../common/base";
import { request } from "../helpers";
import { PageState } from "../common/PageState";
import { RuleConditionBuilder } from "./RuleConditionBuilder";

const Content = Layout.Content;

function RoutingRules() {
  document.title = "QuantumPACS - Routing Rules";

  let [data, setData] = useState<any[]>([]);
  let [loading, setLoading] = useState(false);
  let [error, setError] = useState<string | null>(null);
  let [pagination, setPagination] = useState<any>({
    current: 1,
    pageSize: 50,
    total: 0,
    pages: 0,
  });
  let [visible, setVisible] = useState(false);
  let [editingRule, setEditingRule] = useState<any | null>(null);
  let [conditions, setConditions] = useState<Record<string, any>>({});
  const [form] = Form.useForm();

  const columns: any[] = [
    { title: "Name", dataIndex: "name", width: "18%" },
    {
      title: "Status",
      dataIndex: "enabled",
      width: "8%",
      render: (enabled: boolean) =>
        enabled ? (
          <Tag color="green">Active</Tag>
        ) : (
          <Tag color="default">Disabled</Tag>
        ),
    },
    { title: "Destination", dataIndex: "destination", width: "15%" },
    { title: "Priority", dataIndex: "priority", width: "6%" },
    {
      title: "Conditions",
      dataIndex: "conditions",
      width: "28%",
      render: (c: any) => {
        if (!c) return "-";
        return (
          <span>
            {Object.entries(c)
              .slice(0, 2)
              .map(([k, v]) => (
                <Tag key={k} style={{ marginBottom: 2 }}>
                  {k}: {typeof v === "object" ? JSON.stringify(v) : String(v)}
                </Tag>
              ))}
            {Object.keys(c).length > 2 && (
              <Tag color="default">+{Object.keys(c).length - 2}</Tag>
            )}
          </span>
        );
      },
    },
    {
      title: "Action",
      key: "action",
      width: "10%",
      render: (_: any, record: any) => (
        <span>
          <EditOutlined
            onClick={() => handleEdit(record)}
            style={{ cursor: "pointer", marginRight: 12, fontSize: 16 }}
          />
          <Popconfirm
            title="Delete this rule?"
            onConfirm={() => handleDelete(record.id)}
          >
            <DeleteOutlined
              title="Delete"
              style={{ cursor: "pointer", color: "#ff4d4f", fontSize: 16 }}
            />
          </Popconfirm>
        </span>
      ),
    },
  ];

  useEffect(() => {
    fetch({ page: 1, per_page: 50 });
  }, []);

  const fetch = (params: any) => {
    setLoading(true);
    setError(null);
    request("routing", params)
      .then((res: any) => {
        setLoading(false);
        setData(Array.isArray(res.data) ? res.data : []);
        if (res.pagination) setPagination(res.pagination);
      })
      .catch((e: any) => {
        setLoading(false);
        setError(e.message);
        message.error(e.message);
      });
  };

  const handleTableChange = (pag: any) => {
    setPagination(pag);
    fetch({ page: pag.current, per_page: pag.pageSize });
  };

  const handleCreate = () => {
    form
      .validateFields()
      .then((values: any) => {
        request("routing", { data: { ...values, conditions } })
          .then(() => {
            form.resetFields();
            setConditions({});
            setVisible(false);
            fetch({ page: 1, per_page: 50 });
          })
          .catch((e: any) => {
            message.error(e.message);
          });
      })
      .catch(() => {});
  };

  const handleEdit = (rule: any) => {
    setEditingRule(rule);
    setConditions(rule.conditions || {});
    form.setFieldsValue({
      name: rule.name,
      destination: rule.destination,
      priority: rule.priority,
      enabled: rule.enabled !== false,
      description: rule.description || "",
    });
    setVisible(true);
  };

  const handleUpdate = () => {
    form
      .validateFields()
      .then((values: any) => {
        const data: any = {};
        for (const key of [
          "name",
          "destination",
          "priority",
          "enabled",
          "description",
        ]) {
          if (values[key] !== undefined && values[key] !== editingRule[key])
            data[key] = values[key];
        }
        data.conditions = conditions;
        if (Object.keys(data).length === 0) {
          setVisible(false);
          setEditingRule(null);
          return;
        }
        request(`routing/${editingRule.id}`, { data })
          .then(() => {
            form.resetFields();
            setConditions({});
            setEditingRule(null);
            setVisible(false);
            fetch({ page: 1, per_page: 50 });
          })
          .catch((e: any) => {
            message.error(e.message);
          });
      })
      .catch(() => {});
  };

  const handleDelete = (id: string) => {
    request(`routing/${id}`, { data: undefined, method: "DELETE" })
      .then(() => {
        fetch({ page: 1, per_page: 50 });
      })
      .catch((e: any) => {
        message.error(e.message);
      });
  };

  const handleModalCancel = () => {
    form.resetFields();
    setConditions({});
    setEditingRule(null);
    setVisible(false);
  };

  return (
    <Content style={{ padding: 50 }}>
      <Button
        type="primary"
        onClick={() => {
          setEditingRule(null);
          form.resetFields();
          setConditions({});
          setVisible(true);
        }}
        style={{ marginBottom: 16 }}
      >
        Create Rule
      </Button>
      <PageState
        error={error}
        onRetry={() => fetch({ page: 1, per_page: 50 })}
        empty={!loading && !error && data.length === 0}
        emptyMessage="No routing rules configured"
        emptyAction={
          <Button
            type="primary"
            onClick={() => {
              setEditingRule(null);
              form.resetFields();
              setConditions({});
              setVisible(true);
            }}
          >
            Create Rule
          </Button>
        }
      >
        <Table
          rowKey="id"
          columns={columns}
          dataSource={data}
          loading={loading}
          pagination={{
            current: pagination.page,
            pageSize: pagination.per_page,
            total: pagination.total,
          }}
          onChange={handleTableChange}
        />
      </PageState>
      <Modal
        title={editingRule ? "Edit Routing Rule" : "Create Routing Rule"}
        open={visible}
        onCancel={handleModalCancel}
        onOk={editingRule ? handleUpdate : handleCreate}
        width={640}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="Name" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item
            name="destination"
            label="Destination"
            rules={[{ required: true }]}
          >
            <Input placeholder="e.g., replica_2" />
          </Form.Item>
          <Form.Item name="priority" label="Priority">
            <InputNumber min={0} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="enabled" label="Enabled" valuePropName="checked">
            <Switch defaultChecked />
          </Form.Item>
          <Form.Item name="description" label="Description">
            <Input.TextArea rows={2} />
          </Form.Item>
          <Form.Item label="Conditions">
            <RuleConditionBuilder value={conditions} onChange={setConditions} />
          </Form.Item>
        </Form>
      </Modal>
    </Content>
  );
}

export default withSidebar(RoutingRules);
