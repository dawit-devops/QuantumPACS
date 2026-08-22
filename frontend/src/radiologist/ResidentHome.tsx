import { useDocumentTitle, useTenantRefetch } from "../hooks";
import React, { useState, useEffect, useCallback } from "react";
import {
  Layout,
  Card,
  Col,
  Row,
  Tag,
  Button,
  Spin,
  Alert,
  Statistic,
  Empty,
  Tooltip,
} from "antd";
import {
  ClockCircleOutlined,
  BookOutlined,
  RightOutlined,
  ReadOutlined,
} from "@ant-design/icons";
import { useNavigate } from "react-router";
import withSidebar from "../common/base";
import { request } from "../helpers";
import { useAuth } from "../auth/AuthContext";
import { patientInitials, mrnLast4 } from "./patientLabel";
import "./ResidentHome.css";

const Content = Layout.Content;

const PRIORITY_LABEL: Record<string, string> = {
  stat: "STAT",
  urgent: "Urgent",
  routine: "Routine",
};

const PRIORITY_COLORS: Record<string, string> = {
  stat: "red",
  urgent: "orange",
  routine: "default",
};

const REPORT_STATUS_COLORS: Record<string, string> = {
  draft: "gold",
  preliminary: "purple",
  submitted: "cyan",
  final: "green",
};

// NFR-R12-04: worklist staleness ≤ 30s — the home mirrors the queue poll so
// the queue counts never lag the Reading Worklist.
const REFRESH_MS = 30000;

interface ReadingItem {
  exam_id: number;
  patient_id: string;
  patient_name: string;
  patient_sex: string | null;
  priority: string;
  requested_procedure_desc: string | null;
  modality: string;
  report_status: string | null;
  assigned_radiologist: string | null;
  review_feedback: string | null;
}

function ResidentHome() {
  useDocumentTitle("QuantumPACS - Resident Home");

  const navigate = useNavigate();
  const { user } = useAuth();
  const [mine, setMine] = useState<ReadingItem[] | null>(null);
  const [claimedToday, setClaimedToday] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const m = await request("reports/reading-list", {
        query: { radiologist: "me" },
      });
      setMine(Array.isArray(m.data) ? m.data : []);
      // R13 review fix P0-2: the "Claimed today" figure comes from the
      // backend (drafts started today), not the queue total — previously
      // it double-counted the whole queue and misled the resident.
      if (typeof m.claimed_today === "number") {
        setClaimedToday(m.claimed_today);
      }
      setError(null);
    } catch (e: any) {
      setError(e.message);
    }
  }, []);

  useEffect(() => {
    load();
    const timer = setInterval(load, REFRESH_MS);
    return () => clearInterval(timer);
  }, [load]);

  useTenantRefetch(load);

  if (mine === null) {
    return (
      <Content className="rh-content">
        <div className="rh-loading">
          <Spin size="large" />
        </div>
      </Content>
    );
  }

  const counts = (items: ReadingItem[]) => {
    const c = { stat: 0, urgent: 0, routine: 0 };
    items.forEach((r) => {
      if (r.priority === "stat") c.stat += 1;
      else if (r.priority === "urgent") c.urgent += 1;
      else c.routine += 1;
    });
    return c;
  };
  const myCounts = counts(mine);
  const totalMine = mine.length;
  // An exam leaves the queue when a final report is signed, so anything
  // still assigned with a report (draft/preliminary/submitted) counts as
  // "worked".
  const inProgress = mine.filter((r) => r.report_status).length;
  // Reports the resident handed to the attending that are not final yet —
  // the supervision loop: submitted → co-signed or returned.
  const awaitingReview = mine.filter(
    (r) => r.report_status === "submitted",
  ).length;
  const recent = mine.slice(0, 5);

  return (
    <Content className="rh-content">
      <div className="rh-header">
        <div>
          <h2>
            <ReadOutlined /> Resident Home
          </h2>
          <p className="rh-subtitle">
            {user?.username || "Resident"} — supervised reading queue and
            learning progress.
          </p>
        </div>
      </div>

      {error && (
        <Alert
          type="warning"
          showIcon
          title="Could not refresh queue data"
          description={error}
          className="rh-error"
        />
      )}

      <Row gutter={[16, 16]} className="rh-cards">
        <Col xs={24} md={12} xl={8}>
          <Card
            className="rh-card"
            title="My Queue"
            extra={<ClockCircleOutlined />}
            styles={{ body: { paddingTop: 16 } }}
          >
            <Row gutter={16}>
              <Col span={8}>
                <Statistic
                  title="STAT"
                  value={myCounts.stat}
                  styles={{ content: { color: "var(--color-error)" } }}
                />
              </Col>
              <Col span={8}>
                <Statistic
                  title="Urgent"
                  value={myCounts.urgent}
                  styles={{ content: { color: "var(--color-warning)" } }}
                />
              </Col>
              <Col span={8}>
                <Statistic title="Routine" value={myCounts.routine} />
              </Col>
            </Row>
            <div className="rh-card-footer">
              <span className="rh-total">Total claimed: {totalMine}</span>
              <Button
                type="primary"
                size="small"
                onClick={() => navigate("/reading?radiologist=me")}
              >
                Open worklist <RightOutlined />
              </Button>
            </div>
          </Card>
        </Col>

        <Col xs={24} md={12} xl={8}>
          <Card
            className="rh-card"
            title="Feedback & Progress"
            extra={<BookOutlined />}
          >
            <Row gutter={16}>
              <Col span={8}>
                <Statistic
                  title="In progress"
                  value={inProgress}
                  styles={{ content: { color: "var(--color-warning)" } }}
                />
              </Col>
              <Col span={8}>
                <Statistic
                  title="Awaiting review"
                  value={awaitingReview}
                  styles={{ content: { color: "var(--color-info)" } }}
                />
              </Col>
              <Col span={8}>
                <Statistic title="Claimed today" value={claimedToday} />
              </Col>
            </Row>
            <Alert
              type="info"
              showIcon
              className="rh-note"
              title="Attending agreement arrives when a submitted report is co-signed FINAL; returned drafts carry revision feedback."
            />
          </Card>
        </Col>

        <Col xs={24} md={12} xl={8}>
          <Card
            className="rh-card"
            title="Teaching Library"
            extra={<BookOutlined />}
          >
            <Empty
              image={Empty.PRESENTED_IMAGE_SIMPLE}
              description={
                <>
                  No curated teaching cases yet.
                  <br />
                  Ask your attending to flag interesting studies during QA
                  review so they can be added to the library.
                </>
              }
            />
          </Card>
        </Col>
      </Row>

      <Card
        className="rh-recent"
        title="My recent exams"
        extra={
          <Button
            type="link"
            size="small"
            onClick={() => navigate("/reading?radiologist=me")}
          >
            View all <RightOutlined />
          </Button>
        }
      >
        {recent.length === 0 ? (
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description="No exams assigned to you yet."
          />
        ) : (
          <div className="rh-exam-list">
            {recent.map((r) => (
              <button
                key={r.exam_id}
                type="button"
                className="rh-exam"
                onClick={() => navigate(`/reading/${r.exam_id}`)}
              >
                <span className="rh-exam-priority">
                  <Tag color={PRIORITY_COLORS[r.priority] || "default"}>
                    {PRIORITY_LABEL[r.priority] || r.priority}
                  </Tag>
                </span>
                <Tooltip title={`${r.patient_name} (MRN ${r.patient_id})`}>
                  <span className="rh-exam-patient">
                    {patientInitials(r.patient_name)}
                    <span className="rh-exam-mrn">
                      ·{mrnLast4(r.patient_id)}
                    </span>
                  </span>
                </Tooltip>
                <span className="rh-exam-desc">
                  {r.requested_procedure_desc || r.modality || "Study"}
                </span>
                <span className="rh-exam-status">
                  {r.report_status ? (
                    <Tag
                      color={REPORT_STATUS_COLORS[r.report_status] || "default"}
                    >
                      {r.report_status}
                    </Tag>
                  ) : (
                    <Tag color="blue">Not started</Tag>
                  )}
                  {r.review_feedback ? (
                    <Tooltip title={r.review_feedback}>
                      <Tag color="volcano">Returned</Tag>
                    </Tooltip>
                  ) : null}
                </span>
              </button>
            ))}
          </div>
        )}
      </Card>
    </Content>
  );
}

export default withSidebar(ResidentHome);
