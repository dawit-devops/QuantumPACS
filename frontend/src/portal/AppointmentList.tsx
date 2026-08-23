import { useDocumentTitle, useTenantRefetch } from "../hooks";
import React, { useCallback, useEffect, useRef, useState } from "react";
import {
  App,
  Layout,
  Card,
  Table,
  Tag,
  Tabs,
  Button,
  Spin,
  Alert,
  Empty,
  Typography,
  Space,
  Tooltip,
  Select,
  DatePicker,
} from "antd";
import {
  CalendarOutlined,
  ClockCircleOutlined,
  CheckCircleOutlined,
  ArrowLeftOutlined,
  InfoCircleOutlined,
  FilterOutlined,
} from "@ant-design/icons";
import { useNavigate, useSearchParams } from "react-router";
import withSidebar from "../common/base";
import { PageState } from "../common/PageState";
import {
  listScope,
  getPortalAppointments,
  type PortalScope,
} from "../api/portal";
import "./Portal.css";

const { Text } = Typography;
const Content = Layout.Content;
const { RangePicker } = DatePicker;

const APPT_STATUS_COLORS: Record<string, string> = {
  SCHEDULED: "blue",
  CONFIRMED: "green",
  ARRIVED: "cyan",
  IN_PROGRESS: "blue",
  COMPLETED: "green",
  CANCELLED: "red",
  NO_SHOW: "orange",
};

const URGENCY_COLORS: Record<string, string> = {
  STAT: "red",
  URGENT: "orange",
  ROUTINE: "default",
};

// Modality-specific prep instruction defaults
const DEFAULT_PREP: Record<string, string> = {
  CT: "Do not eat or drink for 4 hours before your exam. Arrive 15 minutes early.",
  MR: "Remove all metal jewelry. Wear comfortable clothing without metal zippers.",
  US: "Drink 32 oz of water 1 hour before your exam (for abdominal/pelvic).",
  MG: "Do not wear deodorant, powder, or lotion on the day of your exam.",
  DX: "Remove any jewelry or metal objects from the area being imaged.",
  PET: "Do not eat or drink for 6 hours before your exam. Arrive 30 minutes early.",
};

interface PortalAppointment {
  id: string;
  patient_id?: string;
  start_time?: string;
  end_time?: string;
  status?: string;
  modality?: string;
  room?: string;
  prep_instructions?: string;
  procedure?: string;
  priority?: string;
  accession_number?: string;
  report_id?: string | null;
}

function AppointmentList() {
  const { message } = App.useApp();
  useDocumentTitle("QuantumPACS - Appointments");
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  const [scope, setScope] = useState<PortalScope[]>([]);
  const [loadingScope, setLoadingScope] = useState(true);
  const [activePatientId, setActivePatientId] = useState<string | null>(null);
  const [appointments, setAppointments] = useState<PortalAppointment[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // S6 (P-03): history filters — modality + date range, applied client-side
  // over the fetched history set.
  const [filterModality, setFilterModality] = useState<string | undefined>();
  const [dateRange, setDateRange] = useState<
    [Date | null, Date | null] | null
  >(null);

  const activeTab = searchParams.get("tab") || "upcoming";

  const loadScope = useCallback(() => {
    setLoadingScope(true);
    setError(null);
    listScope()
      .then((rows) => {
        setScope(rows);
        if (rows.length > 0) setActivePatientId(rows[0].patient_id);
        else setActivePatientId(null);
      })
      .catch((e: any) => setError(e.message || "Failed to load appointments"))
      .finally(() => setLoadingScope(false));
  }, []);

  useEffect(() => {
    loadScope();
  }, [loadScope]);

  useTenantRefetch(loadScope);

  const patientSeq = useRef(0);
  const loadAppointments = useCallback(
    (patientId: string, history: boolean) => {
      const seq = ++patientSeq.current;
      setLoading(true);
      setError(null);
      setAppointments([]);
      const query = history ? { status: "history" } : undefined;
      getPortalAppointments(patientId, query)
        .then((appts) => {
          if (seq !== patientSeq.current) return;
          setAppointments(appts);
        })
        .catch((e: any) => {
          if (seq === patientSeq.current) {
            setError(e.message || "Failed to load appointments");
          }
        })
        .finally(() => {
          if (seq === patientSeq.current) setLoading(false);
        });
    },
    [],
  );

  useEffect(() => {
    if (activePatientId) {
      loadAppointments(activePatientId, activeTab === "history");
    }
  }, [activePatientId, activeTab, loadAppointments]);

  // The backend already filters future vs past by the status=history query;
  // the tab just switches which set is loaded. History filters apply
  // client-side (modality + date range) per spec P-03.
  const upcoming = appointments;
  let history = appointments;
  if (filterModality) {
    history = history.filter((a) => a.modality === filterModality);
  }
  if (dateRange && dateRange[0] && dateRange[1]) {
    const start = dateRange[0].getTime();
    const end = dateRange[1].getTime() + 86_400_000;
    history = history.filter((a) => {
      if (!a.start_time) return true;
      const t = new Date(a.start_time).getTime();
      return t >= start && t <= end;
    });
  }
  const historyModalities = Array.from(
    new Set(appointments.map((a) => a.modality).filter(Boolean)),
  ) as string[];

  const columns = [
    {
      title: "Date",
      dataIndex: "start_time",
      key: "date",
      width: 140,
      render: (v: string) =>
        v ? new Date(v).toLocaleDateString() : "—",
    },
    {
      title: "Procedure",
      dataIndex: "procedure",
      key: "procedure",
      render: (v: string) => <Text strong>{v || "Imaging"}</Text>,
    },
    {
      title: "Modality",
      dataIndex: "modality",
      key: "modality",
      width: 90,
      render: (v: string) => (v ? <Tag>{v}</Tag> : "—"),
    },
    {
      title: "Priority",
      dataIndex: "priority",
      key: "priority",
      width: 90,
      render: (v: string) =>
        v ? (
          <Tag color={URGENCY_COLORS[v] || "default"}>
            {v.toLowerCase()}
          </Tag>
        ) : (
          "routine"
        ),
    },
    {
      title: "Status",
      dataIndex: "status",
      key: "status",
      width: 130,
      render: (v: string) => (
        <Tag color={APPT_STATUS_COLORS[v] || "default"}>
          {v === "COMPLETED" && <CheckCircleOutlined style={{ marginRight: 4 }} />}
          {v === "ARRIVED" && <CheckCircleOutlined style={{ marginRight: 4 }} />}
          {v === "ARRIVED" ? "Checked in" : (v || "SCHEDULED").toLowerCase()}
        </Tag>
      ),
    },
    {
      title: "Prep",
      key: "prep",
      width: 60,
      render: (_: any, r: PortalAppointment) => {
        const prep = r.prep_instructions || DEFAULT_PREP[r.modality || ""];
        if (!prep) return null;
        return (
          <Tooltip title={prep} placement="topLeft">
            <InfoCircleOutlined style={{ color: "#fa8c16", cursor: "pointer" }} />
          </Tooltip>
        );
      },
    },
    {
      title: "Action",
      key: "action",
      width: 100,
      render: (_: any, r: PortalAppointment) => {
        if (r.status === "SCHEDULED" || r.status === "CONFIRMED") {
          return (
            <Button
              type="link"
              size="small"
              onClick={() => navigate(`/portal`)}
            >
              Details
            </Button>
          );
        }
        if ((r.status === "COMPLETED" || r.status === "SIGNED") &&
            (r.report_id || r.accession_number)) {
          return (
            <Button
              type="link"
              size="small"
              onClick={() =>
                r.report_id
                  ? navigate(`/portal/results/${r.report_id}`)
                  : navigate(`/portal/results`)
              }
            >
              View Report
            </Button>
          );
        }
        return null;
      },
    },
  ];

  return (
    <Content className="portal-home" role="main">
      <div className="portal-home-header">
        <div>
          <h2 style={{ margin: 0 }}>
            <CalendarOutlined style={{ marginRight: 8 }} />
            Appointments
          </h2>
          <Text type="secondary">Your upcoming and past appointments</Text>
        </div>
        <Button onClick={() => navigate("/portal")}>
          <ArrowLeftOutlined /> Back to Portal
        </Button>
      </div>

      {error && (
        <Alert
          type="warning"
          title="Some data could not be loaded"
          description={error}
          showIcon
          closable
          style={{ marginBottom: 16 }}
        />
      )}

      <Card className="portal-card">
        <Tabs
          activeKey={activeTab}
          onChange={(key) => setSearchParams({ tab: key })}
          items={[
            {
              key: "upcoming",
              label: (
                <span>
                  <CalendarOutlined style={{ marginRight: 4 }} />
                  Upcoming ({upcoming.length})
                </span>
              ),
              children: (
                <PageState
                  loading={loading}
                  error={null}
                  empty={!loading && upcoming.length === 0}
                  emptyMessage="No upcoming appointments"
                >
                  <Table
                    rowKey="id"
                    columns={columns}
                    dataSource={upcoming}
                    pagination={false}
                    size="small"
                  />
                </PageState>
              ),
            },
            {
              key: "history",
              label: (
                <span>
                  <ClockCircleOutlined style={{ marginRight: 4 }} />
                  History ({history.length})
                </span>
              ),
              children: (
                <>
                  <Space
                    style={{ marginBottom: 12 }}
                    wrap
                    data-testid="history-filters"
                  >
                    <Select
                      allowClear
                      placeholder="Filter by modality"
                      value={filterModality}
                      onChange={setFilterModality}
                      style={{ minWidth: 160 }}
                      options={historyModalities.map((m) => ({
                        value: m,
                        label: m,
                      }))}
                      aria-label="Filter by modality"
                    />
                    <RangePicker
                      onChange={(_, dateStrings) => {
                        if (dateStrings[0] && dateStrings[1]) {
                          setDateRange([
                            new Date(dateStrings[0]),
                            new Date(dateStrings[1]),
                          ]);
                        } else {
                          setDateRange(null);
                        }
                      }}
                      aria-label="Filter by date range"
                    />
                    {(filterModality || dateRange) && (
                      <Button
                        size="small"
                        onClick={() => {
                          setFilterModality(undefined);
                          setDateRange(null);
                        }}
                      >
                        Clear filters
                      </Button>
                    )}
                  </Space>
                  <PageState
                    loading={loading}
                    error={null}
                    empty={!loading && history.length === 0}
                    emptyMessage="No appointment history"
                  >
                    <Table
                      rowKey="id"
                      columns={columns}
                      dataSource={history}
                      pagination={{ pageSize: 10, showSizeChanger: false }}
                      size="small"
                    />
                  </PageState>
                </>
              ),
            },
          ]}
        />
      </Card>
    </Content>
  );
}

export default withSidebar(AppointmentList);
