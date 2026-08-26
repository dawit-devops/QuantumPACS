import React, { useEffect, useState } from "react";
import { Skeleton, Statistic } from "antd";
import { request } from "../../api/client";

/** Platform totals from /v2/dashboard/metrics — METRICS_READ-gated. */
function formatBytes(bytes: number): string {
  if (!bytes) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  return `${(bytes / 1024 ** i).toFixed(i === 0 ? 0 : 1)} ${units[i]}`;
}

const PlatformTotals = () => {
  const [totals, setTotals] = useState<Record<string, number> | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    request<{ totals: Record<string, number> }>("v2/dashboard/metrics")
      .then((res) => {
        const body = res as unknown as { totals?: Record<string, number> };
        if (alive) setTotals(body?.totals ?? {});
      })
      .catch((e: Error) => {
        if (alive) setError(e.message);
      });
    return () => {
      alive = false;
    };
  }, []);

  if (error) return <span style={{ color: "var(--color-error)" }}>{error}</span>;
  if (!totals) return <Skeleton active paragraph={{ rows: 1 }} />;
  return (
    <div style={{ display: "flex", gap: 24, flexWrap: "wrap" }}>
      <Statistic title="Patients" value={totals.patients ?? 0} />
      <Statistic title="Studies" value={totals.studies ?? 0} />
      <Statistic title="Files" value={totals.files ?? 0} />
      <Statistic title="Users" value={totals.users ?? 0} />
      <Statistic title="Storage" value={formatBytes(Number(totals.storage_bytes ?? 0))} />
    </div>
  );
};

export default PlatformTotals;
