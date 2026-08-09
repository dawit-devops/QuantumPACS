import React from "react";

/**
 * Shared page header for the admin surfaces: title + description on the left,
 * optional action buttons on the right. Keeps the admin pages consistent and
 * removes per-page h1 styling drift (dense ops style, token-driven).
 */
export default function PageHeader({
  title,
  description,
  extra,
}: {
  title: string;
  description?: React.ReactNode;
  extra?: React.ReactNode;
}) {
  return (
    <div
      className="page-header"
      style={{
        display: "flex",
        alignItems: "flex-end",
        justifyContent: "space-between",
        gap: 16,
        flexWrap: "wrap",
        marginBottom: 16,
      }}
    >
      <div style={{ minWidth: 0 }}>
        <h1
          style={{
            margin: 0,
            fontSize: "var(--font-size-2xl)",
            fontWeight: 700,
            color: "var(--text-primary)",
            lineHeight: 1.25,
          }}
        >
          {title}
        </h1>
        {description && (
          <div
            style={{
              marginTop: 4,
              color: "var(--text-secondary)",
              fontSize: "var(--font-size-sm)",
              maxWidth: 720,
            }}
          >
            {description}
          </div>
        )}
      </div>
      {extra && (
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          {extra}
        </div>
      )}
    </div>
  );
}
