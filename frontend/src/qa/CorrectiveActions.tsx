import { useDocumentTitle } from "../hooks";
import React, { useState, useEffect, useCallback } from "react";
import {
  App,
  Layout,
  Card,
  Tag,
  Button,
  Select,
  Modal,
  Input,
  Alert,
  Empty,
  Space,
  Badge,
} from "antd";
import { ReloadOutlined, CheckOutlined } from "@ant-design/icons";
import withSidebar from "../common/base";
import { useAuth } from "../auth/AuthContext";
import { request } from "../helpers";
import "./CorrectiveActions.css";

const Content = Layout.Content;
const { TextArea } = Input;

const SOURCE_COLORS: Record<string, string> = {
  R03: "purple",
  R05_self: "blue",
  R06: "orange",
};

function CorrectiveActions() {
  const { message } = App.useApp();
  useDocumentTitle("QuantumPACS - Corrective Actions");
  const { hasPermission } = useAuth();
  const canWrite = hasPermission("QA_WRITE");
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string | undefined>();
  const [resolving, setResolving] = useState<any>(null);
  const [findings, setFindings] = useState("");
  const [actionsTaken, setActionsTaken] = useState("");

  const fetchActions = useCallback(() => {
    setLoading(true);
    const query: Record<string, string> = {};
    if (statusFilter) query.status = statusFilter;
    request("qa/corrective-actions", { query })
      .then((res: any) => {
        setLoading(false);
        setData(Array.isArray(res.data) ? res.data : []);
      })
      .catch((e: any) => {
        setLoading(false);
        setError(e.message);
      });
  }, [statusFilter]);

  useEffect(() => {
    fetchActions();
  }, [fetchActions]);

  const resolve = async () => {
    if (!resolving) return;
    try {
      await request(`qa/corrective-actions/${resolving.id}/resolve`, {
        method: "POST",
        data: { findings, actions_taken: actionsTaken },
      });
      message.success("Corrective action resolved");
      setResolving(null);
      setFindings("");
      setActionsTaken("");
      fetchActions();
    } catch (e: any) {
      message.error(e.message || "Failed to resolve action");
    }
  };

  const openCount = data.filter((a) => a.status !== "resolved").length;

  return (
    <Content style={{ padding: "16px" }}>
      <div className="qa-header">
        <h2>
          Corrective Actions{" "}
          {openCount > 0 && (
            <Badge count={openCount} style={{ marginLeft: 8 }} />
          )}
        </h2>
        <Space>
          <Select
            allowClear
            placeholder="Status"
            style={{ width: 140 }}
            value={statusFilter}
            onChange={setStatusFilter}
            options={["open", "in_progress", "resolved"].map((s) => ({
              value: s,
              label: s,
            }))}
          />
          <Button
            icon={<ReloadOutlined />}
            onClick={fetchActions}
            aria-label="Refresh actions"
          />
        </Space>
      </div>
      {error && (
        <Alert
          type="error"
          showIcon
          title={error}
          style={{ margin: "8px 0" }}
        />
      )}
      {loading ? (
        <div className="ca-skeleton">Loading corrective actions...</div>
      ) : data.length === 0 ? (
        <Empty description="No corrective actions assigned" />
      ) : (
        <div className="ca-list">
          {data.map((a) => (
            <Card
              key={a.id}
              size="small"
              className={`ca-card ${a.status === "resolved" ? "resolved" : ""}`}
              title={
                <Space>
                  <Tag color={SOURCE_COLORS[a.source] || "default"}>
                    {a.source}
                  </Tag>
                  <Tag
                    color={
                      a.status === "resolved"
                        ? "green"
                        : a.status === "in_progress"
                          ? "blue"
                          : "gold"
                    }
                  >
                    {a.status}
                  </Tag>
                </Space>
              }
              extra={
                canWrite && a.status !== "resolved" ? (
                  <Button
                    type="primary"
                    size="small"
                    icon={<CheckOutlined />}
                    onClick={() => {
                      setResolving(a);
                      setFindings("");
                      setActionsTaken("");
                    }}
                  >
                    Resolve
                  </Button>
                ) : null
              }
            >
              <p className="ca-issue">{a.issue}</p>
              {(a.study_uids || []).length > 0 && (
                <p className="ca-uids">
                  <strong>Studies:</strong> {(a.study_uids || []).join(", ")}
                </p>
              )}
              <p className="ca-meta">
                Assigned{" "}
                {a.created_at
                  ? new Date(a.created_at).toLocaleDateString()
                  : "-"}
                {a.resolved_at
                  ? ` · Resolved ${new Date(a.resolved_at).toLocaleDateString()}`
                  : ""}
              </p>
              {a.status === "resolved" && (
                <div className="ca-resolution">
                  <p>
                    <strong>Findings:</strong> {a.findings}
                  </p>
                  <p>
                    <strong>Actions taken:</strong> {a.actions_taken}
                  </p>
                </div>
              )}
            </Card>
          ))}
        </div>
      )}

      <Modal
        title="Resolve Corrective Action"
        open={Boolean(resolving)}
        onCancel={() => setResolving(null)}
        onOk={resolve}
        okText="Mark resolved"
      >
        <p className="ca-issue">{resolving?.issue}</p>
        <TextArea
          rows={2}
          placeholder="Findings"
          value={findings}
          onChange={(e) => setFindings(e.target.value)}
          aria-label="Findings"
          style={{ marginBottom: 8 }}
        />
        <TextArea
          rows={2}
          placeholder="Actions taken"
          value={actionsTaken}
          onChange={(e) => setActionsTaken(e.target.value)}
          aria-label="Actions taken"
        />
      </Modal>
    </Content>
  );
}

export default withSidebar(CorrectiveActions);
