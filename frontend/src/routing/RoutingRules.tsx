import { useDocumentTitle } from "../hooks";
import React, { useState, useEffect } from "react";
import {
  App,
  Layout,
  Table,
  Button,
  Tag,
  Modal,
  Form,
  Input,
  InputNumber,
  Switch,
  Popconfirm,
  Tooltip,
} from "antd";
import { EditOutlined, DeleteOutlined } from "@ant-design/icons";
import withSidebar from "../common/base";
import PageHeader from "../common/PageHeader";
import {
  listRoutingRules,
  createRoutingRule,
  updateRoutingRule,
  deleteRoutingRule,
  type RoutingRule,
} from "../api/routing";
import { PageState } from "../common/PageState";
import RequirePermission from "../auth/RequirePermission";
import { useAuth } from "../auth/AuthContext";
import { RuleConditionBuilder } from "./RuleConditionBuilder";

const Content = Layout.Content;

function RoutingRules() {
  const { message } = App.useApp();
  useDocumentTitle("QuantumPACS - Routing Rules");
  const { hasPermission } = useAuth();

  // ROUTING_READ gates the page; create/edit/delete are ROUTING_WRITE actions
  // (backend /api/routing guards match).
  const canWrite = hasPermission("ROUTING_WRITE");

  const [data, setData] = useState<RoutingRule[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pagination, setPagination] = useState<any>({
    current: 1,
    pageSize: 50,
    total: 0,
    pages: 0,
  });
  const [visible, setVisible] = useState(false);
  const [editingRule, setEditingRule] = useState<RoutingRule | null>(null);
  const [conditions, setConditions] = useState<Record<string, any>>({});
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
      render: (_: any, record: any) =>
        canWrite ? (
          <span>
            <Tooltip title="Edit rule">
              <EditOutlined
                onClick={() => handleEdit(record)}
                style={{ cursor: "pointer", marginRight: 12, fontSize: 16 }}
              />
            </Tooltip>
            <Popconfirm
              title="Delete this rule?"
              onConfirm={() => handleDelete(record.id)}
            >
              <Tooltip title="Delete rule">
                <DeleteOutlined
                  title="Delete"
                  style={{ cursor: "pointer", color: "#ff4d4f", fontSize: 16 }}
                />
              </Tooltip>
            </Popconfirm>
          </span>
        ) : null,
    },
  ];

  useEffect(() => {
    fetch({ page: 1, per_page: 50 });
  }, []);

  const fetch = (params: any) => {
    setLoading(true);
    setError(null);
    listRoutingRules(params)
      .then((res) => {
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
        createRoutingRule({ ...values, conditions })
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
        if (!editingRule) return;
        const data: any = {};
        for (const key of [
          "name",
          "destination",
          "priority",
          "enabled",
          "description",
        ] as const) {
          if (values[key] !== undefined && values[key] !== editingRule[key])
            data[key] = values[key];
        }
        data.conditions = conditions;
        if (Object.keys(data).length === 0) {
          setVisible(false);
          setEditingRule(null);
          return;
        }
        updateRoutingRule(editingRule.id, data)
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
    deleteRoutingRule(id)
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

  const openCreate = () => {
    setEditingRule(null);
    form.resetFields();
    setConditions({});
    setVisible(true);
  };

  return (
    <Content style={{ padding: 24 }}>
      <PageHeader
        title="Routing"
        description="Route incoming studies and messages to destinations by rule."
        extra={
          <RequirePermission permission="ROUTING_WRITE">
            <Button type="primary" onClick={openCreate}>
              Create Rule
            </Button>
          </RequirePermission>
        }
      />
      <PageState
        error={error}
        onRetry={() => fetch({ page: 1, per_page: 50 })}
        empty={!loading && !error && data.length === 0}
        emptyMessage="No routing rules configured"
        emptyAction={
          <RequirePermission permission="ROUTING_WRITE">
            <Button type="primary" onClick={openCreate}>
              Create Rule
            </Button>
          </RequirePermission>
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
