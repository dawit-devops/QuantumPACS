import React from "react";
import { Modal, Descriptions, Card, Table, Button } from "antd";
import { StatusBadge } from "./StatusBadge";

interface DetailModalProps {
  detail: any;
  onClose: () => void;
}

export function DetailModal({ detail, onClose }: DetailModalProps) {
  return (
    <Modal
      title="HL7 Message Detail"
      open={!!detail}
      onCancel={onClose}
      width={720}
      footer={<Button onClick={onClose}>Close</Button>}
    >
      {detail && (
        <div>
          <Descriptions column={2} size="small" bordered>
            <Descriptions.Item label="Type">
              {detail.message_type}-{detail.event_type}
            </Descriptions.Item>
            <Descriptions.Item label="Status">
              <StatusBadge status={detail.parse_status} />
            </Descriptions.Item>
            <Descriptions.Item label="Patient ID">
              {detail.patient_id || "-"}
            </Descriptions.Item>
            <Descriptions.Item label="Accession">
              {detail.accession_number || "-"}
            </Descriptions.Item>
            <Descriptions.Item label="Facility">
              {detail.sending_facility || "-"}
            </Descriptions.Item>
            <Descriptions.Item label="Time">
              {new Date(detail.created_at).toLocaleString()}
            </Descriptions.Item>
          </Descriptions>
          {detail.error_message && (
            <Card size="small" title="Error" style={{ marginTop: 12 }}>
              <pre style={{ color: "red", margin: 0, whiteSpace: "pre-wrap" }}>
                {detail.error_message}
              </pre>
            </Card>
          )}
          <Card size="small" title="Parsed Fields" style={{ marginTop: 12 }}>
            <pre
              style={{
                margin: 0,
                maxHeight: 200,
                overflow: "auto",
                fontSize: 12,
              }}
            >
              {JSON.stringify(detail.parsed_fields, null, 2)}
            </pre>
          </Card>
          <Card size="small" title="Raw Content" style={{ marginTop: 12 }}>
            <pre
              style={{
                margin: 0,
                maxHeight: 300,
                overflow: "auto",
                fontSize: 11,
                whiteSpace: "pre-wrap",
              }}
            >
              {detail.raw_content}
            </pre>
          </Card>
          {detail.errors?.length > 0 && (
            <Card size="small" title="Parse Errors" style={{ marginTop: 12 }}>
              <Table
                dataSource={detail.errors}
                columns={[
                  { title: "Segment", dataIndex: "segment", key: "segment" },
                  {
                    title: "Field",
                    dataIndex: "field_name",
                    key: "field_name",
                  },
                  {
                    title: "Raw Value",
                    dataIndex: "raw_value",
                    key: "raw_value",
                  },
                  {
                    title: "Error",
                    dataIndex: "error_message",
                    key: "error_message",
                  },
                ]}
                rowKey="id"
                pagination={false}
                size="small"
              />
            </Card>
          )}
        </div>
      )}
    </Modal>
  );
}
