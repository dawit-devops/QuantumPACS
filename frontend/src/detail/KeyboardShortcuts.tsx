import React from 'react';
import { Modal, Table } from 'antd';

interface ShortcutEntry {
  key: string;
  action: string;
  group: string;
}

const SHORTCUTS: ShortcutEntry[] = [
  { key: '1', action: 'Pan (default)', group: 'Tool Selection' },
  { key: '2', action: 'Length measurement', group: 'Tool Selection' },
  { key: '3', action: 'Rectangle ROI', group: 'Tool Selection' },
  { key: '4', action: 'Ellipse ROI', group: 'Tool Selection' },
  { key: '5', action: 'Angle measurement', group: 'Tool Selection' },
  { key: '6', action: 'Arrow annotation', group: 'Tool Selection' },
  { key: '7 / E', action: 'Eraser', group: 'Tool Selection' },
  { key: 'R', action: 'Rotate 90° CW', group: 'Viewer Controls' },
  { key: 'H', action: 'Horizontal flip', group: 'Viewer Controls' },
  { key: 'V', action: 'Vertical flip', group: 'Viewer Controls' },
  { key: 'I', action: 'Invert colors', group: 'Viewer Controls' },
  { key: 'F', action: 'Toggle fullscreen', group: 'Viewer Controls' },
  { key: 'Esc', action: 'Exit fullscreen', group: 'Viewer Controls' },
  { key: 'S', action: 'Save annotations', group: 'Annotations' },
  { key: 'C', action: 'Clear all annotations', group: 'Annotations' },
  { key: '← / →', action: 'Previous / Next file', group: 'Navigation' },
  { key: 'Ctrl+Scroll', action: 'Zoom', group: 'Navigation' },
  { key: 'Shift+Scroll', action: 'Window / Level', group: 'Navigation' },
  { key: '+ / -', action: 'Zoom in / Zoom out', group: 'Navigation' },
  { key: '?', action: 'Show this help', group: 'Help' },
];

const GROUP_ORDER = ['Tool Selection', 'Viewer Controls', 'Annotations', 'Navigation', 'Help'];

interface KeyboardShortcutsProps {
  open: boolean;
  onClose: () => void;
}

export function KeyboardShortcuts({ open, onClose }: KeyboardShortcutsProps) {
  const grouped = GROUP_ORDER.flatMap(group =>
    SHORTCUTS.filter(s => s.group === group).map((s, i) => ({
      ...s,
      groupOrder: GROUP_ORDER.indexOf(s.group),
      rowKey: `${group}-${i}`,
    }))
  ).sort((a, b) => a.groupOrder - b.groupOrder);

  const columns = [
    {
      title: 'Key',
      dataIndex: 'key',
      key: 'key',
      width: 160,
      render: (k: string) => <kbd style={{
        background: 'var(--bg-muted)',
        border: '1px solid var(--border-color)',
        borderRadius: 4,
        padding: '2px 8px',
        fontFamily: 'var(--font-mono)',
        fontSize: 12,
        whiteSpace: 'nowrap',
      }}>{k}</kbd>,
    },
    {
      title: 'Action',
      dataIndex: 'action',
      key: 'action',
    },
  ];

  return (
    <Modal
      title="Keyboard Shortcuts"
      open={open}
      onCancel={onClose}
      footer={null}
      width={520}
      centered
    >
      <Table
        dataSource={grouped}
        columns={columns}
        pagination={false}
        size="small"
        showHeader={false}
        rowKey="rowKey"
        bordered
      />
      <p style={{ marginTop: 16, fontSize: 12, color: 'var(--text-muted)', textAlign: 'center' }}>
        Press <kbd style={{
          background: 'var(--bg-muted)',
          border: '1px solid var(--border-color)',
          borderRadius: 4,
          padding: '1px 6px',
          fontFamily: 'var(--font-mono)',
          fontSize: 11,
        }}>?</kbd> anytime to toggle this reference
      </p>
    </Modal>
  );
}

export function getToolShortcut(toolName: string): string {
  const map: Record<string, string> = {
    Pan: '1',
    Length: '2',
    RectangleROI: '3',
    EllipticalROI: '4',
    Angle: '5',
    ArrowAnnotate: '6',
    Eraser: '7 / E',
  };
  return map[toolName] || '';
}
