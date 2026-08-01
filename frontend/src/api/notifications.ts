import { request } from "./client";

export interface Notification {
  id: number;
  type: string;
  title?: string;
  message?: string;
  read: boolean;
  created_at?: string;
  data?: Record<string, unknown>;
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
