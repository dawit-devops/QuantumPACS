import { useDocumentTitle } from "../hooks";
import React, { useEffect, useState } from "react";
import {
  App,
  Layout,
  Card,
  Switch,
  Button,
  Space,
  Typography,
  Alert,
  Popconfirm,
} from "antd";
import withSidebar from "../common/base";
import PageHeader from "../common/PageHeader";
import { PageState } from "../common/PageState";
import {
  getNotificationPreferences,
  updateNotificationPreferences,
} from "../api/notifications";
import { useAuth } from "../auth/AuthContext";

const { Content } = Layout;
const { Text } = Typography;

// Event-type grouping for the preferences page — mirrors the backend role
// default (db/notification_prefs.py): clinical events are noise for the
// platform admin, operational alerts stay ON.
const GROUPS: { key: string; title: string; hint: string; events: string[] }[] =
  [
    {
      key: "operational",
      title: "Operational alerts",
      hint: "Platform conditions only the admin can act on.",
      events: [
        "storage.quota_breach",
        "quota.warning",
        "system.alert",
        "interface.failure",
        "exam.assigned",
      ],
    },
    {
      key: "clinical",
      title: "Clinical activity",
      hint: "Per-study/file lifecycle events — muted by default for the platform admin.",
      events: [
        "study.arrived",
        "study.verified",
        "worklist.performed",
        "share.accessed",
        "annotation.shared",
        "report.ready",
        "report.returned",
        "report.signed",
      ],
    },
  ];

const EVENT_LABELS: Record<string, string> = {
  "storage.quota_breach": "Storage quota breach",
  "quota.warning": "Quota approaching limit",
  "system.alert": "System alert",
  "interface.failure": "Interface failure",
  "exam.assigned": "Exam assigned",
  "study.arrived": "Study arrived (upload receipt)",
  "study.verified": "Study verified",
  "worklist.performed": "Worklist performed",
  "share.accessed": "Share link accessed",
  "annotation.shared": "Annotations shared",
  "report.ready": "Report ready",
  "report.returned": "Report returned for revision",
  "report.signed": "Report signed",
};

function NotificationPreferences() {
  const { message } = App.useApp();
  useDocumentTitle("QuantumPACS - Notification Preferences");
  const { user } = useAuth();
  const [prefs, setPrefs] = useState<Record<string, boolean> | null>(null);
  const [roleDefaults, setRoleDefaults] = useState<Record<string, boolean>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState<Record<string, boolean>>({});

  const load = () => {
    setLoading(true);
    setError(null);
    getNotificationPreferences()
      .then((res) => {
        setPrefs(res.preferences);
        setRoleDefaults(res.role_defaults);
      })
      .catch((e: any) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, []);

  const toggle = async (eventType: string, enabled: boolean) => {
    if (!prefs) return;
    // Optimistic flip with per-toggle loading; roll back on failure.
    const next = { ...prefs, [eventType]: enabled };
    setPrefs(next);
    setSaving((s) => ({ ...s, [eventType]: true }));
    try {
      await updateNotificationPreferences({ [eventType]: enabled });
      message.success("Preference saved");
    } catch (e: any) {
      setPrefs(prefs); // rollback
      message.error(e.message);
    } finally {
      setSaving((s) => ({ ...s, [eventType]: false }));
    }
  };

  const resetToDefaults = async () => {
    if (!prefs) return;
    const next: Record<string, boolean> = {};
    for (const g of GROUPS) {
      for (const ev of g.events) next[ev] = roleDefaults[ev] ?? true;
    }
    setPrefs(next);
    try {
      await updateNotificationPreferences(next);
      message.success("Reset to role defaults");
    } catch (e: any) {
      message.error(e.message);
    }
  };

  const mutedCount = prefs ? Object.values(prefs).filter((v) => !v).length : 0;

  return (
    <Content style={{ padding: 24 }}>
      <PageHeader
        title="Notification Preferences"
        description="Choose which event types reach your notification bell. Admin accounts (platform and tenant admins) mute clinical noise by default while keeping operational alerts — clinical roles receive everything until they opt out."
        extra={
          <Popconfirm
            title="Reset to role defaults?"
            description="Overrides your current choices with the defaults for your role."
            onConfirm={resetToDefaults}
            disabled={!prefs}
          >
            <Button disabled={!prefs}>Reset to role defaults</Button>
          </Popconfirm>
        }
      />

      <PageState
        loading={loading}
        error={error}
        onRetry={load}
        empty={!loading && !error && !prefs}
        emptyMessage="No preferences available"
      >
        {prefs && (
          <Space direction="vertical" style={{ width: "100%" }} size={16}>
            {mutedCount > 0 && (
              <Alert
                type="info"
                showIcon
                title={`${mutedCount} event type(s) muted for your account`}
              />
            )}
            {GROUPS.map((group) => (
              <Card key={group.key} size="small" title={group.title}>
                <Text
                  type="secondary"
                  style={{ fontSize: 12, display: "block", marginBottom: 12 }}
                >
                  {group.hint}
                </Text>
                <Space direction="vertical" style={{ width: "100%" }} size={8}>
                  {group.events.map((ev) => (
                    <div
                      key={ev}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        gap: 16,
                      }}
                    >
                      <Text>{EVENT_LABELS[ev] ?? ev}</Text>
                      <Switch
                        checked={prefs[ev] ?? true}
                        loading={saving[ev]}
                        onChange={(checked) => toggle(ev, checked)}
                        aria-label={`${EVENT_LABELS[ev] ?? ev} notifications`}
                      />
                    </div>
                  ))}
                </Space>
              </Card>
            ))}
            {user?.role && (
              <Text type="secondary" style={{ fontSize: 12 }}>
                Role: {user.role} — defaults applied when no explicit choice is
                made.
              </Text>
            )}
          </Space>
        )}
      </PageState>
    </Content>
  );
}

export default withSidebar(NotificationPreferences);
