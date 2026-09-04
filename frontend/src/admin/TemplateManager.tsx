import { useDocumentTitle } from "../hooks";
import React, { useState, useCallback, useEffect } from "react";
import {
  App,
  Layout,
  Table,
  Button,
  Space,
  Modal,
  Input,
  Tag,
  Drawer,
} from "antd";
import { ReloadOutlined, HistoryOutlined } from "@ant-design/icons";
import withSidebar from "../common/base";
import { PageState } from "../common/PageState";
import {
  listReportTemplates,
  listTemplateVersions,
  publishTemplateVersion,
  rollbackTemplateVersion,
  type ReportTemplate,
  type TemplateVersion,
} from "../api/reports-ris";

const Content = Layout.Content;

// R2-02-08: template manager — the admin surface for the versioned
// report-template library. Publish snapshots a new version; rollback
// re-activates any prior one (history is append-only).
function TemplateManager() {
  const { message } = App.useApp();
  useDocumentTitle("QuantumPACS - Report Templates");
  const [rows, setRows] = useState<ReportTemplate[]>([]);
  const [loading, setLoading] = useState(false);
  const [editing, setEditing] = useState<ReportTemplate | null>(null);
  const [findings, setFindings] = useState("");
  const [impression, setImpression] = useState("");
  const [saving, setSaving] = useState(false);
  const [versionsFor, setVersionsFor] = useState<ReportTemplate | null>(null);
  const [versions, setVersions] = useState<TemplateVersion[]>([]);
  const [versionsLoading, setVersionsLoading] = useState(false);

  const fetchRows = useCallback(async () => {
    setLoading(true);
    try {
      setRows(await listReportTemplates());
    } catch (e) {
      message.error(e instanceof Error ? e.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }, [message]);

  useEffect(() => {
    fetchRows();
  }, [fetchRows]);

  const openEdit = (row: ReportTemplate) => {
    setFindings(row.findings_template || "");
    setImpression(row.impression_template || "");
    setEditing(row);
  };

  const publish = async () => {
    if (!editing) return;
    setSaving(true);
    try {
      await publishTemplateVersion(editing.id, { findings, impression });
      message.success("New version published");
      setEditing(null);
      fetchRows();
    } catch (e) {
      message.error(e instanceof Error ? e.message : "Publish failed");
    } finally {
      setSaving(false);
    }
  };

  const openVersions = async (row: ReportTemplate) => {
    setVersionsFor(row);
    setVersionsLoading(true);
    try {
      setVersions(await listTemplateVersions(row.id));
    } catch {
      setVersions([]);
    } finally {
      setVersionsLoading(false);
    }
  };

  const rollback = async (version: number) => {
    if (!versionsFor) return;
    try {
      await rollbackTemplateVersion(versionsFor.id, version);
      message.success(`Rolled back to v${version}`);
      setVersionsFor(null);
      fetchRows();
    } catch (e) {
      message.error(e instanceof Error ? e.message : "Rollback failed");
    }
  };

  return (
    <Content style={{ padding: 24 }}>
      <div style={{ marginBottom: 16 }}>
        <h2>Report Templates</h2>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={fetchRows}>
            Refresh
          </Button>
        </Space>
      </div>
      <Table
        rowKey="id"
        size="small"
        loading={loading}
        dataSource={rows}
        pagination={{ pageSize: 20, showSizeChanger: false }}
        columns={[
          { title: "Name", dataIndex: "name" },
          {
            title: "Modality",
            dataIndex: "modality",
            width: 110,
            render: (v: string) => <Tag>{v}</Tag>,
          },
          {
            title: "Actions",
            key: "actions",
            width: 200,
            render: (_: unknown, row: ReportTemplate) => (
              <Space>
                <Button size="small" onClick={() => openEdit(row)}>
                  Edit
                </Button>
                <Button
                  size="small"
                  icon={<HistoryOutlined />}
                  onClick={() => openVersions(row)}
                >
                  History
                </Button>
              </Space>
            ),
          },
        ]}
      />

      <Modal
        title={`Edit — ${editing?.name || ""}`}
        open={editing !== null}
        onOk={publish}
        onCancel={() => setEditing(null)}
        okText="Publish"
        confirmLoading={saving}
      >
        <Input.TextArea
          rows={4}
          value={findings}
          onChange={(e) => setFindings(e.target.value)}
          placeholder="Findings template"
          style={{ marginBottom: 12 }}
        />
        <Input.TextArea
          rows={3}
          value={impression}
          onChange={(e) => setImpression(e.target.value)}
          placeholder="Impression template"
        />
      </Modal>

      <Drawer
        title={`Versions — ${versionsFor?.name || ""}`}
        open={versionsFor !== null}
        onClose={() => setVersionsFor(null)}
        size={480}
      >
        <PageState loading={versionsLoading}>
          <Table
            rowKey={(v) => String(v.version_number)}
            size="small"
            dataSource={versions}
            pagination={false}
            columns={[
              { title: "Ver", dataIndex: "version_number", width: 60 },
              { title: "Findings", dataIndex: "findings_template", ellipsis: true },
              {
                title: "",
                key: "act",
                width: 120,
                render: (_: unknown, v: TemplateVersion) => (
                  <Button size="small" onClick={() => rollback(v.version_number)}>
                    Rollback
                  </Button>
                ),
              },
            ]}
          />
        </PageState>
      </Drawer>
    </Content>
  );
}

const TemplateManagerPage = withSidebar(TemplateManager);
export default TemplateManagerPage;
export { TemplateManager };
