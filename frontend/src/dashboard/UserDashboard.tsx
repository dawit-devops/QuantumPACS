import React, { useEffect, useMemo, useState } from "react";
import { App, Button, Card, Popconfirm, Select, Space, Tag } from "antd";
import { DndContext, PointerSensor, closestCenter, useSensor, useSensors } from "@dnd-kit/core";
import { SortableContext, arrayMove, rectSortingStrategy, useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";

import { useDocumentTitle } from "../hooks";
import withSidebar from "../common/base";
import PageHeader from "../common/PageHeader";
import { useAuth } from "../auth/AuthContext";
import { getPreferences, updatePreferences, type DashboardLayout } from "../api/preferences";
import {
  DEFAULT_LAYOUT_IDS,
  ROLE_DEFAULT_LAYOUTS,
  WIDGET_BY_ID,
  type WidgetDef,
} from "./widgets/registry";
import "./DashboardGrid.css";

function SortableCard({ def, onRemove }: { def: WidgetDef; onRemove: (id: string) => void }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: def.id,
  });
  const Widget = def.component;
  return (
    <Card
      ref={setNodeRef}
      className={`dashboard-widget size-${def.defaultSize}`}
      style={{
        transform: CSS.Transform.toString(transform),
        transition,
        opacity: isDragging ? 0.6 : undefined,
      }}
      title={
        <span {...attributes} {...listeners} style={{ cursor: "grab" }}>
          {def.title}
        </span>
      }
      extra={
        <Button
          size="small"
          type="text"
          onClick={() => onRemove(def.id)}
          aria-label={`Remove ${def.title}`}
        >
          ✕
        </Button>
      }
    >
      <Widget />
    </Card>
  );
}

/**
 * §3 configurable widget dashboard. Role defaults come from the registry;
 * the user's saved arrangement (order + hidden set) lives in their
 * preference document under dashboard_layout and always wins. Widgets are
 * permission-filtered at render time so a shared layout can never leak a
 * surface the viewer has no grant for.
 */
function UserDashboard() {
  useDocumentTitle("QuantumPACS - Dashboard");
  const { message } = App.useApp();
  const { user, hasPermission } = useAuth();
  const role = user?.role ?? "";
  const [order, setOrder] = useState<string[]>([]);
  const [hidden, setHidden] = useState<string[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    let alive = true;
    getPreferences()
      .then((prefs) => {
        if (!alive) return;
        const layout = (prefs?.dashboard_layout ?? {}) as DashboardLayout;
        setOrder(layout.order ?? []);
        setHidden(layout.hidden ?? []);
        setLoaded(true);
      })
      .catch(() => setLoaded(true)); // defaults render even offline
    return () => {
      alive = false;
    };
  }, []);

  const permitted = (def?: WidgetDef) =>
    !!def && (def.permissions ?? []).every((p) => hasPermission(p));

  const widgets = useMemo<WidgetDef[]>(() => {
    const roleDefaults = ROLE_DEFAULT_LAYOUTS[role ?? ""] ?? DEFAULT_LAYOUT_IDS;
    // Saved order wins; never-seen default ids trail; hidden drops out.
    const merged = [...order, ...roleDefaults.filter((id) => !order.includes(id))];
    return merged
      .filter((id) => !hidden.includes(id))
      .map((id) => WIDGET_BY_ID.get(id))
      .filter((def): def is WidgetDef => !!def && permitted(def));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [order, hidden, role, loaded]);

  const restorable = useMemo(
    () =>
      [...WIDGET_BY_ID.values()].filter(
        (w) => hidden.includes(w.id) || (!order.includes(w.id) && !visibleIds().includes(w.id))
      ),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [order, hidden]
  );

  function visibleIds(): string[] {
    const roleDefaults = ROLE_DEFAULT_LAYOUTS[role ?? ""] ?? DEFAULT_LAYOUT_IDS;
    const merged = [...order, ...roleDefaults.filter((id) => !order.includes(id))];
    return merged.filter((id) => !hidden.includes(id));
  }

  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 5 } }));

  const persist = async (nextOrder: string[], nextHidden: string[]) => {
    setSaving(true);
    try {
      await updatePreferences({
        dashboard_layout: { order: nextOrder, hidden: nextHidden },
      });
      message.success("Dashboard layout saved");
    } catch (e: any) {
      message.error(e.message || "Failed to save layout");
    } finally {
      setSaving(false);
    }
  };

  const onDragEnd = ({ active, over }: any) => {
    if (!over || active.id === over.id) return;
    const current = visibleIds();
    const from = current.indexOf(String(active.id));
    const to = current.indexOf(String(over.id));
    if (from < 0 || to < 0) return;
    setOrder(arrayMove(current, from, to));
  };

  const removeWidget = (id: string) => setHidden([...hidden, id]);

  const restoreWidget = (id: string) => {
    setHidden(hidden.filter((h) => h !== id));
    if (!order.includes(id)) setOrder([...visibleIds(), id]);
  };

  const resetToDefaults = () => {
    const roleDefaults = ROLE_DEFAULT_LAYOUTS[role ?? ""] ?? DEFAULT_LAYOUT_IDS;
    setOrder(roleDefaults);
    setHidden([]);
    persist(roleDefaults, []);
  };

  return (
    <div style={{ padding: 24 }} data-testid="user-dashboard">
      <PageHeader
        title="Dashboard"
        description="Your configurable workspace — drag cards to rearrange, remove what you don't need."
      />
      <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
        {restorable.length > 0 && (
          <Select
            aria-label="Add widget"
            placeholder="Add widget"
            style={{ minWidth: 180 }}
            value={null}
            onChange={(id: string) => restoreWidget(id)}
            options={restorable.map((w) => ({ value: w.id, label: w.title }))}
          />
        )}
        <Space>
          <Button onClick={() => persist(visibleIds(), hidden)} loading={saving}>
            Save layout
          </Button>
          <Popconfirm title="Reset to the default layout?" onConfirm={resetToDefaults}>
            <Button danger>Reset to defaults</Button>
          </Popconfirm>
        </Space>
      </div>
      <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={onDragEnd}>
        <SortableContext items={widgets.map((w) => w.id)} strategy={rectSortingStrategy}>
          <div className="dashboard-grid" data-testid="dashboard-grid">
            {widgets.map((def) => (
              <SortableCard key={def.id} def={def} onRemove={removeWidget} />
            ))}
            {widgets.length === 0 && loaded && (
              <Tag data-testid="dashboard-empty">No widgets on this dashboard</Tag>
            )}
          </div>
        </SortableContext>
      </DndContext>
    </div>
  );
}

export default withSidebar(UserDashboard);
