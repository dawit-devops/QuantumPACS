import React from "react";

export const EXAM_STATUS_COLORS: Record<string, string> = {
  ready: "blue",
  in_progress: "gold",
  completed: "green",
  cancelled: "red",
};

export const EXAM_PRIORITY_COLORS: Record<string, string> = {
  stat: "red",
  urgent: "orange",
  routine: "default",
};

export const PRIORITY_LABEL: Record<string, string> = {
  stat: "STAT",
  urgent: "Urgent",
  routine: "Routine",
};

export const TRACKING_STATUS_COLORS: Record<string, string> = {
  scheduled: "blue",
  arrived: "cyan",
  in_progress: "orange",
  completed: "green",
  cancelled: "red",
};

export const TRACKING_PRIORITY_COLORS: Record<string, string> = {
  STAT: "red",
  S: "red",
  A: "orange",
  ASAP: "orange",
  U: "orange",
  URGENT: "orange",
  T: "orange",
  R: "default",
  ROUTINE: "default",
};

export const SCHEDULE_CALENDAR_STATUS_COLORS: Record<string, string> = {
  SCHEDULED: "blue",
  ARRIVED: "orange",
  IN_PROGRESS: "cyan",
  COMPLETED: "green",
  CANCELLED: "red",
};

export const SCHEDULE_BOARD_STATUS_COLORS: Record<string, string> = {
  scheduled: "blue",
  performed: "green",
  cancelled: "red",
};

export const WORKLIST_CALENDAR_STATUS_COLORS = SCHEDULE_BOARD_STATUS_COLORS;

export const SCHEDULE_BOARD_BOARD_STATUS_COLORS: Record<string, string> = {
  scheduled: "var(--color-primary)",
  performed: "var(--color-success)",
  cancelled: "var(--color-error)",
};

export const REPORT_STATUS_COLORS: Record<string, string> = {
  none: "blue",
  draft: "gold",
  preliminary: "purple",
  submitted: "cyan",
  final: "green",
};

export const REPORT_STATUS_LABEL: Record<string, string> = {
  draft: "Draft",
  preliminary: "Preliminary",
  submitted: "In review",
  final: "Final",
};