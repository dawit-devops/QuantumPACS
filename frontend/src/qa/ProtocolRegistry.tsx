import { useDocumentTitle } from "../hooks";
import React, { useState, useEffect, useCallback } from "react";
import {
  Layout,
  Table,
  Button,
  Input,
  Modal,
  Form,
  Select,
  Tag,
  InputNumber,
  message,
  Popconfirm,
  Alert,
  Space,
} from "antd";
import { PlusOutlined, ReloadOutlined } from "@ant-design/icons";
import withSidebar from "../common/base";
import { useAuth } from "../auth/AuthContext";
import { MODALITIES } from "../common/modalities";
import { request } from "../helpers";
import "./ProtocolRegistry.css";

const Content = Layout.Content;
const { TextArea } = Input;

// Protocol registry modalities — subset of the canonical list.
const PROTOCOL_MODALITIES = MODALITIES.filter((m) =>
  ["CT", "MR", "US", "DX", "MG", "FL", "PET"].includes(m)
);

function ProtocolRegistry() {
  useDocumentTitle("QuantumPACS - Protocol Registry");
  const { hasPermission } = useAuth();
  const canManage = hasPermission("PROTOCOL_MANAGE");
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<any>(null);
  const [form] = Form.useForm();
  const [sequences, setSequences] = useState<any[]>([]);
  const [search, setSearch] = useState("");
  const [modality, setModality] = useState<string | undefined>();

  const fetchProtocols = useCallback(() => {
    setLoading(true);
    const query: Record<string, string> = {};
    if (modality) query.modality = modality;
    if (search) query.search = search;
    request("qa/protocols", { query })
      .then((res: any) => {
        setLoading(false);
        setData(Array.isArray(res.data) ? res.data : []);
      })
      .catch((e: any) => {
        setLoading(false);
        setError(e.message);
      });
  }, [modality, search]);

  useEffect(() => {
    fetchProtocols();
  }, [fetchProtocols]);

  const openCreate = () => {
    setEditing(null);
    setSequences([{ name: "", required: true }]);
    form.resetFields();
    setModalOpen(true);
  };

  const openEdit = (row: any) => {
    setEditing(row);
    form.setFieldsValue({
      name: row.name,
      protocol_code: row.protocol_code,
      modality: row.modality,
      body_part: row.body_part,
      acr_benchmark_dlp: row.acr_benchmark_dlp,
      acr_benchmark_ctdivol: row.acr_benchmark_ctdivol,
      acr_benchmark_min_snr: row.acr_benchmark_min_snr,
      is_default: row.is_default,
    });
    setSequences(
      (row.sequences || []).length > 0
        ? (row.sequences || []).map((s: any) => ({
            name: s.name,
            required: s.required !== false,
          }))
        : [{ name: "", required: true }],
    );
    setModalOpen(true);
  };

  const submit = async () => {
    const values = await form.validateFields();
    const payload = {
      ...values,
      sequences: sequences
        .filter((s) => s.name && s.name.trim())
        .map((s) => ({ name: s.name.trim(), required: s.required })),
    };
    try {
      if (editing) {
        await request(`qa/protocols/${editing.id}`, {
          method: "PUT",
          data: payload,
        });
        message.success("Protocol updated");
      } else {
        await request("qa/protocols", { method: "POST", data: payload });
        message.success("Protocol created");
      }
      setModalOpen(false);
      fetchProtocols();
    } catch (e: any) {
      message.error(e.message || "Failed to save protocol");
    }
  };

  const remove = async (id: string) => {
    try {
      await request(`qa/protocols/${id}`, { method: "DELETE" });
      message.success("Protocol deleted");
      fetchProtocols();
    } catch (e: any) {
      message.error(e.message || "Failed to delete protocol");
    }
  };

  const columns = [
    {
      title: "Code",
      dataIndex: "protocol_code",
      key: "code",
      render: (v: string) => (v ? <Tag color="blue">{v}</Tag> : "-"),
    },
    { title: "Name", dataIndex: "name", key: "name" },
    {
      title: "Modality",
      dataIndex: "modality",
      key: "modality",
      render: (v: string) => <Tag>{v}</Tag>,
    },
    {
      title: "Body Part",
      dataIndex: "body_part",
      key: "body_part",
      render: (v: string) => v || "-",
    },
    {
      title: "Sequences",
      key: "sequences",
      render: (_: any, row: any) => (
        <span>{(row.sequences || []).length} required</span>
      ),
    },
    {
      title: "ACR DLP",
      dataIndex: "acr_benchmark_dlp",
      key: "dlp",
      render: (v: number) => (v != null ? `${v} mGy·cm` : "-"),
    },
    {
      title: "",
      key: "actions",
      render: (_: any, row: any) =>
        canManage ? (
          <Space>
            <Button size="small" onClick={() => openEdit(row)}>
              Edit
            </Button>
            <Popconfirm
              title="Delete this protocol?"
              onConfirm={() => remove(row.id)}
            >
              <Button size="small" danger>
                Delete
              </Button>
            </Popconfirm>
          </Space>
        ) : null,
    },
  ];

  return (
    <Content style={{ padding: "16px" }}>
      <div className="qa-header">
        <h2>Protocol Registry</h2>
        <Space>
          <Select
            allowClear
            placeholder="Modality"
            style={{ width: 120 }}
            value={modality}
            onChange={setModality}
            options={PROTOCOL_MODALITIES.map((m) => ({ value: m, label: m }))}
          />
          <Input
            allowClear
            placeholder="Search name / code"
            style={{ width: 200 }}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <Button
            icon={<ReloadOutlined />}
            onClick={fetchProtocols}
            aria-label="Refresh protocols"
          />
          {canManage && (
            <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
              Add Protocol
            </Button>
          )}
        </Space>
      </div>
      {error && (
        <Alert
          type="error"
          showIcon
          message={error}
          style={{ margin: "8px 0" }}
        />
      )}
      <Table
        rowKey="id"
        loading={loading}
        columns={columns}
        dataSource={data}
        pagination={false}
      />

      <Modal
        title={editing ? "Edit Protocol" : "Add Protocol"}
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={submit}
        okText={editing ? "Save" : "Create"}
        width={640}
      >
        <Form
          form={form}
          layout="vertical"
          initialValues={{ modality: "CT", is_default: false }}
        >
          <div className="proto-form-grid">
            <Form.Item
              name="name"
              label="Protocol Name"
              rules={[{ required: true, message: "Name required" }]}
            >
              <Input maxLength={120} aria-label="Protocol name" />
            </Form.Item>
            <Form.Item
              name="protocol_code"
              label="Protocol Code (unique)"
              rules={[
                { pattern: /^[A-Za-z0-9_]*$/, message: "Alphanumeric only" },
              ]}
            >
              <Input maxLength={40} aria-label="Protocol code" />
            </Form.Item>
          </div>
          <div className="proto-form-grid">
            <Form.Item
              name="modality"
              label="Modality"
              rules={[{ required: true }]}
            >
              <Select
                options={PROTOCOL_MODALITIES.map((m) => ({ value: m, label: m }))}
              />
            </Form.Item>
            <Form.Item name="body_part" label="Body Part">
              <Input maxLength={80} aria-label="Body part" />
            </Form.Item>
          </div>

          <div className="qa-field">
            <label>Required Sequences</label>
            {sequences.map((s, idx) => (
              <div className="proto-seq-row" key={idx}>
                <Input
                  placeholder="Sequence name (e.g. Axial T1)"
                  value={s.name}
                  onChange={(e) => {
                    const next = [...sequences];
                    next[idx] = { ...next[idx], name: e.target.value };
                    setSequences(next);
                  }}
                  aria-label={`Sequence ${idx + 1} name`}
                />
                <Select
                  value={s.required}
                  style={{ width: 130 }}
                  onChange={(v) => {
                    const next = [...sequences];
                    next[idx] = { ...next[idx], required: v };
                    setSequences(next);
                  }}
                  options={[
                    { value: true, label: "Required" },
                    { value: false, label: "Optional" },
                  ]}
                />
                <Button
                  danger
                  onClick={() =>
                    setSequences(sequences.filter((_, i) => i !== idx))
                  }
                  aria-label={`Remove sequence ${idx + 1}`}
                >
                  ✕
                </Button>
              </div>
            ))}
            <Button
              type="dashed"
              block
              onClick={() =>
                setSequences([...sequences, { name: "", required: true }])
              }
              style={{ marginTop: 6 }}
            >
              + Add sequence
            </Button>
          </div>

          <div className="qa-field">
            <label>ACR Benchmarks</label>
            <div className="qa-dose-grid">
              <div>
                <span>Max DLP (mGy·cm)</span>
                <Form.Item name="acr_benchmark_dlp" noStyle>
                  <InputNumber
                    min={0}
                    style={{ width: "100%" }}
                    aria-label="ACR max DLP"
                  />
                </Form.Item>
              </div>
              <div>
                <span>Max CTDIvol (mGy)</span>
                <Form.Item name="acr_benchmark_ctdivol" noStyle>
                  <InputNumber
                    min={0}
                    style={{ width: "100%" }}
                    aria-label="ACR max CTDIvol"
                  />
                </Form.Item>
              </div>
              <div>
                <span>Min SNR</span>
                <Form.Item name="acr_benchmark_min_snr" noStyle>
                  <InputNumber
                    min={0}
                    style={{ width: "100%" }}
                    aria-label="ACR min SNR"
                  />
                </Form.Item>
              </div>
            </div>
          </div>
        </Form>
      </Modal>
    </Content>
  );
}

export default withSidebar(ProtocolRegistry);
