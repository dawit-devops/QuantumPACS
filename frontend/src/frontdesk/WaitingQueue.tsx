import {
  useDocumentTitle,
  useTenantRefetch,
  useVisibilityGatedInterval,
} from "../hooks";
import React, { useCallback, useEffect, useState } from "react";
import { Layout, Tag, Spin, Alert, Button, DatePicker } from "antd";
import { LockOutlined, ReloadOutlined } from "@ant-design/icons";
import withSidebar from "../common/base";
import PageHeader from "../common/PageHeader";
import { getWaitingQueue, type QueueEntry } from "../api/frontdesk";
import dayjs from "dayjs";
import "./FrontDesk.css";

const Content = Layout.Content;

const STATUS_COLORS: Record<string, string> = {
  registered: "blue",
  checked_in: "gold",
  in_progress: "cyan",
  complete: "green",
};

// US-R08-07: the queue board in a shared waiting area shows ONLY initials +
// MRN last-4 (the backend projects these server-side and never sends full
// names/MRNs). Full PHI stays behind authenticated screens.
function WaitingQueue() {
  useDocumentTitle("QuantumPACS - Waiting Queue");
  const [day, setDay] = useState<string>(() => dayjs().format("YYYY-MM-DD"));
  const [data, setData] = useState<QueueEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetch = useCallback(() => {
    setLoading(true);
    setError(null);
    getWaitingQueue({ date: day })
      .then((rows) => {
        setLoading(false);
        setData(rows);
      })
      .catch((e: any) => {
        setLoading(false);
        setError(e.message);
      });
  }, [day]);

  useEffect(() => {
    fetch();
  }, [fetch]);

  // Keep the board fresh while patients move through statuses — paused while
  // the tab is hidden (R1-04), with an immediate refetch on return.
  useVisibilityGatedInterval(fetch, 30000);

  useTenantRefetch(fetch);

  return (
    <Content style={{ padding: 24 }} role="main">
      {/* (R1-05) PageHeader renders the single h1 (was an h2 under no h1) and
          hosts the date picker + refresh in `extra`. */}
      <PageHeader
        title="Waiting Queue"
        description="Privacy-limited view — auto-refreshes every 30s"
        extra={
          <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
            <DatePicker
              aria-label="Queue date"
              value={dayjs(day)}
              onChange={(d) => d && setDay(d.format("YYYY-MM-DD"))}
              allowClear={false}
            />
            <Button icon={<ReloadOutlined />} onClick={fetch}>
              Refresh
            </Button>
          </div>
        }
      />

      <div className="fd-privacy-note">
        <LockOutlined />
        HIPAA minimum necessary: initials + MRN last 4 only — full names are
        never shown on this board.
      </div>

      {error && (
        <Alert
          type="error"
          message="Failed to load queue"
          description={error}
          showIcon
          style={{ marginBottom: 16 }}
          action={
            <Button size="small" onClick={fetch}>
              Retry
            </Button>
          }
        />
      )}

      {loading && data.length === 0 ? (
        <div className="fd-loading">
          <Spin />
        </div>
      ) : data.length === 0 ? (
        <Alert type="info" showIcon message={`No patients waiting on ${day}`} />
      ) : (
        data.map((row) => (
          <div key={row.visit_id} className="fd-queue-item">
            <Tag
              color={STATUS_COLORS[row.status] || "default"}
              style={{ minWidth: 110, textAlign: "center" }}
            >
              {row.status}
            </Tag>
            <span className="fd-queue-id">
              {row.initials || "—"} · · · · {row.last4}
            </span>
            {row.destination && (
              <Tag className="fd-queue-dest" color="cyan">
                {row.destination}
              </Tag>
            )}
            <span className="fd-queue-time">
              {row.updated_at
                ? new Date(row.updated_at).toLocaleTimeString([], {
                    hour: "2-digit",
                    minute: "2-digit",
                  })
                : "—"}
            </span>
          </div>
        ))
      )}
    </Content>
  );
}

export default withSidebar(WaitingQueue);
