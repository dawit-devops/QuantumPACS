import React, { useState, useEffect, useRef } from "react";
import {
  App,
  Badge,
  Drawer,
  List,
  Button,
  Space,
  Typography,
  Empty,
  Spin,
  Tag,
} from "antd";
import {
  BellOutlined,
  CheckOutlined,
  DeleteOutlined,
  CheckCircleOutlined,
} from "@ant-design/icons";
import { useNavigate } from "react-router";
import {
  getUnreadCount,
  listNotifications,
  markRead as markReadApi,
  markAllRead as markAllReadApi,
  deleteNotification,
  clearNotifications,
} from "../api/notifications";
import * as ws from "../ws";

const { Text } = Typography;

const EVENT_LABELS: Record<string, string> = {
  "study.arrived": "blue",
  "study.verified": "green",
  "worklist.performed": "purple",
  "share.accessed": "orange",
  "annotation.shared": "cyan",
  "report.ready": "green",
  "quota.warning": "orange",
  "system.alert": "red",
};

function NotificationBell() {
  const { message } = App.useApp();
  const [unread, setUnread] = useState(0);
  const [open, setOpen] = useState(false);
  const [notifs, setNotifs] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const navigate = useNavigate();
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchUnread = async () => {
    try {
      setUnread(await getUnreadCount());
    } catch {}
  };

  const fetchList = async () => {
    setLoading(true);
    try {
      const res = await listNotifications();
      setNotifs(res.data);
      setTotal(res.total);
    } catch {
      message.error("Failed to load notifications");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUnread();
    // (P-M1) The backend pushes a {'type': 'notifications'} event over the WS
    // channel when a notification is created, so the badge refreshes
    // immediately. The poll stays as a fallback for when the socket is down
    // (e.g. behind a proxy that drops long-lived connections).
    const onWsEvent = (data: any) => {
      if (data?.type === "notifications") fetchUnread();
    };
    ws.addEventListener(onWsEvent);
    intervalRef.current = setInterval(fetchUnread, 30000);
    return () => {
      ws.removeEventListener(onWsEvent);
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, []);

  const handleOpen = () => {
    setOpen(true);
    fetchList();
  };

  const markRead = async (id: string) => {
    try {
      await markReadApi(id);
      setNotifs((prev) =>
        prev.map((n) => (n.id === id ? { ...n, read: true } : n)),
      );
      setUnread((prev) => Math.max(0, prev - 1));
    } catch (e) {
      message.error(`Failed to mark read: ${(e as Error).message || ""}`);
    }
  };

  const markAllRead = async () => {
    try {
      await markAllReadApi();
      setNotifs((prev) => prev.map((n) => ({ ...n, read: true })));
      setUnread(0);
      message.success("All marked as read");
    } catch (e) {
      message.error(`Failed to mark all read: ${(e as Error).message || ""}`);
    }
  };

  const dismiss = async (id: string) => {
    try {
      await deleteNotification(id);
      setNotifs((prev) => prev.filter((n) => n.id !== id));
      setTotal((prev) => prev - 1);
    } catch (e) {
      message.error(`Failed to dismiss: ${(e as Error).message || ""}`);
    }
  };

  const dismissAll = async () => {
    try {
      await clearNotifications();
      setNotifs([]);
      setTotal(0);
      setUnread(0);
      message.success("All notifications dismissed");
    } catch (e) {
      message.error(`Failed to dismiss all: ${(e as Error).message || ""}`);
    }
  };

  const handleClick = (n: any) => {
    if (!n.read) markRead(n.id);
    // (M4) The link arrives from the server — refuse anything that is not a
    // same-origin path so a compromised/buggy payload cannot navigate the SPA
    // to an external origin or a javascript: URL.
    if (n.link && typeof n.link === "string" && /^\/(?!\/)/.test(n.link)) {
      setOpen(false);
      navigate(n.link);
    }
  };

  return (
    <>
      <Badge count={unread} size="small" offset={[2, -2]}>
        <BellOutlined
          onClick={handleOpen}
          style={{ fontSize: 16, cursor: "pointer", color: "#fff" }}
        />
      </Badge>
      <Drawer
        title={
          <Space style={{ width: "100%", justifyContent: "space-between" }}>
            <span>Notifications ({total})</span>
            <Space size={4}>
              <Button
                size="small"
                icon={<CheckCircleOutlined />}
                onClick={markAllRead}
                disabled={unread === 0}
              >
                Read all
              </Button>
              <Button
                size="small"
                icon={<DeleteOutlined />}
                onClick={dismissAll}
                disabled={total === 0}
              >
                Dismiss all
              </Button>
            </Space>
          </Space>
        }
        open={open}
        onClose={() => setOpen(false)}
        width={400}
      >
        <Spin spinning={loading}>
          {notifs.length === 0 ? (
            <Empty description="No notifications" />
          ) : (
            <List
              dataSource={notifs}
              renderItem={(n: any) => (
                <List.Item
                  style={{
                    cursor: n.link ? "pointer" : "default",
                    background: n.read ? "transparent" : "#f0f5ff",
                    padding: "12px 16px",
                    borderLeft: n.read ? "none" : "3px solid #1677ff",
                  }}
                  onClick={() => handleClick(n)}
                  actions={[
                    !n.read && (
                      <Button
                        key="read"
                        type="text"
                        size="small"
                        icon={<CheckOutlined />}
                        onClick={(e) => {
                          e.stopPropagation();
                          markRead(n.id);
                        }}
                      />
                    ),
                    <Button
                      key="dismiss"
                      type="text"
                      size="small"
                      icon={<DeleteOutlined />}
                      onClick={(e) => {
                        e.stopPropagation();
                        dismiss(n.id);
                      }}
                    />,
                  ].filter(Boolean)}
                >
                  <List.Item.Meta
                    title={
                      <Space size={6}>
                        <Tag
                          color={EVENT_LABELS[n.event_type] || "default"}
                          style={{ fontSize: 10, lineHeight: "16px" }}
                        >
                          {n.event_type}
                        </Tag>
                        <Text strong={!n.read} style={{ fontSize: 13 }}>
                          {n.title}
                        </Text>
                      </Space>
                    }
                    description={
                      <div>
                        {n.body && (
                          <div
                            style={{
                              fontSize: 12,
                              color: "#888",
                              marginBottom: 2,
                            }}
                          >
                            {n.body}
                          </div>
                        )}
                        <div style={{ fontSize: 11, color: "#aaa" }}>
                          {n.created_at
                            ? new Date(n.created_at).toLocaleString()
                            : ""}
                        </div>
                      </div>
                    }
                  />
                </List.Item>
              )}
            />
          )}
        </Spin>
      </Drawer>
    </>
  );
}

export default NotificationBell;
