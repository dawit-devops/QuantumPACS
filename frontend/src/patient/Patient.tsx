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
} from "antd";
import {
  FolderOutlined,
  FileOutlined,
  ExperimentOutlined,
  CalendarOutlined,
  UserOutlined,
  MedicineBoxOutlined,
} from "@ant-design/icons";
import withSidebar from "../common/base";
import { getPatient, type PatientSummary } from "../api/patient";
import { PageState } from "../common/PageState";
import { useNavigate, useParams } from "react-router";

const { Text, Title } = Typography;
const Content = Layout.Content;

function Patient(props: any) {
  useDocumentTitle("QuantumPACS - Patient");

  const [data, setData] = useState<PatientSummary>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedKeys, setExpandedKeys] = useState<React.Key[]>([]);

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
        </Spin>
      </PageState>
    </Content>
  );
}

export default withSidebar(Patient);
