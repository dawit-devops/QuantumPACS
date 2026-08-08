import React from "react";
import { Tag } from "antd";
import type { WorklistEntry } from "../api/worklist";
import "./Worklist.css";

const STATUS_COLORS: Record<string, string> = {
  scheduled: "blue",
  performed: "green",
  cancelled: "red",
};

// Groups entries by scheduled date for the calendar view. Extracted from the
// Worklist monolith (Q-6) so the table/calendar toggle stays a pure presentational
// concern.
export const groupByDate = (
  entries: WorklistEntry[],
): Array<[string, WorklistEntry[]]> => {
  const grouped: Record<string, WorklistEntry[]> = {};
  for (const entry of entries) {
    const date = entry.scheduled_date || "No date";
    if (!grouped[date]) grouped[date] = [];
    grouped[date].push(entry);
  }
  return Object.entries(grouped).sort(([a], [b]) => a.localeCompare(b));
};

interface CalendarViewProps {
  entries: WorklistEntry[];
  // Optional: read-only viewers (no WORKLIST_WRITE) get a non-interactive
  // calendar; the parent omits the handler instead of opening an edit modal.
  onEdit?: (entry: WorklistEntry) => void;
}

const CalendarView = ({ entries, onEdit }: CalendarViewProps) => (
  <div className="calendar-view">
    {groupByDate(entries).map(([date, dayEntries]) => (
      <div key={date} className="calendar-day">
        <div className="calendar-day-header">
          {date === "No date" ? "Unscheduled" : date}
          <Tag style={{ marginLeft: 8 }}>{dayEntries.length}</Tag>
        </div>
        {dayEntries.map((entry) => (
          <div
            key={entry.id}
            className={`calendar-entry ${entry.status}`}
            onClick={() => onEdit?.(entry)}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => {
              if (e.key === "Enter") onEdit?.(entry);
            }}
          >
            <Tag
              color={STATUS_COLORS[entry.status ?? "scheduled"]}
              style={{ margin: 0, flexShrink: 0 }}
            >
              {entry.status}
            </Tag>
            <span style={{ fontWeight: 500, flex: 1 }}>
              {entry.patient_name || entry.patient_id}
            </span>
            <span
              style={{
                color: "var(--text-secondary, #64748b)",
                fontSize: 13,
              }}
            >
              {entry.modality}
            </span>
            {entry.scheduled_time && (
              <span
                style={{
                  color: "var(--text-secondary, #64748b)",
                  fontSize: 13,
                }}
              >
                {entry.scheduled_time}
              </span>
            )}
            <span
              style={{
                color: "var(--text-secondary, #64748b)",
                fontSize: 13,
              }}
            >
              {entry.accession_number}
            </span>
          </div>
        ))}
      </div>
    ))}
  </div>
);

export default CalendarView;
