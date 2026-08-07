import React, { useState } from "react";
import { Card, Table, Input, Button, Space, message, App, Tag } from "antd";
import {
  SearchOutlined,
  ReloadOutlined,
  DownloadOutlined,
  InboxOutlined,
} from "@ant-design/icons";
import {
  searchStudies,
  getSeries,
  getInstances,
  wadoRsUrl,
  downloadStudyArchive,
  Study,
  Series,
  Instance,
} from "../api/studies";

interface StudyBrowserProps {
  onSelectInstance?: (wadoRsUrl: string) => void;
}

export default function StudyBrowser({ onSelectInstance }: StudyBrowserProps) {
  const { message } = App.useApp();
  const [query, setQuery] = useState("");
  const [studies, setStudies] = useState<Study[]>([]);
  const [series, setSeries] = useState<Series[]>([]);
  const [instances, setInstances] = useState<Instance[]>([]);
  const [selectedStudy, setSelectedStudy] = useState<string | null>(null);
  const [selectedSeries, setSelectedSeries] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState<string | null>(null);

  const handleExport = async (studyUid: string) => {
    setExporting(studyUid);
    try {
      await downloadStudyArchive(studyUid);
      message.success("Archive downloaded");
    } catch (e: any) {
      message.error(e.message);
    } finally {
      setExporting(null);
    }
  };

  const handleSearch = async () => {
    setLoading(true);
    try {
      const q: Record<string, string> = {};
      if (query) q.PatientID = query;
      const results = await searchStudies(query ? q : undefined);
      setStudies(results);
      setSeries([]);
      setInstances([]);
      setSelectedStudy(null);
      setSelectedSeries(null);
    } catch (e: any) {
      message.error(e.message);
    }
    setLoading(false);
  };

  const handleSelectStudy = async (studyUid: string) => {
    setSelectedStudy(studyUid);
    setSelectedSeries(null);
    setInstances([]);
    setLoading(true);
    try {
      const results = await getSeries(studyUid);
      setSeries(results);
    } catch (e: any) {
      message.error(e.message);
    }
    setLoading(false);
  };

  const handleSelectSeries = async (studyUid: string, seriesUid: string) => {
    setSelectedSeries(seriesUid);
    setLoading(true);
    try {
      const results = await getInstances(studyUid, seriesUid);
      setInstances(results);
    } catch (e: any) {
      message.error(e.message);
    }
    setLoading(false);
  };

  return (
    <Card title="DICOMweb Study Browser" style={{ margin: 16 }}>
      <Space style={{ marginBottom: 16 }}>
        <Input
          placeholder="Patient ID"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onPressEnter={handleSearch}
        />
        <Button
          icon={<SearchOutlined />}
          onClick={handleSearch}
          loading={loading}
        >
          Search
        </Button>
        <Button
          icon={<ReloadOutlined />}
          onClick={() => {
            setQuery("");
            setStudies([]);
            setSeries([]);
            setInstances([]);
          }}
        >
          Clear
        </Button>
      </Space>

      <Table
        dataSource={studies}
        rowKey="studyInstanceUid"
        size="small"
        pagination={{ pageSize: 5 }}
        onRow={(record) => ({
          onClick: () => handleSelectStudy(record.studyInstanceUid),
          style: {
            cursor: "pointer",
            background:
              selectedStudy === record.studyInstanceUid ? "#e6f4ff" : undefined,
          },
        })}
        columns={[
          {
            title: "Study UID",
            dataIndex: "studyInstanceUid",
            key: "studyInstanceUid",
            ellipsis: true,
          },
          { title: "Patient", dataIndex: "patientName", key: "patientName" },
          {
            title: "Description",
            dataIndex: "studyDescription",
            key: "studyDescription",
            ellipsis: true,
          },
          {
            title: "Modality",
            dataIndex: "modalities",
            key: "modalities",
            width: 100,
          },
          {
            title: "Date",
            dataIndex: "studyDate",
            key: "studyDate",
            width: 100,
          },
          {
            title: "",
            key: "actions",
            width: 100,
            render: (_: unknown, record: Study) => (
              <Button
                size="small"
                icon={<DownloadOutlined />}
                loading={exporting === record.studyInstanceUid}
                onClick={(e) => {
                  e.stopPropagation();
                  handleExport(record.studyInstanceUid);
                }}
              >
                Export ZIP
              </Button>
            ),
          },
        ]}
      />

      {selectedStudy && series.length === 0 && !loading && (
        <Tag icon={<InboxOutlined />} color="default" style={{ marginTop: 12 }}>
          No series in this study
        </Tag>
      )}

      {selectedStudy && (
        <Table
          dataSource={series}
          rowKey="seriesInstanceUid"
          size="small"
          pagination={{ pageSize: 5 }}
          style={{ marginTop: 16 }}
          onRow={(record) => ({
            onClick: () =>
              handleSelectSeries(selectedStudy, record.seriesInstanceUid),
            style: {
              cursor: "pointer",
              background:
                selectedSeries === record.seriesInstanceUid
                  ? "#e6f4ff"
                  : undefined,
            },
          })}
          columns={[
            {
              title: "Series UID",
              dataIndex: "seriesInstanceUid",
              key: "seriesInstanceUid",
              ellipsis: true,
            },
            {
              title: "Number",
              dataIndex: "seriesNumber",
              key: "seriesNumber",
              width: 80,
            },
            {
              title: "Modality",
              dataIndex: "modality",
              key: "modality",
              width: 100,
            },
            {
              title: "Description",
              dataIndex: "seriesDescription",
              key: "seriesDescription",
              ellipsis: true,
            },
            {
              title: "Instances",
              dataIndex: "numberOfInstances",
              key: "numberOfInstances",
              width: 90,
            },
          ]}
        />
      )}

      {selectedStudy && selectedSeries && instances.length > 0 && (
        <Table
          dataSource={instances}
          rowKey="sopInstanceUid"
          size="small"
          pagination={{ pageSize: 10 }}
          style={{ marginTop: 16 }}
          columns={[
            {
              title: "SOP UID",
              dataIndex: "sopInstanceUid",
              key: "sopInstanceUid",
              ellipsis: true,
            },
            {
              title: "Instance #",
              dataIndex: "instanceNumber",
              key: "instanceNumber",
              width: 100,
            },
          ]}
        />
      )}
    </Card>
  );
}
