import React, { useState } from "react";
import { Button, Collapse, Input, Space, Tooltip, Tag, Popconfirm } from "antd";
import {
  SaveOutlined,
  DeleteOutlined,
  StarOutlined,
  AppstoreOutlined,
  ColumnWidthOutlined,
  TableOutlined,
} from "@ant-design/icons";
import type { ReadingPreset, WindowLevelConfig } from "./presets";
import { layoutLabel, STANDARD_WL } from "./presets";
import type { ReadingPresetsApi } from "./useReadingPresets";
import "./ReadingPresetsPanel.css";

interface Props {
  modality: string;
  presets: ReadingPresetsApi;
  /** Reads the current viewport W/L so "Save current" captures real values. */
  readCurrentWl: () => WindowLevelConfig;
}

const LAYOUT_KEYS = ["1x1", "1x2", "2x2"];

function formatWl(cfg: WindowLevelConfig): string {
  return `${Math.round(cfg.window_width)} / ${Math.round(cfg.window_center)}`;
}

/**
 * Reading-preset manager (FR-R12-15): save/apply/delete per-modality
 * window/level presets and pick a viewport layout. Reads the current W/L from
 * the active viewport, so a radiologist can tune then save in one step.
 */
export function ReadingPresetsPanel({
  modality,
  presets,
  readCurrentWl,
}: Props) {
  const [name, setName] = useState("");
  const [saving, setSaving] = useState(false);
  const [layoutName, setLayoutName] = useState("");
  const [savingLayout, setSavingLayout] = useState(false);

  const saveCurrent = async () => {
    const trimmed = name.trim();
    if (!trimmed) return;
    setSaving(true);
    try {
      await presets.saveWl(trimmed, readCurrentWl());
      setName("");
    } finally {
      setSaving(false);
    }
  };

  const saveLayout = async (key: string, isDefault: boolean) => {
    setSavingLayout(true);
    try {
      const label = layoutName.trim() || `${key} grid`;
      return await presets.saveLayout(
        label,
        {
          rows: Number(key[0]),
          cols: Number(key[2]),
        },
        isDefault,
      );
    } finally {
      setLayoutName("");
      setSavingLayout(false);
    }
  };

  const applyLayout = async (key: string) => {
    const existing = presets.layoutPresets.find(
      (p) => layoutLabel(p.config as any) === key,
    );
    if (existing) {
      presets.applyLayout(existing);
      return;
    }
    // No saved preset for this grid yet — create one and activate it so the
    // viewport grid changes immediately instead of on a second click.
    const created = await saveLayout(key, true);
    if (created) presets.applyLayout(created);
  };

  const standardButtons = Object.entries(STANDARD_WL);

  return (
    <Collapse
      ghost
      defaultActiveKey={["presets"]}
      className="reading-presets-panel"
      styles={{
        header: {
          padding: '8px 12px',
          color: 'var(--text-secondary, #c7c9d4)',
        },
      }}
      items={[
        {
          key: "presets",
          label: (
            <Space size={6}>
              <AppstoreOutlined />
              Reading Presets
              {modality && <Tag color="blue">{modality}</Tag>}
            </Space>
          ),
          children: (
            <div className="rp-inner">
              <div className="rp-section-title">Window / Level</div>
              {presets.wlPresets.length === 0 && (
                <div className="rp-empty">
                  No saved W/L presets for {modality || "this study"}.
                </div>
              )}
              <div className="rp-preset-list">
                {presets.wlPresets.map((p) => (
                  <div className="rp-preset-row" key={p.id}>
                    <Tooltip
                      title={p.is_default ? "Default" : "Set as default"}
                    >
                      <Button
                        type="text"
                        size="small"
                        className={p.is_default ? "rp-star active" : "rp-star"}
                        aria-label={`Make ${p.name} default`}
                        icon={<StarOutlined />}
                        onClick={() => presets.setDefault(p.id, "window_level")}
                      />
                    </Tooltip>
                    <span
                      className="rp-name"
                      title={`${p.name} — ${formatWl(p.config as WindowLevelConfig)}`}
                    >
                      {p.name}
                    </span>
                    <Tag className="rp-wl">
                      {formatWl(p.config as WindowLevelConfig)}
                    </Tag>
                    <Button
                      type="primary"
                      size="small"
                      onClick={() => presets.applyWl(p)}
                      aria-label={`Apply ${p.name}`}
                    >
                      Apply
                    </Button>
                    <Popconfirm
                      title="Delete this preset?"
                      onConfirm={() => presets.remove(p.id)}
                    >
                      <Button
                        type="text"
                        size="small"
                        danger
                        icon={<DeleteOutlined />}
                        aria-label={`Delete ${p.name}`}
                      />
                    </Popconfirm>
                  </div>
                ))}
              </div>
              <div className="rp-save-row">
                <Input
                  size="small"
                  placeholder={`Preset name (e.g. ${
                    standardButtons[0]?.[0] || "Bone"
                  })`}
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  onPressEnter={saveCurrent}
                  aria-label="New window/level preset name"
                  style={{
                    flex: 1,
                    background: 'var(--bg-input, #12141d)',
                    color: 'var(--text-primary, #e8eaf2)',
                  }}
                />
                <Button
                  size="small"
                  type="primary"
                  ghost
                  icon={<SaveOutlined />}
                  loading={saving}
                  disabled={!name.trim()}
                  onClick={saveCurrent}
                  aria-label="Save current window/level as preset"
                >
                  Save current
                </Button>
              </div>
              <details className="rp-standard">
                <summary>Quick-standard W/L</summary>
                <div className="rp-standard-grid">
                  {standardButtons.map(([label, cfg]) => (
                    <Button
                      key={label}
                      size="small"
                      onClick={() => {
                        const preset: ReadingPreset = {
                          id: `std-${label}`,
                          preset_type: "window_level",
                          modality: modality || "",
                          name: label,
                          config: cfg,
                          is_default: false,
                          created_at: "",
                          updated_at: "",
                        };
                        presets.applyWl(preset);
                      }}
                    >
                      {label}
                    </Button>
                  ))}
                </div>
              </details>

              <div className="rp-section-title rp-layout-title">Layout</div>
              <div className="rp-layout-grid">
                {LAYOUT_KEYS.map((key) => {
                  const active =
                    presets.activeLayout &&
                    layoutLabel(presets.activeLayout.config as any) === key;
                  return (
                    <Tooltip key={key} title={`${key} grid`}>
                      <Button
                        size="small"
                        className={active ? "rp-layout active" : "rp-layout"}
                        onClick={() => applyLayout(key)}
                        aria-label={`Apply ${key} layout`}
                      >
                        {key === "1x1" ? (
                          <TableOutlined />
                        ) : key === "1x2" ? (
                          <ColumnWidthOutlined />
                        ) : (
                          <AppstoreOutlined />
                        )}
                        <span>{key}</span>
                      </Button>
                    </Tooltip>
                  );
                })}
              </div>
              <div className="rp-save-row">
                <Input
                  size="small"
                  placeholder="Layout preset name (optional)"
                  value={layoutName}
                  onChange={(e) => setLayoutName(e.target.value)}
                  aria-label="New layout preset name"
                />
                <Button
                  size="small"
                  icon={<SaveOutlined />}
                  loading={savingLayout}
                  onClick={() => {
                    const cur = presets.activeLayout?.config as any;
                    if (cur) saveLayout(layoutLabel(cur), false);
                  }}
                  disabled={!presets.activeLayout}
                  aria-label="Save current layout as preset"
                >
                  Save layout
                </Button>
              </div>
              {presets.layoutPresets.length > 0 && (
                <div className="rp-preset-list rp-layout-list">
                  {presets.layoutPresets.map((p) => (
                    <div className="rp-preset-row" key={p.id}>
                      <Tooltip
                        title={p.is_default ? "Default" : "Set as default"}
                      >
                        <Button
                          type="text"
                          size="small"
                          className={
                            p.is_default ? "rp-star active" : "rp-star"
                          }
                          aria-label={`Make ${p.name} default`}
                          icon={<StarOutlined />}
                          onClick={() => presets.setDefault(p.id, "layout")}
                        />
                      </Tooltip>
                      <span className="rp-name">{p.name}</span>
                      <Tag className="rp-wl">
                        {layoutLabel(p.config as any)}
                      </Tag>
                      <Button
                        type="primary"
                        size="small"
                        onClick={() => presets.applyLayout(p)}
                        aria-label={`Apply layout ${p.name}`}
                      >
                        Apply
                      </Button>
                      <Popconfirm
                        title="Delete this preset?"
                        onConfirm={() => presets.remove(p.id)}
                      >
                        <Button
                          type="text"
                          size="small"
                          danger
                          icon={<DeleteOutlined />}
                          aria-label={`Delete ${p.name}`}
                        />
                      </Popconfirm>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ),
        },
      ]}
    />
  );
}
