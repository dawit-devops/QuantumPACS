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
  InputNumber,
  Modal,
  Form,
  Alert,
  Tabs,
  Drawer,
  Popconfirm,
} from "antd";
import {
  ReloadOutlined,
  PlusOutlined,
  UploadOutlined,
  HistoryOutlined,
  CheckCircleOutlined,
} from "@ant-design/icons";
import withSidebar from "../common/base";
import { PageState } from "../common/PageState";
import {
  listFeeSchedule,
  updateFeeScheduleItem,
  importFeeSchedule,
  getFeeScheduleHistory,
  listPayerContracts,
  createPayerContract,
  updatePayerContract,
  deletePayerContract,
  getContractComparison,
  type FeeScheduleItem,
  type FeeScheduleHistoryRow,
  type PayerContract,
  type ContractComparisonRow,
} from "../api/billing-ris";

const Content = Layout.Content;

const FLAG_COLORS: Record<string, string> = {
  under_charge: "orange",
  over_charge: "red",
  at_rate: "green",
};

function FeeSchedule() {
  const { message } = App.useApp();
  useDocumentTitle("QuantumPACS - Fee Schedule & Contracts");

  // B-09 fee schedule
  const [items, setItems] = useState<FeeScheduleItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [editTarget, setEditTarget] = useState<FeeScheduleItem | null>(null);
  const [editForm] = Form.useForm();
  const [importOpen, setImportOpen] = useState(false);
  const [importForm] = Form.useForm();
  const [importing, setImporting] = useState(false);
  const [historyTarget, setHistoryTarget] = useState<FeeScheduleItem | null>(null);
  const [historyRows, setHistoryRows] = useState<FeeScheduleHistoryRow[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);

  // B-08 payer contracts
  const [contracts, setContracts] = useState<PayerContract[]>([]);
  const [contractsLoading, setContractsLoading] = useState(false);
  const [contractsError, setContractsError] = useState<string | null>(null);
  const [contractModal, setContractModal] = useState(false);
  const [contractForm] = Form.useForm();
  const [comparison, setComparison] = useState<ContractComparisonRow[]>([]);
  const [comparisonLoading, setComparisonLoading] = useState(false);

  const fetchSchedule = useCallback(() => {
    setLoading(true);
    setError(null);
    listFeeSchedule(search ? { code: search } : {})
      .then(setItems)
      .catch((e: any) => setError(e.message))
      .finally(() => setLoading(false));
  }, [search]);

  const fetchContracts = useCallback(() => {
    setContractsLoading(true);
    setContractsError(null);
    listPayerContracts()
      .then(setContracts)
      .catch((e: any) => setContractsError(e.message))
      .finally(() => setContractsLoading(false));
  }, []);

  const fetchComparison = useCallback(() => {
    setComparisonLoading(true);
    getContractComparison()
      .then(setComparison)
      .catch(() => setComparison([]))
      .finally(() => setComparisonLoading(false));
  }, []);

  useEffect(() => {
    fetchSchedule();
  }, [fetchSchedule]);

  useEffect(() => {
    fetchContracts();
    fetchComparison();
  }, [fetchContracts, fetchComparison]);

  const openEdit = (item: FeeScheduleItem) => {
    setEditTarget(item);
    editForm.setFieldsValue({ list_price: item.list_price, description: item.description });
  };

  const saveEdit = async () => {
    if (!editTarget) return;
    try {
      const values = await editForm.validateFields();
      await updateFeeScheduleItem(editTarget.procedure_code, values);
      message.success("Fee schedule updated");
      setEditTarget(null);
      fetchSchedule();
    } catch (e: any) {
      if (e.message) message.error(e.message || "Failed to update");
    }
  };

  const doImport = async () => {
    try {
      const values = await importForm.validateFields();
      setImporting(true);
      const rows = values.rows
        .split("\n")
        .map((line: string) => line.trim())
        .filter(Boolean)
        .map((line: string) => {
          const [procedure_code, ...rest] = line.split(",");
          const description = rest.slice(0, -1).join(",");
          const list_price = parseFloat(rest[rest.length - 1]);
          return {
            procedure_code: procedure_code.trim(),
            description: description.trim(),
            list_price,
          };
        })
        .filter((r: FeeScheduleItem) => r.procedure_code && !isNaN(r.list_price));
      const res = await importFeeSchedule(rows);
      message.success(`Imported ${res.imported} procedure(s)`);
      setImportOpen(false);
      importForm.resetFields();
      fetchSchedule();
    } catch (e: any) {
      if (e.message) message.error(e.message || "Import failed");
    } finally {
      setImporting(false);
    }
  };

  const openHistory = async (item: FeeScheduleItem) => {
    setHistoryTarget(item);
    setHistoryLoading(true);
    setHistoryRows([]);
    try {
      setHistoryRows(await getFeeScheduleHistory(item.procedure_code));
    } catch (e: any) {
      message.error(e.message || "Failed to load history");
    } finally {
      setHistoryLoading(false);
    }
  };

  const saveContract = async () => {
    try {
      const values = await contractForm.validateFields();
      if (values.id) {
        await updatePayerContract(values.id, {
          contracted_rate: values.contracted_rate,
          effective_date: values.effective_date,
        });
        message.success("Contract updated");
      } else {
        await createPayerContract(values);
        message.success("Contract created");
      }
      setContractModal(false);
      contractForm.resetFields();
      fetchContracts();
      fetchComparison();
    } catch (e: any) {
      if (e.message) message.error(e.message || "Failed to save contract");
    }
  };

  const openContractEdit = (c: PayerContract) => {
    contractForm.setFieldsValue({
      id: c.id,
      payer_id: c.payer_id,
      payer_name: c.payer_name,
      procedure_code: c.procedure_code,
      contracted_rate: c.contracted_rate,
      effective_date: c.effective_date?.slice(0, 10),
    });
    setContractModal(true);
  };

  const openContractCreate = () => {
    contractForm.resetFields();
    setContractModal(true);
  };

  const deactivateContract = async (c: PayerContract) => {
    try {
      await deletePayerContract(c.id);
      message.success("Contract deactivated");
      fetchContracts();
      fetchComparison();
    } catch (e: any) {
      if (e.message) message.error(e.message || "Failed to deactivate");
    }
  };

  const money = (v: number | null | undefined) => (v == null ? "—" : `$${Number(v).toFixed(2)}`);

  const scheduleColumns = [
    {
      title: "Code",
      dataIndex: "procedure_code",
      key: "code",
      width: 120,
    },
    {
      title: "Description",
      dataIndex: "description",
      key: "desc",
    },
    {
      title: "List Price",
      dataIndex: "list_price",
      key: "price",
      width: 130,
      render: (v: number) => money(v),
    },
    {
      title: "Status",
      dataIndex: "active",
      key: "active",
      width: 100,
      render: (v: boolean) => (v ? <Tag color="green">Active</Tag> : <Tag>Inactive</Tag>),
    },
    {
      title: "Actions",
      key: "actions",
      width: 200,
      render: (_: unknown, row: FeeScheduleItem) => (
        <Space>
          <Button size="small" onClick={() => openEdit(row)}>
            Edit
          </Button>
          <Button size="small" icon={<HistoryOutlined />} onClick={() => openHistory(row)}>
            History
          </Button>
        </Space>
      ),
    },
  ];

  const contractColumns = [
    {
      title: "Payer",
      dataIndex: "payer_name",
      key: "payer",
      render: (v: string, row: PayerContract) => v || row.payer_id,
    },
    {
      title: "Procedure",
      dataIndex: "procedure_code",
      key: "proc",
      width: 120,
    },
    {
      title: "Contracted Rate",
      dataIndex: "contracted_rate",
      key: "rate",
      width: 150,
      render: (v: number) => money(v),
    },
    {
      title: "Effective",
      dataIndex: "effective_date",
      key: "eff",
      width: 120,
      render: (v: string) => (v ? new Date(v).toLocaleDateString() : "—"),
    },
    {
      title: "Status",
      dataIndex: "active",
      key: "active",
      width: 100,
      render: (v: boolean) => (v ? <Tag color="green">Active</Tag> : <Tag>Inactive</Tag>),
    },
    {
      title: "Actions",
      key: "actions",
      width: 160,
      render: (_: unknown, row: PayerContract) => (
        <Space>
          <Button size="small" onClick={() => openContractEdit(row)}>
            Edit
          </Button>
          {row.active && (
            <Popconfirm title="Deactivate this contract?" onConfirm={() => deactivateContract(row)}>
              <Button size="small" danger>
                Deactivate
              </Button>
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ];

  const comparisonColumns = [
    {
      title: "Payer",
      dataIndex: "payer_name",
      key: "payer",
      render: (v: string) => v || "—",
    },
    {
      title: "Procedure",
      dataIndex: "procedure_code",
      key: "proc",
      width: 120,
    },
    {
      title: "Charged",
      dataIndex: "charged_amount",
      key: "charged",
      width: 120,
      render: (v: number) => money(v),
    },
    {
      title: "Contracted",
      dataIndex: "contracted_rate",
      key: "contracted",
      width: 120,
      render: (v: number) => money(v),
    },
    {
      title: "Variance",
      dataIndex: "variance",
      key: "variance",
      width: 110,
      render: (v: number) => (
        <span>
          {v >= 0 ? "+" : ""}
          {money(v)}
        </span>
      ),
    },
    {
      title: "Flag",
      dataIndex: "flag",
      key: "flag",
      width: 130,
      render: (v: string) => <Tag color={FLAG_COLORS[v] || "default"}>{v}</Tag>,
    },
  ];

  const feeTab = (
    <>
      <div className="billing-queue-header">
        <h2 style={{ margin: 0 }}>Procedure Fee Schedule</h2>
        <Space>
          <Input.Search
            placeholder="Search by code"
            allowClear
            onSearch={(v) => setSearch(v)}
            style={{ width: 220 }}
          />
          <Button icon={<UploadOutlined />} onClick={() => setImportOpen(true)}>
            Import (CMS)
          </Button>
          <Button icon={<ReloadOutlined />} onClick={fetchSchedule}>
            Refresh
          </Button>
        </Space>
      </div>

      <PageState
        error={error}
        onRetry={fetchSchedule}
        loading={loading}
        empty={!loading && !error && items.length === 0}
        emptyMessage="No procedures in the fee schedule"
      >
        <Table<FeeScheduleItem>
          rowKey="procedure_code"
          columns={scheduleColumns}
          dataSource={items}
          pagination={{ pageSize: 20 }}
          size="middle"
        />
      </PageState>

      <Modal
        title={`Edit ${editTarget?.procedure_code ?? ""}`}
        open={!!editTarget}
        onCancel={() => setEditTarget(null)}
        onOk={saveEdit}
        okText="Save"
      >
        <Form form={editForm} layout="vertical">
          <Form.Item
            name="list_price"
            label="List Price"
            rules={[{ required: true, message: "Price required" }]}
          >
            <InputNumber min={0} step={0.01} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="description" label="Description">
            <Input />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="Import Fee Schedule"
        open={importOpen}
        onCancel={() => setImportOpen(false)}
        onOk={doImport}
        okText="Import"
        confirmLoading={importing}
        width={560}
      >
        <Alert
          type="info"
          showIcon
          message="One procedure per line: procedure_code, description, list_price"
          style={{ marginBottom: 16 }}
        />
        <Form form={importForm} layout="vertical">
          <Form.Item
            name="rows"
            label="CSV Rows"
            rules={[{ required: true, message: "Paste at least one row" }]}
          >
            <Input.TextArea
              rows={8}
              placeholder={"71250, CT Chest, 350.00\n72125, CT Head, 320.00"}
            />
          </Form.Item>
        </Form>
      </Modal>

      <Drawer
        title={`History — ${historyTarget?.procedure_code ?? ""}`}
        open={!!historyTarget}
        onClose={() => setHistoryTarget(null)}
        width={520}
      >
        <Table<FeeScheduleHistoryRow>
          rowKey={(r, i) => `${r.changed_at}-${i}`}
          loading={historyLoading}
          columns={[
            { title: "Price", dataIndex: "list_price", width: 110, render: money },
            { title: "Description", dataIndex: "description" },
            {
              title: "Changed",
              dataIndex: "changed_at",
              width: 160,
              render: (v: string) => (v ? new Date(v).toLocaleString() : "—"),
            },
          ]}
          dataSource={historyRows}
          pagination={false}
          size="small"
        />
      </Drawer>
    </>
  );

  const contractsTab = (
    <>
      <div className="billing-queue-header">
        <h2 style={{ margin: 0 }}>Payer Contract Rates</h2>
        <Space>
          <Button type="primary" icon={<PlusOutlined />} onClick={openContractCreate}>
            Add Contract
          </Button>
          <Button icon={<CheckCircleOutlined />} onClick={fetchComparison}>
            Refresh Comparison
          </Button>
        </Space>
      </div>

      <PageState
        error={contractsError}
        onRetry={fetchContracts}
        loading={contractsLoading}
        empty={!contractsLoading && !contractsError && contracts.length === 0}
        emptyMessage="No payer contracts configured"
      >
        <Table<PayerContract>
          rowKey="id"
          columns={contractColumns}
          dataSource={contracts}
          pagination={{ pageSize: 10 }}
          size="middle"
        />
      </PageState>

      <h3 style={{ marginTop: 24 }}>Charge vs. Contract Comparison</h3>
      <PageState
        error={null}
        onRetry={fetchComparison}
        loading={comparisonLoading}
        empty={!comparisonLoading && comparison.length === 0}
        emptyMessage="No charges match an active contract rate yet"
      >
        <Table<ContractComparisonRow>
          rowKey="charge_id"
          columns={comparisonColumns}
          dataSource={comparison}
          pagination={{ pageSize: 10 }}
          size="middle"
        />
      </PageState>

      <Modal
        title={contractForm.getFieldValue("id") ? "Edit Contract" : "Add Contract"}
        open={contractModal}
        onCancel={() => setContractModal(false)}
        onOk={saveContract}
        okText="Save"
        width={520}
      >
        <Form form={contractForm} layout="vertical" initialValues={{}}>
          <Form.Item name="id" hidden>
            <Input />
          </Form.Item>
          <Form.Item
            name="payer_id"
            label="Payer ID"
            rules={[{ required: true, message: "Payer ID required" }]}
          >
            <Input placeholder="e.g. AETNA" disabled={!!contractForm.getFieldValue("id")} />
          </Form.Item>
          <Form.Item name="payer_name" label="Payer Name">
            <Input placeholder="e.g. Aetna" disabled={!!contractForm.getFieldValue("id")} />
          </Form.Item>
          <Form.Item
            name="procedure_code"
            label="Procedure Code"
            rules={[{ required: true, message: "Procedure code required" }]}
          >
            <Input placeholder="e.g. 71250" disabled={!!contractForm.getFieldValue("id")} />
          </Form.Item>
          <Form.Item
            name="contracted_rate"
            label="Contracted Rate"
            rules={[{ required: true, message: "Rate required" }]}
          >
            <InputNumber min={0} step={0.01} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="effective_date" label="Effective Date">
            <Input type="date" />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );

  return (
    <Content style={{ padding: 24 }} role="main">
      <Tabs
        defaultActiveKey="feeschedule"
        items={[
          { key: "feeschedule", label: "Fee Schedule", children: feeTab },
          { key: "contracts", label: "Payer Contracts", children: contractsTab },
        ]}
      />
    </Content>
  );
}

export default withSidebar(FeeSchedule);
