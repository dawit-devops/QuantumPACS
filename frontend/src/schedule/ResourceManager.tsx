import { ApartmentOutlined, PlusOutlined } from "@ant-design/icons";
import {
  App,
  Button,
  Card,
  Drawer,
  Empty,
  Form,
  Input,
  Select,
  Space,
  Spin,
  Tag,
  Alert,
  Descriptions,
} from "antd";
import dayjs from "dayjs";
import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";

import {
  listRisResources,
  createRisResource,
  listRisSchedules,
  createRisSchedule,
  dayOfWeekLabel,
  type RisResource,
  type RisSchedule,
} from "../api/scheduling";
import { useAuth } from "../auth/AuthContext";
import withSidebar from "../common/base";
import { toErrorMessage } from "../common/errors";
import { MODALITIES } from "../common/modalities";
import { useDocumentTitle, useTenantRefetch } from "../hooks";

import "./schedule.css";

interface ResourceFormValues {
  name: string;
  resource_type: string;
  modality?: string;
  location?: string;
}

const RESOURCE_TYPES = [
  { value: "ROOM", label: "Room" },
  { value: "MODALITY", label: "Modality" },
  { value: "TECH", label: "Technologist" },
];

const WEEK_DAYS = [0, 1, 2, 3, 4, 5, 6];

/**
 * S4-08 resource manager — rooms, modalities and technologists as
 * schedulable capacity. Lists the tenant's resources, creates new ones, and
 * manages each resource's weekly availability windows (ris_resource_schedules)
 * that the availability search (S4-07) and booking engine (S4-10) consume.
 */
function ResourceManager() {
  useDocumentTitle("QuantumPACS - Resources");
  const { message } = App.useApp();
  const { hasPermission } = useAuth();
  const canWrite = hasPermission("SCHEDULE_WRITE");

  const [resources, setResources] = useState<RisResource[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [typeFilter, setTypeFilter] = useState<string | undefined>();
  const [modalityFilter, setModalityFilter] = useState<string | undefined>();

  const [createOpen, setCreateOpen] = useState(false);
  const [creating, setCreating] = useState(false);

  const [schedules, setSchedules] = useState<Record<string, RisSchedule[]>>({});
  const [schedResource, setSchedResource] = useState<RisResource | null>(null);
  const [schedLoading, setSchedLoading] = useState(false);
  const [addingDay, setAddingDay] = useState<number | null>(null);
  const [newTime, setNewTime] = useState({ start: "08:00", end: "17:00" });

  // A stale filter-change response must never paint over the newest one.
  const fetchSeq = useRef(0);
  const fetch = useCallback(() => {
    const seq = ++fetchSeq.current;
    setLoading(true);
    setError(null);
    listRisResources({
      resource_type: typeFilter,
      modality: modalityFilter,
    })
      .then((rows) => {
        if (seq === fetchSeq.current) setResources(rows);
      })
      .catch((e: unknown) => {
        if (seq === fetchSeq.current) {
          setError(toErrorMessage(e) || "Failed to load resources");
        }
      })
      .finally(() => {
        if (seq === fetchSeq.current) setLoading(false);
      });
  }, [typeFilter, modalityFilter]);

  useEffect(() => {
    fetch();
  }, [fetch]);

  useTenantRefetch(fetch);

  // R5: seq guard for the schedule drawer — opening A then quickly B
  // must not let A's finally flip schedLoading off while B is still pending.
  const schedSeq = useRef(0);
  const openSchedules = useCallback(
    (r: RisResource) => {
      const seq = ++schedSeq.current;
      setSchedResource(r);
      setSchedLoading(true);
      listRisSchedules(r.id)
        .then((rows) => {
          if (seq !== schedSeq.current) return;
          setSchedules((prev) => ({ ...prev, [r.id]: rows }));
        })
        .catch((e: unknown) => {
          if (seq !== schedSeq.current) return;
          message.error(toErrorMessage(e) || "Failed to load schedules");
        })
        .finally(() => {
          if (seq === schedSeq.current) setSchedLoading(false);
        });
    },
    [message]
  );

  const doCreate = async (values: ResourceFormValues) => {
    setCreating(true);
    try {
      const created = await createRisResource({
        name: values.name,
        resource_type: values.resource_type,
        modality: values.modality || undefined,
        location: values.location || undefined,
      });
      message.success(`Resource "${created.name}" created`);
      setCreateOpen(false);
      fetch();
    } catch (e: unknown) {
      message.error(toErrorMessage(e) || "Failed to create resource");
    } finally {
      setCreating(false);
    }
  };

  const doAddSchedule = async (day: number) => {
    if (!schedResource) return;
    if (newTime.end <= newTime.start) {
      message.error("End time must be after start time");
      return;
    }
    setAddingDay(day);
    try {
      const created = await createRisSchedule(schedResource.id, {
        day_of_week: day,
        start_time: `${newTime.start}:00`,
        end_time: `${newTime.end}:00`,
      });
      message.success(`${dayOfWeekLabel(day)} window ${newTime.start}-${newTime.end} added`);
      setSchedules((prev) => ({
        ...prev,
        [schedResource.id]: [...(prev[schedResource.id] ?? []), created],
      }));
    } catch (e: unknown) {
      message.error(toErrorMessage(e) || "Failed to add schedule window");
    } finally {
      setAddingDay(null);
    }
  };

  const filtered = useMemo(
    () =>
      resources.filter(
        (r) =>
          (!modalityFilter || r.modality === modalityFilter) &&
          (!typeFilter || r.resource_type === typeFilter)
      ),
    [resources, typeFilter, modalityFilter]
  );

  const modalityOptions = useMemo(() => {
    const seen = new Set<string>();
    for (const r of resources) if (r.modality) seen.add(r.modality);
    return [...seen].map((m) => ({ value: m, label: m }));
  }, [resources]);

  return (
    <div style={{ padding: 24 }} role="main">
      <div className="sched-header">
        <div className="sched-header-title">
          <ApartmentOutlined />
          <h2>Resources</h2>
          <Tag>Scheduling capacity</Tag>
        </div>
        {canWrite && (
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateOpen(true)}>
            New Resource
          </Button>
        )}
      </div>

      <div className="sched-toolbar">
        <Select
          placeholder="All types"
          allowClear
          style={{ width: 160 }}
          value={typeFilter}
          onChange={setTypeFilter}
          options={RESOURCE_TYPES}
          aria-label="Filter by type"
        />
        <Select
          placeholder="All modalities"
          allowClear
          style={{ width: 160 }}
          value={modalityFilter}
          onChange={setModalityFilter}
          options={modalityOptions}
          aria-label="Filter by modality"
        />
      </div>

      {error && <Alert type="error" showIcon title={error} style={{ marginBottom: 16 }} />}

      {loading ? (
        <div style={{ padding: 40, textAlign: "center" }}>
          <Spin />
        </div>
      ) : filtered.length === 0 ? (
        <Empty description="No resources found" />
      ) : (
        <div className="sched-resource-grid">
          {filtered.map((r) => (
            <Card
              key={r.id}
              className="sched-resource-card"
              size="small"
              title={
                <div className="sched-resource-card-title">
                  <b>{r.name}</b>
                  <Tag color={r.status === "ACTIVE" ? "green" : "default"}>{r.status}</Tag>
                </div>
              }
              extra={
                canWrite && (
                  <Button
                    size="small"
                    onClick={() => openSchedules(r)}
                    aria-label={`Manage schedules for ${r.name}`}
                  >
                    Schedules
                  </Button>
                )
              }
            >
              <div className="sched-resource-meta">
                {r.modality && <div>Modality: {r.modality}</div>}
                {r.location && <div>Location: {r.location}</div>}
                <div style={{ fontSize: 11, marginTop: 4 }}>
                  Created {r.created_at ? dayjs(r.created_at).format("YYYY-MM-DD") : "—"}
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      <Drawer
        title={schedResource ? `Schedules — ${schedResource.name}` : "Schedules"}
        open={!!schedResource}
        onClose={() => setSchedResource(null)}
        size="large"
      >
        {schedLoading ? (
          <div style={{ padding: 24, textAlign: "center" }}>
            <Spin />
          </div>
        ) : schedResource ? (
          <>
            <Descriptions column={1} size="small" bordered style={{ marginBottom: 16 }}>
              <Descriptions.Item label="Type">{schedResource.resource_type}</Descriptions.Item>
              {schedResource.modality && (
                <Descriptions.Item label="Modality">{schedResource.modality}</Descriptions.Item>
              )}
            </Descriptions>

            <div className="sched-form-section-title">Weekly windows</div>
            <div className="sched-week">
              {WEEK_DAYS.map((day) => {
                const windows =
                  schedules[schedResource.id]?.filter((s) => s.day_of_week === day) ?? [];
                return (
                  <div key={day} className="sched-week-row">
                    <span>{dayOfWeekLabel(day)}</span>
                    <span>
                      {windows.length === 0
                        ? "—"
                        : windows
                            .map((w) => `${w.start_time.slice(0, 5)}-${w.end_time.slice(0, 5)}`)
                            .join(", ")}
                    </span>
                  </div>
                );
              })}
            </div>

            {canWrite && (
              <div style={{ marginTop: 16 }}>
                <div className="sched-form-section-title">Add window</div>
                <Space style={{ width: "100%", marginBottom: 8 }} wrap>
                  <Select
                    style={{ width: 150 }}
                    value={addingDay}
                    placeholder="Day"
                    onChange={(v) => {
                      if (v !== null && v !== undefined) {
                        setAddingDay(v);
                      }
                    }}
                    options={WEEK_DAYS.filter(
                      (d) => !schedules[schedResource.id]?.some((s) => s.day_of_week === d)
                    ).map((d) => ({ value: d, label: dayOfWeekLabel(d) }))}
                  />
                  <Input
                    style={{ width: 90 }}
                    type="time"
                    value={newTime.start}
                    onChange={(e) => setNewTime((t) => ({ ...t, start: e.target.value }))}
                    aria-label="Start time"
                  />
                  <Input
                    style={{ width: 90 }}
                    type="time"
                    value={newTime.end}
                    onChange={(e) => setNewTime((t) => ({ ...t, end: e.target.value }))}
                    aria-label="End time"
                  />
                  <Button
                    type="primary"
                    size="small"
                    icon={<PlusOutlined />}
                    loading={addingDay !== null}
                    disabled={addingDay === null}
                    onClick={() => addingDay !== null && doAddSchedule(addingDay)}
                  >
                    Add
                  </Button>
                </Space>
              </div>
            )}
          </>
        ) : null}
      </Drawer>

      <Drawer
        title="New Resource"
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        size="large"
      >
        <Form layout="vertical" onFinish={doCreate}>
          <Form.Item
            label="Name"
            name="name"
            rules={[{ required: true, message: "Name is required" }]}
          >
            <Input placeholder="e.g. CT Room 1" maxLength={128} />
          </Form.Item>
          <Form.Item
            label="Type"
            name="resource_type"
            rules={[{ required: true, message: "Type is required" }]}
          >
            <Select options={RESOURCE_TYPES} placeholder="Select type" />
          </Form.Item>
          <Form.Item label="Modality" name="modality">
            <Select
              allowClear
              options={MODALITIES.filter((m) => m !== "MRI").map((m) => ({ value: m, label: m }))}
              placeholder="Required for modalities"
            />
          </Form.Item>
          <Form.Item label="Location" name="location">
            <Input placeholder="e.g. Ground floor, east wing" maxLength={128} />
          </Form.Item>
          <Button type="primary" htmlType="submit" icon={<PlusOutlined />} loading={creating} block>
            Create Resource
          </Button>
        </Form>
      </Drawer>
    </div>
  );
}

export default withSidebar(ResourceManager);
