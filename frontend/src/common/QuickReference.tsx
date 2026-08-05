import React from "react";
import { Modal, Tabs, Table, Typography } from "antd";
import { getToolShortcut } from "../detail/KeyboardShortcuts";

const { Text } = Typography;

interface ShortcutEntry {
  key: string;
  action: string;
  group: string;
}

const SHORTCUTS: ShortcutEntry[] = [
  { key: "1", action: "Pan (default)", group: "Tool Selection" },
  { key: "2", action: "Length measurement", group: "Tool Selection" },
  { key: "3", action: "Rectangle ROI", group: "Tool Selection" },
  { key: "4", action: "Ellipse ROI", group: "Tool Selection" },
  { key: "5", action: "Angle measurement", group: "Tool Selection" },
  { key: "6", action: "Arrow annotation", group: "Tool Selection" },
  { key: "7 / E", action: "Eraser", group: "Tool Selection" },
  { key: "R", action: "Rotate 90° CW", group: "Viewer Controls" },
  { key: "H", action: "Horizontal flip", group: "Viewer Controls" },
  { key: "V", action: "Vertical flip", group: "Viewer Controls" },
  { key: "I", action: "Invert colors", group: "Viewer Controls" },
  { key: "F", action: "Toggle fullscreen", group: "Viewer Controls" },
  { key: "Esc", action: "Exit fullscreen / Close", group: "Viewer Controls" },
  { key: "S", action: "Save annotations", group: "Annotations" },
  { key: "C", action: "Clear all annotations", group: "Annotations" },
  { key: "← / →", action: "Previous / Next file", group: "Navigation" },
  { key: "Scroll", action: "Scroll through slices", group: "Navigation" },
  { key: "Ctrl+Scroll", action: "Zoom", group: "Navigation" },
  { key: "Shift+Scroll", action: "Window / Level", group: "Navigation" },
  { key: "+ / -", action: "Zoom in / Zoom out", group: "Navigation" },
  { key: "?", action: "Show this reference", group: "Help" },
];

const GROUP_ORDER = [
  "Tool Selection",
  "Viewer Controls",
  "Annotations",
  "Navigation",
  "Help",
];

const GESTURES = [
  { gesture: "Tap", action: "Focus thumbnail / select tool" },
  { gesture: "Drag (single finger)", action: "Pan image" },
  { gesture: "Pinch", action: "Zoom in / Zoom out" },
  { gesture: "Swipe (two fingers)", action: "Scroll through slices" },
  { gesture: "Long press", action: "Show context menu" },
  { gesture: "Double tap", action: "Reset view to fit" },
];

const kbdStyle: React.CSSProperties = {
  background: "var(--bg-muted)",
  border: "1px solid var(--border-color)",
  borderRadius: 4,
  padding: "2px 8px",
  fontFamily: "var(--font-mono)",
  fontSize: 12,
  whiteSpace: "nowrap",
};

interface QuickReferenceProps {
  open: boolean;
  onClose: () => void;
}

export function QuickReference({ open, onClose }: QuickReferenceProps) {
  const grouped = GROUP_ORDER.flatMap((group) =>
    SHORTCUTS.filter((s) => s.group === group).map((s, i) => ({
      ...s,
      groupOrder: GROUP_ORDER.indexOf(s.group),
      rowKey: `${group}-${i}`,
    })),
  ).sort((a, b) => a.groupOrder - b.groupOrder);

  const shortcutColumns = [
    {
      title: "Key",
      dataIndex: "key",
      key: "key",
      width: 160,
      render: (k: string) => <kbd style={kbdStyle}>{k}</kbd>,
    },
    {
      title: "Action",
      dataIndex: "action",
      key: "action",
    },
  ];

  const gestureColumns = [
    {
      title: "Gesture",
      dataIndex: "gesture",
      key: "gesture",
      width: 200,
      render: (g: string) => <strong>{g}</strong>,
    },
    {
      title: "Action",
      dataIndex: "action",
      key: "action",
    },
  ];

  return (
    <Modal
      title="Quick Reference"
      open={open}
      onCancel={onClose}
      footer={null}
      width={600}
      centered
      destroyOnHidden
    >
      <Tabs
        items={[
          {
            key: "keyboard",
            label: "Keyboard Shortcuts",
            children: (
              <Table
                dataSource={grouped}
                columns={shortcutColumns}
                pagination={false}
                size="small"
                showHeader={false}
                rowKey="rowKey"
                bordered
              />
            ),
          },
          {
            key: "gestures",
            label: "Touch Gestures",
            children: (
              <div>
                <Text
                  style={{
                    display: "block",
                    marginBottom: 16,
                    color: "var(--text-secondary)",
                  }}
                >
                  Available on touch-enabled devices and the mobile viewer.
                </Text>
                <Table
                  dataSource={GESTURES}
                  columns={gestureColumns}
                  pagination={false}
                  size="small"
                  showHeader={false}
                  rowKey="gesture"
                  bordered
                />
              </div>
            ),
          },
          {
            key: "tools",
            label: "Tool Reference",
            children: (
              <div>
                <Text
                  style={{
                    display: "block",
                    marginBottom: 16,
                    color: "var(--text-secondary)",
                  }}
                >
                  Press a number key to activate a tool. Press{" "}
                  <kbd style={kbdStyle}>1</kbd> to return to Pan.
                </Text>
                <Table
                  dataSource={[
                    {
                      tool: "Pan",
                      key: "1",
                      desc: "Default — drag to move the image",
                    },
                    {
                      tool: "Length",
                      key: "2",
                      desc: "Measure distance between two points",
                    },
                    {
                      tool: "Rectangle ROI",
                      key: "3",
                      desc: "Draw rectangular region of interest",
                    },
                    {
                      tool: "Ellipse ROI",
                      key: "4",
                      desc: "Draw elliptical region of interest",
                    },
                    {
                      tool: "Angle",
                      key: "5",
                      desc: "Measure angle between two lines",
                    },
                    {
                      tool: "Arrow Annotate",
                      key: "6",
                      desc: "Add arrow with text label",
                    },
                    {
                      tool: "Eraser",
                      key: "7 / E",
                      desc: "Delete individual annotations",
                    },
                  ]}
                  columns={[
                    {
                      title: "Tool",
                      dataIndex: "tool",
                      key: "tool",
                      width: 140,
                    },
                    {
                      title: "Key",
                      dataIndex: "key",
                      key: "key",
                      width: 100,
                      render: (k: string) => <kbd style={kbdStyle}>{k}</kbd>,
                    },
                    { title: "Description", dataIndex: "desc", key: "desc" },
                  ]}
                  pagination={false}
                  size="small"
                  rowKey="tool"
                  bordered
                />
              </div>
            ),
          },
        ]}
      />
    </Modal>
  );
}

export { getToolShortcut };
