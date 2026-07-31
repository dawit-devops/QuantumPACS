import React, { useState, useEffect, useCallback, useMemo } from "react";
import {
  Layout,
  Table,
  message,
  Button,
  Tag,
  Modal,
  Form,
  Select,
  Popconfirm,
  Tabs,
  Tooltip,
  Badge,
  Radio,
  Input,
  DatePicker,
} from "antd";
import {
  EditOutlined,
  CloseCircleOutlined,
  CheckCircleOutlined,
  CalendarOutlined,
  TableOutlined,
} from "@ant-design/icons";
import withSidebar from "../common/base";
import { request } from "../helpers";
import { PageState } from "../common/PageState";
import { CreateEntry } from "./CreateEntry";
import dayjs from "dayjs";
import "./Worklist.css";

const Content = Layout.Content;

const STATUS_COLORS: Record<string, string> = {
  scheduled: "blue",
  performed: "green",
  cancelled: "red",
};

const STATUS_TABS = [
  { key: "all", label: "All" },
  { key: "scheduled", label: "Scheduled" },
  { key: "performed", label: "Performed" },
  { key: "cancelled", label: "Cancelled" },
];

function Worklist() {
  document.title = "QuantumPACS - Worklist";

  let [data, setData] = useState<any[]>([]);
  let [loading, setLoading] = useState(false);
  let [error, setError] = useState<string | null>(null);
  let [pagination, setPagination] = useState<any>({
    current: 1,
    pageSize: 20,
    total: 0,
  });
  let [visible, setVisible] = useState(false);
  let [editingEntry, setEditingEntry] = useState<any | null>(null);
  let [statusTab, setStatusTab] = useState("all");
  let [stationFilter, setStationFilter] = useState<string | undefined>(
    undefined,
  );
  let [searchQuery, setSearchQuery] = useState("");
  let [dateRange, setDateRange] = useState<[string, string] | null>(null);
  let [stationOptions, setStationOptions] = useState<string[]>([]);
  let [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);
  let [viewMode, setViewMode] = useState<"table" | "calendar">("table");
  let [batchLoading, setBatchLoading] = useState(false);
  const [form] = Form.useForm();

  const fetch = useCallback(
    (params?: any) => {
      setLoading(true);
      setError(null);
      const query: any = { ...(params || {}) };
      if (statusTab !== "all") query.status = statusTab;
      if (stationFilter) query.station_ae_title = stationFilter;
      if (searchQuery) query.search = searchQuery;
      if (dateRange) {
        query.date_from = dateRange[0];
        query.date_to = dateRange[1];
      }
      request("worklist", query)
        .then((res: any) => {
          setLoading(false);
          const items = Array.isArray(res.data) ? res.data : [];
          setData(items);
          setPagination((prev: any) => ({
            ...prev,
            total: res.total || items.length,
            current: res.page || prev.current,
          }));
        })
        .catch((e: any) => {
          setLoading(false);
          setError(e.message);
          message.error(e.message);
        });
    },
    [statusTab, stationFilter, searchQuery, dateRange],
  );

  useEffect(() => {
    fetch();
    request("worklist/station-aes", { method: "GET" })
      .then((res: any) => {
        if (Array.isArray(res)) setStationOptions(res);
        else if (res?.data) setStationOptions(res.data);
      })
      .catch(() => {});
  }, [fetch]);

  const stationOptionsFromEntries = useMemo(() => {
    const stations = new Set(
      data.map((e) => e.station_ae_title).filter(Boolean),
    );
    return Array.from(stations).sort();
  }, [data]);

  const handleTableChange = (pag: any) => {
    setPagination(pag);
    setSelectedRowKeys([]);
    fetch({ page: pag.current, per_page: pag.pageSize });
  };

  const handleCreate = () => {
    form
      .validateFields()
      .then((values: any) => {
        const data: any = { ...values };
        if (data.station_ae_title && Array.isArray(data.station_ae_title)) {
          data.station_ae_title = data.station_ae_title[0];
        }
        if (data.scheduled_date)
          data.scheduled_date = data.scheduled_date.format("YYYY-MM-DD");
        if (data.scheduled_time)
          data.scheduled_time = data.scheduled_time.format("HH:mm");
        request("worklist", { data })
          .then(() => {
            form.resetFields();
            setVisible(false);
            fetch();
          })
          .catch((e: any) => {
            message.error(e.message);
          });
      })
      .catch(() => {});
  };

  const handleEdit = (entry: any) => {
    setEditingEntry(entry);
    form.setFieldsValue({
      ...entry,
      station_ae_title: entry.station_ae_title
        ? [entry.station_ae_title]
        : undefined,
      scheduled_date: entry.scheduled_date ? dayjs(entry.scheduled_date) : null,
      scheduled_time: entry.scheduled_time
        ? dayjs(entry.scheduled_time, "HH:mm")
        : null,
    });
    setVisible(true);
  };

  const handleUpdate = () => {
    form
      .validateFields()
      .then((values: any) => {
        const data: any = {};
        for (const key of [
          "patient_name",
          "patient_birth_date",
          "patient_sex",
          "accession_number",
          "requested_procedure_id",
          "requested_procedure_desc",
          "modality",
          "station_ae_title",
        ]) {
          if (values[key] !== undefined && values[key] !== editingEntry[key]) {
            data[key] = Array.isArray(values[key])
              ? values[key][0]
              : values[key];
          }
        }
        if (values.scheduled_date)
          data.scheduled_date = values.scheduled_date.format("YYYY-MM-DD");
        if (values.scheduled_time)
          data.scheduled_time = values.scheduled_time.format("HH:mm");
        if (Object.keys(data).length === 0) {
          setVisible(false);
          setEditingEntry(null);
          return;
        }
        request(`worklist/${editingEntry.id}`, { data })
          .then(() => {
            form.resetFields();
            setEditingEntry(null);
            setVisible(false);
            fetch();
          })
          .catch((e: any) => {
            message.error(e.message);
          });
      })
      .catch(() => {});
  };

  const handleCancel = (id: string) => {
    request(`worklist/${id}`, { data: undefined, method: "DELETE" })
      .then(() => {
        fetch();
        setSelectedRowKeys((prev) => prev.filter((k) => k !== id));
      })
      .catch((e: any) => {
        message.error(e.message);
      });
  };

  const handleMarkPerformed = (id: string) => {
    request(`worklist/${id}`, { data: { status: "performed" } })
      .then(() => {
        message.success("Marked as performed");
        fetch();
        setSelectedRowKeys((prev) => prev.filter((k) => k !== id));
      })
      .catch((e: any) => {
        message.error(e.message);
      });
  };

  const handleBatchCancel = () => {
    setBatchLoading(true);
    const ids = [...selectedRowKeys];
    Promise.all(
      ids.map((id) =>
        request(`worklist/${id}`, { data: undefined, method: "DELETE" }).catch(
          () => {},
        ),
      ),
    ).then(() => {
      setBatchLoading(false);
      setSelectedRowKeys([]);
      message.success(`Cancelled ${ids.length} entries`);
      fetch();
    });
  };

  const handleBatchPerformed = () => {
    setBatchLoading(true);
    const ids = [...selectedRowKeys];
    Promise.all(
      ids.map((id) =>
        request(`worklist/${id}`, { data: { status: "performed" } }).catch(
          () => {},
        ),
      ),
    ).then(() => {
      setBatchLoading(false);
      setSelectedRowKeys([]);
      message.success(`Marked ${ids.length} entries as performed`);
      fetch();
    });
  };

  const handleModalCancel = () => {
    form.resetFields();
    setEditingEntry(null);
    setVisible(false);
  };

  const handleStatusTabChange = (key: string) => {
    setStatusTab(key);
    setSelectedRowKeys([]);
    setPagination((prev: any) => ({ ...prev, current: 1 }));
  };

  const countedTabs = useMemo(() => {
    return STATUS_TABS.map((tab) => {
      let count: number | undefined;
      if (tab.key === "all") {
        count = data.length;
      } else {
        count = data.filter((e) => e.status === tab.key).length;
      }
      return { ...tab, count };
    });
  }, [data]);

  const filteredData = useMemo(() => {
    let items = data;
    if (statusTab !== "all") {
      items = items.filter((e) => e.status === statusTab);
    }
    return items;
  }, [data, statusTab]);

  const columns: any[] = [
    {
      title: "Patient Name",
      dataIndex: "patient_name",
      width: "14%",
      render: (v: string) => v || "-",
    },
    { title: "Patient ID", dataIndex: "patient_id", width: "8%" },
    { title: "Accession #", dataIndex: "accession_number", width: "9%" },
    {
      title: "Proc ID",
      dataIndex: "requested_procedure_id",
      width: "7%",
      render: (v: string) => v || "-",
    },
    { title: "Modality", dataIndex: "modality", width: "6%" },
    {
      title: "Scheduled Date",
      dataIndex: "scheduled_date",
      width: "9%",
      render: (d: string) => d || "-",
    },
    {
      title: "Station AE",
      dataIndex: "station_ae_title",
      width: "10%",
      render: (v: string) => (v ? <Tag style={{ margin: 0 }}>{v}</Tag> : "-"),
    },
    {
      title: "Status",
      dataIndex: "status",
      width: "7%",
      render: (s: string) =>
        s ? <Tag color={STATUS_COLORS[s] || "default"}>{s}</Tag> : null,
    },
    {
      title: "Study UID",
      dataIndex: "study_uid",
      width: "10%",
      render: (v: string) =>
        v ? (
          <Tag style={{ margin: 0, fontFamily: "monospace", fontSize: 11 }}>
            {v.slice(0, 20)}…
          </Tag>
        ) : (
          "-"
        ),
    },
    {
      title: "Performed",
      dataIndex: "performed_at",
      width: "9%",
      render: (v: string) => (v ? new Date(v).toLocaleString() : "-"),
    },
    {
      title: "Action",
      key: "action",
      width: "11%",
      render: (_: any, record: any) => (
        <span style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <Tooltip title="Edit">
            <EditOutlined
              onClick={() => handleEdit(record)}
              style={{ cursor: "pointer", fontSize: 16 }}
            />
          </Tooltip>
          {record.status === "scheduled" && (
            <>
              <Popconfirm
                title="Mark as performed?"
                onConfirm={() => handleMarkPerformed(record.id)}
              >
                <Tooltip title="Mark performed">
                  <CheckCircleOutlined
                    style={{
                      cursor: "pointer",
                      color: "#16a34a",
                      fontSize: 16,
                    }}
                  />
                </Tooltip>
              </Popconfirm>
              <Popconfirm
                title="Cancel this entry?"
                onConfirm={() => handleCancel(record.id)}
              >
                <Tooltip title="Cancel">
                  <CloseCircleOutlined
                    style={{
                      cursor: "pointer",
                      color: "#dc2626",
                      fontSize: 16,
                    }}
                  />
                </Tooltip>
              </Popconfirm>
            </>
          )}
          {record.status === "performed" && (
            <Tooltip
              title={`Performed at ${record.performed_at ? new Date(record.performed_at).toLocaleString() : "unknown"}`}
            >
              <CheckCircleOutlined
                style={{ color: "#16a34a", fontSize: 16, opacity: 0.5 }}
              />
            </Tooltip>
          )}
        </span>
      ),
    },
  ];

  const calendarEntries = useMemo(() => {
    const grouped: Record<string, any[]> = {};
    for (const entry of filteredData) {
      const date = entry.scheduled_date || "No date";
      if (!grouped[date]) grouped[date] = [];
      grouped[date].push(entry);
    }
    const sorted = Object.entries(grouped).sort(([a], [b]) =>
      a.localeCompare(b),
    );
    return sorted;
  }, [filteredData]);

  const rowSelection = {
    selectedRowKeys,
    onChange: (keys: React.Key[]) => setSelectedRowKeys(keys),
    getCheckboxProps: (record: any) => ({
      disabled: record.status === "cancelled",
    }),
  };

  return (
    <Content style={{ padding: 24 }} role="main" id="main-content">
      <div
        aria-live="polite"
        aria-atomic="true"
        style={{
          position: "absolute",
          width: 1,
          height: 1,
          overflow: "hidden",
          clip: "rect(0,0,0,0)",
        }}
      >
        {loading
          ? "Loading worklist"
          : `${filteredData.length} worklist entries`}
      </div>

      <div className="worklist-toolbar">
        <Button
          type="primary"
          onClick={() => {
            setEditingEntry(null);
            form.resetFields();
            setVisible(true);
          }}
          aria-label="Create worklist entry"
        >
          Create Entry
        </Button>
        <Radio.Group
          value={viewMode}
          onChange={(e) => setViewMode(e.target.value)}
          buttonStyle="solid"
          size="small"
        >
          <Radio.Button value="table">
            <TableOutlined /> Table
          </Radio.Button>
          <Radio.Button value="calendar">
            <CalendarOutlined /> Calendar
          </Radio.Button>
        </Radio.Group>
        <div className="worklist-toolbar-filters">
          <Input.Search
            placeholder="Search patients..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onSearch={() => {
              setPagination((p: any) => ({ ...p, current: 1 }));
              fetch();
            }}
            style={{ width: 200 }}
            size="small"
            allowClear
          />
          <DatePicker.RangePicker
            size="small"
            onChange={(dates) => {
              if (dates && dates[0] && dates[1]) {
                setDateRange([
                  dates[0].format("YYYY-MM-DD"),
                  dates[1].format("YYYY-MM-DD"),
                ]);
              } else {
                setDateRange(null);
              }
            }}
            style={{ width: 220 }}
          />
          <Select
            allowClear
            placeholder="Station AE"
            value={stationFilter}
            onChange={setStationFilter}
            style={{ minWidth: 160 }}
            size="small"
            options={[
              ...new Set([...stationOptions, ...stationOptionsFromEntries]),
            ].map((s) => ({ value: s, label: s }))}
          />
        </div>
      </div>

      <Tabs
        activeKey={statusTab}
        onChange={handleStatusTabChange}
        className="worklist-tabs"
        items={countedTabs.map((tab) => ({
          key: tab.key,
          label: (
            <span>
              {tab.label}
              <Badge count={tab.count} style={{ marginLeft: 6 }} size="small" />
            </span>
          ),
        }))}
      />

      {selectedRowKeys.length > 0 && (
        <div className="worklist-batch-bar">
          <span style={{ fontWeight: 500, marginRight: 8 }}>
            {selectedRowKeys.length} selected
          </span>
          <Button
            size="small"
            icon={<CheckCircleOutlined />}
            onClick={handleBatchPerformed}
            loading={batchLoading}
          >
            Mark Performed
          </Button>
          <Button
            size="small"
            icon={<CloseCircleOutlined />}
            onClick={handleBatchCancel}
            loading={batchLoading}
            danger
          >
            Cancel All
          </Button>
        </div>
      )}

      <PageState
        error={error}
        onRetry={() => fetch()}
        empty={!loading && !error && filteredData.length === 0}
        emptyMessage={
          statusTab !== "all"
            ? `No ${statusTab} entries`
            : "No worklist entries found"
        }
        emptyAction={
          <Button
            type="primary"
            onClick={() => {
              setEditingEntry(null);
              form.resetFields();
              setVisible(true);
            }}
          >
            Create Entry
          </Button>
        }
      >
        {viewMode === "table" ? (
          <Table
            rowKey="id"
            columns={columns}
            dataSource={filteredData}
            loading={loading}
            pagination={pagination}
            onChange={handleTableChange}
            rowSelection={rowSelection}
            size="middle"
          />
        ) : (
          <div className="calendar-view">
            {calendarEntries.map(([date, entries]) => (
              <div key={date} className="calendar-day">
                <div className="calendar-day-header">
                  {date === "No date" ? "Unscheduled" : date}
                  <Tag style={{ marginLeft: 8 }}>{entries.length}</Tag>
                </div>
                {entries.map((entry) => (
                  <div
                    key={entry.id}
                    className={`calendar-entry ${entry.status}`}
                    onClick={() => handleEdit(entry)}
                    role="button"
                    tabIndex={0}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") handleEdit(entry);
                    }}
                  >
                    <Tag
                      color={STATUS_COLORS[entry.status]}
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
        )}
      </PageState>

      <Modal
        title={editingEntry ? "Edit Worklist Entry" : "Create Worklist Entry"}
        open={visible}
        onCancel={handleModalCancel}
        onOk={editingEntry ? handleUpdate : handleCreate}
        width={560}
        afterOpenChange={(open) => {
          if (open) {
            setTimeout(() => {
              const input = document.querySelector(
                ".ant-modal-body input",
              ) as HTMLInputElement;
              input?.focus();
            }, 50);
          }
        }}
      >
        <CreateEntry form={form} editingEntry={editingEntry} />
      </Modal>
    </Content>
  );
}

export default withSidebar(Worklist);
