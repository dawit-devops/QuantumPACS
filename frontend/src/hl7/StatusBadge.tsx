import React from "react";
import { Tag } from "antd";

const STATUS_COLORS: Record<string, [string, string]> = {
  ok: ["green", "Parsed"],
  partial: ["orange", "Partial"],
  failed: ["red", "Failed"],
};

export function StatusBadge({ status }: { status: string }) {
  const [color, label] = STATUS_COLORS[status] || ["default", status];
  return <Tag color={color}>{label}</Tag>;
}
