import { useDocumentTitle } from "../hooks";
import React, { useState, useEffect, useCallback } from "react";
import {
  App,
  Layout,
  Table,
  Tag,
  Button,
  Alert,
  Spin,
  Modal,
  Form,
  Select,
  Input,
  Popconfirm,
} from "antd";
import {
  AuditOutlined,
  ReloadOutlined,
  TeamOutlined,
  CheckOutlined,
  CloseOutlined,
} from "@ant-design/icons";
import withSidebar from "../common/base";
import { request } from "../helpers";
import { useAuth } from "../auth/AuthContext";
import "./PeerReviewInbox.css";

const Content = Layout.Content;

const STATUS_COLORS: Record<string, string> = {
  assigned: "blue",
  in_progress: "gold",
  completed: "green",
  rejected: "red",
};

const DISCREPANCY_COLORS: Record<string, string> = {
  none: "green",
  minor: "blue",
  major: "orange",
  discrepancy: "red",
};

function PeerReviewInbox() {
  const { message } = App.useApp();
  useDocumentTitle("QuantumPACS - Peer Review");
  // Submitting an outcome posts to /submit, gated PEER_REVIEW_WRITE on the
  // backend — a reviewer without the write grant views and discusses but
  // cannot close a review.
  const { hasPermission } = useAuth();
  const canSubmit = hasPermission("PEER_REVIEW_WRITE");
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [review, setReview] = useState<any | null>(null);
  const [reviewLoading, setReviewLoading] = useState(false);
  const [reviewError, setReviewError] = useState<string | null>(null);

  const [submitOpen, setSubmitOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [submitForm] = Form.useForm();

  const [declineOpen, setDeclineOpen] = useState(false);
  const [declining, setDeclining] = useState(false);
  const [declineForm] = Form.useForm();

  const fetchList = useCallback(() => {
    setLoading(true);
    setError(null);
    request("peer-reviews")
      .then((res: any) => {
        setLoading(false);
        setData(Array.isArray(res.data) ? res.data : []);
      })
      .catch((e: any) => {
        setLoading(false);
        setError(e.message);
      });
  }, []);

  useEffect(() => {
    fetchList();
  }, [fetchList]);

  const openReview = async (id: string) => {
    setReviewLoading(true);
    setReviewError(null);
    try {
      const res = await request(`peer-reviews/${id}`);
      setReview(res.data);
    } catch (e: any) {
      setReviewError(e.message);
    } finally {
      setReviewLoading(false);
    }
  };

  const submitReview = async () => {
    let values;
    try {
      values = await submitForm.validateFields();
    } catch {
      return;
    }
    if (!review) return;
    setSubmitting(true);
    try {
      await request(`peer-reviews/${review.id}/submit`, {
        data: {
          discrepancy_level: values.discrepancy_level,
          comment: values.comment || "",
        },
      });
      message.success("Peer review submitted");
      setSubmitOpen(false);
      setReview(null);
      submitForm.resetFields();
      fetchList();
    } catch (e: any) {
      message.error(e.message || "Submit failed");
    } finally {
      setSubmitting(false);
    }
  };

  const acceptReview = async () => {
    if (!review) return;
    setSubmitting(true);
    try {
      const res = await request(`peer-reviews/${review.id}/accept`, {
        method: "POST",
      });
      message.success("Review started");
      setReview(res.data);
      fetchList();
    } catch (e: any) {
      message.error(e.message || "Accept failed");
    } finally {
      setSubmitting(false);
    }
  };

  const declineReview = async () => {
    let values;
    try {
      values = await declineForm.validateFields();
    } catch {
      return;
    }
    if (!review) return;
    setDeclining(true);
    try {
      const res = await request(`peer-reviews/${review.id}/decline`, {
        method: "POST",
        data: { reason: values.reason || "" },
      });
      message.success("Peer review declined");
      setDeclineOpen(false);
      setReview(res.data);
      declineForm.resetFields();
      fetchList();
    } catch (e: any) {
      message.error(e.message || "Decline failed");
    } finally {
      setDeclining(false);
    }
  };

  const columns = [
    {
      title: "Accession",
      key: "accession",
      render: (_: unknown, r: any) => r.exam?.accession_number || "—",
    },
    {
      title: "Patient",
      key: "patient",
      render: (_: unknown, r: any) => r.exam?.patient_name || r.exam?.patient_id || "—",
    },
    {
      title: "Modality",
      key: "modality",
      width: 90,
      render: (_: unknown, r: any) => r.exam?.modality || "—",
    },
    {
      title: "Status",
      dataIndex: "status",
      key: "status",
      width: 120,
      render: (s: string) => <Tag color={STATUS_COLORS[s] || "default"}>{s}</Tag>,
    },
    {
      title: "Discrepancy",
      dataIndex: "discrepancy_level",
      key: "discrepancy_level",
      width: 130,
      render: (v: string) => (v ? <Tag color={DISCREPANCY_COLORS[v]}>{v}</Tag> : <span>—</span>),
    },
    {
      title: "Assigned",
      dataIndex: "assigned_at",
      key: "assigned_at",
      width: 170,
      render: (v: string) => (v ? new Date(v).toLocaleString() : "—"),
    },
    {
      title: "",
      key: "action",
      width: 130,
      render: (_: unknown, r: any) => (
        <Button
          size="small"
          type="primary"
          ghost
          onClick={() => openReview(r.id)}
          disabled={r.status === "completed"}
        >
          {r.status === "completed" ? "Done" : "Review"}
        </Button>
      ),
    },
  ];

  return (
    <Content style={{ padding: 24 }} role="main">
      <div className="pr-header">
        <div>
          <h2 style={{ margin: 0 }}>
            <AuditOutlined /> Peer Review
          </h2>
          <span className="pr-subtitle">
            Discrepancy-level reviews of signed reports assigned to you
          </span>
        </div>
        <Button icon={<ReloadOutlined />} onClick={fetchList}>
          Refresh
        </Button>
      </div>

      {error && (
        <Alert
          type="error"
          title="Failed to load peer reviews"
          description={error}
          showIcon
          style={{ marginBottom: 16 }}
        />
      )}

      {loading && !data.length ? (
        <div className="pr-loading">
          <Spin />
        </div>
      ) : (
        <Table
          rowKey="id"
          columns={columns}
          dataSource={data}
          pagination={{ pageSize: 20, showSizeChanger: false }}
          scroll={{ x: 800 }}
          locale={{ emptyText: "No peer reviews assigned to you yet." }}
        />
      )}

      {/* Review drawer/modal: full report + exam context, then submit outcome */}
      <Modal
        title="Peer Review"
        open={!!review}
        onCancel={() => setReview(null)}
        width={720}
        footer={null}
        destroyOnHidden
      >
        {reviewLoading && (
          <div className="pr-loading">
            <Spin />
          </div>
        )}
        {reviewError && <Alert type="error" title={reviewError} showIcon />}
        {review && (
          <div className="pr-review-body">
            <h3>
              {review.exam?.patient_name || review.exam?.patient_id} · {review.exam?.modality} ·{" "}
              {review.exam?.accession_number || "no accession"}
            </h3>
            <div className="pr-review-section">
              <b>Original Findings</b>
              <pre className="pr-review-text">{review.report?.findings || "—"}</pre>
            </div>
            <div className="pr-review-section">
              <b>Original Impression</b>
              <pre className="pr-review-text">{review.report?.impression || "—"}</pre>
            </div>
            {review.status === "completed" ? (
              <Alert
                type="success"
                showIcon
                title={`Review complete — discrepancy: ${review.discrepancy_level}`}
              />
            ) : review.status === "rejected" ? (
              <Alert
                type="error"
                showIcon
                title={`Review declined — ${review.declined_reason || "no reason given"}`}
              />
            ) : review.status === "assigned" ? (
              <div style={{ marginTop: 12 }}>
                <Popconfirm
                  title="Start this peer review?"
                  description="Accepts the assignment and moves it to in-progress."
                  okText="Start"
                  cancelText="Back"
                  onConfirm={acceptReview}
                >
                  <Button
                    type="primary"
                    icon={<CheckOutlined />}
                    loading={submitting}
                    disabled={!canSubmit}
                  >
                    Start Review
                  </Button>
                </Popconfirm>
                <Button
                  danger
                  icon={<CloseOutlined />}
                  onClick={() => setDeclineOpen(true)}
                  disabled={!canSubmit}
                  style={{ marginLeft: 8 }}
                >
                  Decline
                </Button>
              </div>
            ) : canSubmit ? (
              <Button
                type="primary"
                icon={<TeamOutlined />}
                onClick={() => setSubmitOpen(true)}
                style={{ marginTop: 12 }}
              >
                Submit Review Outcome
              </Button>
            ) : (
              <Alert
                type="info"
                showIcon
                style={{ marginTop: 12 }}
                title="Read-only review — submitting an outcome requires the PEER_REVIEW_WRITE permission."
              />
            )}
          </div>
        )}
      </Modal>

      <Modal
        title="Submit Peer Review"
        open={submitOpen}
        onCancel={() => setSubmitOpen(false)}
        onOk={submitReview}
        okText="Submit"
        okButtonProps={{ loading: submitting }}
        destroyOnHidden
      >
        <Form form={submitForm} layout="vertical">
          <Form.Item
            name="discrepancy_level"
            label="Discrepancy level"
            rules={[{ required: true, message: "Select a discrepancy level" }]}
          >
            <Select
              placeholder="Select level"
              options={["none", "minor", "major", "discrepancy"].map((l) => ({
                value: l,
                label: l,
              }))}
            />
          </Form.Item>
          <Form.Item name="comment" label="Comment (optional)">
            <Input.TextArea rows={4} placeholder="Feedback for the reading radiologist…" />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="Decline Peer Review"
        open={declineOpen}
        onCancel={() => setDeclineOpen(false)}
        onOk={declineReview}
        okText="Decline"
        okButtonProps={{ danger: true, loading: declining }}
        cancelButtonProps={{ disabled: declining }}
        destroyOnHidden
      >
        <Form form={declineForm} layout="vertical">
          <Form.Item
            name="reason"
            label="Reason (optional)"
            extra="Declining returns the assignment to the pool — the report stays available for another reviewer."
          >
            <Input.TextArea
              rows={3}
              placeholder="e.g. out of scope, already reviewing, workload…"
            />
          </Form.Item>
        </Form>
      </Modal>
    </Content>
  );
}

export default withSidebar(PeerReviewInbox);
