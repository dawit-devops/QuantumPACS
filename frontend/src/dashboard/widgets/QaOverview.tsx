import React, { useEffect, useState } from "react";
import { Skeleton, Statistic } from "antd";
import { request } from "../../api/client";

/** QA operations overview — consumes GET /api/qa/dashboard (QA_READ). */
const QaOverview = () => {
  const [data, setData] = useState<Record<string, number> | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    request<{ data: Record<string, number> }>("qa/dashboard")
      .then((res) => {
        if (alive) setData((res as { data?: Record<string, number> })?.data ?? {});
      })
      .catch((e: Error) => {
        if (alive) setError(e.message);
      });
    return () => {
      alive = false;
    };
  }, []);

  if (error) return <span style={{ color: "var(--color-error)" }}>{error}</span>;
  if (!data) return <Skeleton active paragraph={{ rows: 1 }} />;
  return (
    <div style={{ display: "flex", gap: 24, flexWrap: "wrap" }}>
      <Statistic title="Exams reviewed" value={data.exams_reviewed ?? 0} />
      <Statistic title="Compliance %" value={data.compliance_pct ?? 0} />
      <Statistic title="Open incidents" value={data.open_incidents ?? 0} />
      <Statistic title="Open actions" value={data.open_actions ?? 0} />
    </div>
  );
};

export default QaOverview;
