import React, { useEffect, useState } from "react";
import { Skeleton, Statistic } from "antd";
import { request } from "../../api/client";

/**
 * Waiting-room pulse (spec §2.1 kpi-waiting-count / kpi-overdue-wait):
 * queue size + patients waiting past the 30-minute red threshold.
 */
interface QueueEntry {
  wait_minutes?: number | null;
}

const FrontDeskWaiting = () => {
  const [rows, setRows] = useState<QueueEntry[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    request<{ data: QueueEntry[] }>("queue")
      .then((res) => {
        if (alive) setRows((res as { data?: QueueEntry[] })?.data ?? []);
      })
      .catch((e: Error) => {
        if (alive) setError(e.message);
      });
    return () => {
      alive = false;
    };
  }, []);

  if (error) return <span style={{ color: "var(--color-error)" }}>{error}</span>;
  if (!rows) return <Skeleton active paragraph={{ rows: 1 }} />;

  const overdue = rows.filter((r) => (r.wait_minutes ?? 0) >= 30).length;
  return (
    <div style={{ display: "flex", gap: 24, flexWrap: "wrap" }}>
      <Statistic title="Waiting now" value={rows.length} />
      <Statistic
        title="Waiting >30 min"
        value={overdue}
        valueStyle={overdue > 0 ? { color: "var(--color-error)" } : undefined}
      />
    </div>
  );
};

export default FrontDeskWaiting;
