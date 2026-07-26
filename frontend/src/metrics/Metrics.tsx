import React, { useState, useEffect } from 'react';
import { Layout, Card, Col, Row, Statistic, Table, Spin, message } from 'antd';
import { DatabaseOutlined, TeamOutlined, FileOutlined, HddOutlined, FolderOutlined, ExperimentOutlined } from '@ant-design/icons';
import withSidebar from '../common/base';
import { request } from '../helpers';
import './Metrics.css';

const Content = Layout.Content;

function Metrics() {
  document.title = 'QuantumPACS - Metrics';

  let [data, setData] = useState<any>(null);
  let [loading, setLoading] = useState(true);

  useEffect(() => {
    request('v2/dashboard/metrics').then((resp: any) => {
      setData(resp);
      setLoading(false);
    }).catch((e: any) => {
      message.error(e.message);
      setLoading(false);
    });
  }, []);

  if (loading) {
    return (
      <Content style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <Spin size="large" data-testid="metrics-loading" />
      </Content>
    );
  }

  const totals = data?.totals || {};
  const modalities = data?.modalities || {};
  const ingestion30d = data?.ingestion_30d || [];
  const latestFiles = data?.latest_files || [];

  const modalityData = Object.entries(modalities).map(([modality, count]) => ({
    key: modality,
    modality,
    count,
  }));

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
        <Col xs={24} md={12}>
          <Card title="Modality Distribution">
            <Table
              dataSource={modalityData}
              columns={[
                { title: 'Modality', dataIndex: 'modality', key: 'modality' },
                { title: 'Count', dataIndex: 'count', key: 'count' },
              ]}
              pagination={false}
              size="small"
            />
          </Card>
        </Col>
        <Col xs={24} md={12}>
          <Card title="Recent Ingestion (30 days)">
            <Table
              dataSource={ingestion30d}
              columns={[
                { title: 'Date', dataIndex: 'date', key: 'date' },
                { title: 'Files', dataIndex: 'count', key: 'count' },
              ]}
              pagination={false}
              size="small"
            />
          </Card>
        </Col>
      </Row>

      <Row style={{ marginTop: 16 }}>
        <Col span={24}>
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
