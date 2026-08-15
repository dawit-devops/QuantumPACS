import { request } from "./client";

// Matches backend/db/notifications.py: notifications are stored and
// returned with event_type/title/body/link — not a generic type/message pair.
export interface Notification {
  id: string;
  event_type: string;
  title: string;
  body?: string;
  link?: string;
  read: boolean;
  created_at?: string;
}

export const getUnreadCount = (): Promise<number> =>
  request<{ count: number }>("notifications/unread-count").then(
    (res) => res.count ?? 0,
  );

export interface NotificationList {
  data: Notification[];
  total: number;
}

export const listNotifications = (): Promise<NotificationList> =>
  request<{ data: Notification[]; total: number }>("notifications").then(
    (res) => ({ data: res.data ?? [], total: res.total ?? 0 }),
  );

export const markRead = (id: number | string): Promise<void> =>
  request(`notifications/${id}`, { method: "POST" });

export const markAllRead = (): Promise<void> =>
  request("notifications/read-all", { method: "POST" });

export const deleteNotification = (id: number | string): Promise<void> =>
  request(`notifications/${id}`, { method: "DELETE" });

export const clearNotifications = (): Promise<void> =>
  request("notifications", { method: "DELETE" });

// P1-1 (super_admin review): per-user event-type subscriptions. The backend
// returns {preferences, explicit, role_defaults} at the top level (ok() does
// not add a data envelope here).
export interface NotificationPrefs {
  preferences: Record<string, boolean>;
  explicit: Record<string, boolean>;
  role_defaults: Record<string, boolean>;
}

export const getNotificationPreferences = (): Promise<NotificationPrefs> =>
  request<NotificationPrefs>("notifications/preferences");

export const updateNotificationPreferences = (
  preferences: Record<string, boolean>,
): Promise<{ updated: string[] }> =>
  request<{ updated: string[] }>("notifications/preferences", {
    method: "PUT",
    data: { preferences },
  });
