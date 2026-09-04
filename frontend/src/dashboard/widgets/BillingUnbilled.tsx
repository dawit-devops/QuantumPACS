import React, { useEffect, useState } from "react";
import { Skeleton, Statistic } from "antd";
import { request } from "../../api/client";
import type { UnbilledAgingReport } from "../../api/billing-ris";

/** Unbilled charges at a glance (spec §2.6 kpi-unbilled) — BILLING_READ. */
const BillingUnbilled = () => {
  const [data, setData] = useState<UnbilledAgingReport | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    request<UnbilledAgingReport>("ris/billing/unbilled")
      .then((res) => {
        if (alive) setData(res as UnbilledAgingReport);
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

  const oldest = Math.max(0, ...(data.groups ?? []).map((g) => g.oldest_charge_days ?? 0));
  return (
    <div style={{ display: "flex", gap: 24, flexWrap: "wrap" }}>
      <Statistic title="Total unbilled ($)" value={data.total_unbilled ?? 0} precision={2} />
      <Statistic title="Aged >5 days" value={data.buckets?.over5 ?? 0} />
      <Statistic title="Oldest charge (days)" value={oldest} />
    </div>
  );
};

export default BillingUnbilled;
