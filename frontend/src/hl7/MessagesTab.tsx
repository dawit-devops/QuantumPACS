import React from "react";
import { Table, Tag, Button, Select, Input, Space } from "antd";
import { ReloadOutlined, SearchOutlined } from "@ant-design/icons";
import { StatusBadge } from "./StatusBadge";

interface MessagesTabProps {
  messages: any[];
  total: number;
  loading: boolean;
  error: string | null;
  msgFilter: string;
  setMsgFilter: (v: string) => void;
  statusFilter: string;
  setStatusFilter: (v: string) => void;
  patientFilter: string;
  setPatientFilter: (v: string) => void;
  facilityFilter: string;
  setFacilityFilter: (v: string) => void;
  limit: number;
  offset: number;
  setOffset: (v: number) => void;
  fetchMessages: () => void;
  onViewDetail: (id: string) => void;
}

export function MessagesTab({
  messages,
  total,
  loading,
  error,
  msgFilter,
  setMsgFilter,
  statusFilter,
  setStatusFilter,
  patientFilter,
  setPatientFilter,
  facilityFilter,
  setFacilityFilter,
  limit,
  offset,
  setOffset,
  fetchMessages,
  onViewDetail,
}: MessagesTabProps) {
  const columns = [
    {
      title: "Time",
      dataIndex: "created_at",
      key: "created_at",
      render: (t: string) => new Date(t).toLocaleString(),
      width: 160,
    },
    {
      title: "Type",
      key: "type",
      width: 140,
      render: (_: any, r: any) => (
        <Tag>
          {r.message_type}
          {r.event_type ? `-${r.event_type}` : ""}
        </Tag>
      ),
    },
    {
      title: "Patient ID",
      dataIndex: "patient_id",
      key: "patient_id",
      width: 120,
    },
    {
      title: "Accession",
      dataIndex: "accession_number",
      key: "accession_number",
      width: 120,
    },
    {
      title: "Facility",
      dataIndex: "sending_facility",
      key: "sending_facility",
      width: 120,
    },
    {
      title: "Status",
      dataIndex: "parse_status",
      key: "parse_status",
      render: (s: string) => <StatusBadge status={s} />,
      width: 90,
    },
    {
      title: "Actions",
      key: "actions",
      width: 80,
      render: (_: any, r: any) => (
        <Button size="small" onClick={() => onViewDetail(r.id)}>
          View
        </Button>
      ),
    },
  ];

  return (
    <div>
      <Space style={{ marginBottom: 12 }} wrap>
        <Select
          value={msgFilter}
          onChange={(v) => {
            setMsgFilter(v);
            setOffset(0);
          }}
          allowClear
          placeholder="Message Type"
          style={{ width: 150 }}
          options={[
            { value: "", label: "All Types" },
            { value: "ADT", label: "ADT" },
            { value: "ORM", label: "ORM" },
          ]}
        />
        <Select
          value={statusFilter}
          onChange={(v) => {
            setStatusFilter(v);
            setOffset(0);
          }}
          allowClear
          placeholder="Status"
          style={{ width: 130 }}
          options={[
            { value: "", label: "All Status" },
            { value: "ok", label: "Parsed OK" },
            { value: "partial", label: "Partial" },
            { value: "failed", label: "Failed" },
          ]}
        />
        <Input
          placeholder="Patient ID"
          value={patientFilter}
          onChange={(e) => setPatientFilter(e.target.value)}
          onPressEnter={() => setOffset(0)}
          style={{ width: 150 }}
          prefix={<SearchOutlined />}
          allowClear
        />
        <Input
          placeholder="Facility"
          value={facilityFilter}
          onChange={(e) => setFacilityFilter(e.target.value)}
          onPressEnter={() => setOffset(0)}
          style={{ width: 150 }}
          prefix={<SearchOutlined />}
          allowClear
        />
        <Button icon={<ReloadOutlined />} onClick={fetchMessages}>
          Refresh
        </Button>
        <span style={{ color: "var(--text-secondary)", fontSize: 12 }}>
          {total} messages
        </span>
      </Space>
      <Table
        dataSource={messages}
        columns={columns}
        rowKey="id"
        loading={loading && !error}
        size="small"
        pagination={{
          current: offset / limit + 1,
          pageSize: limit,
          total,
          onChange: (page) => setOffset((page - 1) * limit),
          showSizeChanger: false,
        }}
        locale={{ emptyText: "No HL7 messages received yet." }}
      />
    </div>
  );
}
