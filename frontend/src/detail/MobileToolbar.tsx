import { Button } from "antd";
import {
  DragOutlined,
  ZoomInOutlined,
  ColumnWidthOutlined,
  LineOutlined,
  ScissorOutlined,
  CloseOutlined,
} from "@ant-design/icons";

interface MobileToolbarProps {
  activeTool: string;
  onToolChange: (tool: string) => void;
  visible: boolean;
  onClose: () => void;
}

const tools = [
  { key: "Pan", label: "Pan", icon: <DragOutlined /> },
  { key: "Zoom", label: "Zoom", icon: <ZoomInOutlined /> },
  { key: "WindowLevel", label: "WW/WL", icon: <ColumnWidthOutlined /> },
  { key: "Length", label: "Measure", icon: <LineOutlined /> },
  { key: "StackScroll", label: "Scroll", icon: <ScissorOutlined /> },
];

export function MobileToolbar({
  activeTool,
  onToolChange,
  visible,
  onClose,
}: MobileToolbarProps) {
  if (!visible) return null;

  return (
    <div
      style={{
        position: "fixed",
        bottom: 0,
        left: 0,
        right: 0,
        zIndex: 1000,
        display: "flex",
        alignItems: "center",
        gap: 4,
        padding: "8px env(safe-area-inset-bottom, 8px)",
        background: "var(--bg-surface, #1e293b)",
        borderTop: "1px solid var(--border-color, #334155)",
        overflowX: "auto",
        WebkitOverflowScrolling: "touch",
      }}
      role="toolbar"
      aria-label="Mobile viewer tools"
    >
      {tools.map((tool) => (
        <Button
          key={tool.key}
          type={activeTool === tool.key ? "primary" : "default"}
          size="small"
          icon={tool.icon}
          onClick={() => onToolChange(tool.key)}
          style={{
            flex: "0 0 auto",
            minWidth: 48,
            minHeight: 44,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            flexDirection: "column",
            gap: 2,
            fontSize: 10,
            lineHeight: 1.2,
          }}
          aria-label={tool.label}
          aria-pressed={activeTool === tool.key}
        >
          {tool.label}
        </Button>
      ))}
      <Button
        type="text"
        size="small"
        icon={<CloseOutlined />}
        onClick={onClose}
        style={{
          flex: "0 0 auto",
          minWidth: 44,
          minHeight: 44,
          marginLeft: "auto",
        }}
        aria-label="Close toolbar"
      />
    </div>
  );
}
