import React from "react";

/**
 * Dense KPI card used on the admin dashboard. Token-driven (no raw colors):
 * surfaces use --bg-surface / --border-color, values render in --font-mono for
 * the ops-console feel, and the optional `tone` maps to the semantic status
 * colors so it stays theme-correct in light and dark mode.
 */
export default function StatCard({
  label,
  value,
  icon,
  hint,
  tone,
}: {
  label: string;
  value: React.ReactNode;
  icon?: React.ReactNode;
  hint?: string;
  tone?: "ok" | "warn" | "error";
}) {
  const toneColor = {
    ok: "var(--color-success)",
    warn: "var(--color-warning)",
    error: "var(--color-error)",
  }[tone ?? "ok"];
  return (
    <div
      className="stat-card"
      style={{
        background: "var(--bg-surface)",
        border: "1px solid var(--border-color)",
        borderRadius: "var(--radius-lg)",
        boxShadow: "var(--shadow-card)",
        padding: "14px 16px",
        display: "flex",
        flexDirection: "column",
        gap: 6,
        minWidth: 0,
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 8,
        }}
      >
        <span
          style={{
            fontSize: 11,
            fontWeight: 600,
            letterSpacing: "0.08em",
            textTransform: "uppercase",
            color: "var(--text-muted)",
            whiteSpace: "nowrap",
            overflow: "hidden",
            textOverflow: "ellipsis",
          }}
        >
          {label}
        </span>
        {icon && (
          <span style={{ color: tone === undefined ? "var(--text-muted)" : toneColor }}>
            {icon}
          </span>
        )}
      </div>
      <div
        style={{
          fontSize: 24,
          lineHeight: 1.1,
          fontWeight: 700,
          fontFamily: "var(--font-mono)",
          color: tone === undefined ? "var(--text-primary)" : toneColor,
        }}
      >
        {value}
      </div>
      {hint && (
        <div
          style={{
            fontSize: 12,
            color: "var(--text-secondary)",
            whiteSpace: "nowrap",
            overflow: "hidden",
            textOverflow: "ellipsis",
          }}
        >
          {hint}
        </div>
      )}
    </div>
  );
}
