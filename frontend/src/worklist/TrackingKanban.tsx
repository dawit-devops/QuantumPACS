import React, { useMemo, useState } from "react";
import { App, Badge, Card, Modal, Tag } from "antd";
import {
  DndContext,
  PointerSensor,
  useSensor,
  useSensors,
  closestCorners,
  useDroppable,
  type DragEndEvent,
} from "@dnd-kit/core";
import { SortableContext, useSortable, verticalListSortingStrategy } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { useAuth } from "../auth/AuthContext";
import { TRACKING_STATUS_COLORS } from "../common/statusColors";
import type { TrackingEntry } from "../api/tracking";

/**
 * §6.1 role-scoped kanban columns, mapped onto the platform's REAL exam
 * status lifecycle (the spec's read/signed/billing columns belong to other
 * domains — this board stays the single source for exam progression).
 */
export const ROLE_KANBAN_COLUMNS: Record<string, string[]> = {
  receptionist: ["scheduled", "arrived", "in_progress", "completed"],
  care_coordinator: ["scheduled", "arrived", "in_progress", "performed", "completed"],
  technologist: ["scheduled", "arrived", "in_progress", "completed"],
  radiologist: ["performed", "completed"],
  resident: ["performed", "completed"],
  teleradiologist: ["performed", "completed"],
  cashier: ["completed"],
  dept_manager: ["scheduled", "arrived", "in_progress", "performed", "completed"],
};

export const DEFAULT_KANBAN_COLUMNS = [
  "scheduled",
  "arrived",
  "in_progress",
  "performed",
  "completed",
];

const COLUMN_LABELS: Record<string, string> = {
  scheduled: "Scheduled",
  arrived: "Arrived",
  in_progress: "In Progress",
  performed: "Performed",
  completed: "Completed",
};

/** Forward-only transition map — mirrors the table view's action buttons
    so both §6.2 modes enforce identical state machines. */
export const KANBAN_VALID_TRANSITIONS: Record<string, string[]> = {
  scheduled: ["arrived"],
  arrived: ["in_progress"],
  in_progress: ["completed"],
  performed: [],
  completed: [],
};

/** Legal-move gate shared by drag-and-drop (§6.2 power users). Cancellation
    stays on its explicit confirm button in the table view. */
export function canTransition(from: string, to: string): boolean {
  return (KANBAN_VALID_TRANSITIONS[from] ?? []).includes(to);
}

function KanbanCard({
  entry,
  onOpen,
}: {
  entry: TrackingEntry;
  onOpen: (e: TrackingEntry) => void;
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: String(entry.id),
  });
  return (
    <div
      ref={setNodeRef}
      {...attributes}
      {...listeners}
      className="tracking-kanban-card"
      style={{
        transform: CSS.Transform.toString(transform),
        transition,
        opacity: isDragging ? 0.5 : undefined,
      }}
      onClick={() => onOpen(entry)}
      data-testid={`kanban-card-${entry.id}`}
    >
      <div className="tracking-kanban-card-title">
        {entry.patient_name || entry.patient_id}
        {(entry.requested_procedure_priority === "STAT" ||
          entry.requested_procedure_priority === "S") && (
          <Badge count="STAT" style={{ backgroundColor: "#ff4d4f" }} />
        )}
      </div>
      <div className="tracking-kanban-card-meta">
        <Tag style={{ margin: 0 }}>{entry.modality}</Tag>
        <span>{entry.accession_number}</span>
      </div>
      <div className="tracking-kanban-card-meta">
        {entry.station_ae_title || "—"} · {entry.scheduled_time || ""}
      </div>
    </div>
  );
}

function KanbanColumn({
  status,
  entries,
  onOpenDetail,
}: {
  status: string;
  entries: TrackingEntry[];
  onOpenDetail: (e: TrackingEntry) => void;
}) {
  const { setNodeRef, isOver } = useDroppable({ id: status });
  return (
    <div className="tracking-kanban-column" data-testid={`kanban-col-${status}`}>
      <div className="tracking-kanban-column-header">
        <Tag color={TRACKING_STATUS_COLORS[status] || "default"} style={{ margin: 0 }}>
          {COLUMN_LABELS[status] || status}
        </Tag>
        <span className="tracking-kanban-count">{entries.length}</span>
      </div>
      <SortedList status={status} entries={entries} onOpenDetail={onOpenDetail} />
      {/* Column body doubles as the drop target so empty columns accept drops. */}
      <div ref={setNodeRef} className="tracking-kanban-dropzone" data-over={isOver || undefined} />
    </div>
  );
}

function SortedList({
  status,
  entries,
  onOpenDetail,
}: {
  status: string;
  entries: TrackingEntry[];
  onOpenDetail: (e: TrackingEntry) => void;
}) {
  return (
    <SortableContext
      items={entries.map((e) => String(e.id))}
      strategy={verticalListSortingStrategy}
    >
      <div className="tracking-kanban-list">
        {entries.map((entry) => (
          <KanbanCard key={entry.id} entry={entry} onOpen={onOpenDetail} />
        ))}
      </div>
    </SortableContext>
  );
}

interface Props {
  entries: TrackingEntry[];
  onStatusChange: (entry: TrackingEntry, next: string) => void;
  onOpenDetail: (entry: TrackingEntry) => void;
}

/** §6 kanban view: drag cards between columns behind a confirm dialog
    (§6.2 power-user mode); everyone else keeps click-to-transition. */
export default function TrackingKanban({ entries, onStatusChange, onOpenDetail }: Props) {
  const { message } = App.useApp();
  const { user, hasPermission } = useAuth();
  const canWrite = hasPermission("WORKLIST_WRITE");
  const [confirming, setConfirming] = useState<{ entry: TrackingEntry; to: string } | null>(null);

  const columns = useMemo(
    () => ROLE_KANBAN_COLUMNS[user?.role ?? ""] ?? DEFAULT_KANBAN_COLUMNS,
    [user?.role]
  );

  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 5 } }));

  const byColumn = useMemo(() => {
    const map: Record<string, TrackingEntry[]> = {};
    for (const c of columns) map[c] = [];
    for (const e of entries) {
      if (map[e.status]) map[e.status].push(e);
    }
    return map;
  }, [entries, columns]);

  const onDragEnd = ({ active, over }: DragEndEvent) => {
    if (!over || active.id === over.id) return;
    const entry = entries.find((e) => String(e.id) === String(active.id));
    const to = String(over.id);
    if (!entry || !columns.includes(to) || !canWrite) return;
    if (!canTransition(entry.status, to)) {
      message.warning(`Cannot move ${entry.status} → ${to}`);
      return;
    }
    setConfirming({ entry, to });
  };

  return (
    <div className="tracking-kanban" data-testid="tracking-kanban">
      <DndContext sensors={sensors} collisionDetection={closestCorners} onDragEnd={onDragEnd}>
        <div className="tracking-kanban-columns">
          {columns.map((col) => (
            <KanbanColumn
              key={col}
              status={col}
              entries={byColumn[col] ?? []}
              onOpenDetail={onOpenDetail}
            />
          ))}
        </div>
      </DndContext>

      <Modal
        open={!!confirming}
        title="Move exam?"
        okText="Move"
        onCancel={() => setConfirming(null)}
        onOk={() => {
          if (confirming) {
            onStatusChange(confirming.entry, confirming.to);
            setConfirming(null);
          }
        }}
      >
        {confirming && (
          <span>
            Move <strong>{confirming.entry.patient_name || confirming.entry.patient_id}</strong>{" "}
            from {confirming.entry.status} to <strong>{confirming.to}</strong>?
          </span>
        )}
      </Modal>
    </div>
  );
}
