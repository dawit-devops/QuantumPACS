import { useDocumentTitle, useTenantRefetch } from "../hooks";
import React, { useState, useEffect, useCallback, useMemo } from "react";
import {
  App,
  Layout,
  Table,
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
import { mapLimit } from "../helpers";
import { useAuth } from "../auth/AuthContext";
import {
  listWorklist,
  listStationAes,
  createWorklistEntry,
  updateWorklistEntry,
  deleteWorklistEntry,
  markWorklistPerformed,
  type WorklistEntry,
} from "../api/worklist";
import { PageState } from "../common/PageState";
import { CreateEntry } from "./CreateEntry";
import CalendarView from "./CalendarView";
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
  const { message } = App.useApp();
  useDocumentTitle("QuantumPACS - Worklist");

  // Create / edit / perform / cancel all hit WORKLIST_WRITE-gated endpoints
  // (api/worklist.py). View-only holders (WORKLIST_READ — nurse, referring
  // physician) keep the queue but lose the write affordances.
  const { hasPermission } = useAuth();
  const canWrite = hasPermission("WORKLIST_WRITE");

  const [data, setData] = useState<WorklistEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pagination, setPagination] = useState<any>({
    current: 1,
    pageSize: 20,
    total: 0,
  });
  const [visible, setVisible] = useState(false);
  const [editingEntry, setEditingEntry] = useState<WorklistEntry | null>(null);
  const [statusTab, setStatusTab] = useState("all");
  const [stationFilter, setStationFilter] = useState<string | undefined>(
    undefined,
  );
  const [searchQuery, setSearchQuery] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [dateRange, setDateRange] = useState<[string, string] | null>(null);
  const [stationOptions, setStationOptions] = useState<string[]>([]);
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);
  const [tabTotals, setTabTotals] = useState<Record<string, number>>({});
  const [viewMode, setViewMode] = useState<"table" | "calendar">("table");
  const [batchLoading, setBatchLoading] = useState(false);
  const [form] = Form.useForm();

  // Debounce the search field so each keystroke does not fire a request.
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(searchQuery), 300);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  const buildQuery = useCallback(
    (overrides?: Record<string, string>) => {
      const query: Record<string, string> = {};
      if (stationFilter) query.station_ae_title = stationFilter;
      if (debouncedSearch) query.search = debouncedSearch;
      if (dateRange) {
        query.date_from = dateRange[0];
        query.date_to = dateRange[1];
      }
      if (overrides) Object.assign(query, overrides);
      return query;
    },
    [stationFilter, debouncedSearch, dateRange],
  );

  const fetchTabTotals = useCallback(() => {
    // Server-side per-status totals for the tab badges: the current page
    // only reflects the active filter, so per-tab counts cannot be derived
    // client-side (Q-7).
    Promise.all(
      STATUS_TABS.filter((t) => t.key !== "all").map((t) =>
        listWorklist(buildQuery({ status: t.key, page: "1", per_page: "1" })),
      ),
    )
      .then((results) => {
        const totals: Record<string, number> = {};
        STATUS_TABS.filter((t) => t.key !== "all").forEach((t, i) => {
          totals[t.key] = results[i]?.total || 0;
        });
        setTabTotals(totals);
      })
      .catch(() => {});
  }, [buildQuery]);

  const fetch = useCallback(
    (params?: any) => {
      setLoading(true);
      setError(null);
      const query = buildQuery(
        statusTab !== "all" ? { status: statusTab } : {},
      );
      if (params?.page) query.page = String(params.page);
      if (params?.per_page) query.per_page = String(params.per_page);
      listWorklist(query)
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
      fetchTabTotals();
    },
    [statusTab, buildQuery, fetchTabTotals],
  );

  useEffect(() => {
    fetch();
    listStationAes()
      .then((res: any) => {
        if (Array.isArray(res)) setStationOptions(res);
        else if (res?.data) setStationOptions(res.data);
      })
      .catch(() => {});
  }, [fetch]);

  // Tenant switch → refetch list and per-status tab totals together.
  useTenantRefetch(() => {
    fetch({ page: 1, per_page: 20 });
    fetchTabTotals();
  });

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
        createWorklistEntry(data)
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

  const handleEdit = useCallback((entry: any) => {
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
  }, []);

  const handleUpdate = () => {
    form
      .validateFields()
      .then((values: any) => {
        if (!editingEntry) return;
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
        ] as const) {
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
        updateWorklistEntry(editingEntry.id, data)
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

  const handleCancel = useCallback((id: string) => {
    deleteWorklistEntry(id)
      .then(() => {
        fetch();
        setSelectedRowKeys((prev) => prev.filter((k) => k !== id));
      })
      .catch((e: any) => {
        message.error(e.message);
      });
  }, []);

  const handleMarkPerformed = useCallback((id: string) => {
    markWorklistPerformed(id)
      .then(() => {
        message.success("Marked as performed");
        fetch();
        setSelectedRowKeys((prev) => prev.filter((k) => k !== id));
      })
      .catch((e: any) => {
        message.error(e.message);
      });
  }, []);

  const handleBatchCancel = () => {
    setBatchLoading(true);
    const ids = [...selectedRowKeys];
    // Track failures individually so a fully-failed batch reports failure
    // instead of a false success (Q-17). Runs at most 4 concurrent requests
    // so a large selection cannot fan out hundreds of calls (P-M8).
    mapLimit(ids, 4, (id) =>
      deleteWorklistEntry(id as number).then(
        () => true,
        () => false,
      ),
    ).then((results) => {
      setBatchLoading(false);
      const ok = results.filter(Boolean).length;
      const failed = ids.length - ok;
      setSelectedRowKeys(ids.filter((_, i) => !results[i]));
      if (failed > 0) {
        message.error(
          `Cancelled ${ok}/${ids.length} entries (${failed} failed)`,
        );
      } else {
        message.success(`Cancelled ${ok} entries`);
      }
      fetch();
    });
  };

  const handleBatchPerformed = () => {
    setBatchLoading(true);
    const ids = [...selectedRowKeys];
    mapLimit(ids, 4, (id) =>
      markWorklistPerformed(id as number).then(
        () => true,
        () => false,
      ),
    ).then((results) => {
      setBatchLoading(false);
      const ok = results.filter(Boolean).length;
      const failed = ids.length - ok;
      setSelectedRowKeys(ids.filter((_, i) => !results[i]));
      if (failed > 0) {
        message.error(
          `Marked ${ok}/${ids.length} performed (${failed} failed)`,
        );
      } else {
        message.success(`Marked ${ok} entries as performed`);
      }
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
    return STATUS_TABS.map((tab) => ({
      ...tab,
      count: tab.key === "all" ? pagination.total : tabTotals[tab.key],
    }));
  }, [pagination.total, tabTotals]);

  // The server already filters by the active status tab (query.status), so
  // data is exactly the current view — no client-side re-filter (Q-7).

  // (P-M6) Columns are stable across renders — memoize so the Table doesn't
  // re-render its full cell set on every state change (e.g. each keystroke).
  const columns: any[] = useMemo(
    () => [
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
        render: (_: any, record: any) =>
          canWrite ? (
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
          ) : (
            <span>—</span>
          ),
      },
    ],
    [canWrite, handleEdit, handleCancel, handleMarkPerformed],
  );

  const rowSelection = {
    selectedRowKeys,
    onChange: (keys: React.Key[]) => setSelectedRowKeys(keys),
    getCheckboxProps: (record: any) => ({
      disabled: record.status === "cancelled",
    }),
  };

  return (
    <Content style={{ padding: 24 }} role="main">
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
        {loading ? "Loading worklist" : `${data.length} worklist entries`}
      </div>

      <div className="worklist-toolbar">
        {canWrite && (
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
        )}
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

      {canWrite && selectedRowKeys.length > 0 && (
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
        empty={!loading && !error && data.length === 0}
        emptyMessage={
          statusTab !== "all"
            ? `No ${statusTab} entries`
            : "No worklist entries found"
        }
        emptyAction={
          canWrite ? (
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
          ) : undefined
        }
      >
        {viewMode === "table" ? (
          <Table
            rowKey="id"
            columns={columns}
            dataSource={data}
            loading={loading}
            pagination={pagination}
            onChange={handleTableChange}
            rowSelection={canWrite ? rowSelection : undefined}
            size="middle"
          />
        ) : (
          <CalendarView
            entries={data}
            onEdit={canWrite ? handleEdit : undefined}
          />
        )}
      </PageState>

      <Modal
        title={editingEntry ? "Edit Worklist Entry" : "Create Worklist Entry"}
        open={visible}
        onCancel={handleModalCancel}
        onOk={
          canWrite ? (editingEntry ? handleUpdate : handleCreate) : undefined
        }
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
