import { useDocumentTitle } from "../hooks";
import React, { useState, useEffect, useMemo } from "react";
import {
  Layout,
  Card,
  Descriptions,
  Tag,
  Tree,
  Typography,
  Space,
  Badge,
  Empty,
  Spin,
  Tabs,
} from "antd";
import {
  FolderOutlined,
  FileOutlined,
  FileDoneOutlined,
  ExperimentOutlined,
  CalendarOutlined,
  UserOutlined,
  MedicineBoxOutlined,
} from "@ant-design/icons";
import withSidebar from "../common/base";
import { getPatient, type PatientSummary } from "../api/patient";
import { PageState } from "../common/PageState";
import { REPORT_STATUS_COLORS, REPORT_STATUS_LABEL } from "../common/statusColors";
import { useAuth } from "../auth/AuthContext";
import { useNavigate, useParams } from "react-router";
import { request } from "../helpers";

const { Text, Title } = Typography;
const Content = Layout.Content;

// Care-coordinator review (P2-1): report status labels + colors mirror the
// reading worklist conventions.

function Patient(props: any) {
  useDocumentTitle("QuantumPACS - Patient");

  const { hasPermission } = useAuth();
  const canReadReports = hasPermission("REPORT_READ");

  const [data, setData] = useState<PatientSummary>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedKeys, setExpandedKeys] = useState<React.Key[]>([]);

  // CC-09/CC-10: chart tabs — prior-report summaries and the patient's
  // RIS orders, composed from existing endpoints (no new aggregate).
  const [priors, setPriors] = useState<any[]>([]);
  const [orders, setOrders] = useState<any[]>([]);

  const navigate = useNavigate();
  const { id: patientId } = useParams();

  const fetchPatient = () => {
    setLoading(true);
    setError(null);
    getPatient(patientId as string)
      .then((res: any) => {
        setLoading(false);
        setData(res);
        if (res.studies) {
          setExpandedKeys(res.studies.map((s: any) => `study-${s.id}`));
        }
      })
      .catch((e: any) => {
        setLoading(false);
        setError(e.message);
      });
  };

  useEffect(() => {
    if (patientId) fetchPatient();
  }, [patientId]);

  useEffect(() => {
    if (!patientId) return;
    const q = new URLSearchParams({
      patient_id: String(patientId),
      exclude_exam_id: "",
    });
    request(`reports/priors?${q.toString()}`)
      .then((res: any) => setPriors(Array.isArray(res.data) ? res.data : []))
      .catch(() => {});
    // Orders tab uses the RIS order list's patient filter.
    request("ris/orders", { query: { patient: String(patientId) } })
      .then((res: any) =>
        setOrders(Array.isArray(res?.data) ? res.data : res?.data?.data || []),
      )
      .catch(() => {});
  }, [patientId]);

  const stats = useMemo(() => {
    const studies = data.studies || [];
    const seriesCount = studies.reduce(
      (acc: number, s: any) => acc + (s.series?.length || 0),
      0,
    );
    const fileCount = studies.reduce(
      (acc: number, s: any) =>
        acc +
        (s.series?.reduce(
          (a: number, sr: any) => a + (sr.files?.length || 0),
          0,
        ) || 0),
      0,
    );
    return { studyCount: studies.length, seriesCount, fileCount };
  }, [data]);

  const treeData = useMemo(() => {
    const studies = data.studies || [];
    return studies.map((s: any) => ({
      key: `study-${s.id}`,
      icon: <ExperimentOutlined />,
      title: (
        <Space size={12}>
          <Text strong>
            {s.study_id || s.study_instance_uid?.slice(0, 20) || "Study"}
          </Text>
          {s.description && <Text type="secondary">{s.description}</Text>}
          {s.accession_number && (
            <Tag style={{ fontSize: 10 }}>{s.accession_number}</Tag>
          )}
          <Text type="secondary" style={{ fontSize: 11 }}>
            {s.series?.length || 0} series
          </Text>
        </Space>
      ),
      children: (s.series || []).map((sr: any) => ({
        key: `series-${sr.id}`,
        icon: <MedicineBoxOutlined />,
        title: (
          <Space size={8}>
            <Tag color="blue" style={{ fontSize: 10 }}>
              {sr.modality || "?"}
            </Tag>
            <Text>{sr.number ? `#${sr.number}` : ""}</Text>
            {sr.description && <Text type="secondary">{sr.description}</Text>}
            <Text type="secondary" style={{ fontSize: 11 }}>
              {sr.files?.length || 0} files
            </Text>
          </Space>
        ),
        children: (sr.files || []).map((f: any) => ({
          key: `file-${f.id}`,
          icon: <FileOutlined />,
          isLeaf: true,
          title: (
            <a
              onClick={(e) => {
                e.stopPropagation();
                navigate(`/files/${f.id}`);
              }}
            >
              <Space size={4}>
                <Text>
                  {f.name || f.sop_instance_uid?.slice(0, 20) || "File"}
                </Text>
                {f.indexed ? (
                  <Tag color="green" style={{ fontSize: 9 }}>
                    indexed
                  </Tag>
                ) : (
                  <Tag style={{ fontSize: 9 }}>pending</Tag>
                )}
              </Space>
            </a>
          ),
        })),
      })),
    }));
  }, [data]);

  return (
    <Content style={{ padding: 32 }}>
      <PageState
        loading={loading}
        error={error}
        onRetry={fetchPatient}
        empty={!loading && !error && !data.patient_id}
        emptyMessage="Patient not found"
      >
        <Spin spinning={loading}>
          <Card style={{ marginBottom: 16 }}>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "flex-start",
                marginBottom: 16,
              }}
            >
              <div>
                <Title level={4} style={{ margin: 0 }}>
                  <UserOutlined style={{ marginRight: 8 }} />
                  {data.name || "Unknown"}
                </Title>
                {data.patient_id && (
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    Patient ID: {data.patient_id}
                  </Text>
                )}
              </div>
              <Space size={16}>
                <Badge count={stats.studyCount} showZero>
                  <Tag
                    icon={<ExperimentOutlined />}
                    style={{ padding: "2px 8px" }}
                  >
                    Studies
                  </Tag>
                </Badge>
                <Badge count={stats.seriesCount} showZero>
                  <Tag
                    icon={<MedicineBoxOutlined />}
                    style={{ padding: "2px 8px" }}
                  >
                    Series
                  </Tag>
                </Badge>
                <Badge count={stats.fileCount} showZero>
                  <Tag icon={<FileOutlined />} style={{ padding: "2px 8px" }}>
                    Files
                  </Tag>
                </Badge>
              </Space>
            </div>
            <Descriptions size="small" column={3}>
              <Descriptions.Item label="Patient ID">
                {data.patient_id || "-"}
              </Descriptions.Item>
              <Descriptions.Item label="Name">
                {data.name || "-"}
              </Descriptions.Item>
              <Descriptions.Item label="Sex">
                {data.sex ? (
                  <Tag>
                    {data.sex === "M"
                      ? "Male"
                      : data.sex === "F"
                        ? "Female"
                        : data.sex}
                  </Tag>
                ) : (
                  "-"
                )}
              </Descriptions.Item>
              <Descriptions.Item label="Date of Birth">
                {data.birth_date || "-"}
              </Descriptions.Item>
              <Descriptions.Item label="Internal ID">
                <Text copyable style={{ fontSize: 12 }}>
                  {data.id}
                </Text>
              </Descriptions.Item>
            </Descriptions>
          </Card>

          {canReadReports && (
            <Tabs
              defaultActiveKey="reports"
              items={[
                {
                  key: "reports",
                  label: "Reports",
                  children: (
                    <>
                      {/* CC-10: signed-report summaries (impression +
                          recommendations excerpts) with click-through to the
                          reading console for the full report. */}
                      <Card
                        title={
                          <span>
                            <FileDoneOutlined style={{ marginRight: 8 }} />
                            Report Summaries
                          </span>
                        }
                        style={{ marginBottom: 16 }}
                      >
                        {priors.length === 0 ? (
                          <Empty description="No prior reports yet" />
                        ) : (
                          priors.map((p: any) => (
                            <Card
                              key={p.report_id}
                              type="inner"
                              size="small"
                              title={`${p.accession_number || p.exam_id} · ${p.modality || ""}`}
                              extra={
                                <a
                                  href={`/reading/${p.exam_id}`}
                                  aria-label={`Open report ${p.accession_number || p.exam_id}`}
                                >
                                  Open full report
                                </a>
                              }
                              style={{ marginBottom: 8 }}
                            >
                              <p style={{ margin: "4px 0", fontSize: 13 }}>
                                <strong>Impression:</strong>{" "}
                                {p.impression_excerpt || "—"}
                              </p>
                              <p style={{ margin: "4px 0", fontSize: 13 }}>
                                <strong>Recommendations:</strong>{" "}
                                {p.recommendations_excerpt || "—"}
                              </p>
                            </Card>
                          ))
                        )}
                      </Card>

                      <Card
                        title={
                          <span>
                            <FileDoneOutlined style={{ marginRight: 8 }} />
                            Reports & Results
                          </span>
                        }
                        style={{ marginBottom: 16 }}
                      >
                        {(data.reports || []).length === 0 ? (
                          <Empty description="No reports yet" />
                        ) : (
                          <table style={{ width: "100%", borderCollapse: "collapse" }}>
                            <thead>
                              <tr>
                                {["Status", "Procedure", "Accession", "Date"].map((h) => (
                                  <th
                                    key={h}
                                    style={{
                                      textAlign: "left",
                                      fontSize: 12,
                                      color: "var(--color-secondary)",
                                      padding: "6px 8px",
                                    }}
                                  >
                                    {h}
                                  </th>
                                ))}
                              </tr>
                            </thead>
                            <tbody>
                              {(data.reports as any[]).map((r: any) => (
                                <tr
                                  key={r.id}
                                  style={{
                                    borderTop: "1px solid var(--color-slate-200)",
                                  }}
                                >
                                  <td style={{ padding: "6px 8px" }}>
                                    <Tag
                                      color={REPORT_STATUS_COLORS[r.status] ?? "default"}
                                    >
                                      {REPORT_STATUS_LABEL[r.status] ?? r.status}
                                    </Tag>
                                  </td>
                                  <td style={{ padding: "6px 8px", fontSize: 13 }}>
                                    {r.procedure_desc || r.modality || "—"}
                                  </td>
                                  <td style={{ padding: "6px 8px", fontSize: 12 }}>
                                    {r.accession_number || "—"}
                                  </td>
                                  <td style={{ padding: "6px 8px", fontSize: 12 }}>
                                    {r.signed_at || r.created_at
                                      ? new Date(
                                          r.signed_at || r.created_at,
                                        ).toLocaleDateString()
                                      : "—"}
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        )}
                      </Card>
                    </>
                  ),
                },
                {
                  key: "orders",
                  label: "Orders",
                  children: (
                    <Card
                      title={
                        <span>
                          <CalendarOutlined style={{ marginRight: 8 }} />
                          Orders
                        </span>
                      }
                    >
                      {orders.length === 0 ? (
                        <Empty description="No RIS orders for this patient" />
                      ) : (
                        <table style={{ width: "100%", borderCollapse: "collapse" }}>
                          <thead>
                            <tr>
                              {["Accession", "Status", "Priority", "Referring"].map(
                                (h) => (
                                  <th
                                    key={h}
                                    style={{
                                      textAlign: "left",
                                      fontSize: 12,
                                      color: "var(--color-secondary)",
                                      padding: "6px 8px",
                                    }}
                                  >
                                    {h}
                                  </th>
                                ),
                              )}
                            </tr>
                          </thead>
                          <tbody>
                            {orders.map((o: any) => (
                              <tr
                                key={o.id}
                                style={{
                                  borderTop: "1px solid var(--color-slate-200)",
                                }}
                              >
                                <td style={{ padding: "6px 8px", fontSize: 13 }}>
                                  {o.accession_number || "—"}
                                </td>
                                <td style={{ padding: "6px 8px" }}>
                                  <Tag>{o.status || "—"}</Tag>
                                </td>
                                <td style={{ padding: "6px 8px", fontSize: 12 }}>
                                  {o.priority || "—"}
                                </td>
                                <td style={{ padding: "6px 8px", fontSize: 12 }}>
                                  {o.referring_md || o.referring_physician || "—"}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      )}
                    </Card>
                  ),
                },
                {
                  key: "studies",
                  label: "Studies",
                  children: (
                    <Card
                      title={
                        <span>
                          <FolderOutlined style={{ marginRight: 8 }} />
                          Studies
                        </span>
                      }
                    >
                      {treeData.length === 0 ? (
                        <Empty description="No studies found for this patient" />
                      ) : (
                        <Tree
                          showIcon
                          defaultExpandAll
                          treeData={treeData}
                          expandedKeys={expandedKeys}
                          onExpand={setExpandedKeys}
                        />
                      )}
                    </Card>
                  ),
                },
              ]}
            />
          )}

          {!canReadReports && (
            <Card
              title={
                <span>
                  <FolderOutlined style={{ marginRight: 8 }} />
                  Studies
                </span>
              }
            >
              {treeData.length === 0 ? (
                <Empty description="No studies found for this patient" />
              ) : (
                <Tree
                  showIcon
                  defaultExpandAll
                  treeData={treeData}
                  expandedKeys={expandedKeys}
                  onExpand={setExpandedKeys}
                />
              )}
            </Card>
          )}
        </Spin>
      </PageState>
    </Content>
  );
}

export default withSidebar(Patient);
