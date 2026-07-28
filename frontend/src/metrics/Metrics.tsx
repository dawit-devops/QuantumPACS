import React, { useState, useEffect } from 'react';
import { Layout, Card, Col, Row, Statistic, Table, message, Tag } from 'antd';
import { DatabaseOutlined, TeamOutlined, FileOutlined, HddOutlined, FolderOutlined, ExperimentOutlined, CheckCircleOutlined, WarningOutlined, CloseCircleOutlined } from '@ant-design/icons';
import { Bar, Line } from 'react-chartjs-2';
import { Chart as ChartJS, CategoryScale, LinearScale, BarElement, PointElement, LineElement, Title, Tooltip, Legend } from 'chart.js';
import withSidebar from '../common/base';
import { request } from '../helpers';
import './Metrics.css';
import { MetricsSkeleton } from './MetricsSkeleton';

ChartJS.register(CategoryScale, LinearScale, BarElement, PointElement, LineElement, Title, Tooltip, Legend);

const Content = Layout.Content;

const CHART_OPTIONS = {
  responsive: true,
  plugins: { legend: { display: false } },
};

function healthColor(status: string): string {
  if (status === 'ok') return 'green';
  if (status === 'degraded') return 'orange';
  return 'red';
}

function healthIcon(status: string) {
  if (status === 'ok') return <CheckCircleOutlined />;
  if (status === 'degraded') return <WarningOutlined />;
  return <CloseCircleOutlined />;
}

function Metrics() {
  document.title = 'QuantumPACS - Metrics';

  let [data, setData] = useState<any>(null);
  let [health, setHealth] = useState<any>(null);
  let [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      request('v2/dashboard/metrics'),
      request('v2/health').catch(() => null),
    ]).then(([metricsResp, healthResp]) => {
      setData(metricsResp);
      setHealth(healthResp);
      setLoading(false);
    }).catch((e: any) => {
      message.error(e.message);
      setLoading(false);
    });
  }, []);

  if (loading) {
    return <MetricsSkeleton />;
  }

  const totals = data?.totals || {};
  const modalities = data?.modalities || {};
  const ingestion30d = data?.ingestion_30d || [];
  const latestFiles = data?.latest_files || [];

  const modalityLabels = Object.keys(modalities);
  const modalityValues = Object.values(modalities) as number[];

  const modalityChartData = {
    labels: modalityLabels,
    datasets: [{ data: modalityValues, backgroundColor: ['#1677ff', '#52c41a', '#faad14', '#ff4d4f', '#722ed1', '#13c2c2'] }],
  };

  const ingestionLabels = ingestion30d.map((d: any) => d.date);
  const ingestionValues = ingestion30d.map((d: any) => d.count);

  const ingestionChartData = {
    labels: ingestionLabels,
    datasets: [{ data: ingestionValues, borderColor: '#1677ff', backgroundColor: 'rgba(22,119,255,0.1)', fill: true, tension: 0.3 }],
  };

  const components = health?.components || {};

  return (
    <Content style={{ padding: 24 }}>
      <Row gutter={[16, 16]}>
        <Col xs={12} sm={8} lg={4}>
          <Card><Statistic title="Patients" value={totals.patients} prefix={<TeamOutlined />} /></Card>
        </Col>
        <Col xs={12} sm={8} lg={4}>
          <Card><Statistic title="Studies" value={totals.studies} prefix={<FolderOutlined />} /></Card>
        </Col>
        <Col xs={12} sm={8} lg={4}>
          <Card><Statistic title="Series" value={totals.series} prefix={<ExperimentOutlined />} /></Card>
        </Col>
        <Col xs={12} sm={8} lg={4}>
          <Card><Statistic title="Files" value={totals.files} prefix={<FileOutlined />} /></Card>
        </Col>
        <Col xs={12} sm={8} lg={4}>
          <Card><Statistic title="Users" value={totals.users} prefix={<TeamOutlined />} /></Card>
        </Col>
        <Col xs={12} sm={8} lg={4}>
          <Card><Statistic title="Storage" value={formatBytes(totals.storage_bytes)} prefix={<HddOutlined />} /></Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 24 }}>
        <Col xs={24} md={8}>
          <Card title="System Health">
            {Object.entries(components).length > 0 ? (
              Object.entries(components).map(([name, comp]: [string, any]) => (
                <div key={name} style={{ marginBottom: 8, display: 'flex', alignItems: 'center', gap: 8 }}>
                  {healthIcon(comp.status)}
                  <span style={{ flex: 1, fontWeight: 500 }}>{labelName(name)}</span>
                  <Tag color={healthColor(comp.status)}>{comp.status.toUpperCase()}</Tag>
                </div>
              ))
            ) : (
              <Tag color="green">OK</Tag>
            )}
          </Card>
        </Col>
        <Col xs={24} md={16}>
          <Card title="Modality Distribution">
            <Bar data={modalityChartData} options={CHART_OPTIONS} />
          </Card>
          <Card title="Component Latency" style={{ marginTop: 16 }}>
            {Object.entries(components).length > 0 ? (
              <Bar
                data={{
                  labels: Object.keys(components).map(labelName),
                  datasets: [{
                    label: 'Latency (ms)',
                    data: Object.values(components).map((c: any) => c.latency_ms || 0),
                    backgroundColor: Object.values(components).map((c: any) => {
                      if (c.status === 'ok') return '#52c41a';
                      if (c.status === 'degraded') return '#faad14';
                      return '#ff4d4f';
                    }),
                  }],
                }}
                options={{
                  ...CHART_OPTIONS,
                  indexAxis: 'y',
                  scales: {
                    x: { title: { display: true, text: 'ms' } },
                  },
                }}
              />
            ) : (
              <Tag color="green">OK</Tag>
            )}
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} md={12}>
          <Card title="Ingestion (30 days)">
            <Line data={ingestionChartData} options={CHART_OPTIONS} />
          </Card>
        </Col>
        <Col xs={24} md={12}>
          <Card title="Latest Files">
            <Table
              dataSource={latestFiles}
              columns={[
                { title: 'ID', dataIndex: 'id', key: 'id' },
                { title: 'Name', dataIndex: 'name', key: 'name' },
                { title: 'Created', dataIndex: 'created', key: 'created' },
              ]}
              pagination={false}
              size="small"
            />
          </Card>
        </Col>
      </Row>
    </Content>
  );
}

function labelName(key: string): string {
  const map: Record<string, string> = {
    database: 'Database',
    elasticsearch: 'Elasticsearch',
    redis: 'Redis',
    storage: 'Storage',
    dicom_listener: 'DICOM Listener',
    ingestion_service: 'Ingestion Service',
  };
  return map[key] || key;
}

function formatBytes(bytes: number): string {
  if (!bytes) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  let i = 0;
  let val = bytes;
  while (val >= 1024 && i < units.length - 1) {
    val /= 1024;
    i++;
  }
  return `${val.toFixed(1)} ${units[i]}`;
}

export default withSidebar(Metrics);