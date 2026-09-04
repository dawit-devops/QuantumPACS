import React, { useEffect, useState } from "react";
import { Skeleton, Statistic } from "antd";
import { request } from "../../api/client";
import { derivedOrderStatus, type OrderRow } from "../../coordinator/Orders";

/**
 * Order lifecycle KPIs (spec §2.7 widgets kpi-open-orders / kpi-stuck-orders)
 * — counts derived client-side over GET /api/orders (ORDER_READ).
 */
const OrdersPipeline = () => {
  const [rows, setRows] = useState<OrderRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    request<{ data: OrderRow[] }>("orders")
      .then((res) => {
        if (alive) setRows((res as { data?: OrderRow[] })?.data ?? []);
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

  const open = rows.filter((r) => {
    const s = derivedOrderStatus(r);
    return s !== "cancelled" && s !== "reported";
  });
  const stuck = open.filter((r) => {
    if (!r.created_at) return false;
    const ageDays = (Date.now() - new Date(r.created_at).getTime()) / 86_400_000;
    return ageDays > 1;
  });

  return (
    <div style={{ display: "flex", gap: 24, flexWrap: "wrap" }}>
      <Statistic title="Open orders" value={open.length} />
      <Statistic title="Stuck >24h" value={stuck.length} />
      <Statistic
        title="Reported today"
        value={rows.filter((r) => derivedOrderStatus(r) === "reported").length}
      />
    </div>
  );
};

export default OrdersPipeline;
