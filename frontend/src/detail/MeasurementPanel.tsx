import React, { useMemo } from "react";
import { Button, Tag, Tooltip, Empty, Typography } from "antd";
import {
  DownloadOutlined,
  AimOutlined,
  LineOutlined,
  BorderOutlined,
  PlusCircleOutlined,
  RightOutlined,
  ArrowRightOutlined,
  NodeIndexOutlined,
  EnvironmentOutlined,
  RadiusUprightOutlined,
} from "@ant-design/icons";
import { useTheme } from "../common/ThemeProvider";

const { Text, Title: TypographyTitle } = Typography;

export interface Measurement {
  annotationUID: string;
  toolName: string;
  type: string;
  label: string;
  value: string;
  seriesNumber?: number;
  handles?: any[];
}

interface MeasurementPanelProps {
  measurements: Measurement[];
  onFocusAnnotation: (annotationUID: string) => void;
  collapsed: boolean;
  onToggle: () => void;
  visible: boolean;
}

const TOOL_ICONS: Record<string, React.ReactNode> = {
  Length: <LineOutlined />,
  Angle: <RightOutlined />,
  ArrowAnnotate: <ArrowRightOutlined />,
  RectangleROI: <BorderOutlined />,
  EllipticalROI: <PlusCircleOutlined />,
  CobbAngle: <NodeIndexOutlined />,
  Probe: <EnvironmentOutlined />,
  CircleROI: <RadiusUprightOutlined />,
};

const TOOL_COLORS: Record<string, string> = {
  Length: "#22D3EE",
  Angle: "#FBBF24",
  ArrowAnnotate: "#A78BFA",
  RectangleROI: "#34D399",
  EllipticalROI: "#F87171",
  CobbAngle: "#F472B6",
  Probe: "#60A5FA",
  CircleROI: "#FB923C",
};

const TOOL_LABELS: Record<string, string> = {
  Length: "Length",
  Angle: "Angle",
  ArrowAnnotate: "Arrow",
  RectangleROI: "Rectangle ROI",
  EllipticalROI: "Ellipse ROI",
  CobbAngle: "Cobb Angle",
  Probe: "Probe",
  CircleROI: "Circle ROI",
};

// ROI annotation classes -> display type. Unknown tools yield "" so a future
// ROI added without a mapping surfaces as skipped, never mislabeled as an
// Ellipse (a nested ternary would silently fall through to EllipticalROI).
const ROI_TYPES: Record<string, string> = {
  RectangleROITool: "RectangleROI",
  EllipticalROITool: "EllipticalROI",
  CircleROITool: "CircleROI",
};

function MeasurementPanel({
  measurements,
  onFocusAnnotation,
  collapsed,
  onToggle,
  visible,
}: MeasurementPanelProps) {
  const { isDark } = useTheme();

  const grouped = useMemo(() => {
    const groups: Record<string, Measurement[]> = {};
    for (const m of measurements) {
      if (!groups[m.toolName]) groups[m.toolName] = [];
      groups[m.toolName].push(m);
    }
    return groups;
  }, [measurements]);

  if (!visible) return null;

  const exportCSV = () => {
    const header = "Type,Label,Value,Series\n";
    const rows = measurements
      .map(
        (m) =>
          `"${m.type}","${m.label}","${m.value}","${m.seriesNumber || ""}"`,
      )
      .join("\n");
    const blob = new Blob([header + rows], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `measurements-${Date.now()}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div
      style={{
        width: collapsed ? 0 : 300,
        minWidth: collapsed ? 0 : 300,
        overflow: "hidden",
        borderLeft: `1px solid var(--border-color)`,
        background: "var(--bg-surface)",
        display: "flex",
        flexDirection: "column",
        transition:
          "width var(--duration-normal) var(--easing-standard), min-width var(--duration-normal) var(--easing-standard)",
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "12px 16px",
          borderBottom: `1px solid var(--border-color)`,
        }}
      >
        <TypographyTitle level={5} style={{ margin: 0, fontSize: 13 }}>
          Measurements
          {measurements.length > 0 && (
            <Tag style={{ marginLeft: 8 }}>{measurements.length}</Tag>
          )}
        </TypographyTitle>
        <div style={{ display: "flex", gap: 4 }}>
          {measurements.length > 0 && (
            <Tooltip title="Export CSV">
              <Button
                size="small"
                icon={<DownloadOutlined />}
                onClick={exportCSV}
              />
            </Tooltip>
          )}
          <Button size="small" onClick={onToggle}>
            ✕
          </Button>
        </div>
      </div>

      <div style={{ flex: 1, overflowY: "auto", padding: 8 }}>
        {measurements.length === 0 ? (
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description={<Text style={{ fontSize: 12 }}>No measurements</Text>}
            style={{ marginTop: 32 }}
          />
        ) : (
          Object.entries(grouped).map(([toolName, items]) => (
            <div key={toolName} style={{ marginBottom: 12 }}>
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 6,
                  marginBottom: 4,
                  padding: "4px 8px",
                }}
              >
                <span
                  style={{
                    color: TOOL_COLORS[toolName] || "var(--text-muted)",
                  }}
                >
                  {TOOL_ICONS[toolName] || <LineOutlined />}
                </span>
                <Text
                  strong
                  style={{
                    fontSize: 11,
                    textTransform: "uppercase",
                    letterSpacing: "0.5px",
                  }}
                >
                  {TOOL_LABELS[toolName] || toolName}
                </Text>
                <Tag
                  style={{ fontSize: 10, lineHeight: "16px", padding: "0 6px" }}
                >
                  {items.length}
                </Tag>
              </div>
              {items.map((m) => (
                <div
                  key={m.annotationUID}
                  onClick={() => onFocusAnnotation(m.annotationUID)}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    padding: "6px 8px 6px 12px",
                    marginBottom: 2,
                    borderRadius: 4,
                    cursor: "pointer",
                    transition: "background var(--duration-fast)",
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.background = isDark
                      ? "rgba(255,255,255,0.06)"
                      : "rgba(0,0,0,0.03)";
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.background = "transparent";
                  }}
                >
                  <div style={{ flex: 1, minWidth: 0 }}>
                    {m.label && (
                      <div
                        style={{
                          fontSize: 11,
                          color: "var(--text-secondary)",
                          overflow: "hidden",
                          textOverflow: "ellipsis",
                          whiteSpace: "nowrap",
                        }}
                      >
                        {m.label}
                      </div>
                    )}
                  </div>
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 6,
                      marginLeft: 8,
                    }}
                  >
                    <Text code style={{ fontSize: 11, whiteSpace: "nowrap" }}>
                      {m.value}
                    </Text>
                    <AimOutlined
                      style={{
                        fontSize: 10,
                        color: "var(--text-muted)",
                        opacity: 0.6,
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>
          ))
        )}
      </div>
    </div>
  );
}

export function parseAnnotations(
  annotations: any[],
  image: string,
): Measurement[] {
  if (!annotations || !Array.isArray(annotations)) return [];

  const results: Measurement[] = [];

  for (const a of annotations) {
    const toolName = a.metadata?.toolName || "";
    const stats = a.data?.cachedStats?.[image];

    let type = "";
    let value = "";
    let label = a.data?.label || "";

    switch (toolName) {
      case "LengthTool": {
        type = "Length";
        const len = stats?.length;
        value = len ? `${len.toFixed(1)} mm` : "";
        break;
      }
      case "AngleTool": {
        type = "Angle";
        const angle = stats?.angle;
        value = angle ? `${angle.toFixed(1)}°` : "";
        break;
      }
      case "CobbAngleTool": {
        type = "CobbAngle";
        const angle = stats?.angle;
        value = angle ? `${angle.toFixed(1)}°` : "";
        break;
      }
      case "ProbeTool": {
        // Single-click pixel readout. `value` is a scalar (most modalities)
        // or an array for multi-value ones (ECG/US); `modalityUnit` carries
        // the display unit (e.g. "HU") when available.
        type = "Probe";
        const raw = stats?.value;
        if (raw === undefined || raw === null) break;
        const formatted = Array.isArray(raw)
          ? (raw.filter((v: unknown) => v != null) as number[])
              .map((v: number) => Number(v).toFixed(1))
              .join(" / ")
          : Number(raw).toFixed(1);
        value = stats?.modalityUnit
          ? `${formatted} ${stats.modalityUnit}`
          : formatted;
        break;
      }
      case "ArrowAnnotateTool": {
        type = "ArrowAnnotate";
        value = a.data?.text || "";
        label = a.data?.text || "";
        break;
      }
      case "RectangleROITool":
      case "EllipticalROITool":
      case "CircleROITool": {
        type = ROI_TYPES[toolName] || "";
        const area = stats?.area;
        const mean = stats?.mean;
        const stdDev = stats?.stdDev;
        if (area) {
          value = `${area.toFixed(1)} mm²`;
          if (mean !== undefined) {
            value += ` μ=${mean.toFixed(1)}`;
          }
        } else {
          value = "";
        }
        break;
      }
      default:
        continue;
    }

    if (!value && type !== "ArrowAnnotate") continue;

    results.push({
      annotationUID: a.annotationUID,
      toolName: type,
      type,
      label,
      value,
      handles: a.data?.handles?.points,
    });
  }

  return results;
}

export default MeasurementPanel;
